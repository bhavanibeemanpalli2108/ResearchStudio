import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  Clock3,
  FlaskConical,
  FolderOpen,
  GitBranch,
  Globe2,
  KeyRound,
  Layers3,
  Lightbulb,
  Play,
  Plus,
  RefreshCw,
  Search,
  Server,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { api, formatNumber, isActive, label } from './api';
import { useProjects } from './hooks';
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
import type { Project, Run } from './types';
export function useRuns() {
  return useQuery({ queryKey: ['runs'], queryFn: () => api.runs(), refetchInterval: 4000 });
}
const iconFor = (domain: string) =>
  domain.toLowerCase().includes('machine')
    ? GitBranch
    : domain.toLowerCase().includes('computer')
      ? Layers3
      : Globe2;
export function ProjectCard({ project, runs }: { project: Project; runs: Run[] }) {
  const run = runs.filter((r) => r.project_id === project.id)[0];
  const Icon = iconFor(project.domain);
  return (
    <Link to={run ? `/workspace/${run.id}` : `/projects/${project.id}`} className="project-card">
      <div className="project-card-top">
        <span className="domain-icon">
          <Icon size={19} />
        </span>
        {run ? <Badge status={run.status} /> : <span className="badge">Ready to start</span>}
        <ArrowUpRight size={17} className="project-arrow" />
      </div>
      <span className="overline">{project.domain || 'Interdisciplinary'}</span>
      <h3>{project.title}</h3>
      <p>{project.question}</p>
      <div className="project-card-footer">
        <span>
          <FlaskConical size={13} />
          {runs.filter((r) => r.project_id === project.id).length} runs
        </span>
        <span>{date(project.created_at).split(',')[0]}</span>
      </div>
    </Link>
  );
}
export function Dashboard() {
  const projects = useProjects();
  const runs = useRuns();
  const usage = useQuery({ queryKey: ['usage'], queryFn: api.usage, refetchInterval: 5000 });
  const allRuns = runs.data ?? [];
  const active = allRuns.filter((r) => isActive(r.status));
  const completed = allRuns.filter((r) => r.status === 'completed');
  const stats = [
    {
      label: 'Research projects',
      value: projects.data?.length ?? 0,
      icon: FolderOpen,
      detail: 'Questions being explored',
    },
    {
      label: 'Active runs',
      value: active.length,
      icon: Activity,
      detail: active.length ? 'Research in progress' : 'Ready when you are',
    },
    {
      label: 'Completed runs',
      value: completed.length,
      icon: CheckCircle2,
      detail: 'Reproducible results',
    },
    {
      label: 'Model calls',
      value: formatNumber(usage.data?.calls ?? usage.data?.calls_used ?? usage.data?.llm_calls),
      icon: Zap,
      detail: `${formatNumber(usage.data?.total_tokens ?? (Number(usage.data?.input_tokens) || 0) + (Number(usage.data?.output_tokens) || 0))} tokens reported`,
    },
  ];
  return (
    <>
      <PageHeading
        eyebrow="YOUR RESEARCH, CONNECTED"
        title="A little curiosity. A lot of possibility."
        description="Turn your next question into ideas, experiments, and evidence."
        actions={
          <Link to="/create" className="button primary">
            <Plus size={17} />
            New research
          </Link>
        }
      />
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="hero-kicker">
            <span className="green-dot" />
            DISCOVERY STARTS HERE
          </span>
          <h2>
            Ask a question.
            <br />
            Build the evidence.
          </h2>
          <p>
            Your AI research team, with you in the loop. Explore hypotheses, follow every decision,
            and turn findings into a paper.
          </p>
          <Link to="/create" className="button primary">
            Start a research project
            <ArrowRight size={16} />
          </Link>
          <span className="hero-note">
            <ShieldCheck size={13} />
            Local-first · Open source · Fully observable
          </span>
        </div>
        <div
          className="hero-diagram"
          aria-label="Research process: question to ideas, experiments and discovery"
        >
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="diagram-core">
            <span>
              <Sparkles size={29} />
            </span>
            <small>YOUR NEXT</small>
            <strong>discovery</strong>
          </div>
          <span className="diagram-node question">
            <BookOpen size={17} />A good question
          </span>
          <span className="diagram-node ideas">
            <Lightbulb size={17} />
            Fresh hypotheses
          </span>
          <span className="diagram-node experiment">
            <FlaskConical size={17} />
            Real experiments
          </span>
          <span className="diagram-dot d1" />
          <span className="diagram-dot d2" />
          <span className="diagram-dot d3" />
        </div>
      </section>
      <div className="stats-grid">
        {stats.map(({ label: title, value, icon: Icon, detail }) => (
          <div className="stat-card" key={title}>
            <div>
              <span>{title}</span>
              <Icon size={17} />
            </div>
            <strong>{value}</strong>
            <small>{detail}</small>
          </div>
        ))}
      </div>
      <div className="dashboard-columns">
        <section>
          <div className="section-heading">
            <div>
              <h2>
                Your research projects <span>{projects.data?.length ?? 0}</span>
              </h2>
              <p>A home for every question worth asking.</p>
            </div>
            <Link to="/history" className="text-link">
              View all
              <ArrowUpRight size={15} />
            </Link>
          </div>
          <ErrorNotice
            error={projects.error}
            retry={() => {
              void projects.refetch();
            }}
          />
          {projects.isLoading ? (
            <Loading />
          ) : projects.data?.length ? (
            <div className="project-grid">
              {projects.data.slice(0, 4).map((project) => (
                <ProjectCard key={project.id} project={project} runs={allRuns} />
              ))}
            </div>
          ) : (
            <div className="first-project">
              <span className="empty-icon">
                <FolderOpen size={25} />
              </span>
              <div>
                <h3>Your next discovery belongs here</h3>
                <p>Create a project to keep ideas, experiments, and evidence together.</p>
              </div>
              <Link to="/create" className="button secondary">
                <Plus size={15} />
                Create a project
              </Link>
            </div>
          )}
          <div className="section-heading recent-heading">
            <div>
              <h2>Recent activity</h2>
              <p>The latest from your research team.</p>
            </div>
            <Clock3 size={17} />
          </div>
          <Panel>
            {allRuns.length ? (
              <div className="activity-list">
                {allRuns.slice(0, 4).map((run) => (
                  <Link to={`/workspace/${run.id}`} key={run.id}>
                    <span className={`activity-icon ${run.status}`}>
                      <Activity size={15} />
                    </span>
                    <div>
                      <strong>
                        {projects.data?.find((p) => p.id === run.project_id)?.title ??
                          'Research run'}
                      </strong>
                      <p>
                        {label(run.current_stage)}
                        <span>·</span>
                        {date(run.updated_at)}
                      </p>
                    </div>
                    <Badge status={run.status} />
                    <ChevronRight size={16} />
                  </Link>
                ))}
              </div>
            ) : (
              <Empty
                title="A quiet lab, for now"
                description="Your team's progress will appear here when a run starts."
                icon={<Activity size={23} />}
              />
            )}
          </Panel>
        </section>
        <aside className="dashboard-aside">
          <Panel title="The discovery loop" subtitle="Small steps. Meaningful progress.">
            <ol className="discovery-steps">
              {[
                {
                  icon: BookOpen,
                  title: 'Frame your question',
                  text: 'Give your team a clear direction.',
                },
                {
                  icon: Lightbulb,
                  title: 'Explore the possibilities',
                  text: 'Review and refine proposed ideas.',
                },
                {
                  icon: FlaskConical,
                  title: 'Test with evidence',
                  text: 'Run reproducible experiments.',
                },
                {
                  icon: ArrowDownToLine,
                  title: 'Share what you learned',
                  text: 'Export your paper and artifacts.',
                },
              ].map(({ icon: Icon, title, text }, i) => (
                <li key={title}>
                  <span>
                    <Icon size={16} />
                  </span>
                  <div>
                    <small>0{i + 1}</small>
                    <strong>{title}</strong>
                    <p>{text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </Panel>
          <div className="demo-callout">
            <span className="demo-icon">
              <Play size={18} />
            </span>
            <span className="overline">EXPLORE WITHOUT API KEYS</span>
            <h3>Meet your research team.</h3>
            <p>Try the complete workflow with a deterministic demo. No setup, no model charges.</p>
            <Link to="/create?profile=demo" className="text-link">
              Launch a demo
              <ArrowRight size={15} />
            </Link>
          </div>
        </aside>
      </div>
    </>
  );
}
export function HistoryPage() {
  const { projectId } = useParams();
  const projects = useProjects();
  const runs = useRuns();
  const [search, setSearch] = useState('');
  const project = projects.data?.find((p) => p.id === projectId);
  const visible = projects.data?.filter(
    (p) =>
      (!projectId || p.id === projectId) &&
      `${p.title} ${p.domain}`.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading
        eyebrow="THE RESEARCH LIBRARY"
        title={project?.title ?? 'Every question has a home.'}
        description={project?.question ?? 'Browse your projects and pick up where you left off.'}
        actions={
          <Link
            to={projectId ? `/create?project=${projectId}` : '/create'}
            className="button primary"
          >
            <Plus size={16} />
            {projectId ? 'New run' : 'New research'}
          </Link>
        }
      />
      <div className="toolbar">
        <div className="search-field">
          <Search size={16} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search your projects..."
            aria-label="Filter projects"
          />
        </div>
        <span className="muted">{visible?.length ?? 0} projects</span>
        <Button
          variant="ghost"
          onClick={() => {
            void projects.refetch();
            void runs.refetch();
          }}
          aria-label="Refresh projects"
        >
          <RefreshCw size={16} />
        </Button>
      </div>
      <ErrorNotice error={projects.error} />
      {projects.isLoading ? (
        <Loading />
      ) : visible?.length ? (
        <div className="project-grid library-grid">
          {visible.map((p) => (
            <ProjectCard key={p.id} project={p} runs={runs.data ?? []} />
          ))}
        </div>
      ) : (
        <Empty
          title="No projects found"
          description="A research project starts with a question. What are you curious about?"
          action={
            <Link to="/create" className="button primary">
              Create research project
            </Link>
          }
        />
      )}
      {projectId && (
        <Panel title="Run history" subtitle="Each run keeps its own evidence and configuration.">
          <RunTable runs={(runs.data ?? []).filter((r) => r.project_id === projectId)} />
        </Panel>
      )}
      <ImportPanel projects={projects.data ?? []} />
    </>
  );
}
export function RunTable({ runs }: { runs: Run[] }) {
  if (!runs.length)
    return (
      <Empty
        title="No research runs yet"
        description="Create a run to turn this question into a reproducible investigation."
      />
    );
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Run</th>
            <th>Profile / provider</th>
            <th>Current stage</th>
            <th>Status</th>
            <th>Started</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>
                <Link to={`/workspace/${run.id}`} className="table-title">
                  {run.id.slice(0, 12)}
                </Link>
              </td>
              <td>
                {label(run.profile)}
                <small>
                  {run.provider} · {run.model}
                </small>
              </td>
              <td>{label(run.current_stage)}</td>
              <td>
                <Badge status={run.status} />
              </td>
              <td>{date(run.created_at)}</td>
              <td>
                <Link to={`/workspace/${run.id}`} aria-label={`Open run ${run.id}`}>
                  <ArrowUpRight size={17} />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export function SettingsPage() {
  const providers = useQuery({ queryKey: ['providers'], queryFn: api.providers });
  const capabilities = useQuery({ queryKey: ['capabilities'], queryFn: api.capabilities });
  const usage = useQuery({ queryKey: ['usage'], queryFn: api.usage });
  return (
    <>
      <PageHeading
        eyebrow="YOUR RESEARCH ENVIRONMENT"
        title="Ready for the way you work."
        description="Check provider availability, inspect usage, and keep your research portable."
      />
      <div className="settings-grid">
        <Panel
          title="Model providers"
          subtitle="Credentials stay on your backend. Only configuration status is shown here."
        >
          <ErrorNotice error={providers.error} />
          {providers.isLoading ? (
            <Loading />
          ) : (
            <div className="provider-list">
              {providers.data?.map((p) => (
                <div key={p.id}>
                  <span className="provider-icon">
                    {p.id === 'mock' ? <FlaskConical size={20} /> : <Server size={20} />}
                  </span>
                  <div>
                    <strong>{p.name ?? label(p.id)}</strong>
                    <p>
                      {p.id === 'mock'
                        ? 'Deterministic local demonstration'
                        : (p.reason ?? 'Configure credentials in your local environment')}
                    </p>
                  </div>
                  <Badge
                    status={
                      p.available || p.configured || p.id === 'mock' ? 'completed' : 'pending'
                    }
                  >
                    {p.available || p.configured || p.id === 'mock'
                      ? 'Configured'
                      : 'Not configured'}
                  </Badge>
                </div>
              ))}
            </div>
          )}
          <div className="info-note">
            <KeyRound size={17} />
            <p>
              Set GEMINI_API_KEY or GROQ_API_KEY in your local environment. Ollama uses your local
              service. Restart the backend after changes. Configured credentials do not guarantee
              provider connectivity or free quota.
            </p>
          </div>
        </Panel>
        <Panel title="Usage & portability" subtitle="Your local workspace, at a glance.">
          <dl className="settings-facts">
            <div>
              <dt>Model calls</dt>
              <dd>{formatNumber(usage.data?.calls ?? usage.data?.llm_calls)}</dd>
            </div>
            <div>
              <dt>Reported input tokens</dt>
              <dd>{formatNumber(usage.data?.input_tokens)}</dd>
            </div>
            <div>
              <dt>Reported output tokens</dt>
              <dd>{formatNumber(usage.data?.output_tokens)}</dd>
            </div>
            <div>
              <dt>Estimated cost (USD)</dt>
              <dd>
                {usage.data?.estimated_cost == null
                  ? 'Unknown'
                  : Number(usage.data.estimated_cost).toFixed(4)}
              </dd>
            </div>
            <div>
              <dt>Unreported token estimate</dt>
              <dd>{formatNumber(usage.data?.estimated_tokens)}</dd>
            </div>
          </dl>
          <Button
            variant="secondary"
            onClick={() =>
              downloadText(
                'research-usage.json',
                JSON.stringify(usage.data ?? {}, null, 2),
                'application/json',
              )
            }
          >
            <ArrowDownToLine size={16} />
            Export usage
          </Button>
        </Panel>
        <Panel title="System capabilities" subtitle="Live information from your connected backend.">
          <ErrorNotice error={capabilities.error} />
          {capabilities.isLoading ? <Loading /> : <CodeBlock value={capabilities.data} />}
        </Panel>
        <Panel
          title="Built to be observable"
          subtitle="Understand every step of the investigation."
        >
          <div className="settings-description">
            <ShieldCheck size={30} />
            <h3>Evidence you can trace.</h3>
            <p>
              Every run keeps its graph state, decisions, experiment configurations, and artifacts.
              Full research runs use the trusted upstream CLI. Import their evidence or open the
              original Run Inspector to explore them.
            </p>
            <a
              href="http://127.0.0.1:8765"
              target="_blank"
              rel="noreferrer"
              className="button secondary"
            >
              Open Run Inspector
              <ArrowUpRight size={16} />
            </a>
          </div>
        </Panel>
      </div>
    </>
  );
}

function ImportPanel({ projects }: { projects: Project[] }) {
  const [open, setOpen] = useState(false);
  const [upstreamId, setUpstreamId] = useState('');
  const [projectId, setProjectId] = useState('');
  const navigate = useNavigate();
  const client = useQueryClient();
  const upstream = useQuery({ queryKey: ['upstream'], queryFn: api.upstream, enabled: open });
  const mutation = useMutation({
    mutationFn: async () => {
      let target = projectId;
      if (!target) {
        const source = upstream.data?.runs.find((r) => r.id === upstreamId);
        const project = await api.createProject({
          title: 'Imported ' + (source?.task ?? 'research') + ' results',
          question:
            'Review and compare evidence from an existing upstream Agentic Scientist research run.',
          domain: 'Computer science',
          objectives: ['Inspect imported numeric evidence'],
          references: [],
        });
        target = project.id;
      }
      return api.importRun(target, upstreamId);
    },
    onSuccess: (run) => {
      void client.invalidateQueries({ queryKey: ['projects'] });
      void client.invalidateQueries({ queryKey: ['runs'] });
      setOpen(false);
      navigate('/workspace/' + run.id);
    },
  });
  return (
    <>
      <div className="import-callout">
        <span className="domain-icon">
          <ArrowDownToLine size={19} />
        </span>
        <div>
          <h3>Already have upstream research?</h3>
          <p>Bring existing Agentic Scientist results into this workspace.</p>
        </div>
        <Button variant="secondary" onClick={() => setOpen(true)}>
          Import existing run
          <ArrowUpRight size={14} />
        </Button>
      </div>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Bring your research together"
        description="Import numeric evidence from a run in the configured upstream results directory. The original files stay in place."
      >
        <ErrorNotice error={upstream.error || mutation.error} />
        {upstream.isLoading ? (
          <Loading />
        ) : upstream.data?.runs.length ? (
          <>
            <label className="field">
              Upstream run
              <select value={upstreamId} onChange={(e) => setUpstreamId(e.target.value)}>
                <option value="">Choose an existing run</option>
                {upstream.data.runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.task} ? {r.agent} ? {r.run_id}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Destination project
              <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
                <option value="">Create a new imported project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.title}
                  </option>
                ))}
              </select>
            </label>
            <div className="modal-actions">
              <Button variant="secondary" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={() => mutation.mutate()}
                disabled={!upstreamId || mutation.isPending}
              >
                {mutation.isPending ? 'Importing evidence?' : 'Import evidence'}
                <ArrowRight size={15} />
              </Button>
            </div>
          </>
        ) : (
          <Empty
            title="No upstream runs found"
            description="Run the trusted upstream CLI with your own isolated worker, then return here to import its results."
            icon={<FolderOpen size={25} />}
            action={
              <a
                className="button secondary"
                href={upstream.data?.inspector_url ?? 'http://127.0.0.1:8765'}
                target="_blank"
                rel="noreferrer"
              >
                Open Run Inspector
                <ArrowUpRight size={15} />
              </a>
            }
          />
        )}
      </Modal>
    </>
  );
}
