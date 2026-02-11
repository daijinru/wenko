import { useECSWindow } from './hooks/use-ecs-window';
import { ECSForm } from './components/ecs-form';
import { ECSActions } from './components/ecs-actions';
import { ECSDisplay } from './components/ecs-display';
import { ECSDisplayActions } from './components/ecs-display-actions';
import { isDisplayRequest } from './types/ecs';
import type { ECSDisplayRequest } from './types/ecs';
import './styles/globals.css';

export default function App() {
  const {
    request,
    formData,
    error,
    isSubmitting,
    isLoaded,
    updateField,
    submit,
  } = useECSWindow();

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
        <header className="window-draggable border-b border-border !p-[6px] !mb-[6px] flex justify-between items-center">
          <h1 className="flex-1 text-center text-xs font-bold">{request.title || 'ECS'}</h1>
        </header>

        {/* Content */}
        <div className="!p-[12px] window-body flex-1 flex flex-col overflow-hidden">
          {isDisplay ? (
            <>
              <ECSDisplay request={request as ECSDisplayRequest} />
              {/* <ECSDisplayActions
                dismissLabel={(request as ECSDisplayRequest).dismiss_label}
                onDismiss={() => submit('reject')}
                isSubmitting={isSubmitting}
              /> */}
            </>
          ) : (
            <>
              <ECSForm
                request={request}
                formData={formData}
                onFieldChange={updateField}
                error={error}
                readonly={request.readonly}
              />
              <ECSActions
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
