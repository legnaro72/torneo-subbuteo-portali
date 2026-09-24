import {useId} from 'react';

export type CrestConfig={
  schema_version:1;
  shape:'shield'|'circle'|'rounded'|'badge';primary:string;secondary:string;border:string;text:string;
  title:string;initials:string;subtitle:string;year:string;
  icon:'none'|'initials'|'ball'|'star'|'trophy'|'crown'|'flag'|'sport';
  stripe:'none'|'horizontal'|'vertical';double_border:boolean;
};

export function defaultCrest(name:string):CrestConfig{
  const team=name.split(' - ')[0].trim()||name;
  return {schema_version:1,shape:'shield',primary:'#173b67',secondary:'#f4e8cb',border:'#d5a83d',text:'#ffffff',
    title:team.slice(0,22),initials:team.split(/\s+/).map(word=>word[0]).join('').slice(0,3).toUpperCase(),
    subtitle:'',year:'',icon:'ball',stripe:'none',double_border:false};
}

const shapes={
  shield:'M12 8 H108 V69 C108 94 83 113 60 120 C37 113 12 94 12 69 Z',
  circle:'M60 8 A52 52 0 1 1 59.99 8 Z',
  rounded:'M25 8 H95 Q108 8 108 21 V68 Q108 96 60 120 Q12 96 12 68 V21 Q12 8 25 8 Z',
  badge:'M24 8 H96 L112 28 V94 L96 112 H24 L8 94 V28 Z',
};

function CrestSymbol({config}:{config:CrestConfig}){
  const common={fill:'none',stroke:config.text,strokeWidth:3,strokeLinecap:'round' as const,strokeLinejoin:'round' as const};
  switch(config.icon){
    case 'none':return null;
    case 'initials':return <text x="60" y="75" textAnchor="middle" fill={config.text} fontWeight="900" fontSize={config.initials.length>3?24:31}>{config.initials||'FC'}</text>;
    case 'ball':return <g {...common}><circle cx="60" cy="62" r="20"/><path d="M60 52 L70 59 L66 70 H54 L50 59 Z M60 42 V52 M42 55 L50 59 M78 55 L70 59 M49 80 L54 70 M71 80 L66 70"/></g>;
    case 'star':return <path d="M60 38 L66 53 L82 54 L70 65 L74 81 L60 72 L46 81 L50 65 L38 54 L54 53 Z" fill={config.text}/>;
    case 'trophy':return <g {...common}><path d="M46 43 H74 V57 Q74 71 60 74 Q46 71 46 57 Z M46 49 H36 Q36 62 49 63 M74 49 H84 Q84 62 71 63 M60 74 V82 M48 83 H72"/></g>;
    case 'crown':return <g {...common}><path d="M38 73 L34 47 L47 57 L60 39 L73 57 L86 47 L82 73 Z M39 79 H81"/></g>;
    case 'flag':return <g {...common}><path d="M43 82 V42 M43 44 Q56 37 69 44 Q77 48 83 43 V65 Q75 70 67 65 Q55 60 43 67"/></g>;
    case 'sport':return <g {...common}><circle cx="60" cy="61" r="20"/><path d="M42 61 H78 M60 42 V80 M47 47 Q61 62 47 75 M73 47 Q59 62 73 75"/></g>;
  }
}

export function CustomCrest({config,className='team-badge'}:{config:CrestConfig;className?:string}){
  const clipId=useId();
  const title=config.title.trim().slice(0,22)||config.initials.trim().slice(0,4)||'SUBBUTEO';
  const titleSize=title.length>16?8:title.length>11?10:12;
  const path=shapes[config.shape];
  return <svg className={className} viewBox="0 0 120 128" role="img" aria-label={`Stemma ${title}`} xmlns="http://www.w3.org/2000/svg">
    <defs><clipPath id={clipId}><path d={path}/></clipPath></defs>
    <path d={path} fill={config.primary} stroke={config.border} strokeWidth="5"/>
    <g clipPath={`url(#${clipId})`}>
      {config.stripe==='horizontal'&&<path d="M0 50 H120 V78 H0 Z" fill={config.secondary} opacity=".8"/>}
      {config.stripe==='vertical'&&<path d="M47 0 H73 V128 H47 Z" fill={config.secondary} opacity=".8"/>}
      <path d="M18 29 H102 V34 H18 Z" fill={config.secondary}/>
    </g>
    {config.double_border&&<path d={path} fill="none" stroke={config.secondary} strokeWidth="1.5" transform="translate(60 64) scale(.89) translate(-60 -64)"/>}
    <CrestSymbol config={config}/>
    <text x="60" y="101" textAnchor="middle" fill={config.text} fontSize={titleSize} fontWeight="900" letterSpacing=".5" textLength={title.length>16?84:undefined} lengthAdjust="spacingAndGlyphs">{title.toUpperCase()}</text>
    {(config.subtitle||config.year)&&<text x="60" y="113" textAnchor="middle" fill={config.text} fontSize="7" fontWeight="700" textLength={config.subtitle.length>14?76:undefined} lengthAdjust="spacingAndGlyphs">{[config.subtitle.slice(0,18),config.year].filter(Boolean).join(' · ')}</text>}
  </svg>;
}

export function CustomCrestEditor({value,onChange}:{value:CrestConfig;onChange:(config:CrestConfig)=>void}){
  const set=<K extends keyof CrestConfig>(key:K,next:CrestConfig[K])=>onChange({...value,[key]:next});
  return <div className="crest-editor"><div className="crest-preview"><CustomCrest config={value} className="crest-large"/><span>Anteprima live · SVG</span></div><div className="crest-controls">
    <label>Forma<select value={value.shape} onChange={e=>set('shape',e.target.value as CrestConfig['shape'])}><option value="shield">Scudo classico</option><option value="circle">Cerchio vintage</option><option value="rounded">Scudo arrotondato</option><option value="badge">Badge moderno</option></select></label>
    <label>Simbolo<select value={value.icon} onChange={e=>set('icon',e.target.value as CrestConfig['icon'])}><option value="ball">Pallone</option><option value="initials">Iniziali</option><option value="star">Stella</option><option value="trophy">Trofeo</option><option value="crown">Corona</option><option value="flag">Bandierina</option><option value="sport">Sportivo</option><option value="none">Nessuno</option></select></label>
    <label>Nome o sigla<input maxLength={22} value={value.title} onChange={e=>set('title',e.target.value)}/></label>
    <label>Iniziali<input maxLength={4} value={value.initials} onChange={e=>set('initials',e.target.value.toUpperCase())}/></label>
    <label>Testo breve<input maxLength={18} value={value.subtitle} onChange={e=>set('subtitle',e.target.value)}/></label>
    <label>Anno<input inputMode="numeric" pattern="(1[89][0-9]{2}|20[0-9]{2})?" maxLength={4} value={value.year} onChange={e=>set('year',e.target.value.replace(/[^0-9]/g,'').slice(0,4))} placeholder="Es. 1985"/></label>
    {([['primary','Principale'],['secondary','Secondario'],['border','Bordo'],['text','Testo']] as const).map(([key,label])=><label key={key}>{label}<input type="color" value={value[key]} onChange={e=>set(key,e.target.value)}/></label>)}
    <label>Fascia<select value={value.stripe} onChange={e=>set('stripe',e.target.value as CrestConfig['stripe'])}><option value="none">Nessuna</option><option value="horizontal">Orizzontale</option><option value="vertical">Verticale</option></select></label>
    <label className="checkbox"><input type="checkbox" checked={value.double_border} onChange={e=>set('double_border',e.target.checked)}/>Doppio bordo</label>
  </div></div>;
}
