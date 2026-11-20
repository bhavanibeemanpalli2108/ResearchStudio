import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  ChevronRight,
  FlaskConical,
  Info,
  LockKeyhole,
  Play,
  ShieldCheck,
  Sparkles,
  Zap,
} from 'lucide-react';
import { api, label } from './api';
import { Badge, Button, ErrorNotice, PageHeading, Panel } from './ui';
import type { Budget, Project, RunRequest } from './types';
const demoQuestion =
  'How do two reviewed square-grid configurations compare when packing 26 non-overlapping circles inside a unit square?';
const researchQuestion =
  'Can a linear predictor reduce held-out root mean squared error compared with a constant training-mean baseline on reproducible synthetic regression data?';
const defaults: Budget = {
  max_llm_calls: 20,
  max_input_tokens: 32000,
  max_output_tokens: 16000,
  max_iterations: 2,
  max_experiments: 3,
  max_runtime_seconds: 300,
};
export function CreatePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [step, setStep] = useState(0);
  const [title, setTitle] = useState('');
  const [question, setQuestion] = useState('');
  const [domain, setDomain] = useState(
    params.get('profile') === 'free_research' ? 'Regression' : 'Optimization',
  );
  const [objectives, setObjectives] = useState('');
  const [references, setReferences] = useState('');
  const [profile, setProfile] = useState(
    params.get('profile') === 'free_research' ? 'free_research' : 'demo',
  );
  const [provider, setProvider] = useState(
    params.get('profile') === 'free_research' ? 'groq' : 'mock',
  );
  const [model, setModel] = useState(
    params.get('profile') === 'free_research' ? 'openai/gpt-oss-20b' : 'mock-researcher',
  );
  const [budgets, setBudgets] = useState<Budget>(defaults);
  const [requireApproval, setRequireApproval] = useState(true);
  const [generateReport, setGenerateReport] = useState(true);
  const [constraints, setConstraints] = useState('');
  const [validation, setValidation] = useState('');
  const [savedProject, setSavedProject] = useState<Project>();
  const existing = useQuery({
    queryKey: ['project', params.get('project')],
    queryFn: () => api.project(params.get('project')!),
    enabled: !!params.get('project'),
  });
  const providers = useQuery({ queryKey: ['providers'], queryFn: api.providers });
  const models = useQuery({ queryKey: ['models', provider], queryFn: () => api.models(provider) });
  useEffect(() => {
    if (existing.data) {
      setTitle(existing.data.title);
      setQuestion(existing.data.question);
      setDomain(existing.data.domain);
      setObjectives(existing.data.objectives.join('\n'));
      setReferences(existing.data.references.join('\n'));
      setSavedProject(existing.data);
    }
  }, [existing.data]);
  const mutation = useMutation({
    mutationFn: async () => {
      const project =
        savedProject ??
        (await api.createProject({
          title: title.trim(),
          question: question.trim(),
          domain,
          objectives: objectives
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean),
          references: references
            .split('\n')
            .map((s) => s.trim())
            .filter(Boolean),
        }));
      setSavedProject(project);
      const request: RunRequest = {
        execution_protocol: 2,
        engine: 'native',
        profile,
        provider,
        model,
        budgets,
        generate_report: generateReport,
        require_approval: profile !== 'demo' || requireApproval,
        constraints: constraints ? { user_instructions: constraints } : {},
      };
      return api.createRun(project.id, request);
    },
    onSuccess: (run) => {
      void client.invalidateQueries({ queryKey: ['projects'] });
      void client.invalidateQueries({ queryKey: ['runs'] });
      navigate(`/workspace/${run.id}`);
    },
  });
  const next = () => {
    if (step === 0 && (!title.trim() || question.trim().length < 10)) {
      setValidation('Give your project a title and a research question of at least 10 characters.');
      return;
    }
    if (step === 1 && !model.trim()) {
      setValidation('Explicitly select a model for the chosen provider.');
      return;
    }
    setValidation('');
    setStep((s) => Math.min(s + 1, 2));
  };
  const setMode = (mode: string) => {
    setProfile(mode);
    if (mode === 'demo') {
      setProvider('mock');
      setModel('mock-researcher');
      setBudgets(defaults);
    } else {
      setRequireApproval(true);
      setProvider('groq');
      setModel('openai/gpt-oss-20b');
      if (question === demoQuestion) {
        setQuestion(researchQuestion);
        setTitle('Linear prediction study');
        setDomain('Regression');
        setObjectives(
          'Freeze a reproducible training and test split\nCompare baseline and candidate test error under the same evaluator',
        );
      }
      setBudgets({
        ...defaults,
        max_llm_calls: 20,
        max_experiments: mode === 'full_research' ? 8 : 3,
        max_runtime_seconds: mode === 'full_research' ? 1800 : 300,
      });
    }
  };
  const useExample = () => {
    const genuine = profile === 'free_research';
    setTitle(genuine ? 'Linear prediction study' : 'Circle-packing optimization study');
    setQuestion(genuine ? researchQuestion : demoQuestion);
    setObjectives(
      genuine
        ? 'Freeze a reproducible training and test split\nCompare baseline and candidate test error under the same evaluator'
        : 'Compare the reviewed 7-by-4 and 6-by-5 grid configurations for 26 circles\nMeasure total radii and verify non-overlap constraints',
    );
    setDomain(genuine ? 'Regression' : 'Optimization');
  };
  return (
    <>
      <PageHeading
        eyebrow="A NEW LINE OF INQUIRY"
        title="What will you discover?"
        description="Set the direction. Your research team will take it from there."
      />
      <div className="create-layout">
        <div>
          <ol className="wizard-steps">
            {['Frame your question', 'Configure your team', 'Review & launch'].map((name, i) => (
              <li key={name} className={step === i ? 'active' : step > i ? 'done' : ''}>
                <span>{step > i ? <Check size={14} /> : i + 1}</span>
                {name}
                {i < 2 && <ChevronRight size={14} />}
              </li>
            ))}
          </ol>
          <ErrorNotice error={mutation.error} />
          {validation && (
            <div role="alert" className="error-notice">
              {validation}
            </div>
          )}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (step < 2) next();
              else mutation.mutate();
            }}
          >
            {step === 0 && (
              <Panel
                title="A clear question is a powerful start."
                subtitle="Be specific about what you want to understand, compare, or improve."
              >
                <div className="form-content">
                  <div className="example-callout">
                    <FlaskConical size={19} />
                    <div>
                      <strong>
                        {profile === 'free_research'
                          ? 'Start with a regression question.'
                          : 'Just exploring? Start with a demo question.'}
                      </strong>
                      <p>
                        {profile === 'free_research'
                          ? 'Generate programs and freeze the evaluation before you approve execution.'
                          : 'A prerecorded circle-packing fixture demonstrates the workflow.'}
                      </p>
                    </div>
                    <Button type="button" variant="secondary" onClick={useExample}>
                      Use example
                      <ArrowRight size={14} />
                    </Button>
                  </div>
                  <label className="field">
                    Project title <span>Required</span>
                    <input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      placeholder="e.g. Circle-packing optimization study"
                      minLength={3}
                      maxLength={180}
                      required
                    />
                  </label>
                  <label className="field">
                    Research question <span>Required</span>
                    <textarea
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      placeholder="What hypothesis would you like to investigate? Include the context and what success looks like."
                      rows={5}
                      minLength={10}
                      required
                    />
                    <small>
                      A focused, testable question helps your team design better experiments.
                    </small>
                  </label>
                  <label className="field">
                    Research domain
                    <select value={domain} onChange={(e) => setDomain(e.target.value)}>
                      {[
                        'Regression',
                        'Scheduling',
                        'Machine learning',
                        'Computer science',
                        'Optimization',
                        'Data science',
                        'Physics',
                        'Mathematics',
                        'Interdisciplinary',
                      ].map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    Research objectives <span>Optional</span>
                    <textarea
                      value={objectives}
                      onChange={(e) => setObjectives(e.target.value)}
                      placeholder="One objective per line"
                      rows={3}
                    />
                  </label>
                  <label className="field">
                    Reference links <span>Optional</span>
                    <textarea
                      value={references}
                      onChange={(e) => setReferences(e.target.value)}
                      placeholder="One paper or source URL per line"
                      rows={2}
                    />
                  </label>
                </div>
              </Panel>
            )}
            {step === 1 && (
              <>
                <Panel
                  title="Choose your research profile"
                  subtitle="Start small, or make room for a deeper investigation."
                >
                  <div className="profile-choices">
                    {[
                      {
                        id: 'demo',
                        title: 'Demo',
                        icon: Play,
                        description:
                          'A prerecorded 26-circle packing fixture demonstrates the workflow. No API keys.',
                        tag: 'NO MODEL COST',
                      },
                      {
                        id: 'free_research',
                        title: 'Free research',
                        icon: Zap,
                        description:
                          'Generate and test question-specific Python for synthetic regression or scheduling in isolated Docker.',
                        tag: 'PROVIDER QUOTAS APPLY',
                      },
                      {
                        id: 'full_research',
                        title: 'Full research',
                        icon: Sparkles,
                        description:
                          'Web launch unavailable. Use the trusted upstream CLI, then import its results.',
                        tag: 'UPSTREAM CLI ONLY',
                      },
                    ].map(({ id, title, icon: Icon, description, tag }) => (
                      <label
                        className={`profile-choice ${profile === id ? 'selected' : ''}`}
                        key={id}
                      >
                        <input
                          type="radio"
                          name="profile"
                          value={id}
                          disabled={id === 'full_research'}
                          checked={profile === id}
                          onChange={() => setMode(id)}
                        />
                        <Icon size={21} />
                        <strong>{title}</strong>
                        <p>{description}</p>
                        <span>{tag}</span>
                      </label>
                    ))}
                  </div>
                </Panel>
                <Panel
                  title="Model & execution"
                  subtitle="Your provider credentials stay in the local backend."
                >
                  <div className="form-content">
                    {profile === 'free_research' && (
                      <div className="info-note">
                        <Info size={17} />
                        <p>
                          Your question must pass a feasibility check. Supported regression and
                          scheduling studies generate Python programs, freeze a shared evaluator,
                          and require approval of the exact experiment digest before isolated
                          execution. Unsupported requests stop with an explanation. Provider quota
                          and billing terms still apply.
                        </p>
                      </div>
                    )}
                    <label className="field">
                      Research engine
                      <select value="native" disabled>
                        <option value="native">
                          {profile === 'demo'
                            ? 'Demonstration fixture (mock)'
                            : 'Native generated experiment engine'}
                        </option>
                        <option value="original" disabled>
                          Original upstream engine - remote worker unavailable
                        </option>
                      </select>
                      <small>
                        Original-engine execution requires an operator-configured isolated worker.
                        Existing upstream evidence can still be imported.
                      </small>
                    </label>
                    <ErrorNotice error={models.error} />
                    {provider === 'groq' && (
                      <p role="status">
                        Groq requires verified Free-plan eligibility before any request. A
                        configured model does not establish generation readiness or free quota.
                        Verify Billing in Groq Console and follow the local setup guide.
                      </p>
                    )}
                    <div className="form-row">
                      <label className="field">
                        Provider
                        <select
                          aria-label="Provider"
                          value={provider}
                          onChange={(e) => {
                            setProvider(e.target.value);
                            setModel('');
                          }}
                          disabled={profile === 'demo'}
                        >
                          {(providers.data?.length
                            ? providers.data.filter((p) => profile === 'demo' || p.id !== 'mock')
                            : [
                                { id: 'mock', name: 'Mock (demo)' },
                                { id: 'gemini', name: 'Google Gemini' },
                                { id: 'groq', name: 'Groq' },
                                { id: 'ollama', name: 'Ollama' },
                              ]
                          ).map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.name ?? label(p.id)}
                              {p.id !== 'mock' && !p.available && !p.configured
                                ? ' · not configured'
                                : ''}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="field">
                        Model
                        {models.data?.length ? (
                          <select
                            aria-label="Model"
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            required
                          >
                            <option value="" disabled>
                              Select a discovered model
                            </option>
                            {models.data.map((m) => (
                              <option key={m} value={m}>
                                {m}
                                {provider !== 'mock'
                                  ? provider === 'groq'
                                    ? ' · configured (unverified)'
                                    : ' · discovered (unverified)'
                                  : ''}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            aria-label="Model"
                            value={model}
                            onChange={(e) => setModel(e.target.value)}
                            placeholder="Model ID"
                            required
                          />
                        )}
                      </label>
                    </div>
                    {profile !== 'demo' && (
                      <p>
                        The configured choice and discovery do not verify generation. On each worker
                        start or approval resume, a bounded generation preflight for the selected
                        model consumes a run-ledger call. These calls share the default 20-call
                        budget. Failures retain reservations and pause research; choose another
                        provider/model explicitly. Groq selection applies to the native engine.
                      </p>
                    )}
                    {profile === 'demo' && (
                      <div className="info-note">
                        <Info size={17} />
                        <p>
                          Demo uses prerecorded 26-circle packing fixture values. These values
                          illustrate the workflow; they are not measured scientific evidence.
                        </p>
                      </div>
                    )}
                    <div className="field-divider" />
                    <h3 className="form-subheading">Research budgets</h3>
                    <div className="budget-grid">
                      {(Object.keys(budgets) as (keyof Budget)[]).map((key) => (
                        <label className="field" key={key}>
                          {label(key.replace('max_', ''))}
                          <input
                            type="number"
                            min={key.includes('tokens') ? 128 : key.includes('runtime') ? 10 : 1}
                            max={
                              key === 'max_input_tokens'
                                ? 32000
                                : key === 'max_output_tokens'
                                  ? 16000
                                  : key === 'max_runtime_seconds'
                                    ? 7200
                                    : key === 'max_llm_calls'
                                      ? 20
                                      : 10
                            }
                            value={budgets[key]}
                            onChange={(e) =>
                              setBudgets((b) => ({
                                ...b,
                                [key]: Math.max(1, Number(e.target.value)),
                              }))
                            }
                            required
                          />
                        </label>
                      ))}
                    </div>
                    <label className="field">
                      Additional constraints <span>Optional</span>
                      <textarea
                        value={constraints}
                        onChange={(e) => setConstraints(e.target.value)}
                        placeholder="e.g. CPU only; prioritize interpretability; avoid external datasets"
                        rows={3}
                      />
                    </label>
                    <label className="check-field">
                      <input
                        type="checkbox"
                        checked={profile !== 'demo' || requireApproval}
                        onChange={(e) => setRequireApproval(e.target.checked)}
                        disabled={profile !== 'demo'}
                      />
                      <span>
                        <strong>Keep me in the loop</strong>
                        <small>
                          Pause for approval of the research plan and experiment design.
                        </small>
                      </span>
                      <ShieldCheck size={19} />
                    </label>
                    <label className="check-field">
                      <input
                        type="checkbox"
                        checked={generateReport}
                        onChange={(e) => setGenerateReport(e.target.checked)}
                      />
                      <span>
                        <strong>Generate a research paper</strong>
                        <small>Write a report from the findings and collected evidence.</small>
                      </span>
                    </label>
                  </div>
                </Panel>
              </>
            )}
            {step === 2 && (
              <Panel
                title="Your team is ready."
                subtitle="Take a moment to review the direction before launching."
              >
                <div className="review-project">
                  <span className="domain-icon">
                    <FlaskConical size={22} />
                  </span>
                  <div>
                    <span className="overline">{domain}</span>
                    <h2>{title}</h2>
                    <p>{question}</p>
                  </div>
                </div>
                <div className="review-grid">
                  <div>
                    <small>RESEARCH PROFILE</small>
                    <strong>{label(profile)}</strong>
                    {profile === 'demo' && <Badge status="demo">Demonstration</Badge>}
                  </div>
                  <div>
                    <small>MODEL PROVIDER</small>
                    <strong>{label(provider)}</strong>
                    <span>{model}</span>
                  </div>
                  <div>
                    <small>EXPERIMENT BUDGET</small>
                    <strong>Up to {budgets.max_experiments} experiments</strong>
                    <span>
                      {budgets.max_iterations} iterations · {budgets.max_runtime_seconds}s runtime
                    </span>
                  </div>
                  <div>
                    <small>YOUR INVOLVEMENT</small>
                    <strong>
                      {requireApproval ? 'Approval at key stages' : 'Autonomous execution'}
                    </strong>
                    <span>
                      {generateReport ? 'Paper generation enabled' : 'Paper generation disabled'}
                    </span>
                  </div>
                </div>
                <div className="info-note">
                  <ShieldCheck size={18} />
                  <p>
                    {profile === 'demo'
                      ? 'This is a local demo. No external model calls or model charges are incurred.'
                      : 'Runs are bounded by your configured budgets. Free-tier providers may still enforce their own quotas.'}{' '}
                    {requireApproval ? 'You will review the plan before experiments begin.' : ''}
                  </p>
                </div>
              </Panel>
            )}
            <div className="wizard-footer">
              {step > 0 ? (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setStep((s) => s - 1)}
                  disabled={mutation.isPending}
                >
                  <ArrowLeft size={15} />
                  Back
                </Button>
              ) : (
                <Link to="/" className="button ghost">
                  Cancel
                </Link>
              )}
              <span>Step {step + 1} of 3</span>
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending
                  ? 'Starting your research...'
                  : step === 2
                    ? 'Launch research'
                    : 'Continue'}
                {step === 2 ? <Play size={15} /> : <ArrowRight size={15} />}
              </Button>
            </div>
          </form>
        </div>
        <aside className="create-aside">
          <span className="aside-symbol">
            <Sparkles size={28} />
          </span>
          <h2>
            Big questions.
            <br />
            Clear next steps.
          </h2>
          <p>
            Research Studio connects the whole discovery process in a single, observable workspace.
          </p>
          <ul>
            <li>
              <Check size={16} />
              Trace every decision
            </li>
            <li>
              <Check size={16} />
              Review before execution
            </li>
            <li>
              <Check size={16} />
              Reproduce every experiment
            </li>
            <li>
              <Check size={16} />
              Keep your data local
            </li>
          </ul>
          <div>
            <LockKeyhole size={17} />
            <span>Provider keys are never sent to the frontend.</span>
          </div>
        </aside>
      </div>
    </>
  );
}
