type Time = {
    hour: string;
    text: string;
}[];
declare function showMessage(text: string | string[], timeout: number, priority: number, override?: boolean): void;
declare function showSSEMessage(text: string, id: string, timeout?: number): void;
declare function welcomeMessage(time: Time, welcomeTemplate: string, referrerTemplate: string): string;
declare function i18n(template: string, ...args: string[]): string;
export { showMessage, showSSEMessage, welcomeMessage, i18n, Time };
