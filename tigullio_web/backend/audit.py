"""Tigullio audit with an atomic, embedded outbox on each changed document.

Only explicitly allowed business fields enter events. Password values, session
IDs, credential fingerprints and request bodies never enter the outbox or logs.
Delivery is idempotent; failed delivery leaves the event on its source document.
Deletes first atomically mark a document invisible with its deletion event, then
physically remove it only after all its events have reached the historical logs.
"""
from copy import deepcopy
from contextvars import ContextVar
from datetime import datetime
import logging
from uuid import uuid4

from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.results import DeleteResult, UpdateResult

OUTBOX = '_tigullio_audit_outbox'
DELETED = '_tigullio_deleted'
INTERNAL = {OUTBOX, DELETED}
logger = logging.getLogger(__name__)
operation_id = ContextVar('tigullio_operation_id', default=None)

FIELDS = {
    'Giocatore', 'Squadra', 'Potenziale', 'Ruolo', 'SetPwd',
    'NCampionatiVinti', 'listaCampionatiVinti', 'NGironiFFVinti', 'listaGironiFFVinti',
    'NFFElimDirettaVinte', 'listaFFElimDirettaVinte', 'nome_torneo',
    'turno_attivo', 'torneo_iniziato', 'torneo_finito', 'modalita_turni', 'max_turni',
    '_tigullio_closed', '_tigullio_withdrawals', '_tigullio_preliminary_id',
    '_tigullio_source_id', '_tigullio_return_matches',
}
ROW_FIELDS = {'Girone', 'Giornata', 'Turno', 'Round', 'Casa', 'Ospite', 'GolCasa',
              'GolOspite', 'Valida', 'Validata', 'Vincitore', 'GiocatoreCasa', 'GiocatoreOspite',
              'Giocatore', 'Squadra', 'Potenziale', 'source_id', 'name', 'team', 'potential', 'guest'}
BADGE_FIELDS = {'kind', 'ref', 'url', 'credit', 'license', 'config'}
CREST_FIELDS = {'schema_version', 'shape', 'primary', 'secondary', 'border', 'text',
                'title', 'initials', 'subtitle', 'year', 'icon', 'stripe', 'double_border'}


class VisibleCollection:
    """Normal application reads exclude committed deletions awaiting delivery."""
    def __init__(self, raw):
        self.raw = raw

    @staticmethod
    def visible(query):
        return {'$and': [query or {}, {DELETED: {'$exists': False}}]}

    def find(self, filter=None, *args, **kwargs):
        return self.raw.find(self.visible(filter), *args, **kwargs)

    def find_one(self, filter=None, *args, **kwargs):
        if filter is not None and not isinstance(filter, dict):
            filter = {'_id': filter}
        return self.raw.find_one(self.visible(filter), *args, **kwargs)

    def count_documents(self, filter, *args, **kwargs):
        return self.raw.count_documents(self.visible(filter), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self.raw, name)


def raw(collection):
    return collection.raw if isinstance(collection, VisibleCollection) else collection


def plain(value):
    if isinstance(value, ObjectId):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool, datetime)):
        return value
    if isinstance(value, list):
        return [plain(item) for item in value if not isinstance(item, dict)]
    return None


def badge(value):
    if not isinstance(value, dict):
        return None
    result = {k: plain(v) for k, v in value.items() if k in BADGE_FIELDS and k != 'config'}
    if isinstance(value.get('config'), dict):
        result['config'] = {k: plain(v) for k, v in value['config'].items() if k in CREST_FIELDS}
    return result


def snapshot(doc):
    doc = doc or {}
    result = {key: plain(value) for key, value in doc.items() if key in FIELDS}
    for key in ('calendario', 'df_torneo', 'df_squadre', '_tigullio_participants'):
        if isinstance(doc.get(key), list):
            result[key] = [{k: plain(v) for k, v in row.items() if k in ROW_FIELDS}
                           for row in doc[key] if isinstance(row, dict)]
    for key in ('_tigullio_badge', 'badge'):
        if key in doc:
            result[key] = badge(doc[key])
    if isinstance(doc.get('_tigullio_badges'), dict):
        result['_tigullio_badges'] = {str(k): badge(v) for k, v in doc['_tigullio_badges'].items()}
    for key in ('team', 'team_key'):
        if key in doc:
            result[key] = plain(doc[key])
    return result


def differences(before, after):
    before, after = snapshot(before), snapshot(after)
    changes = {}
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        if key in ('calendario', 'df_torneo'):
            old, new = old or [], new or []
            changes[key] = [{'index': i, 'before': old[i] if i < len(old) else None,
                             'after': new[i] if i < len(new) else None}
                            for i in range(max(len(old), len(new)))
                            if (old[i] if i < len(old) else None) != (new[i] if i < len(new) else None)]
        else:
            changes[key] = {'before': old, 'after': new}
    return changes


def event(user, action, collection, before=None, after=None, *, login=False, outcome=None, method=None):
    doc = after or before or {}
    name = str(doc.get('nome_torneo') or '')
    area = ('svizzero' if collection.name == 'TigullioSvizzero' else
            'finali' if name.removeprefix('finito_').removeprefix('completato_').startswith('fasefinale') else
            'italiana' if collection.name == 'Tigullio' else 'club')
    entry = {'_id': str(uuid4()), 'schema_version': 2, 'club': 'Tigullio', 'source': 'vercel',
             'timestamp': datetime.utcnow(), 'user_id': str(user.get('id') or ''),
             'username': str(user.get('username') or ''), 'area': 'auth' if login else area,
             'object_id': str(doc.get('_id') or ''), 'object_name': str(doc.get('Giocatore') or name or doc.get('team') or ''),
             'collection': collection.full_name}
    entry['operation_id'] = operation_id.get() or entry['_id']
    if login:
        entry.update(esito=outcome or 'Accesso riuscito', dettagli={'club': 'tigullio_players',
                     'ruolo': user.get('role', 'G'), 'method': method or 'password'})
    else:
        entry.update(action=action, torneo=name or 'gestione_giocatori',
                     details={'changes': differences(before, after)})
        if action in ('password_set', 'password_reset', 'password_change'):
            entry['details']['credential_event'] = {'password_set': 'impostata', 'password_reset': 'resettata', 'password_change': 'cambiata'}[action]
    return {'target': 'Login' if login else 'Actions', 'entry': entry}


def deliver(store, collection, document_id):
    """Never turn a committed write into an apparent failure on log outage."""
    collection = raw(collection)
    try:
        doc = collection.find_one({'_id': document_id}, {OUTBOX: 1, DELETED: 1})
        for item in (doc or {}).get(OUTBOX, []):
            entry = item['entry']
            store.log_db[item['target']].update_one({'_id': entry['_id']}, {'$setOnInsert': entry}, upsert=True)
            collection.update_one({'_id': document_id}, {'$pull': {OUTBOX: {'entry._id': entry['_id']}}})
        # Cleanup checks the current queue, including events appended concurrently.
        if (doc or {}).get(DELETED):
            collection.delete_one({'_id': document_id, DELETED: {'$exists': True}, OUTBOX: {'$size': 0}})
        if collection.full_name == store.sessions.full_name:
            current = collection.find_one({'_id': document_id, OUTBOX: {'$size': 0}}, {'valid_until': 1})
            if current and current.get('valid_until'):
                # The legacy expires_at TTL index must never delete pending events.
                collection.update_one({'_id': document_id, OUTBOX: {'$size': 0}}, {'$set': {'expires_at': current['valid_until']}})
        return True
    except PyMongoError:
        logger.warning('Tigullio audit delivery deferred; event remains in its persistent outbox.')
        return False


def pending_query(store, collection):
    cases = [{OUTBOX + '.0': {'$exists': True}}, {DELETED: {'$exists': True}}]
    if collection.full_name == store.sessions.full_name:
        cases.append({'valid_until': {'$exists': True}, 'expires_at': {'$exists': False}})
    return {'$or': cases}


def retry_pending(store, limit=100):
    checked, delivered = 0, 0
    if limit <= 0:
        return {'checked': 0, 'delivered_documents': 0}
    for collection in store.audit_sources:
        for doc in raw(collection).find(pending_query(store, collection), {'_id': 1}).limit(limit-checked):
            checked += 1
            if not deliver(store, collection, doc['_id']):
                return {'checked': checked, 'delivered_documents': delivered}
            delivered += 1
        if checked >= limit:
            break
    return {'checked': checked, 'delivered_documents': delivered}


def insert(store, user, collection, doc, action):
    doc.setdefault('_id', ObjectId())
    payload = deepcopy(doc)
    payload[OUTBOX] = [event(user, action, collection, after=doc)]
    result = collection.insert_one(payload)
    deliver(store, collection, doc['_id'])
    return result


def projected_update(before, update, inserting=False):
    after = deepcopy(before)
    after.update(deepcopy(update.get('$set', {})))
    if inserting:
        after.update(deepcopy(update.get('$setOnInsert', {})))
    for key, value in update.get('$inc', {}).items():
        after[key] = after.get(key, 0) + value
    for key, value in update.get('$addToSet', {}).items():
        values = after.setdefault(key, [])
        for item in value.get('$each', []) if isinstance(value, dict) else [value]:
            if item not in values:
                values.append(item)
    for key in update.get('$unset', {}):
        after.pop(key, None)
    return after


def update(store, user, collection, query, changes, action, *, upsert=False):
    # Match the business snapshot atomically, so before/after cannot describe a
    # stale read. Existing route guards still decide what a conflict means.
    for _ in range(3):
        before = collection.find_one(query)
        if before is None:
            if not upsert:
                return UpdateResult({'n': 0, 'nModified': 0}, True)
            initial = {k: v for k, v in query.items() if not k.startswith('$') and not isinstance(v, dict)}
            initial = projected_update(initial, changes, inserting=True)
            initial.setdefault('_id', ObjectId())
            initial[OUTBOX] = [event(user, action, collection, after=initial)]
            try:
                result = raw(collection).update_one(query, {'$setOnInsert': initial}, upsert=True)
            except DuplicateKeyError:
                # Deterministic IDs protect concurrent upserts without rewriting
                # or imposing an index migration on existing legacy records.
                continue
            if result.upserted_id is not None:
                deliver(store, collection, result.upserted_id)
                return result
            # Another request inserted the record. Re-read before logging an edit.
            continue
        after = projected_update(before, changes)
        entry = event(user, action, collection, before, after)
        sensitive_event = action in ('password_set', 'password_reset', 'password_change') and before.get('Password') != after.get('Password')
        payload = deepcopy(changes)
        if entry['entry']['details']['changes'] or sensitive_event:
            payload.setdefault('$push', {})[OUTBOX] = entry
        conditions = [{k: {'$eq': v, '$exists': True}} for k, v in before.items() if k not in INTERNAL and k != '_id']
        result = collection.update_one({'_id': before['_id'], '$and': [query, {DELETED: {'$exists': False}}, *conditions]}, payload)
        if result.matched_count:
            deliver(store, collection, before['_id'])
            return result
    return UpdateResult({'n': 0, 'nModified': 0}, True)


def delete(store, user, collection, query, action):
    before = collection.find_one(query)
    if not before:
        return DeleteResult({'n': 0}, True)
    payload = {'$set': {DELETED: datetime.utcnow()}, '$push': {OUTBOX: event(user, action, collection, before=before)}}
    conditions = [{k: {'$eq': v, '$exists': True}} for k, v in before.items() if k not in INTERNAL and k != '_id']
    result = collection.update_one({'_id': before['_id'], '$and': [query, {DELETED: {'$exists': False}}, *conditions]}, payload)
    if result.matched_count:
        deliver(store, collection, before['_id'])
    return DeleteResult({'n': result.matched_count}, True)


def record_login(store, user, outcome, method):
    # Failed attempts have no business document; the auth outbox is the source.
    item = event(user, 'login', store.sessions, login=True, outcome=outcome, method=method)
    ident = ObjectId()
    store.audit_queue.insert_one({'_id': ident, DELETED: datetime.utcnow(), OUTBOX: [item]})
    deliver(store, store.audit_queue, ident)
