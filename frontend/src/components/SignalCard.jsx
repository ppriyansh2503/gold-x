import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function SignalCard() {
  const { data: signals, loading, error } = useApi('/signals', { pollInterval: 10000 });
  const [activeFilter, setActiveFilter] = useState('ALL');
  const [expandedPair, setExpandedPair] = useState(null);

  if (loading && !signals) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="card-title">Relative-Value Trading Signals</h2></div>
        <div className="card-body">
          <div className="loading-skeleton" style={{ height: '300px' }}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="card-title">Relative-Value Trading Signals</h2></div>
        <div className="card-body text-red">Error loading signals: {error}</div>
      </div>
    );
  }

  const allSignals = signals || [];

  // Filter signals
  const filteredSignals = allSignals.filter(s => {
    if (activeFilter === 'TRADEABLE') return s.is_tradeable;
    if (activeFilter === 'REJECTED_COSTS') return s.status === 'REJECTED_COSTS_EXCEED_EDGE';
    if (activeFilter === 'BASELINE') return s.status === 'BASELINE_FORMATION';
    if (activeFilter === 'OPPORTUNITY') return s.status === 'POTENTIAL_OPPORTUNITY';
    return true;
  });

  const counts = {
    all: allSignals.length,
    tradeable: allSignals.filter(s => s.is_tradeable).length,
    rejectedCosts: allSignals.filter(s => s.status === 'REJECTED_COSTS_EXCEED_EDGE').length,
    baseline: allSignals.filter(s => s.status === 'BASELINE_FORMATION').length,
  };

  const toggleExpand = (key) => {
    setExpandedPair(expandedPair === key ? null : key);
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'POTENTIAL_OPPORTUNITY': return 'badge-opportunity';
      case 'WATCH': return 'badge-watch';
      case 'REJECTED_COSTS_EXCEED_EDGE': return 'badge-rejected';
      case 'REJECTED_INSUFFICIENT_LIQUIDITY': return 'badge-rejected';
      case 'BASELINE_FORMATION': return 'badge-baseline';
      default: return 'badge-watch';
    }
  };

  return (
    <div className="flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Cross-Contract Arbitrage & Relative-Value Signals</h2>
            <p className="card-subtitle">
              Every spread signal evaluated against an institutional cost model and liquidity penalty
            </p>
          </div>
          <span className="badge badge-baseline">
            {allSignals.length} Active Pairs Monitored
          </span>
        </div>

        <div className="card-body" style={{ paddingBottom: 'var(--spacing-3)' }}>
          {/* Status Filter Bar */}
          <div className="filter-bar">
            <button
              type="button"
              className={`filter-pill ${activeFilter === 'ALL' ? 'active' : ''}`}
              onClick={() => setActiveFilter('ALL')}
            >
              All Pairs ({counts.all})
            </button>
            <button
              type="button"
              className={`filter-pill ${activeFilter === 'TRADEABLE' ? 'active' : ''}`}
              onClick={() => setActiveFilter('TRADEABLE')}
            >
              Tradeable Signals ({counts.tradeable})
            </button>
            <button
              type="button"
              className={`filter-pill ${activeFilter === 'BASELINE' ? 'active' : ''}`}
              onClick={() => setActiveFilter('BASELINE')}
            >
              Baseline Formation ({counts.baseline})
            </button>
            <button
              type="button"
              className={`filter-pill ${activeFilter === 'REJECTED_COSTS' ? 'active' : ''}`}
              onClick={() => setActiveFilter('REJECTED_COSTS')}
            >
              Rejected: Costs Exceed Edge ({counts.rejectedCosts})
            </button>
          </div>
        </div>
      </div>

      {/* Signal Cards List */}
      {filteredSignals.length === 0 ? (
        <div className="card">
          <div className="card-body text-center text-muted py-8">
            <p>No signals found matching the selected filter.</p>
          </div>
        </div>
      ) : (
        <div className="flex-col gap-4">
          {filteredSignals.map((signal, idx) => {
            const {
              contract_a,
              contract_b,
              expiry_date,
              action,
              status,
              direction,
              reason,
              gross_spread = 0,
              net_edge = 0,
              is_tradeable,
              cost_breakdown = {},
              price_a = 0,
              price_b = 0,
              volume_a = 0,
              volume_b = 0,
            } = signal;

            const pairKey = `${contract_a}-${contract_b}-${expiry_date}`;
            const isExpanded = expandedPair === pairKey;
            const isPositive = net_edge > 0;

            return (
              <div key={idx} className="card" style={{ borderLeft: `4px solid ${is_tradeable ? 'var(--accent-green)' : isPositive ? 'var(--accent-gold)' : 'var(--accent-red)'}` }}>
                <div className="card-body">
                  <div className="flex justify-between items-center" style={{ flexWrap: 'wrap', gap: '8px' }}>
                    <div className="flex items-center gap-3">
                      <span className={`badge ${getStatusBadgeClass(status)}`}>
                        {status.replace(/_/g, ' ')}
                      </span>
                      <h3 className="font-bold text-lg">
                        {contract_a} vs {contract_b}
                      </h3>
                      <span className="text-xs text-muted font-mono">
                        Expiry: {expiry_date}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <span className="text-xs text-muted block">Gross Spread</span>
                        <span className="font-bold font-mono text-gold">₹{gross_spread?.toFixed(2)}/10g</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-muted block">Est. Round-Trip Costs</span>
                        <span className="font-bold font-mono text-red">₹{cost_breakdown?.total_costs?.toFixed(2)}/10g</span>
                      </div>
                      <div className="text-right">
                        <span className="text-xs text-muted block">Net Edge</span>
                        <span className={`font-bold font-mono text-lg ${isPositive ? 'text-green' : 'text-red'}`}>
                          {isPositive ? '+' : ''}₹{net_edge?.toFixed(2)}/10g
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Human-readable Reason Banner */}
                  <div className="reason-box">
                    <strong>Signal Rationale:</strong> {reason}
                  </div>

                  {/* Action & Toggle Bar */}
                  <div className="flex justify-between items-center mt-4">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-muted">Direction:</span>
                      <span className="badge badge-watch font-mono">{direction || action}</span>
                      <span className="text-xs text-muted" style={{ marginLeft: '12px' }}>Execution Verdict:</span>
                      <span className={`font-bold text-sm ${is_tradeable ? 'text-green' : 'text-red'}`}>
                        {is_tradeable ? '✓ EXECUTABLE (Net Edge > 0)' : '✕ REJECTED (Zero/Negative Net Edge or Insufficient Baseline)'}
                      </span>
                    </div>

                    <button
                      type="button"
                      className="btn-secondary"
                      style={{ fontSize: 'var(--font-xs)', padding: '6px 12px' }}
                      onClick={() => toggleExpand(pairKey)}
                    >
                      {isExpanded ? 'Hide Cost Autopsy ▲' : 'Inspect Cost Autopsy ▼'}
                    </button>
                  </div>

                  {/* Expandable Cost Autopsy Drawer */}
                  {isExpanded && (
                    <div className="cost-autopsy-box">
                      <h4 className="font-bold text-sm mb-3" style={{ color: 'var(--accent-gold)' }}>
                        Institutional Cost Autopsy ({contract_a} vs {contract_b})
                      </h4>
                      <p className="text-xs text-muted mb-3">
                        Breakdown of mandatory regulatory fees, exchange charges, brokerage, estimated slippage, and liquidity multipliers applied to both legs.
                      </p>

                      <div className="cost-row">
                        <span className="text-muted">Normalized Price Leg A ({contract_a})</span>
                        <span className="font-mono">₹{price_a?.toFixed(2)} / 10g (Volume: {volume_a?.toLocaleString('en-IN')})</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Normalized Price Leg B ({contract_b})</span>
                        <span className="font-mono">₹{price_b?.toFixed(2)} / 10g (Volume: {volume_b?.toLocaleString('en-IN')})</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Gross Cross-Contract Spread</span>
                        <span className="font-mono font-bold text-gold">₹{gross_spread?.toFixed(2)} / 10g</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">MCX Exchange Fees (0.026% turnover)</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.exchange_fees?.toFixed(2)}</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Discount Brokerage (Flat ₹20/order × 2 sides)</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.brokerage?.toFixed(2)}</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Securities Transaction Tax (STT: 0.01% on sell side)</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.stt?.toFixed(2)}</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">GST on Brokerage + Exchange Fees (18%)</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.gst?.toFixed(2)}</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Estimated Market Slippage (5 bps)</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.slippage?.toFixed(2)}</span>
                      </div>
                      <div className="cost-row">
                        <span className="text-muted">Liquidity Penalty Multiplier</span>
                        <span className="font-mono font-bold">{cost_breakdown?.liquidity_penalty?.toFixed(1)}x</span>
                      </div>
                      <div className="cost-row total">
                        <span>Total Real-World Friction</span>
                        <span className="font-mono text-red">₹{cost_breakdown?.total_costs?.toFixed(2)} / 10g</span>
                      </div>
                      <div className="cost-row total">
                        <span>Net Arbitrage Edge</span>
                        <span className={`font-mono ${isPositive ? 'text-green' : 'text-red'}`}>
                          {isPositive ? '+' : ''}₹{net_edge?.toFixed(2)} / 10g
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
