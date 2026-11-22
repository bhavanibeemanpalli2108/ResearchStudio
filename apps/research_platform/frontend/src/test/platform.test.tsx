import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { CreatePage } from '../create';
import { LiteraturePage, storeSelectedPapers, readSelectedPapers } from '../literature';
import type { Paper } from '../literature';
import { ApprovalModal, Markdown, RunPage, PaperView } from '../run';
import { request, ApiError, numericMetrics } from '../api';
import { approvalDigest, artifactText } from '../evidence';
import type { Artifact, Run } from '../types';
function wrap(
  children: React.ReactNode,
  entries = ['/'],
  client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  }),
) {
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={entries}>{children}</MemoryRouter>
    </QueryClientProvider>,
  );
}
function response(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
const run: Run = {
  id: 'run-1',
  project_id: 'project-1',
  status: 'awaiting_approval',
  current_stage: 'research_plan',
  profile: 'demo',
  provider: 'mock',
  model: 'mock-researcher',
  config: {},
  state: {
    plan: {
      objective: 'Test the 26-circle packing comparison',
      steps: ['Measure baseline', 'Run seeded local search'],
    },
    ideas: [],
  },
  usage: {},
  approval: { gate: 'research_plan' },
  created_at: '2026-11-14T00:00:00Z',
  updated_at: '2026-11-14T00:00:00Z',
};
describe('Research setup', () => {
  it('uses the real curated question and prevents unavailable full research launch', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) =>
        String(input).includes('/models')
          ? response({ models: ['mock-researcher'] })
          : response([{ id: 'mock', name: 'Deterministic demo', available: true }]),
      ),
    );
    const user = userEvent.setup();
    wrap(<CreatePage />);
    await user.click(screen.getByRole('button', { name: /Use example/i }));
    expect((screen.getByLabelText(/Research question/) as HTMLTextAreaElement).value).toContain(
      '26 non-overlapping circles',
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByRole('radio', { name: /Full research/ })).toBeDisabled();
    expect(screen.getByRole('radio', { name: /Demo/ })).toBeChecked();
    expect(screen.getByLabelText('Model')).toHaveValue('mock-researcher');
  });
  it('shows setup validation for an incomplete question', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => response([])),
    );
    const user = userEvent.setup();
    wrap(<CreatePage />);
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    expect(screen.getByLabelText(/Project title/)).toBeInvalid();
  });
});
describe('Human approval', () => {
  it('replaces the approval state before closing the dialog', async () => {
    const queued = { ...run, status: 'queued', approval: null };
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => response(queued)),
    );
    const client = new QueryClient();
    client.setQueryData(['run', run.id], run);
    const onChange = vi.fn((open: boolean) => {
      if (!open) expect(client.getQueryData(['run', run.id])).toEqual(queued);
    });
    wrap(<ApprovalModal run={run} open onOpenChange={onChange} />, ['/'], client);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Approve & continue' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(false));
  });
  it('sends the chosen guidance to the durable approval endpoint', async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, _options?: RequestInit) =>
      response({ ...run, status: 'running' }),
    );
    vi.stubGlobal('fetch', fetcher);
    const onChange = vi.fn();
    const user = userEvent.setup();
    wrap(<ApprovalModal run={run} open onOpenChange={onChange} />);
    expect(screen.getByRole('heading', { name: 'Review your research plan' })).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Additional guidance/), 'Use a fixed seed');
    await user.click(screen.getByRole('button', { name: 'Approve & continue' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(false));
    expect(fetcher).toHaveBeenCalledWith(
      '/api/runs/run-1/approve',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('Use a fixed seed'),
      }),
    );
    const options = fetcher.mock.calls[0]?.[1] as RequestInit;
    expect(JSON.parse(String(options.body))).toMatchObject({
      approved: true,
      action: 'continue',
      constraints: { user_instructions: 'Use a fixed seed' },
    });
  });
});
describe('API failures', () => {
  it('preserves actionable server validation errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => response({ detail: 'Provider quota exceeded' }, 429)),
    );
    await expect(request('/providers')).rejects.toEqual(
      new ApiError(429, 'Provider quota exceeded'),
    );
  });
});

describe('Measured metric shapes', () => {
  it('renders recorded observations as an accessible table in report previews and print', () => {
    render(
      <Markdown
        content={
          '**Recorded observations**\n| Recorded metric | Value |\n| --- | --- |\n| baseline | `7292` |\n| candidate | `5180` |'
        }
      />,
    );
    const table = screen.getByRole('table');
    expect(table).toHaveTextContent('Recorded metric');
    expect(screen.getByRole('columnheader', { name: 'Value' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '7292' })).toBeInTheDocument();
    expect(screen.getByRole('cell', { name: '5180' })).toBeInTheDocument();
  });
  it('flattens nested experiment metrics without turning fixture flags into values', () => {
    expect(
      numericMetrics({
        baseline: { sum_radii: 1.85, valid: true },
        candidate: { sum_radii: 2.16, circles: 26 },
        fixture: true,
      }),
    ).toEqual({ 'baseline.sum_radii': 1.85, 'candidate.sum_radii': 2.16, 'candidate.circles': 26 });
  });
});

describe('Digest-bound generated experiments', () => {
  const digest = 'a'.repeat(64);
  const genuine: Run = {
    ...run,
    profile: 'free_research',
    provider: 'gemini',
    config: { execution_protocol: 2 },
    approval: { gate: 'experiment', approval_digest: digest },
    state: {
      experiment_config: {
        approval_digest: digest,
        spec: {
          research_question: 'Compare prediction error on synthetic regression data',
          protocol: 'regression_v1',
          evaluation: { metric: 'rmse' },
        },
        baseline_sha256: 'b'.repeat(64),
        evaluation_validation: { dataset_sha256: 'c'.repeat(64) },
      },
    },
  };
  it('includes the exact reviewed evaluation digest in experiment approval', async () => {
    const fetcher = vi.fn(async (_input: RequestInfo | URL, _options?: RequestInit) =>
      response({ ...genuine, status: 'running' }),
    );
    vi.stubGlobal('fetch', fetcher);
    const user = userEvent.setup();
    const onChange = vi.fn();
    wrap(<ApprovalModal run={genuine} open onOpenChange={onChange} />);
    expect(screen.getByTestId('approval-digest')).toHaveTextContent(digest);
    await user.click(screen.getByRole('button', { name: 'Approve & continue' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(false));
    expect(JSON.parse(String(fetcher.mock.calls[0]?.[1]?.body))).toMatchObject({
      approved: true,
      approval_digest: digest,
    });
  });
  it('blocks approval when the current state and gate digests differ', () => {
    const changed = {
      ...genuine,
      state: { experiment_config: { approval_digest: 'd'.repeat(64) } },
    };
    expect(approvalDigest(changed)).toBeUndefined();
    wrap(<ApprovalModal run={changed} open onOpenChange={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Approve & continue' })).toBeDisabled();
    expect(screen.getByRole('alert')).toHaveTextContent('Frozen evaluation is incomplete');
  });
  it('launches genuine research with protocol2 native and bounded defaults', async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input);
      if (options?.method === 'POST' && path === '/api/projects')
        return response({ id: 'new-project', title: 'Study' });
      if (options?.method === 'POST' && path.endsWith('/runs')) return response(genuine);
      if (path.includes('/models')) return response({ models: ['openai/gpt-oss-20b'] });
      return response([
        { id: 'mock', name: 'Demo', configured: true },
        { id: 'groq', name: 'Groq', configured: true },
      ]);
    });
    vi.stubGlobal('fetch', fetcher);
    const user = userEvent.setup();
    wrap(<CreatePage />, ['/create?profile=free_research']);
    await user.click(screen.getByRole('button', { name: 'Use example' }));
    expect((screen.getByLabelText(/Research question/) as HTMLTextAreaElement).value).toContain(
      'regression',
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await screen.findByRole('option', { name: /gpt-oss-20b.*configured/ });
    expect(screen.getByLabelText('Model')).toHaveValue('openai/gpt-oss-20b');
    await user.selectOptions(screen.getByLabelText('Model'), 'openai/gpt-oss-20b');
    expect(screen.getByLabelText('Model')).toHaveValue('openai/gpt-oss-20b');
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await user.click(screen.getByRole('button', { name: 'Launch research' }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(
          ([path, options]) => String(path).endsWith('/runs') && options?.method === 'POST',
        ),
      ).toBe(true),
    );
    const call = fetcher.mock.calls.find(
      ([path, options]) => String(path).endsWith('/runs') && options?.method === 'POST',
    );
    expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({
      execution_protocol: 2,
      engine: 'native',
      profile: 'free_research',
      provider: 'groq',
      require_approval: true,
      budgets: { max_llm_calls: 20, max_input_tokens: 32000, max_output_tokens: 16000 },
    });
  });
  it('refuses cross-origin artifact previews without making a request', async () => {
    const fetcher = vi.fn();
    vi.stubGlobal('fetch', fetcher);
    const artifact: Artifact = {
      id: 'a',
      name: 'candidate.py',
      kind: 'source',
      media_type: 'text/x-python',
      size_bytes: 20,
      download_url: 'https://external.invalid/program.py',
    };
    await expect(artifactText(artifact)).rejects.toThrow(
      'requires a download URL from this research API',
    );
    expect(fetcher).not.toHaveBeenCalled();
  });
});

describe('Generation readiness display', () => {
  it.each([
    ['generation_verified', 'Bounded generation succeeded at this time.', ''],
    [
      'unavailable',
      'groq temporarily rejected the request (HTTP 429).',
      'Check account quota; reservations are retained.',
    ],
  ])(
    'renders %s from persisted events without requesting generation',
    async (status, detail, action) => {
      const completed = {
        ...run,
        status: 'completed',
        approval: null,
        provider: 'groq',
        model: 'openai/gpt-oss-20b',
      };
      const fetcher = vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.endsWith('/events'))
          return response([
            {
              id: 'readiness-1',
              run_id: run.id,
              stage: 'provider_preflight',
              kind: 'provider_readiness',
              message: 'Generation preflight result',
              created_at: run.created_at,
              data: {
                provider: completed.provider,
                model: completed.model,
                status,
                detail,
                action,
              },
            },
          ]);
        if (path.endsWith('/runs')) return response([completed]);
        if (path.endsWith(`/runs/${run.id}`)) return response(completed);
        if (path.includes('/projects/'))
          return response({ id: run.project_id, title: 'Existing study' });
        if (path.endsWith('/traces')) return response({ decisions: [] });
        if (path.endsWith('/graph')) return response({ nodes: [], edges: [], state: {} });
        return response([]);
      });
      vi.stubGlobal('fetch', fetcher);
      const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      client.setQueryData(['run', run.id], completed);
      wrap(
        <Routes>
          <Route path="/workspace/:runId" element={<RunPage section="ideas" />} />
        </Routes>,
        [`/workspace/${run.id}`],
        client,
      );
      const notice = await screen.findByText(new RegExp(status));
      expect(notice).toHaveAttribute('role', 'status');
      expect(notice).toHaveTextContent('groq / openai/gpt-oss-20b');
      expect(notice).toHaveTextContent(detail);
      if (action) expect(notice).toHaveTextContent(action);
      await userEvent.setup().click(screen.getByRole('button', { name: 'Refresh run' }));
      expect(fetcher.mock.calls.every(([path]) => !String(path).includes('/providers/'))).toBe(
        true,
      );
    },
  );
});

describe('Final report presentation', () => {
  it('uses the server presentation rather than superseded state for preview and export', async () => {
    const current =
      '# Verified final report\n\nFinal approved experiment contract: 32 jobs.\n\nHistorical proposals are superseded.';
    const fetcher = vi.fn(async () =>
      response({
        markdown: current,
        derived: true,
        renderer_version: 'native-studio-v1',
        original_artifact_id: 'original',
        original_sha256: 'a'.repeat(64),
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    wrap(
      <PaperView
        run={{
          ...run,
          id: 'final-view',
          profile: 'free_research',
          state: { paper: 'UNLABELLED OLD 128-JOB REPORT' },
        }}
        artifacts={[]}
      />,
    );
    await screen.findByText(/Final approved experiment contract: 32 jobs/);
    expect(screen.queryByText('UNLABELLED OLD 128-JOB REPORT')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Download original report' })).toHaveAttribute(
      'href',
      '/api/artifacts/original/download',
    );
    expect(screen.getByRole('button', { name: 'Markdown' })).toBeEnabled();
    expect(fetcher).toHaveBeenCalledWith('/api/runs/final-view/report', expect.anything());
  });
  it('does not fall back to a superseded report after a presentation error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => response({ detail: 'Presentation unavailable' }, 503)),
    );
    wrap(
      <PaperView
        run={{
          ...run,
          id: 'failed-view',
          profile: 'free_research',
          state: { paper: 'OLD UNVERIFIED TEXT' },
        }}
        artifacts={[]}
      />,
    );
    await screen.findByRole('alert');
    expect(screen.queryByText('OLD UNVERIFIED TEXT')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Markdown' })).toBeDisabled();
  });
});

describe('Terminal run evidence refresh', () => {
  it('loads completed measurements even if the last active poll cached an empty list', async () => {
    let completed = false;
    const active = { ...run, status: 'running', approval: null };
    const final = { ...active, status: 'completed' };
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const path = String(input);
        if (path.endsWith('/experiments'))
          return response(
            completed
              ? [
                  {
                    id: 'measured',
                    run_id: run.id,
                    status: 'completed',
                    hypothesis: 'Measured comparison',
                    configuration: {},
                    metrics: { score: 700 },
                    logs: '',
                    artifact_ids: [],
                    started_at: run.created_at,
                    finished_at: run.created_at,
                  },
                ]
              : [],
          );
        if (path.endsWith('/runs')) return response([completed ? final : active]);
        if (path.endsWith(`/runs/${run.id}`)) return response(completed ? final : active);
        if (path.includes('/projects/')) return response({ id: run.project_id, title: 'Study' });
        if (path.endsWith('/traces')) return response({ decisions: [] });
        if (path.endsWith('/graph')) return response({ nodes: [], edges: [], state: {} });
        return response([]);
      }),
    );
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    client.setQueryData(['run', run.id], active);
    wrap(
      <Routes>
        <Route path="/experiments/:runId" element={<RunPage section="experiments" />} />
      </Routes>,
      [`/experiments/${run.id}`],
      client,
    );
    await screen.findByText('The lab is ready for an experiment');
    completed = true;
    act(() => {
      client.setQueryData(['run', run.id], final);
    });
    await screen.findByRole('button', { name: 'Experiment 01' });
  });
});

const scholarlyPaper: Paper = {
  id: 'https://doi.org/10.1000/test',
  selection_id: 'a'.repeat(64),
  title: 'Source paper',
  authors: ['Real Author'],
  year: 2022,
  doi: 'https://doi.org/10.1000/test',
  url: 'https://doi.org/10.1000/test',
  source: 'Crossref',
  abstract: 'Deposited abstract only.',
  abstract_source: 'Crossref',
  abstract_truncated: false,
  retrieved_at: '2026-11-20T00:00:00Z',
  provenance: [
    {
      source: 'Crossref',
      source_id: 'https://api.crossref.org/works/10.1000/test',
      retrieved_at: '2026-11-20T00:00:00Z',
    },
  ],
};
describe('Scholarly literature', () => {
  it('searches only on submission, displays source metadata and remembers explicit selection', async () => {
    const fetcher = vi.fn(async () =>
      response({
        papers: [scholarlyPaper],
        warnings: ['OpenAlex unavailable; Crossref results retained'],
        cached: false,
      }),
    );
    vi.stubGlobal('fetch', fetcher);
    wrap(<LiteraturePage />);
    expect(fetcher).not.toHaveBeenCalled();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Research topic or DOI'), 'scheduling');
    await user.click(screen.getByRole('button', { name: 'Search literature' }));
    await screen.findByRole('heading', { name: 'Source paper' });
    expect(screen.getByText(/Real Author/)).toBeVisible();
    expect(screen.getByRole('link', { name: 'Open original source' })).toHaveAttribute(
      'href',
      scholarlyPaper.url,
    );
    expect(screen.getByText(/Crossref results retained/)).toBeVisible();
    await user.click(screen.getByRole('checkbox', { name: 'Select Source paper' }));
    expect(readSelectedPapers()[0].selection_id).toBe(scholarlyPaper.selection_id);
    expect(screen.getByRole('link', { name: 'Use selected papers in research' })).toHaveAttribute(
      'href',
      '/create?profile=free_research',
    );
    expect(fetcher.mock.calls.length).toBe(1);
  });
  it('handles source errors without invented results', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => response({ detail: 'Literature unavailable' }, 503)),
    );
    wrap(<LiteraturePage />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('Research topic or DOI'), 'scheduling');
    await user.click(screen.getByRole('button', { name: 'Search literature' }));
    await screen.findByRole('alert');
    expect(screen.queryByRole('link', { name: 'Open original source' })).not.toBeInTheDocument();
  });
  it('passes only selected snapshot identifiers when creating native research', async () => {
    storeSelectedPapers([scholarlyPaper]);
    const fetcher = vi.fn(async (input: RequestInfo | URL, options?: RequestInit) => {
      const path = String(input);
      if (options?.method === 'POST' && path === '/api/projects')
        return response({ id: 'project-selected' });
      if (options?.method === 'POST' && path.endsWith('/runs'))
        return response({ ...run, id: 'selected-run' });
      if (path.includes('/models')) return response([{ id: 'openai/gpt-oss-20b' }]);
      return response([{ id: 'groq', name: 'Groq', configured: true }]);
    });
    vi.stubGlobal('fetch', fetcher);
    wrap(<CreatePage />, ['/create?profile=free_research']);
    const user = userEvent.setup();
    expect(screen.getByText('Source paper')).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Use example' }));
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await screen.findByRole('option', { name: /gpt-oss-20b/ });
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await user.click(screen.getByRole('button', { name: 'Launch research' }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(
          ([url, options]) => String(url).endsWith('/runs') && options?.method === 'POST',
        ),
      ).toBe(true),
    );
    const call = fetcher.mock.calls.find(
      ([url, options]) => String(url).endsWith('/runs') && options?.method === 'POST',
    );
    const body = JSON.parse(String(call?.[1]?.body));
    expect(body.selected_paper_ids).toEqual([scholarlyPaper.selection_id]);
    expect(body.selected_literature).toBeUndefined();
  });
});
