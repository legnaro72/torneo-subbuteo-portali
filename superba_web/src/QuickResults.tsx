import {useState} from 'react';
import {ArrowLeftRight, ClipboardPaste, Sparkles, Trash2, X} from 'lucide-react';
import {api} from './api';

type Match={index:number;home:string;away:string;home_goals:number;away_goals:number;valid:boolean;day?:number;round?:number;group?:string;round_name?:string};
type Option={match_id:string;matchday_number:number;group:string;participant1:string;participant2:string;existing_score1:number;existing_score2:number;has_result:boolean;confidence:number;reversed:boolean};
type Parsed={raw_segment:string;spoken_matchday:number|null;participant1_text:string;participant2_text:string;score1:number|null;score2:number|null;selected_match:Option|null;confidence:number;alternatives:Option[];status:string;overwrite?:boolean};
type Analysis={source:'text'|'voice';original_text:string;results:Parsed[]};

const statusName:Record<string,string>={matched:'Associata',ambiguous:'Da verificare',unmatched:'Partita non trovata',incomplete:'Risultato incompleto',duplicate:'Possibile duplicato',invalid:'Punteggio non valido'};

function optionFor(match:Match):Option{return {match_id:String(match.index),matchday_number:match.day??match.round??1,group:match.group??match.round_name??'',participant1:match.home,participant2:match.away,existing_score1:match.home_goals,existing_score2:match.away_goals,has_result:match.valid,confidence:1,reversed:false};}

export default function QuickResults<T>({kind,tournamentId,version,matches,onClose,onSaved}:{kind:'tournaments'|'swiss'|'finals';tournamentId:string;version:string;matches:Match[];onClose:()=>void;onSaved:(value:T)=>void}){
  const [text,setText]=useState('');const [analysis,setAnalysis]=useState<Analysis|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState('');
  const allOptions=matches.map(optionFor);
  async function analyze(){setBusy(true);setError('');try{const value=await api<Analysis>(`/${kind}/${tournamentId}/rapid-results/analyze`,'POST',{source:'text',raw_text:text});setAnalysis(value);if(!value.results.length)setError('Non è stato riconosciuto alcun risultato.');}catch(e){setError(e instanceof Error?e.message:'Analisi non riuscita.');}finally{setBusy(false);}}
  function update(index:number,patch:Partial<Parsed>){setAnalysis(current=>current?{...current,results:current.results.map((row,i)=>i===index?{...row,...patch}:row)}:current);}
  function select(index:number,id:string){const option=allOptions.find(item=>item.match_id===id)||null;update(index,{selected_match:option,status:option?'matched':'unmatched'});}
  function remove(index:number){setAnalysis(current=>current?{...current,results:current.results.filter((_,i)=>i!==index)}:current);}
  const ids=analysis?.results.map(row=>row.selected_match?.match_id).filter(Boolean)??[];const duplicates=new Set(ids.filter((id,i)=>ids.indexOf(id)!==i));
  const valid=!!analysis?.results.length&&analysis.results.every(row=>row.status==='matched'&&row.selected_match&&row.score1!==null&&row.score2!==null&&row.score1>=0&&row.score1<=20&&row.score2>=0&&row.score2<=20&&!duplicates.has(row.selected_match.match_id)&&(!row.selected_match.has_result||row.overwrite));
  async function save(){if(!analysis||!valid)return;setBusy(true);setError('');try{const result=await api<T>(`/${kind}/${tournamentId}/rapid-results`,'PATCH',{version,results:analysis.results.map(row=>({match_id:row.selected_match!.match_id,score1:row.score1,score2:row.score2,overwrite:!!row.overwrite}))});onSaved(result);onClose();}catch(e){setError(e instanceof Error?e.message:'Salvataggio non riuscito.');}finally{setBusy(false);}}
  async function paste(){try{const value=await navigator.clipboard.readText();if(value)setText(value);}catch{setError('Il browser non consente l’accesso agli appunti: incolla manualmente nella casella.');}}
  return <div className="modal-backdrop"><section className="modal quick-results" role="dialog" aria-modal="true" aria-labelledby="quick-results-title">
    <div className="section-heading"><div><span className="eyebrow">RISULTATI DA TESTO</span><h2 id="quick-results-title">Inserimento rapido</h2><p>Incolla più risultati, controlla ogni associazione e salva soltanto dopo la revisione.</p></div><button type="button" aria-label="Chiudi" disabled={busy} onClick={onClose}><X/></button></div>
    {error&&<div className="alert error" role="alert">{error}</div>}
    <label>Testo originale<textarea rows={6} maxLength={12000} value={text} onChange={e=>{setText(e.target.value);setAnalysis(null);}} placeholder={'Rossi - Bianchi 3-1\nVerdi - Neri 0-0'}/></label>
    <div className="quick-input-actions"><button className="secondary" type="button" disabled={busy} onClick={()=>void paste()}><ClipboardPaste size={16}/>Incolla</button><button className="primary" type="button" disabled={busy||!text.trim()} onClick={()=>void analyze()}><Sparkles size={16}/>{busy?'Analisi…':analysis?'Rianalizza risultati':'Analizza risultati'}</button></div>
    {analysis&&<div className="quick-review">{analysis.results.map((row,index)=>{const selected=row.selected_match;const overwrite=!!row.overwrite;const duplicate=selected&&duplicates.has(selected.match_id);return <article className={'quick-row '+((row.status==='matched'&&!duplicate)?'ready':'needs-review')} key={`${index}-${row.raw_segment}`}>
      <div className="quick-row-head"><span>Riga {index+1}</span><strong>{duplicate?'Possibile duplicato':statusName[row.status]||row.status}</strong><button type="button" aria-label={`Elimina riga ${index+1}`} onClick={()=>remove(index)}><Trash2 size={15}/></button></div>
      <small className="quick-original">{row.raw_segment}</small>
      <label>Partita<select value={selected?.match_id||''} onChange={e=>select(index,e.target.value)}><option value="">Seleziona la partita</option>{allOptions.map(option=><option key={option.match_id} value={option.match_id}>{option.group?`${option.group} · `:''}{kind==='tournaments'?'Giornata':'Turno'} {option.matchday_number} · {option.participant1} — {option.participant2}{option.has_result?' · risultato presente':''}</option>)}</select></label>
      {selected&&<div className="quick-score"><div><small>{kind==='tournaments'?'Giornata':'Turno'} {selected.matchday_number}{selected.group?` · ${selected.group}`:''}</small><strong>{selected.participant1}</strong><input aria-label={`Punteggio ${selected.participant1}`} type="number" min={0} max={20} value={row.score1??''} onChange={e=>update(index,{score1:e.target.value===''?null:Number(e.target.value)})}/></div><button type="button" title="Inverti punteggi" aria-label="Inverti punteggi" onClick={()=>update(index,{score1:row.score2,score2:row.score1})}><ArrowLeftRight size={17}/></button><div><small>&nbsp;</small><strong>{selected.participant2}</strong><input aria-label={`Punteggio ${selected.participant2}`} type="number" min={0} max={20} value={row.score2??''} onChange={e=>update(index,{score2:e.target.value===''?null:Number(e.target.value)})}/></div></div>}
      {selected?.has_result&&<label className="checkbox overwrite"><input type="checkbox" checked={overwrite} onChange={e=>update(index,{overwrite:e.target.checked})}/>Sostituisci il risultato già presente ({selected.existing_score1}-{selected.existing_score2})</label>}
      <div className="quick-confidence"><span>Confidenza {Math.round(row.confidence*100)}%</span>{row.spoken_matchday&&<span>Giornata indicata: {row.spoken_matchday}</span>}{row.alternatives.length>1&&<span>{row.alternatives.length} proposte</span>}</div>
    </article>;})}</div>}
    <div className="modal-actions"><button className="secondary" type="button" disabled={busy} onClick={onClose}>Annulla</button>{analysis&&<button className="primary" type="button" disabled={busy||!valid} onClick={()=>void save()}>{busy?'Salvataggio…':'Conferma e salva risultati'}</button>}</div>
  </section></div>;
}
