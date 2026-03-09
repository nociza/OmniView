import { useEffect, useMemo, useState } from 'react';
import { ClientCard } from './components/ClientCard';
import { ClientDetail } from './components/ClientDetail';
import { HubAccess } from './components/HubAccess';
import { LauncherStatus } from './components/LauncherStatus';
import { NodeCard } from './components/NodeCard';
import { NodeDetail } from './components/NodeDetail';
import { SummaryStrip } from './components/SummaryStrip';
import { useDashboard } from './hooks/useDashboard';
import { useHubSession } from './hooks/useHubSession';
import { useLauncher } from './hooks/useLauncher';

function App() {
  const session = useHubSession();
  const { data, loading, refreshing, error, refresh } = useDashboard(session.authenticated, session.invalidate);
  const launcher = useLauncher();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);

  useEffect(() => {
    if (!data?.nodes.length) {
      setSelectedNodeId(null);
      return;
    }

    if (!selectedNodeId || !data.nodes.some((node) => node.node_id === selectedNodeId)) {
      setSelectedNodeId(data.nodes[0].node_id);
    }
  }, [data, selectedNodeId]);

  useEffect(() => {
    if (!data?.clients.length) {
      setSelectedClientId(null);
      return;
    }

    if (!selectedClientId || !data.clients.some((client) => client.client_id === selectedClientId)) {
      setSelectedClientId(data.clients[0].client_id);
    }
  }, [data, selectedClientId]);

  const selectedNode = useMemo(
    () => data?.nodes.find((node) => node.node_id === selectedNodeId) ?? null,
    [data, selectedNodeId],
  );
  const selectedClient = useMemo(
    () => data?.clients.find((client) => client.client_id === selectedClientId) ?? null,
    [data, selectedClientId],
  );

  return (
    <div className="app-shell">
      <header className="hero">
        <div>
          <p className="eyebrow">OMV</p>
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

      {!session.authenticated ? (
        <HubAccess checking={session.checking} error={session.error} onLogin={session.login} />
      ) : null}

      {data && session.authenticated ? (
        <SummaryStrip
          summary={data.summary}
          clientCount={data.clients.length}
          onlineClients={data.clients.filter((client) => client.status === 'online').length}
          refreshing={refreshing}
          onRefresh={() => void refresh()}
        />
      ) : null}

      {session.authenticated ? (
        <LauncherStatus
          baseUrl={launcher.settings.baseUrl}
          token={launcher.settings.token}
          status={launcher.status}
          connected={launcher.connected}
          probing={launcher.probing}
          error={launcher.error}
          onSave={launcher.saveSettings}
          onProbe={launcher.probe}
          onLogout={session.logout}
        />
      ) : null}

      {error && session.authenticated ? <div className="banner banner--error">{error}</div> : null}

      {loading && !data && session.authenticated ? <div className="banner">Loading dashboard…</div> : null}

      {session.authenticated ? <main className="workspace">
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
      </main> : null}

      {session.authenticated ? <section className="workspace workspace--clients">
        <section className="fleet-column">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Viewing clients</p>
              <h2>Launch machines</h2>
            </div>
            <p>{data?.clients.length ?? 0} clients reporting</p>
          </div>
          <div className="node-grid client-grid">
            {data?.clients.map((client) => (
              <ClientCard key={client.client_id} client={client} selected={client.client_id === selectedClientId} onSelect={setSelectedClientId} />
            ))}
          </div>
        </section>
        <ClientDetail client={selectedClient} />
      </section> : null}
    </div>
  );
}

export default App;
