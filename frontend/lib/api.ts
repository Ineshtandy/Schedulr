// API client for backend communication
import {
  Plan,
  PlanGenerateRequest,
  PlanUpdateRequest,
  PlanDeployRequest,
  PlanResponse,
  PlanDeployResponse,
  PlanHistoryItem,
  UserInfo,
} from './types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchAPI(endpoint: string, options: RequestInit = {}) {
  const url = `${API_URL}${endpoint}`;
  
  const config: RequestInit = {
    ...options,
    credentials: 'include', // CRITICAL: Send cookies with requests
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };
  
  const response = await fetch(url, config);
  
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `HTTP error ${response.status}`);
  }
  
  return response.json();
}

export async function getMe(): Promise<UserInfo> {
  return fetchAPI('/api/auth/me');
}

export async function logout(): Promise<void> {
  await fetchAPI('/api/auth/logout', { method: 'POST' });
}

export async function generatePlan(request: PlanGenerateRequest): Promise<PlanResponse> {
  return fetchAPI('/api/plan/generate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function updatePlan(request: PlanUpdateRequest): Promise<PlanResponse> {
  return fetchAPI('/api/plan/update', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function deployPlan(request: PlanDeployRequest): Promise<PlanDeployResponse> {
  return fetchAPI('/api/plan/deploy', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getPlanHistory(): Promise<PlanHistoryItem[]> {
  return fetchAPI('/api/plan/history');
}

export async function getPlan(planId: string): Promise<Plan> {
  return fetchAPI(`/api/plan/${planId}`);
}
