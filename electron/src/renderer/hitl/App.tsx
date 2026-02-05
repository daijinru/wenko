import { useHITLWindow } from './hooks/use-hitl-window';
import { HITLForm } from './components/hitl-form';
import { HITLActions } from './components/hitl-actions';
import { HITLDisplay } from './components/hitl-display';
import { HITLDisplayActions } from './components/hitl-display-actions';
import { isDisplayRequest } from './types/hitl';
import type { HITLDisplayRequest } from './types/hitl';
import './styles/globals.css';
import 'classic-stylesheets/layout.css';
import 'classic-stylesheets/themes/macos9/theme.css';
import 'classic-stylesheets/themes/macos9/skins/bubbles.css';

export default function App() {
  const {
    request,
    formData,
    error,
    isSubmitting,
    isLoaded,
    updateField,
    submit,
  } = useHITLWindow();

  if (!isLoaded) {
    return (
      <div className="theme-classic h-screen flex items-center justify-center">
        <span className="text-xs">加载中...</span>
      </div>
    );
  }

  if (!request) {
    return (
      <div className="theme-classic h-screen flex items-center justify-center">
        <span className="text-xs text-muted-foreground">无表单数据</span>
      </div>
    );
  }

  // Check if this is a visual display request
  const isDisplay = isDisplayRequest(request);

  return (
    <div className="theme-classic h-screen flex flex-col">
      <div className="window active flex-1 flex flex-col">
        {/* Title bar */}
        <header className="window-draggable bg-classic-title border-b border-border !p-[6px] !mb-[6px] flex justify-between items-center">
          <h1 className="flex-1 text-center text-xs font-bold">{request.title || 'HITL'}</h1>
        </header>

        {/* Content */}
        <div className="!p-[12px] window-body flex-1 flex flex-col overflow-hidden">
          {isDisplay ? (
            <>
              <HITLDisplay request={request as HITLDisplayRequest} />
              {/* <HITLDisplayActions
                dismissLabel={(request as HITLDisplayRequest).dismiss_label}
                onDismiss={() => submit('reject')}
                isSubmitting={isSubmitting}
              /> */}
            </>
          ) : (
            <>
              <HITLForm
                request={request}
                formData={formData}
                onFieldChange={updateField}
                error={error}
                readonly={request.readonly}
              />
              <HITLActions
                actions={request.actions}
                isSubmitting={isSubmitting}
                onApprove={() => submit('approve')}
                onReject={() => submit('reject')}
                readonly={request.readonly}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
