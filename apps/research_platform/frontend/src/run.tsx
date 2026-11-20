import { lazy, Suspense, useEffect, useState } from 'react';
import { Link, NavLink, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  Code2,
  FileText,
  FlaskConical,
  Info,
  Lightbulb,
  Pause,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  Square,
} from 'lucide-react';
import { request, api, formatNumber, isActive, label, numericMetrics } from './api';
import { useRun } from './hooks';
import {
  ArtifactList,
  FeasibilityNotice,
  FrozenExperimentReview,
  approvalDigest,
} from './evidence';
import { useRuns } from './pages';
import {
  Badge,
  Button,
  CodeBlock,
  Empty,
  ErrorNotice,
  Loading,
  Modal,
  PageHeading,
  Panel,
  date,
  downloadText,
} from './ui';
import type { Artifact, Decision, Experiment, Idea, Json, Run, RunEvent } from './types';
const FlowGraph = lazy(() => import('./visuals').then((m) => ({ default: m.FlowGraph })));
const MetricsChart = lazy(() => import('./visuals').then((m) => ({ default: m.MetricsChart })));
const Editor = lazy(() => import('./editor'));
const sections = [
  ['workspace', 'Workspace'],
  ['ideas', 'Ideas'],
  ['experiments', 'Experiments'],
  ['analytics', 'Analytics'],
  ['explainability', 'Explainability'],
  ['paper', 'Paper & artifacts'],
];
export function RunPage({ section }: { section: string }) {
  const params = useParams();
  const allRuns = useRuns();
  const navigate = useNavigate();
  const runId = params.runId ?? allRuns.data?.[0]?.id;
  const query = useRun(runId);
  const run = query.data;
  const client = useQueryClient();
  const [approvalOpen, setApprovalOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);
  const project = useQuery({
    queryKey: ['project', run?.project_id],
    queryFn: () => api.project(run!.project_id),
    enabled: !!run?.project_id,
  });
  const events = useQuery({
    queryKey: ['events', runId],
    queryFn: () => api.events(runId!),
    enabled: !!runId,
    refetchInterval: run && isActive(run.status) ? 3000 : false,
  });
  const experiments = useQuery({
    queryKey: ['experiments', runId],
    queryFn: () => api.experiments(runId!),
    enabled: !!runId,
    refetchInterval: run && isActive(run.status) ? 3000 : false,
  });
  const graph = useQuery({
    queryKey: ['graph', runId],
    queryFn: () => api.graph(runId!),
    enabled: !!runId,
    refetchInterval: run && isActive(run.status) ? 3000 : false,
  });
  const artifacts = useQuery({
    queryKey: ['artifacts', runId],
    queryFn: () => api.artifacts(runId!),
    enabled: !!runId,
  });
  const traces = useQuery({
    queryKey: ['traces', runId],
    queryFn: () => api.traces(runId!),
    enabled: !!runId,
  });
  useEffect(() => {
    if (!runId || !run?.status) return;
    // A final run poll may arrive before the final experiment/artifact poll.
    // Refresh evidence at every status transition, including terminal states.
    for (const name of ['events', 'experiments', 'graph', 'artifacts', 'traces']) {
      void client.invalidateQueries({ queryKey: [name, runId] });
    }
  }, [client, runId, run?.status]);
  const action = useMutation({
    mutationFn: ({ name, body }: { name: string; body?: Json }) => api.action(runId!, name, body),
    onSuccess: async (updatedRun) => {
      await client.cancelQueries({ queryKey: ['run', runId], exact: true });
      client.setQueryData(['run', runId], updatedRun);
      setCancelOpen(false);
      void client.invalidateQueries({ queryKey: ['run', runId] });
      void client.invalidateQueries({ queryKey: ['runs'] });
    },
  });
  const awaiting =
    run?.status === 'awaiting_approval' ||
    run?.status === 'waiting_for_approval' ||
    run?.status === 'approval_required';
  const ideas = run?.state.ideas ?? [];
  if (allRuns.isLoading && !runId) return <Loading />;
  if (!runId)
    return (
      <>
        <PageHeading
          eyebrow="YOUR RESEARCH WORKSPACE"
          title="The next step starts with a question."
          description="Start a research run to explore ideas, execute experiments, and collect evidence."
        />
        <Empty
          title="Your lab is ready"
          description="Create your first research project, or try a demo without API keys."
          icon={<FlaskConical size={28} />}
          action={
            <Link to="/create" className="button primary">
              <Plus size={16} />
              Start research
            </Link>
          }
        />
      </>
    );
  return (
    <>
      <div className="run-breadcrumb">
        <Link to="/history">Research projects</Link>
        <ChevronRight size={12} />
        <span>{project.data?.title ?? 'Research run'}</span>
        <ChevronRight size={12} />
        <span>{label(section)}</span>
      </div>
      <PageHeading
        eyebrow={`${project.data?.domain ?? 'RESEARCH'} · ${runId.slice(0, 12)}`}
        title={project.data?.title ?? 'Research workspace'}
        description={project.data?.question}
        actions={
          <>
            <select
              aria-label="Select research run"
              className="run-select"
              value={runId}
              onChange={(e) => navigate(`/${section}/${e.target.value}`)}
            >
              {allRuns.data?.map((r) => (
                <option value={r.id} key={r.id}>
                  {r.id.slice(0, 12)} · {label(r.status)}
                </option>
              ))}
            </select>
            <Button
              variant="secondary"
              onClick={() => {
                void query.refetch();
                void events.refetch();
              }}
              aria-label="Refresh run"
            >
              <RefreshCw size={16} />
            </Button>
          </>
        }
      />
      <ErrorNotice
        error={query.error}
        retry={() => {
          void query.refetch();
        }}
      />
      {query.isLoading ? (
        <Loading label="Opening your research workspace" />
      ) : (
        run && (
          <>
            <div className="run-statusbar">
              <div className="run-status-left">
                <Badge status={run.status} />
                <span className="status-separator" />
                {run.profile === 'demo' && (
                  <span className="demo-label">
                    <FlaskConical size={12} />
                    DEMO RUN
                  </span>
                )}
                <span className="run-model">
                  {run.provider} <span>·</span> {run.model}
                </span>
              </div>
              <div className="run-controls">
                {awaiting ? (
                  <Button className="small" onClick={() => setApprovalOpen(true)}>
                    <ShieldCheck size={14} />
                    Review & approve
                  </Button>
                ) : run.status === 'paused' ? (
                  <Button
                    className="small"
                    onClick={() => action.mutate({ name: 'resume' })}
                    disabled={action.isPending}
                  >
                    <Play size={14} />
                    Resume
                  </Button>
                ) : ['running', 'queued'].includes(run.status) ? (
                  <Button
                    variant="secondary"
                    className="small"
                    onClick={() => action.mutate({ name: 'pause' })}
                    disabled={action.isPending}
                  >
                    <Pause size={14} />
                    Pause
                  </Button>
                ) : null}
                {isActive(run.status) && (
                  <Button
                    variant="ghost"
                    className="small"
                    onClick={() => setCancelOpen(true)}
                    disabled={action.isPending}
                  >
                    <Square size={12} />
                    Cancel
                  </Button>
                )}
                {run.status === 'failed' && (
                  <Button
                    variant="secondary"
                    className="small"
                    onClick={() => action.mutate({ name: 'resume', body: { action: 'retry' } })}
                    disabled={action.isPending}
                  >
                    <RefreshCw size={13} />
                    Retry stage
                  </Button>
                )}
              </div>
            </div>
            <ErrorNotice error={action.error || run.error} />
            {events.data
              ?.filter((event) => event.kind === 'provider_readiness')
              .map((event) => (
                <p key={event.id} role="status">
                  {String(event.data.provider)} / {String(event.data.model)}:{' '}
                  {String(event.data.status)}. {String(event.data.detail)}{' '}
                  {String(event.data.action ?? '')}
                </p>
              ))}
            {run.status === 'paused' && run.profile === 'free_research' && (
              <ProviderSelection run={run} />
            )}
            {awaiting && (
              <div className="approval-banner">
                <span className="approval-icon">
                  <ShieldCheck size={21} />
                </span>
                <div>
                  <strong>Your team is ready for your input.</strong>
                  <p>
                    Review the{' '}
                    {String(
                      run.approval?.gate ??
                        (run.state.approval as Json | undefined)?.gate ??
                        'next step',
                    ).replaceAll('_', ' ')}{' '}
                    before the investigation continues.
                  </p>
                </div>
                <Button onClick={() => setApprovalOpen(true)}>
                  Review proposal
                  <ArrowRight size={15} />
                </Button>
              </div>
            )}
            <nav className="run-tabs" aria-label="Research run views">
              {sections.map(([key, name]) => (
                <NavLink
                  key={key}
                  to={`/${key}/${runId}`}
                  className={section === key ? 'active' : ''}
                >
                  {name}
                  {key === 'ideas' && ideas.length > 0 && <span>{ideas.length}</span>}
                  {key === 'experiments' && (experiments.data?.length ?? 0) > 0 && (
                    <span>{experiments.data?.length}</span>
                  )}
                </NavLink>
              ))}
            </nav>
            {section === 'workspace' && (
              <>
                <FeasibilityNotice value={run.state.feasibility} />
                <div className="run-stats">
                  <div>
                    <span>CURRENT STAGE</span>
                    <strong>
                      <span className={run.status === 'running' ? 'pulse-dot' : 'green-dot'} />
                      {label(run.current_stage)}
                    </strong>
                  </div>
                  <div>
                    <span>EXPERIMENTS</span>
                    <strong>
                      {experiments.data?.length ?? 0}
                      <small>/ {run.config.budgets?.max_experiments ?? '--'}</small>
                    </strong>
                  </div>
                  <div>
                    <span>MODEL CALLS</span>
                    <strong>
                      {formatNumber(run.usage.calls ?? run.usage.calls_used ?? run.usage.llm_calls)}
                      <small>calls</small>
                    </strong>
                  </div>
                  <div>
                    <span>TOKENS REPORTED</span>
                    <strong>
                      {formatNumber(
                        run.usage.total_tokens ??
                          (Number(run.usage.input_tokens) || 0) +
                            (Number(run.usage.output_tokens) || 0),
                      )}
                      <small>tokens</small>
                    </strong>
                  </div>
                </div>
                <div className="workspace-grid">
                  <Panel
                    title="The research journey"
                    subtitle="A live view of your team's discovery process."
                    actions={
                      <span className="live-indicator">
                        <span className={isActive(run.status) ? 'pulse-dot' : 'green-dot'} />
                        {isActive(run.status) ? 'LIVE' : 'SAVED'}
                      </span>
                    }
                  >
                    <Suspense fallback={<Loading />}>
                      {graph.data ? (
                        <FlowGraph graph={graph.data} />
                      ) : (
                        <Loading label="Building research graph" />
                      )}
                    </Suspense>
                    <div className="graph-legend">
                      <span>
                        <i className="completed" />
                        Complete
                      </span>
                      <span>
                        <i className="running" />
                        In progress
                      </span>
                      <span>
                        <i className="pending" />
                        Upcoming
                      </span>
                      <span className="graph-hint">Select a node to inspect its state</span>
                    </div>
                  </Panel>
                  <Panel
                    title="Live activity"
                    subtitle="Every meaningful step, as it happens."
                    className="live-panel"
                  >
                    <EventList events={events.data ?? []} compact />
                  </Panel>
                </div>
                <div className="workspace-lower">
                  <Panel title="Research plan" subtitle="The direction guiding this investigation.">
                    {run.state.plan && Object.keys(run.state.plan as Json).length ? (
                      <PlanContent plan={run.state.plan} />
                    ) : (
                      <Empty
                        title="The plan is taking shape"
                        description="Your team will turn the question into an actionable investigation."
                        icon={<Lightbulb size={24} />}
                      />
                    )}
                  </Panel>
                  <Panel
                    title="Run configuration"
                    subtitle="Boundaries make research reproducible."
                  >
                    <dl className="config-list">
                      <div>
                        <dt>Profile</dt>
                        <dd>{label(run.profile)}</dd>
                      </div>
                      <div>
                        <dt>Engine</dt>
                        <dd>
                          {run.profile === 'demo'
                            ? 'Demo fixture'
                            : run.config.engine === 'original' || run.provider === 'upstream'
                              ? 'Original upstream'
                              : run.config.execution_protocol === 2
                                ? 'Native generated experiment'
                                : 'Legacy protocol'}
                        </dd>
                      </div>
                      <div>
                        <dt>Provider</dt>
                        <dd>{run.provider}</dd>
                      </div>
                      <div>
                        <dt>Model</dt>
                        <dd>{run.model}</dd>
                      </div>
                      <div>
                        <dt>Started</dt>
                        <dd>{date(run.created_at)}</dd>
                      </div>
                      <div>
                        <dt>Last update</dt>
                        <dd>{date(run.updated_at)}</dd>
                      </div>
                      <div>
                        <dt>Run ID</dt>
                        <dd className="mono">{run.id}</dd>
                      </div>
                    </dl>
                  </Panel>
                </div>
              </>
            )}
            {section === 'ideas' && (
              <IdeasView
                ideas={ideas}
                selected={run.state.selected_idea as Idea | undefined}
                awaiting={awaiting}
                onReview={() => setApprovalOpen(true)}
              />
            )}
            {section === 'experiments' && (
              <ExperimentsView
                experiments={experiments.data ?? []}
                error={experiments.error}
                demo={run.profile === 'demo'}
              />
            )}
            {section === 'analytics' && (
              <AnalyticsView run={run} experiments={experiments.data ?? []} />
            )}
            {section === 'explainability' && (
              <ExplainView
                decisions={traces.data?.decisions ?? (run.state.decisions as Decision[]) ?? []}
                events={events.data ?? []}
                run={run}
                traceUrl={traces.data?.trace_url}
              />
            )}
            {section === 'paper' && (
              <PaperView key={run.id} run={run} artifacts={artifacts.data ?? []} />
            )}
            <ApprovalModal
              run={run}
              artifacts={artifacts.data ?? []}
              open={approvalOpen}
              onOpenChange={setApprovalOpen}
            />
          </>
        )
      )}
      <Modal
        open={cancelOpen}
        onOpenChange={setCancelOpen}
        title="Cancel this research run?"
        description="The current investigation will stop. Its existing events and artifacts will remain available."
      >
        <div className="modal-actions">
          <Button variant="secondary" onClick={() => setCancelOpen(false)}>
            Keep researching
          </Button>
          <Button
            variant="danger"
            onClick={() => action.mutate({ name: 'cancel' })}
            disabled={action.isPending}
          >
            Cancel run
          </Button>
        </div>
      </Modal>
    </>
  );
}
export function PlanContent({ plan }: { plan: unknown }) {
  if (typeof plan === 'string')
    return (
      <div className="prose">
        <p>{plan}</p>
      </div>
    );
  if (!plan || typeof plan !== 'object') return null;
  return (
    <div className="plan-content">
      {Object.entries(plan).map(([key, value]) => (
        <div key={key}>
          <h3>{label(key)}</h3>
          {Array.isArray(value) ? (
            <ul>
              {value.map((item, i) => (
                <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
              ))}
            </ul>
          ) : typeof value === 'object' ? (
            <CodeBlock value={value} />
          ) : (
            <p>{String(value)}</p>
          )}
        </div>
      ))}
    </div>
  );
}
export function EventList({ events, compact = false }: { events: RunEvent[]; compact?: boolean }) {
  if (!events.length)
    return (
      <Empty
        title="Listening for your team"
        description="Research events will appear here as the run progresses."
        icon={<Activity size={24} />}
      />
    );
  return (
    <div className={`event-list ${compact ? 'compact' : ''}`}>
      {[...events]
        .reverse()
        .slice(0, compact ? 15 : 100)
        .map((event) => (
          <div className="event-row" key={event.id}>
            <span className={`event-dot ${event.kind}`}>
              {event.kind === 'approval_required' ? (
                <ShieldCheck size={11} />
              ) : event.kind === 'node_completed' ? (
                <Check size={11} />
              ) : (
                <span />
              )}
            </span>
            <div>
              <span className="event-stage">{label(event.stage)}</span>
              <p>{event.message}</p>
              <time>{date(event.created_at)}</time>
            </div>
          </div>
        ))}
    </div>
  );
}
export function ApprovalModal({
  run,
  artifacts = [],
  open,
  onOpenChange,
}: {
  run: Run;
  artifacts?: Artifact[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const client = useQueryClient();
  const [ideaId, setIdeaId] = useState('');
  const [constraints, setConstraints] = useState('');
  const gate = String(run.approval?.gate ?? (run.state.approval as Json)?.gate ?? 'research_plan');
  const experiment = gate.includes('experiment') || gate === 'approval';
  const digest = approvalDigest(run);
  const requiresDigest =
    experiment && run.profile !== 'demo' && run.config.execution_protocol === 2;
  const missingDigest = requiresDigest && !digest;
  const mutation = useMutation({
    mutationFn: (approved: boolean) => {
      if (approved && missingDigest)
        throw new Error(
          'The frozen experiment approval digest is unavailable. Refresh the run or request a revision.',
        );
      return api.action(run.id, 'approve', {
        approved,
        idea_id: ideaId || undefined,
        constraints: constraints ? { user_instructions: constraints } : undefined,
        action: approved ? 'continue' : 'regenerate',
        approval_digest: experiment ? digest : undefined,
      });
    },
    onSuccess: async (updatedRun) => {
      await client.cancelQueries({ queryKey: ['run', run.id], exact: true });
      client.setQueryData(['run', run.id], updatedRun);
      onOpenChange(false);
      void client.invalidateQueries({ queryKey: ['run', run.id] });
    },
  });
  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={experiment ? 'Review the experiment design' : 'Review your research plan'}
      description="You set the direction. Review the proposal and add constraints before continuing."
    >
      <div className="approval-body">
        {experiment ? (
          <>
            <h3>Selected hypothesis</h3>
            <PlanContent plan={run.state.selected_idea ?? run.state.experiment_config} />
            <h3>Experiment configuration</h3>
            {run.config.execution_protocol === 2 && run.profile !== 'demo' ? (
              <FrozenExperimentReview run={run} />
            ) : (
              <CodeBlock value={run.state.experiment_config ?? {}} />
            )}
            <ArtifactList
              artifacts={artifacts.filter(
                (artifact) => artifact.name.endsWith('.py') && artifact.name.startsWith('baseline'),
              )}
            />
          </>
        ) : (
          <PlanContent plan={run.state.plan} />
        )}
        <label className="field">
          Additional guidance <span>Optional</span>
          <textarea
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
            rows={2}
            placeholder="Add constraints or feedback for your research team"
          />
        </label>
        {(run.state.ideas?.length ?? 0) > 0 && (
          <label className="field">
            Preferred idea <span>Optional</span>
            <select value={ideaId} onChange={(e) => setIdeaId(e.target.value)}>
              <option value="">Let the team select</option>
              {run.state.ideas!.map((idea) => (
                <option key={idea.id} value={idea.id}>
                  {idea.title}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <ErrorNotice
        error={
          mutation.error ||
          (missingDigest
            ? new Error(
                'Frozen evaluation is incomplete. Refresh this run or request a revision before approving.',
              )
            : null)
        }
      />
      <div className="modal-actions">
        <Button
          variant="secondary"
          onClick={() => mutation.mutate(false)}
          disabled={mutation.isPending}
        >
          <RefreshCw size={15} />
          Request revision
        </Button>
        <Button
          onClick={() => mutation.mutate(true)}
          disabled={mutation.isPending || missingDigest}
        >
          <Check size={16} />
          {mutation.isPending ? 'Continuing...' : 'Approve & continue'}
        </Button>
      </div>
    </Modal>
  );
}
function IdeasView({
  ideas,
  selected,
  awaiting,
  onReview,
}: {
  ideas: Idea[];
  selected?: Idea;
  awaiting: boolean;
  onReview: () => void;
}) {
  const [detail, setDetail] = useState<Idea>();
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Explore the possibilities</h2>
          <p>Hypotheses grounded in your research question, ready to investigate.</p>
        </div>
        <span className="muted">{ideas.length} ideas generated</span>
      </div>
      {!ideas.length ? (
        <Empty
          title="Good ideas take a little exploration"
          description="Your team's hypotheses will appear after the planning stage."
          icon={<Lightbulb size={26} />}
        />
      ) : (
        <div className="idea-grid">
          {ideas.map((idea, i) => (
            <div
              className={`idea-card ${selected?.id === idea.id ? 'selected' : ''}`}
              key={idea.id}
            >
              <div className="idea-top">
                <span className="idea-number">IDEA {String(i + 1).padStart(2, '0')}</span>
                {selected?.id === idea.id ? (
                  <Badge status="completed">Selected</Badge>
                ) : (
                  <Lightbulb size={18} />
                )}
              </div>
              <h3>{idea.title}</h3>
              <p>{idea.hypothesis ?? idea.description}</p>
              <div className="idea-scores">
                {[
                  ['Novelty', idea.novelty_score],
                  ['Feasibility', idea.feasibility_score],
                ].map(([name, score]) => (
                  <div key={String(name)}>
                    <span>{name}</span>
                    <strong>
                      {typeof score === 'number'
                        ? `${Math.round(score <= 1 ? score * 100 : score)}%`
                        : 'Not scored'}
                    </strong>
                    <span className="score-track">
                      <i
                        style={{
                          width: `${typeof score === 'number' ? (score <= 1 ? score * 100 : score) : 0}%`,
                        }}
                      />
                    </span>
                  </div>
                ))}
              </div>
              <Button variant="ghost" onClick={() => setDetail(idea)}>
                Explore idea
                <ArrowUpRight size={15} />
              </Button>
            </div>
          ))}
        </div>
      )}
      {awaiting && (
        <div className="info-note">
          <ShieldCheck size={18} />
          <p>Review the team's proposal to choose a hypothesis and continue.</p>
          <Button variant="secondary" onClick={onReview}>
            Review proposal
          </Button>
        </div>
      )}
      <Modal
        open={!!detail}
        onOpenChange={(open) => {
          if (!open) setDetail(undefined);
        }}
        title={detail?.title ?? 'Idea detail'}
        description="The hypothesis and rationale behind this proposal."
      >
        {detail && (
          <>
            <div className="prose">
              <h3>Hypothesis</h3>
              <p>{detail.hypothesis ?? detail.description}</p>
              <h3>Rationale</h3>
              <p>
                {detail.rationale ??
                  'The team has not recorded additional rationale for this idea.'}
              </p>
            </div>
            <CodeBlock value={detail} />
          </>
        )}
      </Modal>
    </>
  );
}
function ExperimentsView({
  experiments,
  error,
  demo,
}: {
  experiments: Experiment[];
  error: unknown;
  demo: boolean;
}) {
  const [selected, setSelected] = useState<Experiment>();
  const [tab, setTab] = useState('overview');
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Test. Measure. Learn.</h2>
          <p>Reproducible experiments with configurations, metrics, and logs.</p>
        </div>
        {demo && <Badge status="demo">Prerecorded fixture</Badge>}
      </div>
      <ErrorNotice error={error} />
      {experiments.length ? (
        <Panel>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Experiment</th>
                  <th>Status</th>
                  <th>Metrics</th>
                  <th>Started</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {experiments.map((exp, i) => (
                  <tr
                    key={exp.id}
                    onClick={() => {
                      setSelected(exp);
                      setTab('overview');
                    }}
                    className="clickable"
                  >
                    <td>
                      <button className="table-title" onClick={() => setSelected(exp)}>
                        Experiment {String(i + 1).padStart(2, '0')}
                      </button>
                      <small>{exp.hypothesis}</small>
                    </td>
                    <td>
                      <Badge status={exp.status} />
                    </td>
                    <td>
                      <div className="metric-chips">
                        {Object.entries(numericMetrics(exp.metrics))
                          .slice(0, 3)
                          .map(([key, value]) => (
                            <span key={key}>
                              {label(key)}
                              <strong>
                                {typeof value === 'number'
                                  ? Number(value.toFixed(4))
                                  : String(value)}
                              </strong>
                            </span>
                          ))}
                      </div>
                    </td>
                    <td>{date(exp.started_at)}</td>
                    <td>
                      <ArrowUpRight size={16} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      ) : (
        <Empty
          title="The lab is ready for an experiment"
          description="Approve the research plan and experiment design to begin collecting evidence."
          icon={<FlaskConical size={28} />}
        />
      )}
      <Modal
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(undefined);
        }}
        title="Experiment detail"
        description={selected?.hypothesis ?? 'Inspect the configuration and resulting evidence.'}
      >
        {selected && (
          <>
            <div className="mini-tabs">
              {['overview', 'configuration', 'logs'].map((x) => (
                <button key={x} onClick={() => setTab(x)} className={tab === x ? 'active' : ''}>
                  {label(x)}
                </button>
              ))}
            </div>
            {tab === 'overview' ? (
              <>
                <Badge status={selected.status} />
                <div className="experiment-metrics">
                  {Object.entries(numericMetrics(selected.metrics)).map(([key, value]) => (
                    <div key={key}>
                      <span>{label(key)}</span>
                      <strong>
                        {typeof value === 'number' ? Number(value.toFixed(6)) : String(value)}
                      </strong>
                    </div>
                  ))}
                </div>
                <ErrorNotice error={selected.error} />
              </>
            ) : tab === 'configuration' ? (
              <Suspense fallback={<Loading />}>
                <Editor
                  height="340px"
                  language="json"
                  theme={document.documentElement.dataset.theme === 'light' ? 'light' : 'vs-dark'}
                  value={JSON.stringify(selected.configuration, null, 2)}
                  options={{
                    readOnly: true,
                    minimap: { enabled: false },
                    fontSize: 12,
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </Suspense>
            ) : (
              <CodeBlock
                value={
                  Array.isArray(selected.logs)
                    ? selected.logs.join('\n')
                    : selected.logs || 'No logs recorded.'
                }
              />
            )}
          </>
        )}
      </Modal>
    </>
  );
}
function AnalyticsView({ run, experiments }: { run: Run; experiments: Experiment[] }) {
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Let the evidence speak.</h2>
          <p>
            {run.profile === 'demo'
              ? 'Demo values are prerecorded fixtures; they are not measured scientific evidence.'
              : 'Compare reported outcomes across your investigation.'}
          </p>
        </div>
        {run.profile === 'demo' && <Badge status="demo">Prerecorded demo metrics</Badge>}
      </div>
      <div className="stats-grid analytics-stats">
        {[
          ['Experiments', experiments.length],
          ['Completed', experiments.filter((e) => e.status === 'completed').length],
          ['Reported input tokens', formatNumber(run.usage.input_tokens)],
          ['Reported output tokens', formatNumber(run.usage.output_tokens)],
        ].map(([name, value]) => (
          <div className="stat-card" key={String(name)}>
            <span>{name}</span>
            <strong>{value}</strong>
            <small>Recorded for this run</small>
          </div>
        ))}
      </div>
      <Panel
        title="Experiment comparison"
        subtitle="Reported numeric values from the experiment record."
      >
        {experiments.some((e) => Object.keys(numericMetrics(e.metrics)).length) ? (
          <Suspense fallback={<Loading />}>
            <MetricsChart experiments={experiments} />
          </Suspense>
        ) : (
          <Empty
            title="Evidence is on its way"
            description="Charts appear when completed experiments report numeric metrics."
            icon={<Activity size={25} />}
          />
        )}
      </Panel>
      <div className="workspace-lower">
        <Panel
          title="Analysis & findings"
          subtitle="Interpretation backed by recorded experiment results."
        >
          {run.state.analysis ? (
            <PlanContent plan={run.state.analysis} />
          ) : (
            <Empty
              title="Analysis will follow the evidence"
              description="Your team's interpretation appears after the experiments complete."
            />
          )}
        </Panel>
        <Panel title="Usage against budget" subtitle="Live totals, bounded by your configuration.">
          <div className="budget-usage">
            {[
              [
                'Model calls',
                Number(run.usage.calls ?? run.usage.calls_used ?? run.usage.llm_calls) || 0,
                run.config.budgets?.max_llm_calls,
              ],
              [
                'Input token reservations',
                Number(run.usage.reserved_input_tokens ?? run.usage.input_tokens) || 0,
                run.config.budgets?.max_input_tokens,
              ],
              [
                'Output token reservations',
                Number(run.usage.reserved_output_tokens ?? run.usage.output_tokens) || 0,
                run.config.budgets?.max_output_tokens,
              ],
              ['Experiments', experiments.length, run.config.budgets?.max_experiments],
            ].map(([name, value, max]) => (
              <div key={String(name)}>
                <div>
                  <span>{name}</span>
                  <strong>
                    {formatNumber(value)} <small>/ {formatNumber(max)}</small>
                  </strong>
                </div>
                <span className="score-track">
                  <i
                    style={{ width: `${Math.min(100, (Number(value) / Number(max)) * 100) || 0}%` }}
                  />
                </span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </>
  );
}
function ExplainView({
  decisions,
  events,
  run,
  traceUrl,
}: {
  decisions: Decision[];
  events: RunEvent[];
  run: Run;
  traceUrl?: string;
}) {
  const [stateOpen, setStateOpen] = useState(false);
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>A clear line from question to decision.</h2>
          <p>Inspect the recorded rationale, state, and execution trail behind your findings.</p>
        </div>
        <Button variant="secondary" onClick={() => setStateOpen(true)}>
          <Code2 size={15} />
          Inspect state
        </Button>
      </div>
      <div className="explain-grid">
        <Panel title="Decision journal" subtitle={`${decisions.length} recorded decisions`}>
          {decisions.length ? (
            <div className="decision-list">
              {decisions.map((d, i) => (
                <article key={d.id ?? i}>
                  <span className="decision-number">{String(i + 1).padStart(2, '0')}</span>
                  <div>
                    <div className="decision-meta">
                      <Badge status="completed">{label(d.stage ?? 'decision')}</Badge>
                      <span>{date(d.created_at)}</span>
                    </div>
                    <h3>
                      {String(
                        d.summary ?? d.decision ?? d.message ?? d.title ?? 'Research decision',
                      )}
                    </h3>
                    <p>
                      {String(
                        d.rationale ??
                          d.reasoning ??
                          d.reason ??
                          'Inspect the recorded evidence associated with this step.',
                      )}
                    </p>
                    {(d.evidence !== undefined || d.data !== undefined) && (
                      <CodeBlock value={d.evidence ?? d.data} />
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <Empty
              title="Decisions, with their reasoning"
              description="The team will record meaningful choices as research progresses."
              icon={<ShieldCheck size={26} />}
            />
          )}
        </Panel>
        <Panel title="Execution timeline" subtitle="The sequence behind the science.">
          <EventList events={events} />
        </Panel>
      </div>
      {traceUrl && (
        <a href={traceUrl} target="_blank" rel="noreferrer" className="button secondary">
          Open detailed trace
          <ArrowUpRight size={15} />
        </a>
      )}
      <Modal
        open={stateOpen}
        onOpenChange={setStateOpen}
        title="Research state snapshot"
        description="The current persisted graph state. Export it to inspect or reproduce this investigation."
      >
        <CodeBlock value={run.state} />
        <Button
          variant="secondary"
          onClick={() =>
            downloadText(
              `${run.id}-state.json`,
              JSON.stringify(run.state, null, 2),
              'application/json',
            )
          }
        >
          <ArrowDownToLine size={15} />
          Export state
        </Button>
      </Modal>
    </>
  );
}
export function PaperView({ run, artifacts }: { run: Run; artifacts: Artifact[] }) {
  const native = run.profile === 'free_research' && !!run.state.paper;
  const presentation = useQuery({
    queryKey: ['report', run.id],
    queryFn: () => api.report(run.id),
    enabled: native,
  });
  const paper = native
    ? (presentation.data?.markdown ?? '')
    : typeof run.state.paper === 'string'
      ? run.state.paper
      : '';
  const [mode, setMode] = useState('preview');
  const [draft, setDraft] = useState(() => localStorage.getItem(`paper-draft-${run.id}`) ?? '');
  const [isDraft, setIsDraft] = useState(() => !!localStorage.getItem(`paper-draft-${run.id}`));
  const [editorVersion, setEditorVersion] = useState(0);
  useEffect(() => {
    if (!isDraft) {
      setDraft(paper);
      setEditorVersion((version) => version + 1);
    }
  }, [paper, isDraft]);
  const save = (value: string | undefined) => {
    setDraft(value ?? '');
    setIsDraft(true);
    localStorage.setItem(`paper-draft-${run.id}`, value ?? '');
  };
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>From discovery to a paper.</h2>
          <p>Your findings, methods, and evidence, ready to share.</p>
        </div>
        <div className="heading-actions">
          {isDraft && <Badge status="paused">Local draft</Badge>}
          <Button
            variant="secondary"
            disabled={!draft}
            onClick={() => downloadText(`${run.id}-paper.md`, draft)}
          >
            <ArrowDownToLine size={15} />
            Markdown
          </Button>
          <Button variant="secondary" disabled={!draft} onClick={() => window.print()}>
            <FileText size={15} />
            Print / PDF
          </Button>
        </div>
      </div>
      <ErrorNotice error={presentation.error} />
      {native && presentation.isPending && <Loading />}
      {native && presentation.data && (
        <p className="info-note">
          Final report uses the approved contract and trusted measurements. Historical proposals are
          labeled separately. Original immutable report artifacts remain unchanged.
          {presentation.data.original_artifact_id && (
            <a href={`/api/artifacts/${presentation.data.original_artifact_id}/download`}>
              Download original report
            </a>
          )}
        </p>
      )}
      <div className="paper-layout">
        <Panel className="paper-panel">
          <div className="paper-toolbar">
            <div className="mini-tabs">
              <button
                className={mode === 'preview' ? 'active' : ''}
                onClick={() => setMode('preview')}
              >
                Preview
              </button>
              <button className={mode === 'edit' ? 'active' : ''} onClick={() => setMode('edit')}>
                Edit markdown
              </button>
            </div>
            {isDraft && (
              <Button
                variant="ghost"
                className="small"
                onClick={() => {
                  localStorage.removeItem(`paper-draft-${run.id}`);
                  setIsDraft(false);
                  setDraft(paper);
                }}
              >
                Reset to generated paper
              </Button>
            )}
            <span className="muted">
              {draft ? draft.split(/\s+/).filter(Boolean).length : 0} words
            </span>
          </div>
          {!draft && mode === 'preview' ? (
            <Empty
              title="A paper grounded in your results"
              description="When the investigation is complete, the generated manuscript will appear here."
              icon={<FileText size={28} />}
            />
          ) : mode === 'edit' ? (
            <>
              <div className="info-note">
                <Info size={15} />
                <p>
                  Edits are saved as a local draft in this browser. Download Markdown to share your
                  changes.
                </p>
              </div>
              <Suspense fallback={<Loading />}>
                <Editor
                  key={`${run.id}:${editorVersion}`}
                  height="650px"
                  language="markdown"
                  defaultValue={draft}
                  onChange={save}
                  theme={document.documentElement.dataset.theme === 'light' ? 'light' : 'vs-dark'}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 13,
                    wordWrap: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                  }}
                />
              </Suspense>
            </>
          ) : (
            <article className="paper-document">
              {run.profile === 'demo' && (
                <div className="paper-demo-notice">
                  DEMONSTRATION REPORT · DETERMINISTIC LOCAL WORKFLOW
                </div>
              )}
              <Markdown content={draft} />
            </article>
          )}
        </Panel>
        <aside>
          <Panel
            title="Research artifacts"
            subtitle={`${artifacts.length} files in this investigation`}
          >
            <ArtifactList artifacts={artifacts} />
          </Panel>
          <div className="paper-note">
            <ShieldCheck size={21} />
            <strong>Keep the evidence close.</strong>
            <p>
              Review all claims against your experiments before sharing. A generated paper is a
              starting point for your own scientific review.
            </p>
          </div>
        </aside>
      </div>
    </>
  );
}
function markdownInline(content: string) {
  return content
    .split(/(\*\*.*?\*\*|`[^`]+`)/g)
    .map((part, index) =>
      part.startsWith('**') ? (
        <strong key={index}>{part.slice(2, -2)}</strong>
      ) : part.startsWith('`') ? (
        <code key={index}>{part.slice(1, -1)}</code>
      ) : (
        part
      ),
    );
}
export function Markdown({ content }: { content: string }) {
  const blocks = content
    .replace(/([^\n])\n(?=\|[^\n]+\n\|[ \t:|\-]+\|?[ \t]*\n)/g, '$1\n\n')
    .split(/\n\s*\n/);
  return (
    <>
      {blocks.map((block, i) => {
        if (block.startsWith('```'))
          return <pre key={i}>{block.replace(/^```[^\n]*\n?/, '').replace(/```$/, '')}</pre>;
        if (block.startsWith('### ')) return <h3 key={i}>{block.slice(4)}</h3>;
        if (block.startsWith('## ')) return <h2 key={i}>{block.slice(3)}</h2>;
        if (block.startsWith('# ')) return <h1 key={i}>{block.slice(2)}</h1>;
        const lines = block.trim().split('\n');
        const cells = (line: string) =>
          line
            .trim()
            .replace(/^\||\|$/g, '')
            .split('|')
            .map((cell) => cell.trim());
        if (
          lines.length >= 2 &&
          lines[0].startsWith('|') &&
          cells(lines[1]).every((cell) => /^:?-{3,}:?$/.test(cell))
        ) {
          const header = cells(lines[0]);
          return (
            <table className="paper-table" key={i}>
              <thead>
                <tr>
                  {header.map((cell, index) => (
                    <th key={index} scope="col">
                      {markdownInline(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {lines
                  .slice(2)
                  .filter((line) => line.trim().startsWith('|'))
                  .map((line, row) => (
                    <tr key={row}>
                      {cells(line).map((cell, column) => (
                        <td key={column}>{markdownInline(cell)}</td>
                      ))}
                    </tr>
                  ))}
              </tbody>
            </table>
          );
        }
        if (block.match(/^[-*] /))
          return (
            <ul key={i}>
              {block.split('\n').map((line, j) => (
                <li key={j}>{line.replace(/^[-*] /, '')}</li>
              ))}
            </ul>
          );
        if (block.match(/^\d+\. /))
          return (
            <ol key={i}>
              {block.split('\n').map((line, j) => (
                <li key={j}>{line.replace(/^\d+\. /, '')}</li>
              ))}
            </ol>
          );
        if (block.startsWith('> ')) return <blockquote key={i}>{block.slice(2)}</blockquote>;
        return <p key={i}>{markdownInline(block)}</p>;
      })}
    </>
  );
}

function ProviderSelection({ run }: { run: Run }) {
  const client = useQueryClient();
  const [provider, setProvider] = useState(run.provider);
  const [model, setModel] = useState('');
  const models = useQuery({ queryKey: ['models', provider], queryFn: () => api.models(provider) });
  const selection = useMutation({
    mutationFn: () =>
      request<Run>(`/runs/${encodeURIComponent(run.id)}/model`, {
        method: 'PATCH',
        body: JSON.stringify({ provider, model }),
      }),
    onSuccess: (updated) => {
      client.setQueryData(['run', run.id], updated);
    },
  });
  return (
    <Panel title="Choose another provider/model">
      <p>
        This replaces the selection for all future research calls. The same budget and reservations
        remain. Resume separately to verify generation.
      </p>
      <ErrorNotice error={models.error || selection.error} />
      <label className="field">
        Provider
        <select
          value={provider}
          onChange={(e) => {
            setProvider(e.target.value);
            setModel('');
          }}
        >
          {['gemini', 'groq', 'ollama'].map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </label>
      <label className="field">
        Discovered model (generation unverified)
        <select value={model} onChange={(e) => setModel(e.target.value)}>
          <option value="" disabled>
            Select a model
          </option>
          {models.data?.map((name) => (
            <option key={name}>{name}</option>
          ))}
        </select>
      </label>
      <Button disabled={!model || selection.isPending} onClick={() => selection.mutate()}>
        Save provider/model
      </Button>
      {selection.isSuccess && (
        <p role="status">Selection saved. Resume to run a budgeted generation preflight.</p>
      )}
    </Panel>
  );
}
