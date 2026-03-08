import type { DashboardSummary } from '../types';

interface SummaryStripProps {
  summary: DashboardSummary;
  refreshing: boolean;
  onRefresh: () => void;
}

export function SummaryStrip({ summary, refreshing, onRefresh }: SummaryStripProps) {
  const cards = [
    { label: 'Fleet', value: summary.counts.total, tone: 'neutral' },
    { label: 'Online', value: summary.counts.online, tone: 'online' },
    { label: 'Stale', value: summary.counts.stale, tone: 'stale' },
    { label: 'Offline', value: summary.counts.offline, tone: 'offline' },
    { label: 'Avg CPU', value: summary.average_cpu_percent != null ? `${summary.average_cpu_percent}%` : '—', tone: 'neutral' },
  ];

  return (
    <section className="summary-strip">
      <div>
        <p className="eyebrow">Control plane</p>
        <h2>Fleet status at a glance</h2>
      </div>
      <div className="summary-strip__cards">
        {cards.map((card) => (
          <article key={card.label} className={`summary-card summary-card--${card.tone}`}>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
      <div className="summary-strip__meta">
        <p>{summary.hottest_node_name ? `Hottest node: ${summary.hottest_node_name}` : 'No thermal data reported.'}</p>
        <button type="button" className="ghost-button" onClick={onRefresh} disabled={refreshing}>
          {refreshing ? 'Refreshing…' : 'Refresh now'}
        </button>
      </div>
    </section>
  );
}
