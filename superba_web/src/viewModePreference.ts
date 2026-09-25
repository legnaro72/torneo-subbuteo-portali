export type ViewMode = 'compact'|'premium'|'standard';

export function preferredViewMode(key: string): ViewMode {
  try {
    const saved = JSON.parse(localStorage.getItem(key) || '{}');
    if (saved.viewModeVersion === 2 && ['compact', 'premium', 'standard'].includes(saved.viewMode)) {
      return saved.viewMode;
    }
    // The old Compact value was also the automatic default. Upgrade it once.
    return saved.viewMode === 'standard' ? 'standard' : 'premium';
  } catch {
    return 'premium';
  }
}
