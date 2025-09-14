declare function randomSelection(obj: string[] | string): string;
declare function randomOtherOption(total: number, excludeIndex: number): number;
declare function loadExternalResource(url: string, type: string): Promise<string>;
export declare const generateMsgId: () => string;
export declare const setLocalStorage: (key: string, value: any, expire: number) => void;
export declare const getLocalStorage: (key: string) => any;
export declare const writeOptions: (options: any) => void;
export declare const readOptions: () => any;
export { randomSelection, loadExternalResource, randomOtherOption, };
