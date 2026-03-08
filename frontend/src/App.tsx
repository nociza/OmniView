import { useEffect, useMemo, useState } from 'react';
import { LauncherStatus } from './components/LauncherStatus';
import { NodeCard } from './components/NodeCard';
import { NodeDetail } from './components/NodeDetail';
import { SummaryStrip } from './components/SummaryStrip';
import { useDashboard } from './hooks/useDashboard';
import { useLauncher } from './hooks/useLauncher';

function App() {
  const { data, loading, refreshing, error, refresh } = useDashboard();
  const launcher = useLauncher();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  useEffect(() => {
    if (!data?.nodes.length) {
      setSelectedNodeId(null);
      return;
    }

    if (!selectedNodeId || !data.nodes.some((node) => node.node_id === selectedNodeId)) {
      setSelectedNodeId(data.nodes[0].node_id);
    }
  }, [data, selectedNodeId]);

  const selectedNode = useMemo(
    () => data?.nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [data, selectedNodeId],
  );

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">OmniView</p>
          <h1>One control plane for every box on the mesh.</h1>
          <p className="hero__copy">
            Observe hardware health, confirm each desktop is still rendering, and hand off into the right native client without typing an IP or hunting for the binary.
          </p>
        </div>
        <div className="hero__panel">
          <p className="hero__panel-title">Dispatch strategy</p>
          <ul>
            <li>Moonlight for low-latency Sunshine targets</li>
            <li>Screen Sharing for headless macOS recovery</li>
            <li>SSH as the repair lane</li>
            <li>Browser fallback for borrowed devices</li>
          </ul>
        </div>
      </header>

      {data ? <SummaryStrip summary={data.summary} refreshing={refreshing} onRefresh={() => void refresh()} /> : null}

      <LauncherStatus
        baseUrl={launcher.settings.baseUrl}
        token={launcher.settings.token}
        status={launcher.status}
        connected={launcher.connected}
        probing={launcher.probing}
        error={launcher.error}
        onSave={launcher.saveSettings}
        onProbe={launcher.probe}
      />

      {error ? <div className="banner banner--error">{error}</div> : null}

      {loading && !data ? <div className="banner">Loading dashboard…</div> : null}

      <main className="workspace">
        <section className="fleet-column">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Fleet</p>
              <h2>Nodes</h2>
            </div>
            <p>{data?.nodes.length ?? 0} machines visible</p>
          </div>
          <div className="node-grid">
            {data?.nodes.map((node) => (
              <NodeCard key={node.node_id} node={node} selected={node.node_id === selectedNodeId} onSelect={setSelectedNodeId} />
            ))}
          </div>
        </section>
        <NodeDetail node={selectedNode} launcher={launcher} />
      </main>
    </div>
  );
}

export default App;
