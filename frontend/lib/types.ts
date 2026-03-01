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
  conversation_id?: string;
  goal: string;
  start_date: string;
  num_days: number;
  minutes_per_day: number;
  days: DayPlan[];
  created_at?: string;
}

export interface UserInfo {
  authenticated: boolean;
  user_id?: string;
  email?: string;
  name?: string;
}

export interface Conversation {
  conversation_id: string;
  user_id: string;
  title: string;
  state: 'idle' | 'awaiting_info' | 'generating';
  latest_plan_id?: string | null;
  pending_goal?: string | null;
  created_at?: string;
  updated_at?: string;
  is_deployed?: boolean;
  deployment_id?: string | null;
  tasklist_id?: string | null;
  deployed_at?: string | null;
}

export interface Message {
  message_id?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Message[];
  latest_plan: Plan | null;
}

export interface ConversationCreateResponse {
  conversation_id: string;
}

export interface ConversationPlanResponse {
  state: 'idle' | 'awaiting_info' | 'generating';
  plan_id?: string;
  plan?: Plan;
  questions?: string[];
}

export interface DeployResponse {
  tasklist_id: string;
  tasklist_title: string;
  conversation_id: string;
  plan_id: string;
  created_count: number;
  updated_count: number;
  message: string;
}
