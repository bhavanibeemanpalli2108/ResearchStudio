import type {
  Artifact,
  Experiment,
  Graph,
  Json,
  Project,
  Provider,
  Run,
  RunEvent,
  RunRequest,
  Traces,
  Usage,
} from './types';
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* response has no JSON */
    }
    throw new ApiError(response.status, detail || 'The request could not be completed.');
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const id = encodeURIComponent;
export const api = {
  upstream: () =>
    request<{
      runs: { id: string; task: string; agent: string; run_id: string }[];
      inspector_url: string;
    }>('/upstream/runs'),
  importRun: (projectId: string, upstreamId: string) =>
    request<Run>(`/projects/${id(projectId)}/imports`, {
      method: 'POST',
      body: JSON.stringify({ upstream_id: upstreamId }),
    }),
  runs: () => request<Run[]>('/runs'),
  projects: () => request<Project[]>('/projects'),
  project: (projectId: string) => request<Project>(`/projects/${id(projectId)}`),
  createProject: (
    data: Pick<Project, 'title' | 'question' | 'domain' | 'objectives' | 'references'>,
  ) => request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  createRun: (projectId: string, data: RunRequest) =>
    request<Run>(`/projects/${id(projectId)}/runs`, { method: 'POST', body: JSON.stringify(data) }),
  run: (runId: string) => request<Run>(`/runs/${id(runId)}`),
  report: (runId: string) =>
    request<{
      markdown: string;
      renderer_version: string;
      derived: boolean;
      original_artifact_id: string | null;
      original_sha256: string | null;
    }>(`/runs/${id(runId)}/report`),
  events: (runId: string) => request<RunEvent[]>(`/runs/${id(runId)}/events`),
  graph: (runId: string) => request<Graph>(`/runs/${id(runId)}/graph`),
  experiments: (runId: string) => request<Experiment[]>(`/runs/${id(runId)}/experiments`),
  artifacts: (runId: string) => request<Artifact[]>(`/runs/${id(runId)}/artifacts`),
  traces: (runId: string) => request<Traces>(`/runs/${id(runId)}/traces`),
  action: (runId: string, action: string, body: Json = {}) =>
    request<Run>(`/runs/${id(runId)}/${action}`, { method: 'POST', body: JSON.stringify(body) }),
  usage: () => request<Usage>('/usage'),
  capabilities: () => request<Json>('/system/capabilities'),
  providers: async () => {
    const data = await request<Provider[] | { providers: Provider[] }>('/providers');
    return Array.isArray(data) ? data : data.providers;
  },
  models: async (provider: string) => {
    const data = await request<string[] | { models: (string | { id: string; name?: string })[] }>(
      `/providers/models?provider=${id(provider)}`,
    );
    return (Array.isArray(data) ? data : data.models).map((m) =>
      typeof m === 'string' ? m : m.id,
    );
  },
};
export const isActive = (status: string) =>
  [
    'queued',
    'running',
    'paused',
    'awaiting_approval',
    'waiting_for_approval',
    'approval_required',
  ].includes(status);
export const formatNumber = (value: unknown) =>
  typeof value === 'number'
    ? new Intl.NumberFormat('en', {
        notation: value >= 10000 ? 'compact' : 'standard',
        maximumFractionDigits: 1,
      }).format(value)
    : '0';
export const label = (value: string | undefined) =>
  (value || 'pending').replaceAll('_', ' ').replace(/\b\w/g, (s) => s.toUpperCase());

export function numericMetrics(value: unknown, prefix = ''): Record<string, number> {
  const result: Record<string, number> = {};
  if (!value || typeof value !== 'object') return result;
  for (const [key, item] of Object.entries(value)) {
    const name = prefix ? prefix + '.' + key : key;
    if (typeof item === 'number' && Number.isFinite(item)) result[name] = item;
    else if (item && typeof item === 'object' && !Array.isArray(item))
      Object.assign(result, numericMetrics(item, name));
  }
  return result;
}
