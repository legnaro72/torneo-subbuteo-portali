import {useEffect, useMemo, useState} from 'react';
import {Search, X} from 'lucide-react';
import {CustomCrest, CustomCrestEditor, defaultCrest, type CrestConfig} from './CustomCrest';
import logoPaths from '../backend/football_logos_index.json';

export type TeamBadge = {kind:'none'}|{kind:'flag';ref:string}|{kind:'club';ref:string;url:string;credit?:string;license?:string}|{kind:'custom';config:CrestConfig};
export type BadgeMap = Record<string,TeamBadge>;

const codes = 'AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW'.split(' ');
const regionNames = new Intl.DisplayNames(['it'],{type:'region'});
const countries = codes.map(code=>({code,name:regionNames.of(code)||code})).sort((a,b)=>a.name.localeCompare(b.name,'it'));
const flagUrl=(code:string)=>`https://flagcdn.com/${code.toLowerCase()}.svg`;
const normalized=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLocaleLowerCase('it').trim();
const flagAliases:Record<string,string>={
  'olanda':'NL','eire':'IE','inghilterra':'GB-ENG','england':'GB-ENG',
  'scozia':'GB-SCT','scotland':'GB-SCT','galles':'GB-WLS','wales':'GB-WLS',
  'irlanda del nord':'GB-NIR','northern ireland':'GB-NIR',
};
const flagLabels:Record<string,string>={'GB-ENG':'Inghilterra','GB-SCT':'Scozia','GB-WLS':'Galles','GB-NIR':'Irlanda del Nord'};
const flagLabel=(code:string)=>flagLabels[code]||regionNames.of(code)||code;
function labelCandidates(name:string){
  const candidates=[name.trim()];
  for(let index=name.lastIndexOf('-');index>=0;index=name.lastIndexOf('-',index-1)){
    const team=name.slice(0,index).trim();
    if(team)candidates.push(team);
  }
  return candidates;
}
const clubKey=(value:string)=>normalized(value).replace(/[^a-z0-9]+/g,' ').replace(/^(?:ac|as|us|ssc|fc|cf|afc|cfc|sc)\s+/,'').replace(/\s+(?:ac|as|us|ssc|fc|cf|afc|cfc|sc)$/,'').trim();
const clubLogos=new Map<string,string[]>();
for(const path of logoPaths){
  const name=path.split('/').pop()?.replace(/\.svg$/,'').replace(/_/g,' ')||'';
  if(/(?:national team|league|liga|cup|division|serie [a-d])$/i.test(name))continue;
  const key=clubKey(name);
  clubLogos.set(key,[...(clubLogos.get(key)||[]),path]);
}
const clubAliases:Record<string,string>={
  'inter milano':'inter','bayern monaco':'bayern munchen',
  'paris saint germain':'paris saint germain psg',
};
export function automaticFlag(name:string):TeamBadge|undefined{
  const possible=labelCandidates(name);
  const alias=possible.map(team=>flagAliases[normalized(team)]).find(Boolean);
  if(alias)return {kind:'flag',ref:alias};
  const country=countries.find(item=>possible.some(team=>normalized(item.name)===normalized(team)));
  return country?{kind:'flag',ref:country.code}:undefined;
}

export function automaticClub(name:string):TeamBadge|undefined{
  for(const team of labelCandidates(name)){
    const key=clubAliases[clubKey(team)]||clubKey(team);
    const matches=clubLogos.get(key);
    if(matches?.length!==1)continue;
    const path=matches[0];
    return {kind:'club',ref:`football-logos:${path}`,url:`https://raw.githubusercontent.com/JoseArroyave/football-logos/main/${path.split('/').map(encodeURIComponent).join('/')}`,credit:'Jose Arroyave · football-logos',license:'MIT (repository)'};
  }
  return undefined;
}

export function automaticBadge(name:string):TeamBadge|undefined{
  return automaticFlag(name)||automaticClub(name);
}

export function TeamMark({name,badge}:{name:string;badge?:TeamBadge}){
  const [failed,setFailed]=useState(false);
  const shown=badge||automaticBadge(name);
  useEffect(()=>setFailed(false),[shown?.kind,shown?.kind==='flag'||shown?.kind==='club'?shown.ref:undefined,shown?.kind==='club'?shown.url:undefined]);
  if(shown?.kind==='custom')return <CustomCrest config={shown.config}/>;
  if(shown?.kind==='none')return <>{name.slice(0,1)}</>;
  const src=shown?.kind==='flag'?flagUrl(shown.ref):shown?.kind==='club'?shown.url:undefined;
  return src&&!failed?<img className={'team-badge '+shown?.kind} src={src} alt={shown?.kind==='flag'?`Bandiera ${flagLabel(shown.ref)}`:`Immagine del club ${name}`} title={shown?.kind==='club'&&shown.credit?`${name} · ${shown.credit}${shown.license?` · ${shown.license}`:''}`:name} loading="lazy" referrerPolicy="no-referrer" onError={()=>setFailed(true)}/>:<>{name.slice(0,1)}</>;
}

type ClubResult={ref:string;name:string;description?:string;type:'logo'|'bandiera'|'stemma';source:string;url:string;credit:string;license:string};
function badgeSource(ref:string){
  if(ref.startsWith('File:'))return {url:`https://commons.wikimedia.org/wiki/${encodeURIComponent(ref.replace(/ /g,'_'))}`,label:'Fonte e licenza su Wikimedia Commons ↗'};
  if(ref.startsWith('football-logos:'))return {url:`https://github.com/JoseArroyave/football-logos/blob/main/${ref.slice('football-logos:'.length).split('/').map(encodeURIComponent).join('/')}`,label:'Archivio football-logos ↗'};
  if(ref.startsWith('sportmonks:'))return {url:'https://www.sportmonks.com/',label:'Fonte Sportmonks ↗'};
  return {url:'https://www.football-data.org/',label:'Fonte football-data.org ↗'};
}
async function searchClubLogos(query:string,signal:AbortSignal):Promise<ClubResult[]>{
  const response=await fetch(`/api/club-logos?q=${encodeURIComponent(query)}`,{signal,credentials:'same-origin'});
  if(!response.ok){const detail=await response.json().catch(()=>({}));throw new Error(detail.detail||'Ricerca stemmi non disponibile. Riprova.');}
  return response.json() as Promise<ClubResult[]>;
}

export function BadgeEditor({participants,badges,busy,error,initialSelected,onClose,onSave}:{participants:string[];badges:BadgeMap;busy:boolean;error?:string;initialSelected?:string;onClose:()=>void;onSave:(badges:BadgeMap)=>Promise<void>}){
  const [draft,setDraft]=useState<BadgeMap>({...badges});
  const [selected,setSelected]=useState(initialSelected&&participants.includes(initialSelected)?initialSelected:participants[0]||'');
  const [kind,setKind]=useState<TeamBadge['kind']>(draft[selected]?.kind||automaticBadge(selected)?.kind||'flag');
  const [flagQuery,setFlagQuery]=useState('');const [clubQuery,setClubQuery]=useState('');
  const [clubs,setClubs]=useState<ClubResult[]>([]);const [searchError,setSearchError]=useState('');const [searching,setSearching]=useState(false);
  const visibleCountries=useMemo(()=>countries.filter(c=>`${c.name} ${c.code}`.toLocaleLowerCase('it').includes(flagQuery.toLocaleLowerCase('it'))).slice(0,40),[flagQuery]);
  useEffect(()=>{
    if(kind!=='club'||clubQuery.trim().length<3){setClubs([]);setSearchError('');return;}
    const controller=new AbortController();const timer=window.setTimeout(()=>{
      setSearching(true);setSearchError('');searchClubLogos(clubQuery.trim(),controller.signal).then(setClubs).catch(e=>{if(!controller.signal.aborted)setSearchError(e instanceof Error?e.message:'Ricerca non riuscita.');}).finally(()=>{if(!controller.signal.aborted)setSearching(false);});
    },350);
    return()=>{window.clearTimeout(timer);controller.abort();};
  },[clubQuery,kind]);
  const current=draft[selected]||automaticBadge(selected);
  const invalidYear=Object.values(draft).some(badge=>badge.kind==='custom'&&badge.config.year!==''&&!/^(1[89]\d{2}|20\d{2})$/.test(badge.config.year));
  function choose(badge?:TeamBadge){setDraft(old=>{const next={...old};if(badge)next[selected]=badge;else delete next[selected];return next;});}
  function selectKind(next:TeamBadge['kind']){setKind(next);if(next==='none')choose({kind:'none'});if(next==='custom'&&draft[selected]?.kind!=='custom')choose({kind:'custom',config:defaultCrest(selected)});}
  return <div className="modal-backdrop"><section className="modal badge-modal" role="dialog" aria-modal="true" aria-label="Immagini Premium delle squadre">
    <div className="section-heading"><div><span className="eyebrow">VISTA PREMIUM</span><h2>🛡️ Bandiere e stemmi</h2><p>Le immagini compaiono solo nella vista Premium.</p></div><button aria-label="Chiudi" disabled={busy} onClick={onClose}><X/></button></div>
    <label>Partecipante<select value={selected} onChange={e=>{setSelected(e.target.value);setKind(draft[e.target.value]?.kind||automaticBadge(e.target.value)?.kind||'flag');}}>{participants.map(p=><option key={p}>{p}</option>)}</select></label>
    <div className="badge-current"><span className="team-mark"><TeamMark name={selected} badge={current}/></span><strong>{selected}</strong><span>{current?.kind==='flag'?`${flagLabel(current.ref)}${!draft[selected]?' · automatica':''}`:current?.kind==='club'?`${current.ref.replace(/^File:/,'').replace(/^football-logos:/,'')}${!draft[selected]?' · automatico':''}`:current?.kind==='custom'?'Stemma personalizzato':'Nessuna immagine'}</span><button type="button" className="secondary compact" disabled={busy} onClick={()=>selectKind('none')}>Nessuna immagine</button></div>
    {current?.kind==='club'&&<a className="badge-source-link" href={badgeSource(current.ref).url} target="_blank" rel="noopener noreferrer">{badgeSource(current.ref).label}</a>}
    <div className="segmented badge-tabs"><button type="button" className={kind==='none'?'active':''} onClick={()=>selectKind('none')}>Nessuna</button><button type="button" className={kind==='flag'?'active':''} onClick={()=>selectKind('flag')}>🏳️ Bandiera</button><button type="button" className={kind==='club'?'active':''} onClick={()=>selectKind('club')}>⚽ Club</button><button type="button" className={kind==='custom'?'active':''} onClick={()=>selectKind('custom')}>🎨 Crea stemma</button></div>
    {kind==='none'?<p>Nessuna immagine per questo partecipante, anche se il nome corrisponde a una nazione.</p>:kind==='custom'?<CustomCrestEditor value={current?.kind==='custom'?current.config:defaultCrest(selected)} onChange={config=>choose({kind:'custom',config})}/>:kind==='flag'?<><label className="search badge-search"><Search size={16}/><input aria-label="Cerca nazione" value={flagQuery} onChange={e=>setFlagQuery(e.target.value)} placeholder="Cerca una nazione…"/></label><div className="badge-results">{visibleCountries.map(c=><button type="button" key={c.code} className={current?.kind==='flag'&&current.ref===c.code?'selected':''} onClick={()=>choose({kind:'flag',ref:c.code})}><img src={flagUrl(c.code)} alt="" loading="lazy"/><span>{c.name}</span><small>{c.code}</small></button>)}</div></>:
      <><label className="search badge-search"><Search size={16}/><input aria-label="Cerca club calcistico" value={clubQuery} onChange={e=>setClubQuery(e.target.value)} placeholder="Cerca il nome del club (minimo 3 lettere)…"/></label><p className="badge-source">Ricerca combinata tra Wikimedia Commons, football-logos e le fonti API configurate. Bandiere e stemmi dei club compaiono se disponibili; verifica i diritti dell'immagine presso la fonte.</p>{searching&&<p>Ricerca in corso…</p>}{searchError&&<p role="alert">{searchError}</p>}{!searching&&!searchError&&clubQuery.trim().length>=3&&!clubs.length&&<p>Nessuna immagine trovata. Prova il nome completo del club.</p>}<div className="badge-results">{clubs.map(c=><button type="button" key={c.ref} className={current?.kind==='club'&&current.ref===c.ref?'selected':''} onClick={()=>choose({kind:'club',ref:c.ref,url:c.url,credit:c.credit,license:c.license})}><img src={c.url} alt="" loading="lazy"/><span>{c.name}<small>{c.type} · {c.source} · {c.description} · {c.license} · {c.credit}</small></span></button>)}</div></>}
    {error&&<div className="alert error" role="alert">{error}</div>}
    {invalidYear&&<p className="alert error" role="alert">L’anno deve essere compreso tra 1800 e 2099.</p>}
    <div className="modal-actions"><button type="button" className="secondary" disabled={busy} onClick={onClose}>Annulla</button><button type="button" className="primary" disabled={busy||invalidYear} onClick={()=>void onSave(draft)}>{busy?'Salvataggio…':'Salva immagini'}</button></div>
  </section></div>;
}
