// Type definitions matching the FastAPI backend

export type ProviderType = 'openai' | 'anthropic' | 'gemini' | 'deepseek' | 'ollama' | 'custom';

export interface Provider {
  id: string;
  name: string;
  provider_type: ProviderType;
  base_url: string;
  api_key?: string | null;
  enabled: boolean;
  is_active: boolean;
  priority: number;
  max_rpm: number;
  max_tpm: number;
  current_rpm?: number;
  current_tpm?: number;
  avg_latency_ms: number;
  success_rate: number;
  is_healthy?: boolean;
  requires_proxy: boolean;
  proxy_url?: string | null;
  models: string[];
  extra_config?: Record<string, any>;
  extra_data?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export type RoutingStrategy = 'cheapest' | 'priority' | 'latency' | 'fallback' | 'round_robin' | 'weighted';

export interface RoutingRule {
  id: string;
  name: string;
  strategy: RoutingStrategy;
  model_pattern: string;
  provider_order: string[];
  provider_ids?: string[];
  weights?: Record<string, number>;
  is_active: boolean;
  priority: number;
  fallback_enabled: boolean;
  max_retries: number;
  timeout_ms: number;
  created_at?: string;
  updated_at?: string;
}

export type UserRole = 'admin' | 'user' | 'readonly';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  credits: number;
  is_active: boolean;
  api_key?: string | null;
  extra_metadata?: Record<string, any>;
  created_at?: string;
}

export interface RequestLog {
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
}

export interface Analytics {
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  requests_today: number;
  requests_this_week: number;
  by_provider?: Record<string, { requests: number; cost: number; latency: number }>;
  by_model?: Record<string, { requests: number; cost: number }>;
  recent_errors?: Array<{ provider: string; model: string; error: string; created_at: string }>;
}

export interface Model {
  id: string;
  name: string;
  provider_id: string;
  model_id: string;
  mode: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  context_window: number;
  supports_functions: boolean;
  supports_vision: boolean;
  enabled: boolean;
  is_active: boolean;
}
