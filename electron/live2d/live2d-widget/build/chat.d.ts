export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}
export interface EmotionInfo {
    primary: string;
    category: string;
    confidence: number;
}
export declare function getSessionId(): string;
export declare function createNewSession(): string;
export declare function sendChatMessage(message: string, onChunk: (text: string) => void, onDone?: () => void, onError?: (error: string) => void, onEmotion?: (emotion: EmotionInfo) => void): void;
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
