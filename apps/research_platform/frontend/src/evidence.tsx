import { lazy, Suspense, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ArrowDownToLine, Code2, FileText, ShieldCheck } from 'lucide-react';
import { Badge, CodeBlock, Empty, ErrorNotice, Loading, Modal, Panel } from './ui';
import { formatNumber, label } from './api';
import type { Artifact, Json, Run } from './types';
const Editor = lazy(() => import('./editor'));
export function record(value: unknown): Json {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    ? (value as Json)
    : {};
}
export function approvalDigest(run: Run): string | undefined {
  const payload = record(run.approval?.payload);
  const plan = record(run.state.experiment_config);
  const values = [
    run.approval?.approval_digest,
    payload.approval_digest,
    record(payload.experiment_config).approval_digest,
    plan.approval_digest,
  ].filter((value) => value !== undefined && value !== null);
  if (
    !values.length ||
    values.some((value) => typeof value !== 'string' || !/^[a-f0-9]{64}$/.test(value)) ||
    new Set(values).size !== 1
  )
    return undefined;
  return values[0] as string;
}
export function FeasibilityNotice({ value }: { value: unknown }) {
  const state = record(value);
  if (typeof state.supported !== 'boolean') return null;
  return (
    <Panel
      title="Research feasibility"
      subtitle="The supported computational scope of this question."
    >
      <div className="evidence-review">
        <Badge status={state.supported ? 'completed' : 'failed'}>
          {state.supported ? 'Supported computational study' : 'Unsupported request'}
        </Badge>
        <p>{String(state.scope_statement ?? state.reason ?? '')}</p>
        {Boolean(state.scope_statement) && Boolean(state.reason) && (
          <p className="muted">{String(state.reason)}</p>
        )}
        {Array.isArray(state.limitations) && (
          <div>
            <h3>Limits of the study</h3>
            <ul>
              {state.limitations.map((item, index) => (
                <li key={index}>{String(item)}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Panel>
  );
}
export function FrozenExperimentReview({ run }: { run: Run }) {
  const plan = record(run.state.experiment_config);
  const spec = record(plan.spec);
  const evaluation = record(spec.evaluation);
  const validation = record(plan.evaluation_validation);
  const digest = approvalDigest(run);
  return (
    <div className="evidence-review">
      <div className="info-note">
        <ShieldCheck size={18} />
        <p>
          Approval binds this question, generated baseline, frozen evaluation rules, and dataset
          commitment. A changed design or dataset requires a new approval.
        </p>
      </div>
      <dl className="config-list">
        <div>
          <dt>Research question</dt>
          <dd>{String(spec.research_question ?? run.state.question ?? 'Not recorded')}</dd>
        </div>
        <div>
          <dt>Protocol</dt>
          <dd>{label(typeof spec.protocol === 'string' ? spec.protocol : undefined)}</dd>
        </div>
        <div>
          <dt>Evaluation metric</dt>
          <dd>{label(typeof evaluation.metric === 'string' ? evaluation.metric : undefined)}</dd>
        </div>
        <div>
          <dt>Baseline SHA-256</dt>
          <dd className="mono">{String(plan.baseline_sha256 ?? 'Not recorded')}</dd>
        </div>
        <div>
          <dt>Dataset commitment</dt>
          <dd className="mono">{String(validation.dataset_sha256 ?? 'Not frozen')}</dd>
        </div>
        <div>
          <dt>Approval digest</dt>
          <dd className="mono" data-testid="approval-digest">
            {digest ?? 'Unavailable'}
          </dd>
        </div>
      </dl>
      <h3>Frozen specification and evaluation</h3>
      <CodeBlock
        value={{
          spec: plan.spec,
          evaluation_contract: plan.evaluation_contract,
          evaluation_validation: plan.evaluation_validation,
        }}
      />
    </div>
  );
}
export function isTextArtifact(artifact: Artifact) {
  return (
    artifact.media_type.startsWith('text/') ||
    ['application/json', 'application/x-python', 'application/javascript'].includes(
      artifact.media_type,
    ) ||
    /\.(py|json|md|txt|log|csv|tex|yaml|yml)$/i.test(artifact.name)
  );
}
export async function artifactText(artifact: Artifact): Promise<string> {
  if (artifact.size_bytes > 512 * 1024)
    throw new Error(
      'This artifact is too large for the source preview. Download it to inspect locally.',
    );
  const url = new URL(artifact.download_url, window.location.origin);
  if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/'))
    throw new Error('Artifact preview requires a download URL from this research API.');
  const response = await fetch(url.pathname + url.search, {
    credentials: 'same-origin',
    redirect: 'error',
  });
  if (!response.ok) throw new Error('Artifact download failed (HTTP ' + response.status + ').');
  const content = await response.text();
  if (new TextEncoder().encode(content).length > 512 * 1024)
    throw new Error('Artifact preview exceeded its size limit.');
  return content;
}
export function ArtifactList({ artifacts }: { artifacts: Artifact[] }) {
  const [selected, setSelected] = useState<Artifact>();
  const source = useQuery({
    queryKey: ['artifact-source', selected?.id],
    queryFn: () => artifactText(selected!),
    enabled: !!selected,
    staleTime: Infinity,
  });
  return (
    <>
      {artifacts.length ? (
        <div className="artifact-list">
          {artifacts.map((artifact) => (
            <div className="artifact-row" key={artifact.id}>
              <span className="artifact-icon">
                <FileText size={18} />
              </span>
              <div>
                <strong>{artifact.name}</strong>
                <small>
                  {label(artifact.kind)} / {formatNumber(artifact.size_bytes / 1024)} KB
                </small>
              </div>
              {isTextArtifact(artifact) && (
                <button
                  className="icon-button"
                  aria-label={'Inspect source ' + artifact.name}
                  title="Inspect source"
                  onClick={() => setSelected(artifact)}
                >
                  <Code2 size={16} />
                </button>
              )}
              <a
                className="icon-button"
                href={artifact.download_url}
                download
                aria-label={'Download ' + artifact.name}
              >
                <ArrowDownToLine size={16} />
              </a>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          title="Artifacts will land here"
          description="Inspect generated Python, evaluation contracts, logs, and reports as they become available."
        />
      )}
      <Modal
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(undefined);
        }}
        title={selected?.name ?? 'Artifact source'}
        description="Read-only source from the recorded research artifact. Previewing never executes this program."
      >
        <ErrorNotice error={source.error} />
        {source.isLoading ? (
          <Loading label="Loading recorded source" />
        ) : (
          source.data !== undefined && (
            <Suspense fallback={<Loading />}>
              <Editor
                height="440px"
                language={
                  selected?.name.endsWith('.py')
                    ? 'python'
                    : selected?.name.endsWith('.json')
                      ? 'json'
                      : selected?.name.endsWith('.md')
                        ? 'markdown'
                        : 'plaintext'
                }
                value={source.data}
                theme={document.documentElement.dataset.theme === 'light' ? 'light' : 'vs-dark'}
                options={{
                  readOnly: true,
                  minimap: { enabled: false },
                  fontSize: 12,
                  wordWrap: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                }}
              />
            </Suspense>
          )
        )}
      </Modal>
    </>
  );
}
