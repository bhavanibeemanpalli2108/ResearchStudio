export type Json = Record<string, unknown>;
export interface Project {
  id: string;
  title: string;
  question: string;
  domain: string;
  objectives: string[];
  references: string[];
  created_at: string;
  updated_at?: string;
  runs?: Run[];
  run_count?: number;
}
export interface Budget {
  max_llm_calls: number;
  max_input_tokens: number;
  max_output_tokens: number;
  max_iterations: number;
  max_experiments: number;
  max_runtime_seconds: number;
}
export interface Usage {
  calls?: number;
  calls_used?: number;
  estimated_cost?: number | null;
  estimated_tokens?: number;
  llm_calls?: number;
  input_tokens?: number;
  output_tokens?: number;
  total_tokens?: number;
  estimated_cost_usd?: number;
  cost_usd?: number;
  experiments?: number;
  runtime_seconds?: number;
  [key: string]: unknown;
}
export interface Idea {
  id: string;
  title: string;
  hypothesis?: string;
  description?: string;
  rationale?: string;
  novelty_score?: number;
  feasibility_score?: number;
  selected?: boolean;
  [key: string]: unknown;
}
export interface Run {
  id: string;
  project_id: string;
  status: string;
  current_stage: string;
  profile: string;
  provider: string;
  model: string;
  config: { budgets?: Budget; [key: string]: unknown };
  state: Json & { ideas?: Idea[] };
  usage: Usage;
  created_at: string;
  updated_at: string;
  error?: string | null;
  approval?: Json | null;
}
export interface RunEvent {
  id: string;
  run_id: string;
  stage: string;
  kind: string;
  message: string;
  data: Json;
  created_at: string;
}
export interface Experiment {
  id: string;
  run_id: string;
  status: string;
  hypothesis: string;
  configuration: Json;
  metrics: Record<string, unknown>;
  logs: string | string[];
  error?: string;
  started_at?: string;
  finished_at?: string;
  artifact_ids?: string[];
}
export interface Artifact {
  id: string;
  name: string;
  kind: string;
  media_type: string;
  size_bytes: number;
  download_url: string;
}
export interface Graph {
  nodes: { id: string; label: string; status: string }[];
  edges: { source: string; target: string; kind?: string }[];
  state: Json;
}
export interface Provider {
  id: string;
  name?: string;
  configured?: boolean;
  available?: boolean;
  reason?: string;
  models?: string[];
}
export interface Decision {
  summary?: string;
  data?: Json;
  id?: string;
  stage?: string;
  decision?: string;
  message?: string;
  rationale?: string;
  reasoning?: string;
  created_at?: string;
  [key: string]: unknown;
}
export interface Traces {
  decisions: Decision[];
  trace_url?: string;
}
export interface RunRequest {
  selected_paper_ids?: string[];
  execution_protocol: 2;
  engine: 'native' | 'original';
  profile: string;
  provider: string;
  model: string;
  budgets: Budget;
  generate_report: boolean;
  require_approval: boolean;
  constraints: Json;
}
