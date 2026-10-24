import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function MarketOverview({ onNavigateTab }) {
  const { data: overview, loading: loadingOverview, error: errorOverview } = useApi('/market-overview', { pollInterval: 15000 });
  const [filterSymbol, setFilterSymbol] = useState('ALL');
  const [sortCol, setSortCol] = useState('expiry_date');
  const [sortAsc, setSortAsc] = useState(true);

  if (loadingOverview && !overview) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Market Overview</h2>
        </div>
        <div className="card-body">
          <div className="loading-skeleton" style={{ height: '300px' }}></div>
        </div>
      </div>
    );
  }

  if (errorOverview) {
    return (
      <div className="card">
        <div className="card-body text-red">
          Failed to load market overview: {errorOverview}
        </div>
      </div>
    );
  }

  const {
    trade_date = '2026-09-18',
    benchmark_price = 155001.63,
    benchmark_contract = 'GOLD (Standard 10g 999 Basis)',
    total_contracts = 0,
    active_expiries = [],
    max_spread_abs = 0,
    max_spread_pct = 0,
    contracts = [],
  } = overview || {};

  // Filter contracts
  const filteredContracts = contracts.filter(c => {
    if (filterSymbol !== 'ALL' && c.symbol !== filterSymbol) return false;
    return true;
  });

  // Sort contracts
  filteredContracts.sort((a, b) => {
    let valA = a[sortCol];
    let valB = b[sortCol];
    if (sortCol === 'deviation') {
      valA = a.normalized_price - benchmark_price;
      valB = b.normalized_price - benchmark_price;
    }
    if (valA < valB) return sortAsc ? -1 : 1;
    if (valA > valB) return sortAsc ? 1 : -1;
    return 0;
  });

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(col);
      setSortAsc(true);
    }
  };

  const symbols = ['ALL', 'GOLD', 'GOLDM', 'GOLDGUINEA', 'GOLDPETAL', 'GOLDTEN'];

  return (
    <div className="flex-col gap-6">
      {/* KPI Metrics Summary Grid */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">Observation Date</span>
          <span className="metric-value text-gold">{trade_date}</span>
          <span className="metric-sub">Official MCX Bhavcopy EOD</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Benchmark Reference</span>
          <span className="metric-value text-green">
            ₹{benchmark_price?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
          <span className="metric-sub">{benchmark_contract}</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Active Gold Contracts</span>
          <span className="metric-value">{total_contracts}</span>
          <span className="metric-sub">{active_expiries.length} distinct expiry cycles</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Max Parity Spread</span>
          <span className="metric-value text-red">
            ₹{max_spread_abs?.toFixed(2)}
          </span>
          <span className="metric-sub">
            {max_spread_pct?.toFixed(2)}% cross-contract pricing deviation
          </span>
        </div>
      </div>

      {/* Quantitative Thesis Banner */}
      <div className="info-banner">
        <div style={{ fontSize: '1.5rem' }}>💡</div>
        <div>
          <h3 className="font-bold text-sm" style={{ color: 'var(--accent-blue)', marginBottom: '4px' }}>
            Quantitative Parity Principle
          </h3>
          <p className="text-sm text-muted">
            On MCX, contracts like <strong>GOLD</strong> (1 kg, 995 fineness), <strong>GOLDM</strong> (100g, 995 fineness),
            <strong>GOLDGUINEA</strong> (8g, 999 fineness), <strong>GOLDPETAL</strong> (1g, 999 fineness), and <strong>GOLDTEN</strong> (10g, 999 fineness)
            represent the exact same physical commodity. By converting each contract to a standardized basis of <strong>₹ per 10 grams of 999 fineness</strong>,
            GOLD-X exposes structural price discrepancies that arise from differing retail participation and liquidity fragmentation.
          </p>
        </div>
      </div>

      {/* Normalized Contract Inventory Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Normalized Contract Inventory</h2>
            <p className="card-subtitle">
              All contract quotes adjusted for deliverable weight and chemical purity
            </p>
          </div>
          <div className="filter-bar" style={{ marginBottom: 0 }}>
            {symbols.map(sym => (
              <button
                key={sym}
                type="button"
                className={`filter-pill ${filterSymbol === sym ? 'active' : ''}`}
                onClick={() => setFilterSymbol(sym)}
              >
                {sym}
              </button>
            ))}
          </div>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table className="financial-table">
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('symbol')}>
                    Symbol {sortCol === 'symbol' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('expiry_date')}>
                    Expiry {sortCol === 'expiry_date' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('days_to_expiry')}>
                    DTE {sortCol === 'days_to_expiry' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th>Raw Close</th>
                  <th>Quote Basis</th>
                  <th>Deliverable Purity</th>
                  <th className="sortable" onClick={() => handleSort('normalized_price')}>
                    Normalized (₹/10g 999) {sortCol === 'normalized_price' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('deviation')}>
                    Deviation vs Benchmark {sortCol === 'deviation' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('volume')}>
                    Volume {sortCol === 'volume' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th>OI</th>
                </tr>
              </thead>
              <tbody>
                {filteredContracts.map(c => {
                  const deviation = c.normalized_price - benchmark_price;
                  const devPct = benchmark_price > 0 ? (deviation / benchmark_price) * 100 : 0;
                  const isPositive = deviation >= 0;

                  return (
                    <tr key={`${c.symbol}-${c.expiry_date}`}>
                      <td className="font-bold">{c.symbol}</td>
                      <td>{c.expiry_date}</td>
                      <td className="font-mono">{c.days_to_expiry}d</td>
                      <td className="font-mono">₹{c.raw_close?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                      <td>{c.quote_unit}</td>
                      <td>{c.purity}</td>
                      <td className="font-mono font-bold" style={{ color: 'var(--accent-gold)' }}>
                        ₹{c.normalized_price?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className={`font-mono font-bold ${isPositive ? 'text-green' : 'text-red'}`}>
                        {isPositive ? '+' : ''}₹{deviation.toFixed(2)} ({isPositive ? '+' : ''}{devPct.toFixed(2)}%)
                      </td>
                      <td className="font-mono">{c.volume?.toLocaleString('en-IN') || '0'}</td>
                      <td className="font-mono">{c.open_interest?.toLocaleString('en-IN') || '0'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
