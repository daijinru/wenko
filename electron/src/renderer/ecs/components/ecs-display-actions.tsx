interface ECSDisplayActionsProps {
  dismissLabel?: string;
  onDismiss: () => void;
  isSubmitting: boolean;
}

export function ECSDisplayActions({ dismissLabel = '关闭', onDismiss, isSubmitting }: ECSDisplayActionsProps) {
  return (
    <div className="!mt-2 flex justify-end gap-2 p-4 border-t border-border">
      <button
        onClick={onDismiss}
        disabled={isSubmitting}
        className="px-4 py-1 text-xs border-classic-outset bg-secondary text-secondary-foreground hover:bg-secondary/80 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {dismissLabel}
      </button>
    </div>
  );
}
