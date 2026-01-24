export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}
export interface EmotionInfo {
    primary: string;
    category: string;
    confidence: number;
}
export interface MemorySavedInfo {
    count: number;
    entries: Array<{
        id: string;
        category: string;
        key: string;
    }>;
}
export interface HITLOption {
    value: string;
    label: string;
}
export interface HITLField {
    name: string;
    type: string;
    label: string;
    required?: boolean;
    placeholder?: string;
    default?: any;
    options?: HITLOption[];
    min?: number;
    max?: number;
    step?: number;
}
export interface HITLActions {
    approve?: {
        label: string;
        style: string;
    };
    edit?: {
        label: string;
        style: string;
    };
    reject?: {
        label: string;
        style: string;
    };
}
export interface HITLRequest {
    id: string;
    type: string;
    title: string;
    description?: string;
    fields: HITLField[];
    actions?: HITLActions;
    session_id: string;
}
export interface HITLResult {
    action: 'approve' | 'edit' | 'reject';
    data?: Record<string, any>;
    result?: any;
}
export interface HITLContinuationData {
    request_title: string;
    action: string;
    form_data?: Record<string, any>;
    field_labels: Record<string, string>;
}
export declare function getSessionId(): string;
export declare function createNewSession(): string;
export declare function sendChatMessage(message: string, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onEmotion?: (emotion: EmotionInfo) => void, onHITL?: (hitlRequest: HITLRequest) => void, onMemorySaved?: (info: MemorySavedInfo) => void): void;
export declare function isChatLoading(): boolean;
export declare function clearChatHistory(): void;
export declare function createChatInput(shadowRoot: ShadowRoot): HTMLElement;
export declare function getCurrentEmotion(): EmotionInfo | null;
export declare function getEmotionDisplay(emotion: string): {
    label: string;
    color: string;
};
export declare function createEmotionIndicator(shadowRoot: ShadowRoot): HTMLElement;
export declare function updateEmotionIndicator(container: HTMLElement, emotion: EmotionInfo): void;
export declare function hideEmotionIndicator(container: HTMLElement): void;
export declare function getCurrentHITLRequest(): HITLRequest | null;
export declare function clearHITLRequest(): void;
export declare function submitHITLResponse(requestId: string, sessionId: string, action: string, data: Record<string, any> | null): Promise<any>;
export declare function createHITLForm(hitlRequest: HITLRequest, onComplete?: (result: HITLResult) => void): HTMLElement;
export declare function createHITLFormHtml(hitlRequest: HITLRequest): string;
export declare function bindHITLFormEvents(hitlRequest: HITLRequest, onComplete?: (result: HITLResult) => void): void;
export declare function triggerHITLContinuation(sessionId: string, continuationData: HITLContinuationData, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onHITL?: (hitlRequest: HITLRequest) => void): void;
export declare function sendImageMessage(imageData: string, action: 'analyze_only' | 'analyze_for_memory', onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onHITL?: (hitlRequest: HITLRequest) => void): void;
export declare function handleImagePaste(event: ClipboardEvent, shadowRoot: ShadowRoot, chatInputContainer: HTMLElement): Promise<boolean>;
export interface PlanReminder {
    id: string;
    title: string;
    description?: string;
    target_time: string;
    repeat_type: string;
}
export declare function getCurrentPlanReminder(): PlanReminder | null;
