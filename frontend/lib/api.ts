import {
  Conversation,
  ConversationCreateResponse,
  ConversationDetail,
  ConversationPlanResponse,
  DeployResponse,
  UserInfo,
} from './types';

function getApiBaseCandidates(): string[] {
  const configuredBase = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, '');
  if (configuredBase) {
    return [configuredBase];
  }

  const candidates: string[] = [];

  if (typeof window !== 'undefined') {
    const { protocol, hostname } = window.location;
    const canonicalHost = hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0'
      ? '127.0.0.1'
      : hostname;
    candidates.push(`${protocol}//${canonicalHost}:8000`);
  }

  candidates.push('http://127.0.0.1:8000', 'http://localhost:8000');
  return Array.from(new Set(candidates.map((candidate) => candidate.replace(/\/$/, ''))));
}

function buildHeaders(options: RequestInit): Headers {
  const headers = new Headers(options.headers || {});
  const hasBody = options.body !== undefined && options.body !== null;
  if (hasBody && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return headers;
}

async function extractErrorMessage(response: Response, endpoint: string): Promise<string> {
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    const data = await response.json().catch(() => null);
    if (data && typeof data === 'object') {
      const detail =
        (data as { detail?: unknown; message?: unknown }).detail ??
        (data as { detail?: unknown; message?: unknown }).message;
      if (typeof detail === 'string' && detail.trim()) {
        return `${detail} (${endpoint}) [${response.url}]`;
      }
    }
  }

  const textBody = (await response.text().catch(() => '')).trim();
  if (textBody) {
    const compact = textBody.replace(/\s+/g, ' ').slice(0, 240);
    return `${compact} (${endpoint}) [${response.url}]`;
  }

  return `HTTP ${response.status} ${response.statusText || ''}`.trim() + ` (${endpoint}) [${response.url}]`;
}

function shouldTryNextBase(response: Response): boolean {
  if (response.status === 401 || response.status === 403) {
    return false;
  }

  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  const isHtml = contentType.includes('text/html');
  const isNotFound = response.status === 404;

  if (!isHtml && !isNotFound) {
    return false;
  }

  try {
    const url = new URL(response.url);
    const isFrontendDevPort = url.port === '3000';
    return isHtml || isFrontendDevPort;
  } catch {
    return isHtml;
  }
}

async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const apiBases = getApiBaseCandidates();
  const attemptLog: Array<{ base: string; error: string }> = [];
  let lastNetworkError: unknown = null;
  let lastHttpError: Error | null = null;

  for (const apiBase of apiBases) {
    try {
      const response = await fetch(`${apiBase}${endpoint}`, {
        ...options,
        credentials: 'include',
        headers: buildHeaders(options),
      });

      if (!response.ok) {
        const errorMessage = await extractErrorMessage(response, endpoint);
        const err = new Error(errorMessage);
        if (shouldTryNextBase(response)) {
          lastHttpError = err;
          attemptLog.push({ base: apiBase, error: `HTTP ${response.status}` });
          console.warn(`[API] ${apiBase}${endpoint} -> ${response.status}, trying next...`);
          continue;
        }
        throw err;
      }

      if (attemptLog.length > 0) {
        console.info(`[API] Succeeded with ${apiBase}${endpoint} after ${attemptLog.length} failed attempt(s)`);
      }
      return response.json() as Promise<T>;
    } catch (error) {
      if (error instanceof TypeError) {
        lastNetworkError = error;
        attemptLog.push({ base: apiBase, error: error.message });
        console.warn(`[API] ${apiBase}${endpoint} -> Network error: ${error.message}`);
        continue;
      }
      throw error;
    }
  }

  const summary = attemptLog.map((a) => `${a.base}: ${a.error}`).join('; ');
  const finalMessage = `All API bases failed for ${endpoint}. Attempts: ${summary}`;
  console.error(`[API] ${finalMessage}`);

  throw lastNetworkError instanceof Error
    ? new Error(finalMessage)
    : lastHttpError || new Error(finalMessage);
}

export async function getMe(): Promise<UserInfo> {
  return fetchAPI<UserInfo>('/api/me');
}

export async function listConversations(): Promise<Conversation[]> {
  return fetchAPI<Conversation[]>('/api/conversations');
}

export async function createConversation(): Promise<ConversationCreateResponse> {
  return fetchAPI<ConversationCreateResponse>('/api/conversations', {
    method: 'POST',
  });
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return fetchAPI<ConversationDetail>(`/api/conversations/${conversationId}`);
}

export async function updateConversationTitle(conversationId: string, title: string): Promise<Conversation> {
  return fetchAPI<Conversation>(`/api/conversations/${conversationId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });
}

export async function generatePlan(
  conversationId: string,
  payload: {
    user_message: string;
    num_days?: number;
    minutes_per_day?: number;
    start_date?: string;
    preferences?: string;
  }
): Promise<ConversationPlanResponse> {
  return fetchAPI<ConversationPlanResponse>(`/api/conversations/${conversationId}/plan/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updatePlan(
  conversationId: string,
  payload: {
    user_message: string;
  }
): Promise<ConversationPlanResponse> {
  return fetchAPI<ConversationPlanResponse>(`/api/conversations/${conversationId}/plan/update`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function deployPlan(planId: string): Promise<DeployResponse> {
  return fetchAPI<DeployResponse>(`/api/plans/${planId}/deploy`, {
    method: 'POST',
  });
}

export async function deletePlanDeployment(planId: string): Promise<{ message: string }> {
  return fetchAPI<{ message: string }>(`/api/plans/${planId}/deployment`, {
    method: 'DELETE',
  });
}

export async function updatePlanDeployment(planId: string): Promise<DeployResponse> {
  return fetchAPI<DeployResponse>(`/api/plans/${planId}/deployment/update`, {
    method: 'POST',
  });
}

export async function logout(): Promise<void> {
  await fetchAPI<{ message: string }>('/api/auth/logout', { method: 'POST' });
}
