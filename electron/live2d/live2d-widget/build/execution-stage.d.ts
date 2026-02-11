interface HumanState {
    行动: string;
    原状态: string;
    新状态: string;
    是否已结束: boolean;
    是否需要关注: boolean;
    是否不可逆: boolean;
}
export declare function updateExecutionStage(state: HumanState): void;
export {};
