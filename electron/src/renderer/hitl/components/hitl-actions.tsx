import type { HITLActions as HITLActionsType } from '../types/hitl';

interface HITLActionsProps {
  actions?: HITLActionsType;
  isSubmitting: boolean;
  onApprove: () => void;
  onReject: () => void;
  readonly?: boolean;
}

export function HITLActions({ actions, isSubmitting, onApprove, onReject, readonly }: HITLActionsProps) {
  const approveLabel = actions?.approve?.label || '确认';
  const rejectLabel = actions?.reject?.label || '跳过';

  // Readonly mode: only show close button
  if (readonly) {
    return (
      <div className="flex justify-end gap-2 p-4 border-t border-border">
        <button
          onClick={() => window.electronAPI.invoke('hitl:cancel')}
          className="px-4 py-1 text-xs border-classic-outset bg-secondary text-secondary-foreground hover:bg-secondary/80"
        >
          关闭
        </button>
      </div>
    );
  }

  return (
    <div className="flex justify-end gap-2 p-4 border-t border-border">
      <button
        onClick={onReject}
        disabled={isSubmitting}
        className="px-4 py-1 text-xs border-classic-outset bg-secondary text-secondary-foreground hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {rejectLabel}
      </button>
      <button
        onClick={onApprove}
        disabled={isSubmitting}
        className="primary px-4 py-1 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSubmitting ? '提交中...' : approveLabel}
      </button>
    </div>
  );
}
