import {useState, type FormEvent} from 'react';
import {X} from 'lucide-react';
import {api, type User} from './api';

export default function ChangePassword({onClose,onChanged}:{onClose:()=>void;onChanged:(user:User)=>void}) {
  const [current,setCurrent]=useState('');
  const [password,setPassword]=useState('');
  const [repeat,setRepeat]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  async function submit(e:FormEvent) {
    e.preventDefault();setError('');
    if(password!==repeat){setError('Le nuove password non coincidono.');return;}
    if(new TextEncoder().encode(password).length>72){setError('La password supera il limite di 72 byte.');return;}
    setBusy(true);
    try {onChanged(await api<User>('/auth/password','POST',{current_password:current,password}));}
    catch(e){setError(e instanceof Error?e.message:'Cambio password non riuscito.');}
    finally{setBusy(false);}
  }
  return <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="change-password-title">
    <div className="section-heading"><h2 id="change-password-title">Cambia password</h2><button type="button" aria-label="Chiudi" disabled={busy} onClick={onClose}><X/></button></div>
    <p>Al salvataggio verranno chiusi gli accessi sugli altri dispositivi.</p>
    {error&&<div className="alert error" role="alert">{error}</div>}
    <form onSubmit={submit}>
      <label>Password corrente<input type="password" autoComplete="current-password" required value={current} onChange={e=>setCurrent(e.target.value)}/></label>
      <label>Nuova password<input type="password" autoComplete="new-password" required minLength={10} maxLength={72} value={password} onChange={e=>setPassword(e.target.value)}/></label>
      <label>Conferma nuova password<input type="password" autoComplete="new-password" required value={repeat} onChange={e=>setRepeat(e.target.value)}/></label>
      <div className="modal-actions"><button className="secondary" type="button" disabled={busy} onClick={onClose}>Annulla</button><button className="primary" disabled={busy}>{busy?'Salvataggio…':'Salva password'}</button></div>
    </form>
  </section></div>;
}
