import {LayoutDashboard, Trophy, Users} from 'lucide-react';

export type PortalIconKind = 'home' | 'club' | 'italiana' | 'finali' | 'svizzero';

export default function PortalIcon({kind}: {kind: PortalIconKind}) {
  if (kind === 'italiana') return <span className="portal-icon italian-flag" aria-hidden="true"/>;
  if (kind === 'svizzero') return <span className="portal-icon swiss-flag" aria-hidden="true"/>;
  const Icon = kind === 'home' ? LayoutDashboard : kind === 'club' ? Users : Trophy;
  return <Icon className="portal-icon-outline" size={20} strokeWidth={2} aria-hidden="true"/>;
}
