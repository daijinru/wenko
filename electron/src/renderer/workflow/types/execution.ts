/** Execution state types — mirrors backend ?human=true API responses. */

/** Human-readable execution state from SSE `execution_state` event `human` field. */
export interface HumanExecutionState {
  行动: string;
  原状态: string;
  新状态: string;
  是否已结束: boolean;
  是否需要关注: boolean;
  是否不可逆: boolean;
}

/** Raw SSE `execution_state` event payload (machine + human). */
export interface ExecutionStateEvent {
  execution_id: string;
  action_summary: string;
  from_status: string;
  to_status: string;
  trigger: string;
  actor_category: string;
  is_terminal: boolean;
  is_resumable: boolean;
  has_side_effects: boolean;
  timestamp: number;
  human: HumanExecutionState;
}

/** Single action item from timeline API (?human=true). */
export interface ExecutionTimelineItem {
  行动: string;
  状态: string;
  是否已结束: boolean;
  是否不可逆: boolean;
  结果: string | null;
  错误: string | null;
}

/** Full timeline API response (?human=true). */
export interface ExecutionTimeline {
  行动列表: ExecutionTimelineItem[];
  总数: number;
  已结束: number;
  进行中: number;
  含等待: boolean;
  含不可逆操作: boolean;
}

/** Snapshot API response (?human=true). */
export interface ExecutionSnapshot {
  行动: string;
  状态: string;
  是否需要关注: boolean;
  是否已结束: boolean;
  是否不可逆: boolean;
  结果: string | null;
  错误: string | null;
}
