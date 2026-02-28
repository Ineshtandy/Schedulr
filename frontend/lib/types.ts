// TypeScript types for API communication
export type Priority = 'low' | 'med' | 'high';

export interface TaskItem {
  title: string;
  notes: string;
  duration_min: number;
  priority: Priority;
}

export interface DayPlan {
  date: string;
  tasks: TaskItem[];
}

export interface Plan {
  plan_id: string;
  goal: string;
  start_date: string;
  num_days: number;
  minutes_per_day: number;
  days: DayPlan[];
  created_at?: string;
}

export interface PlanGenerateRequest {
  goal: string;
  num_days?: number;
  minutes_per_day?: number;
  start_date?: string;
  preferences?: string;
}

export interface PlanUpdateRequest {
  plan_id: string;
  user_message: string;
}

export interface PlanDeployRequest {
  plan_id: string;
}

export interface PlanResponse {
  plan_id: string;
  plan: Plan;
}

export interface PlanDeployResponse {
  tasklist_id: string;
  created_count: number;
  message: string;
}

export interface PlanHistoryItem {
  plan_id: string;
  goal: string;
  created_at: string | null;
  num_days: number;
}

export interface UserInfo {
  authenticated: boolean;
  email?: string;
  name?: string;
}

export interface Message {
  role: 'user' | 'assistant';
  content: string;
  planId?: string;
}
