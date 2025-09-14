export declare const getKanbanDaily: (text: any, callback: any, loadingCallback?: any, doneCallback?: any) => void;
export type WeightedText = {
    Text: string;
    Weight: number;
};
export declare const getWeightedTexts: (text: any) => {
    Text: any;
    Weight: number;
}[];
export declare const getSearch: (text: any, callback: any, loadingCallback?: any) => void;
export declare const saveHightlightText: (text: any, callback: any, loadingCallback?: any) => void;
export declare const saveDaily: (callback: any, loadingCallback?: any) => void;
export declare const getDaily: (callback: any, loadingCallback?: any, doneCallback?: any) => void;
