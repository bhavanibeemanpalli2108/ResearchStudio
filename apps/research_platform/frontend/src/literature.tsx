import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { request } from './api';
import { Button, ErrorNotice, PageHeading, Panel } from './ui';

export interface Paper {
  id: string;
  selection_id: string | null;
  title: string;
  authors: string[];
  year: number | null;
  doi: string | null;
  url: string;
  source: string;
  abstract: string | null;
  abstract_source: string | null;
  abstract_truncated: boolean;
  retrieved_at: string;
  provenance: { source: string; source_id: string; retrieved_at: string }[];
}
const STORAGE = 'reseon-selected-papers';
export function readSelectedPapers(): Paper[] {
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE) ?? '[]');
    return Array.isArray(value)
      ? value
          .filter(
            (p) =>
              p &&
              typeof p.title === 'string' &&
              typeof p.selection_id === 'string' &&
              /^[a-f0-9]{64}$/.test(p.selection_id),
          )
          .slice(0, 10)
      : [];
  } catch {
    return [];
  }
}
export function storeSelectedPapers(papers: Paper[]) {
  localStorage.setItem(STORAGE, JSON.stringify(papers));
}

export function LiteraturePage() {
  const [topic, setTopic] = useState('');
  const [selected, setSelected] = useState<Paper[]>(readSelectedPapers);
  const search = useMutation({
    mutationFn: (query: string) =>
      request<{ papers: Paper[]; warnings: string[]; cached: boolean }>('/literature/search', {
        method: 'POST',
        body: JSON.stringify({ query, limit: 10 }),
      }),
  });
  const toggle = (paper: Paper) => {
    const next = selected.some((p) => p.id === paper.id)
      ? selected.filter((p) => p.id !== paper.id)
      : [...selected, paper];
    if (next.length <= 10) {
      setSelected(next);
      storeSelectedPapers(next);
    }
  };
  return (
    <>
      <PageHeading
        eyebrow="SCHOLARLY SOURCES"
        title="Literature"
        description="Search public OpenAlex and Crossref metadata. Retrieval does not verify findings, relevance or novelty."
      />
      <Panel>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            search.mutate(topic.trim());
          }}
        >
          <label className="field">
            Research topic or DOI
            <input
              value={topic}
              onChange={(event) => setTopic(event.target.value)}
              minLength={3}
              maxLength={500}
              required
              placeholder="e.g. shortest processing time scheduling"
            />
          </label>
          <Button type="submit" disabled={search.isPending || topic.trim().length < 3}>
            {search.isPending ? 'Searching…' : 'Search literature'}
          </Button>
        </form>
        <p>
          Up to 10 papers. Two bounded public requests per uncached search; no model calls or paid
          API keys. Abstract excerpts are shown only when supplied by a source and may be
          copyrighted.
        </p>
        <ErrorNotice error={search.error} />
        {search.data?.warnings.map((warning) => (
          <p role="status" key={warning}>
            {warning}
          </p>
        ))}
        {search.data && (
          <p role="status">
            {search.data.papers.length} papers retrieved{search.data.cached ? ' (cached)' : ''}.
          </p>
        )}
      </Panel>
      <Panel title={`Selected papers (${selected.length}/10)`}>
        {selected.length ? (
          <>
            <ul>
              {selected.map((p) => (
                <li key={p.selection_id}>
                  {p.title}{' '}
                  <Button variant="ghost" onClick={() => toggle(p)}>
                    Remove {p.title}
                  </Button>
                </li>
              ))}
            </ul>
            <Link className="button primary" to="/create?profile=free_research">
              Use selected papers in research
            </Link>
          </>
        ) : (
          <p>Select papers to attach their source metadata to a new native research run.</p>
        )}
        <p>
          Selection alone starts no research or generation. You will review the question, provider,
          budget and approval gates before launching.
        </p>
      </Panel>
      {search.data?.papers.map((paper) => (
        <Panel key={paper.id}>
          <article>
            <h2>{paper.title}</h2>
            <p>
              {paper.authors.length ? paper.authors.join(', ') : 'Authors unavailable'} ·{' '}
              {paper.year ?? 'Year unavailable'}
            </p>
            <p>
              {[...new Set(paper.provenance.map((p) => p.source))].join(' + ')} · Retrieved{' '}
              {paper.retrieved_at}
            </p>
            <p>DOI: {paper.doi ?? 'Unavailable'}</p>
            <a href={paper.url} target="_blank" rel="noreferrer">
              Open original source
            </a>
            {paper.abstract ? (
              <details>
                <summary>
                  Source abstract{paper.abstract_truncated ? ' excerpt' : ''} (
                  {paper.abstract_source})
                </summary>
                <p>{paper.abstract}</p>
              </details>
            ) : (
              <p>Abstract unavailable from retrieved metadata.</p>
            )}
            <label>
              <input
                type="checkbox"
                aria-label={`Select ${paper.title}`}
                checked={selected.some((p) => p.id === paper.id)}
                disabled={
                  !paper.selection_id ||
                  (selected.length >= 10 && !selected.some((p) => p.id === paper.id))
                }
                onChange={() => toggle(paper)}
              />{' '}
              Select for research context
            </label>
          </article>
        </Panel>
      ))}
    </>
  );
}
