import {LayoutDashboard, Trophy, Users} from 'lucide-react';

export type PortalIconKind = 'home' | 'club' | 'italiana' | 'finali' | 'svizzero';

export default function PortalIcon({kind}: {kind: PortalIconKind}) {
  if (kind === 'italiana') return <span className="portal-icon italian-flag" aria-hidden="true"/>;
  if (kind === 'svizzero') return <span className="portal-icon swiss-flag" aria-hidden="true"/>;
  const Icon = kind === 'home' ? LayoutDashboard : kind === 'club' ? Users : Trophy;
  return <span className={`portal-icon portal-icon--${kind}`} aria-hidden="true"><Icon size={15} strokeWidth={2.25}/></span>;
}
