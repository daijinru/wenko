export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}
export declare function getSessionId(): string;
export declare function createNewSession(): string;
export declare function sendChatMessage(message: string, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void): void;
export declare function isChatLoading(): boolean;
export declare function clearChatHistory(): void;
export declare function createChatInput(shadowRoot: ShadowRoot): HTMLElement;
