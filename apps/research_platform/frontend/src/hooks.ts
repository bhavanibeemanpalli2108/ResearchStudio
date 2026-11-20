import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, isActive } from './api';
export const useProjects = () =>
  useQuery({ queryKey: ['projects'], queryFn: api.projects, refetchInterval: 10000 });
export function useRun(id: string | undefined) {
  const client = useQueryClient();
  const query = useQuery({
    queryKey: ['run', id],
    queryFn: () => api.run(id!),
    enabled: !!id,
    refetchInterval: (q) => (q.state.data && isActive(q.state.data.status) ? 2000 : false),
  });
  useEffect(() => {
    if (!id || (query.data && !isActive(query.data.status))) return;
    const stream = new EventSource(`/api/runs/${encodeURIComponent(id)}/stream`);
    const refresh = () => {
      void client.invalidateQueries({ queryKey: ['run', id] });
      void client.invalidateQueries({ queryKey: ['events', id] });
      void client.invalidateQueries({ queryKey: ['graph', id] });
      void client.invalidateQueries({ queryKey: ['experiments', id] });
      void client.invalidateQueries({ queryKey: ['artifacts', id] });
      void client.invalidateQueries({ queryKey: ['traces', id] });
    };
    stream.onmessage = refresh;
    for (const kind of [
      'event',
      'node_started',
      'node_completed',
      'approval_required',
      'decision',
      'completed',
    ])
      stream.addEventListener(kind, refresh);
    return () => stream.close();
  }, [id, client, query.data?.status]);
  return query;
}
