import { useMemo, useState } from 'react';
import {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MiniMap,
  Position,
  ReactFlow,
  type NodeProps,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Check,
  Clock3,
  FlaskConical,
  GitBranch,
  Lightbulb,
  LoaderCircle,
  ShieldCheck,
} from 'lucide-react';
import { label, numericMetrics } from './api';
import { CodeBlock, Modal } from './ui';
import type { Experiment, Graph } from './types';
function ResearchNode({ data }: NodeProps) {
  const status = String(data.status ?? 'pending');
  const name = String(data.label ?? 'Research stage');
  const Icon = name.toLowerCase().includes('experiment')
    ? FlaskConical
    : name.toLowerCase().includes('idea')
      ? Lightbulb
      : GitBranch;
  return (
    <div className={`research-node ${status}`}>
      <Handle type="target" position={Position.Left} />
      <span className="research-node-icon">
        <Icon size={17} />
      </span>
      <div>
        <strong>{name}</strong>
        <small>{label(status)}</small>
      </div>
      <span className="node-status-icon">
        {status === 'completed' ? (
          <Check size={14} />
        ) : status === 'running' ? (
          <LoaderCircle className="spin" size={14} />
        ) : status === 'awaiting_approval' ? (
          <ShieldCheck size={14} />
        ) : (
          <Clock3 size={13} />
        )}
      </span>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
const nodeTypes = { research: ResearchNode };
export function FlowGraph({ graph }: { graph: Graph }) {
  const [selected, setSelected] = useState<string>();
  const [showControls, setShowControls] = useState(false);
  const nodes = useMemo(
    () =>
      graph.nodes
        .filter((n) => showControls || n.id !== 'pause')
        .map((n, i) => ({
          id: n.id,
          type: 'research',
          data: { label: n.label, status: n.status },
          position: { x: (i % 3) * 265, y: Math.floor(i / 3) * 135 },
        })),
    [graph.nodes, showControls],
  );
  const edges = useMemo(
    () =>
      graph.edges
        .filter(
          (e) =>
            (showControls || e.kind !== 'control') &&
            nodes.some((n) => n.id === e.source) &&
            nodes.some((n) => n.id === e.target),
        )
        .map((e, i) => ({
          ...e,
          id: `edge-${i}`,
          type: 'smoothstep',
          animated: graph.nodes.find((n) => n.id === e.target)?.status === 'running',
          style: {
            stroke:
              graph.nodes.find((n) => n.id === e.source)?.status === 'completed'
                ? '#6f9e8e'
                : '#4c554f',
            strokeWidth: 1.5,
          },
        })),
    [graph.edges, graph.nodes, nodes, showControls],
  );
  return (
    <>
      <div className="flow-canvas">
        <button
          className="graph-controls-toggle"
          onClick={() => setShowControls((value) => !value)}
          aria-pressed={showControls}
        >
          {showControls ? 'Hide control routes' : 'Show control routes'}
        </button>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={1.5}
          nodesDraggable={false}
          nodesConnectable={false}
          onNodeClick={(_event, node) => setSelected(node.id)}
          colorMode={document.documentElement.dataset.theme === 'light' ? 'light' : 'dark'}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--graph-dot)" />
          <Controls showInteractive={false} />
          <MiniMap
            nodeColor={(node) =>
              node.data.status === 'completed'
                ? '#79aa96'
                : node.data.status === 'running'
                  ? '#9eb8f1'
                  : '#3b4540'
            }
            maskColor="transparent"
          />
        </ReactFlow>
      </div>
      <Modal
        open={!!selected}
        onOpenChange={(open) => {
          if (!open) setSelected(undefined);
        }}
        title={graph.nodes.find((n) => n.id === selected)?.label ?? 'Research node'}
        description="Current persisted state associated with this stage."
      >
        <CodeBlock
          value={
            selected && graph.state?.[selected] !== undefined
              ? graph.state[selected]
              : { node: graph.nodes.find((n) => n.id === selected), state: graph.state }
          }
        />
      </Modal>
    </>
  );
}
const colors = ['#9eb8f1', '#88bfa8', '#e2b988', '#b9a6e3', '#8bc2ce', '#d7949b'];
export function MetricsChart({ experiments }: { experiments: Experiment[] }) {
  const keys = Array.from(
    new Set(
      experiments.flatMap((e) =>
        Object.entries(numericMetrics(e.metrics))
          .filter(([, v]) => typeof v === 'number' && Number.isFinite(v))
          .map(([k]) => k),
      ),
    ),
  );
  const [metric, setMetric] = useState(keys[0] ?? '');
  const data = experiments.map((e, i) => ({ name: `Exp ${i + 1}`, ...numericMetrics(e.metrics) }));
  return (
    <div className="chart-content">
      <div className="chart-toolbar">
        <span className="muted">Measured values · no normalization</span>
        <label className="chart-select">
          Metric
          <select
            aria-label="Chart metric"
            value={metric}
            onChange={(e) => setMetric(e.target.value)}
          >
            {keys.map((k) => (
              <option key={k} value={k}>
                {label(k)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 15, right: 20, bottom: 5, left: 8 }}>
          <defs>
            <linearGradient id="metricGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colors[0]} stopOpacity={0.2} />
              <stop offset="100%" stopColor={colors[0]} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--border)" strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="name"
            tick={{ fill: 'var(--muted)', fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            dy={10}
          />
          <YAxis
            tick={{ fill: 'var(--muted)', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={70}
            tickFormatter={(v) => Number(v).toPrecision(3)}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--panel)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text)',
              fontSize: 12,
            }}
            formatter={(value) => [
              typeof value === 'number' ? Number(value.toFixed(6)) : value,
              label(metric),
            ]}
          />
          <Legend formatter={() => label(metric)} wrapperStyle={{ fontSize: 12, paddingTop: 22 }} />
          <Area
            type="monotone"
            dataKey={metric}
            name={label(metric)}
            stroke={colors[0]}
            strokeWidth={2}
            fill="url(#metricGradient)"
            dot={{ r: 4, strokeWidth: 2, fill: 'var(--panel)' }}
            activeDot={{ r: 6 }}
            connectNulls={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
