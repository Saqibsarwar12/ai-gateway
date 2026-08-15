// Live API client for AI Gateway backend
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api-proxy';
const TOKEN_KEY = 'ai_gateway_token';

// ─── Helpers ─────────────────────────────────────────────────────────────
async function request<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  };
  const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
  const apiKey = typeof window !== 'undefined' ? localStorage.getItem('ai_gateway_api_key') : null;
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  const res = await fetch(`${API_BASE}${path}`, { ...options, credentials: 'include', headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {}
    throw new Error(`${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, body?: any) =>
  request<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined });
const put = <T>(path: string, body?: any) =>
  request<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined });
const del = <T>(path: string) => request<T>(path, { method: 'DELETE' });

// ─── Auth ────────────────────────────────────────────────────────────────
export const apiLogin = (email: string, password: string) =>
  post<{ access_token: string; token_type: string; user: any }>(
    '/admin/auth/login',
    { email, password }
  );

export const apiRegister = (data: { name: string; email: string; password: string; role?: string }) =>
  post<{ id: string; name: string; email: string; api_key: string }>('/admin/auth/register', data);

// ─── Providers ───────────────────────────────────────────────────────────
export const apiListProviders = () => get<Provider[]>('/admin/providers');
export const apiCreateProvider = (data: any) => post<Provider>('/admin/providers', data);
export const apiUpdateProvider = (id: string, data: any) => put<Provider>(`/admin/providers/${id}`, data);
export const apiDeleteProvider = (id: string) => del(`/admin/providers/${id}`);
export const apiTestProvider = (id: string) =>
  post<{ ok: boolean; latency_ms: number; status_code?: number; error?: string }>(
    `/admin/providers/${id}/test`
  );
export const apiSyncProviderModels = (id: string) =>
  post<{ models: string[] }>(`/admin/providers/${id}/sync-models`);

// ─── Models ──────────────────────────────────────────────────────────────
export const apiListModels = () => get<AIModel[]>('/admin/models');
export const apiCreateModel = (data: any) => post<AIModel>('/admin/models', data);
export const apiUpdateModel = (id: string, data: any) => put<AIModel>(`/admin/models/${id}`, data);
export const apiDeleteModel = (id: string) => del(`/admin/models/${id}`);

// ─── Routing ─────────────────────────────────────────────────────────────
export const apiListRules = () => get<RoutingRule[]>('/admin/routing');
export const apiCreateRoutingRule = (data: any) => post<RoutingRule>('/admin/routing', data);
export const apiUpdateRoutingRule = (id: string, data: any) => put<RoutingRule>(`/admin/routing/${id}`, data);
export const apiDeleteRoutingRule = (id: string) => del(`/admin/routing/${id}`);

// ─── Logs ────────────────────────────────────────────────────────────────
export const apiListLogs = (limit = 100) =>
  get<RequestLog[]>(`/admin/logs?limit=${limit}`);

// ─── API Keys ────────────────────────────────────────────────────────────
export const apiListMyKeys = () => get<any[]>("/admin/api-keys");
export const apiCreateMyKey = (data: { name: string; rate_limit_rpm?: number }) => post<any>("/admin/api-keys", data);
export const apiDeleteMyKey = (id: string) => del("/admin/api-keys/" + id);

// ─── Private prompts ─────────────────────────────────────────────────────
export const apiListPrompts = () => get<CustomPrompt[]>('/admin/prompts');
export const apiCreatePrompt = (data: PromptInput) => post<CustomPrompt>('/admin/prompts', data);
export const apiUpdatePrompt = (id: string, data: PromptInput) => put<CustomPrompt>(`/admin/prompts/${id}`, data);
export const apiDeletePrompt = (id: string) => del(`/admin/prompts/${id}`);

// ─── Personal gateway ────────────────────────────────────────────────────
export const apiGetGateway = () => get<any>('/admin/gateway/me');
export const apiSaveGateway = (data: any) => put<any>('/admin/gateway/me', data);
export const apiTestGateway = (id: string) => post<any>(`/admin/personal-gateway/${id}/test`);
export const apiDeleteGateway = (id: string) => del(`/admin/gateway/me/${id}`);

// ─── Users ───────────────────────────────────────────────────────────────
export const apiListUsers = () => get<User[]>('/admin/users');
export const apiCreateUser = (data: any) => post<User>('/admin/users', data);
export const apiDeleteUser = (id: string) => del(`/admin/users/${id}`);

// ─── Models (OpenAI-compatible) ─────────────────────────────────────────
export const apiListOpenAIModels = () =>
  get<{ object: string; data: { id: string; object: string; created: number; owned_by: string }[] }>('/v1/models');

// ─── Analytics ───────────────────────────────────────────────────────────
export const apiGetStats = () => get<{
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_latency_ms: number;
  success_rate: number;
  by_provider: Record<string, { requests: number; cost: number }>;
  by_model: Record<string, { requests: number; cost: number }>;
  recent_24h: { hour: string; requests: number; cost: number }[];
}>('/admin/stats');

// ─── Playground (chat completions) ──────────────────────────────────────
export const apiChat = async (
  payload: {
    model: string;
    messages: { role: 'system' | 'user' | 'assistant'; content: string }[];
    temperature?: number;
    max_tokens?: number;
    stream?: boolean;
  },
  onChunk?: (chunk: string) => void
) => {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const apiKey = typeof window !== 'undefined' ? localStorage.getItem('ai_gateway_api_key') : null;
  const token = typeof window !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
  if (token) headers['Authorization'] = `Bearer ${token}`;
  else if (apiKey) headers['X-API-Key'] = apiKey;

  const res = await fetch(`${API_BASE}/v1/chat/completions`, {
    method: 'POST',
    credentials: 'include',
    headers,
    body: JSON.stringify({ ...payload, stream: false }),
  });
  if (!res.ok) {
    const t = await res.text();
    throw new Error(t);
  }
  return res.json();
};

// ─── Default export (named-aggregate) ───────────────────────────────────
export const api = {
  login: apiLogin,
  register: apiRegister,
  listProviders: apiListProviders,
  createProvider: apiCreateProvider,
  updateProvider: apiUpdateProvider,
  deleteProvider: apiDeleteProvider,
  testProvider: apiTestProvider,
  syncProviderModels: apiSyncProviderModels,
  listModels: apiListModels,
  createModel: apiCreateModel,
  updateModel: apiUpdateModel,
  deleteModel: apiDeleteModel,
  listRules: apiListRules,
  createRule: apiCreateRoutingRule,
  updateRule: apiUpdateRoutingRule,
  deleteRule: apiDeleteRoutingRule,
  listLogs: apiListLogs,
  listUsers: apiListUsers,
  createUser: apiCreateUser,
  deleteUser: apiDeleteUser,
  listOpenAIModels: apiListOpenAIModels,
  getStats: apiGetStats,
  chat: apiChat,
};

export type Provider = {
  id: string;
  name: string;
  provider_type: string;
  base_url: string;
  api_key?: string | null;
  enabled: boolean;
  is_active: boolean;
  priority: number;
  models: string[];
  avg_latency_ms: number;
  success_rate: number;
  is_healthy: boolean;
  max_rpm: number;
  max_tpm: number;
  extra_data?: Record<string, any> | null;
  extraData?: string;
  created_at: string;
  updated_at: string;
};

export type NvidiaSmartProvider = Provider & {
  id: '__nvidia_smart__';
  name: string;
  provider_type: 'nvidia_smart';
  base_url: string;
  extra_data: {
    configured: boolean;
    public_model_id: string;
    display_name: string;
    enabled: boolean;
    enabled_account_count?: number;
  };
};

export type AIModel = {
  id: string;
  name: string;
  provider_id?: string;
  model_id: string;
  mode: 'chat' | 'completion' | 'embedding';
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  context_window: number;
  supports_functions: boolean;
  supports_vision: boolean;
  enabled: boolean;
  is_active: boolean;
};

export type RoutingRule = {
  id: string;
  name: string;
  strategy: 'fallback' | 'cost' | 'latency' | 'round_robin' | 'weighted' | 'priority';
  model_pattern: string;
  provider_ids: string[];
  provider_order?: string[];
  weights: Record<string, number>;
  is_active: boolean;
  priority: number;
  fallback_enabled: boolean;
  max_retries: number;
  timeout_ms: number;
  created_at: string;
};

export type RequestLog = {
  id: string;
  user_id?: string;
  api_key_id?: string;
  provider: string;
  model: string;
  mode: string;
  input_tokens: number;
  output_tokens: number;
  latency_ms: number;
  status_code: number;
  error?: string;
  cache_hit: boolean;
  cost_usd: number;
  created_at: string;
};

export type User = {
  id: string;
  name: string;
  email: string;
  role: string;
  credits: number;
  is_active: boolean;
  api_key?: string;
  created_at: string;
  tier?: string;
};

export type PromptInput = {
  name: string;
  model_pattern: string;
  content: string;
  preset: 'custom' | 'extreme_directness';
  is_active: boolean;
  is_default: boolean;
};

export type CustomPrompt = PromptInput & {
  id: string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type UserResponse = User;
export const API_BASE_URL = API_BASE;