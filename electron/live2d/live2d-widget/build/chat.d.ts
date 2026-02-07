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
export interface ECSOption {
    value: string;
    label: string;
}
export interface ECSField {
    name: string;
    type: string;
    label: string;
    required?: boolean;
    placeholder?: string;
    default?: any;
    options?: ECSOption[];
    min?: number;
    max?: number;
    step?: number;
}
export interface ECSActions {
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
export interface ECSRequest {
    id: string;
    type: string;
    title: string;
    description?: string;
    fields: ECSField[];
    actions?: ECSActions;
    session_id: string;
}
export interface ECSResult {
    action: 'approve' | 'edit' | 'reject';
    data?: Record<string, any>;
    result?: any;
}
export interface ECSContinuationData {
    request_title: string;
    action: string;
    form_data?: Record<string, any>;
    field_labels: Record<string, string>;
}
export declare function getSessionId(): string;
export declare function createNewSession(): string;
export declare function sendChatMessage(message: string, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onEmotion?: (emotion: EmotionInfo) => void, onECS?: (ecsRequest: ECSRequest) => void, onMemorySaved?: (info: MemorySavedInfo) => void): void;
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
export declare function getCurrentECSRequest(): ECSRequest | null;
export declare function clearECSRequest(): void;
export declare function submitECSResponse(requestId: string, sessionId: string, action: string, data: Record<string, any> | null): Promise<any>;
export declare function createECSForm(ecsRequest: ECSRequest, onComplete?: (result: ECSResult) => void): HTMLElement;
export declare function createECSFormHtml(ecsRequest: ECSRequest): string;
export declare function bindECSFormEvents(ecsRequest: ECSRequest, onComplete?: (result: ECSResult) => void): void;
export declare function triggerECSContinuation(sessionId: string, continuationData: ECSContinuationData, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onECS?: (ecsRequest: ECSRequest) => void): void;
export declare function sendImageMessage(imageData: string, action: 'analyze_only' | 'analyze_for_memory', onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onECS?: (ecsRequest: ECSRequest) => void): void;
export declare function handleImagePaste(event: ClipboardEvent, shadowRoot: ShadowRoot, chatInputContainer: HTMLElement): Promise<boolean>;
