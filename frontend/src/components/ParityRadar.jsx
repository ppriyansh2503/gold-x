import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function ParityRadar() {
  const { data, loading, error } = useApi('/parity', { pollInterval: 10000 });
  const [selectedExpiry, setSelectedExpiry] = useState(null);
  const [hoveredContract, setHoveredContract] = useState(null);

  if (loading && !data) {
    return (
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Parity Radar</h2>
        </div>
        <div className="card-body">
          <div className="loading-skeleton" style={{ height: '350px' }}></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-body text-red">
          Failed to load parity radar: {error}
        </div>
      </div>
    );
  }

  const expiries = data ? Object.keys(data).sort() : [];
  const currentExpiry = selectedExpiry && data?.[selectedExpiry] ? selectedExpiry : expiries[0];
  const contracts = data?.[currentExpiry] || [];

  // Compute cheapest and most expensive
  let minContract = null;
  let maxContract = null;
  if (contracts.length > 0) {
    minContract = contracts.reduce((prev, curr) => curr.normalized_price < prev.normalized_price ? curr : prev, contracts[0]);
    maxContract = contracts.reduce((prev, curr) => curr.normalized_price > prev.normalized_price ? curr : prev, contracts[0]);
  }

  const grossSpread = (minContract && maxContract) ? (maxContract.normalized_price - minContract.normalized_price) : 0;
  const spreadPct = minContract && minContract.normalized_price > 0 ? (grossSpread / minContract.normalized_price) * 100 : 0;

  // Chart coordinates
  const svgWidth = 600;
  const svgHeight = 220;
  const padding = { top: 20, right: 30, bottom: 40, left: 90 };
  const chartW = svgWidth - padding.left - padding.right;
  const chartH = svgHeight - padding.top - padding.bottom;

  // Scaled prices for the bar chart
  let minP = contracts.length > 0 ? Math.min(...contracts.map(c => c.normalized_price)) : 0;
  let maxP = contracts.length > 0 ? Math.max(...contracts.map(c => c.normalized_price)) : 100;
  // Offset min slightly so differences stand out visually
  const baseline = Math.max(0, minP - (maxP - minP || 100) * 0.5);
  const range = (maxP - baseline) || 1;

  return (
    <div className="flex-col gap-6">
      {/* Expiry Selector Bar */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Cross-Contract Parity Radar</h2>
            <p className="card-subtitle">
              Isolating contracts with the exact same expiry date to eliminate curve roll-down bias
            </p>
          </div>
          <span className="badge badge-baseline">
            {expiries.length} Expiry Cycles
          </span>
        </div>

        <div className="card-body" style={{ paddingBottom: 'var(--spacing-3)' }}>
          <div className="filter-bar">
            <span className="text-xs text-muted font-bold" style={{ marginRight: '8px' }}>EXPIRY:</span>
            {expiries.map(exp => {
              const count = data[exp]?.length || 0;
              const isActive = exp === currentExpiry;
              return (
                <button
                  key={exp}
                  type="button"
                  className={`filter-pill ${isActive ? 'active' : ''}`}
                  onClick={() => setSelectedExpiry(exp)}
                >
                  {exp} ({count})
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Selected Expiry Spread Analysis */}
      {contracts.length === 0 ? (
        <div className="card">
          <div className="card-body text-center text-muted">No contracts found for this expiry.</div>
        </div>
      ) : (
        <div className="dashboard-grid">
          {/* Left Column: Visual Chart & Arbitrage Pair Analysis */}
          <div className="row-2-main">
            <div className="card h-full">
              <div className="card-header">
                <div>
                  <h3 className="card-title">Normalized Price Comparison</h3>
                  <p className="card-subtitle">Expiry: {currentExpiry} | Basis: ₹ / 10g 999 Fineness</p>
                </div>
                <div className="flex gap-2">
                  <span className="badge badge-opportunity">Cheapest: {minContract?.symbol}</span>
                  <span className="badge badge-rejected">Richest: {maxContract?.symbol}</span>
                </div>
              </div>

              <div className="card-body">
                {/* Responsive Vector SVG Bar Chart */}
                <div className="chart-container" style={{ position: 'relative' }}>
                  <svg
                    viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                    style={{ width: '100%', height: 'auto', display: 'block' }}
                  >
                    {/* Background Grid Lines */}
                    {[0, 0.25, 0.5, 0.75, 1.0].map((ratio, i) => {
                      const yVal = padding.top + chartH * (1 - ratio);
                      const priceVal = baseline + range * ratio;
                      return (
                        <g key={i}>
                          <line
                            x1={padding.left}
                            y1={yVal}
                            x2={padding.left + chartW}
                            y2={yVal}
                            stroke="rgba(255, 255, 255, 0.08)"
                            strokeDasharray="3 3"
                          />
                          <text
                            x={padding.left - 8}
                            y={yVal + 4}
                            fill="var(--text-muted)"
                            fontSize="10"
                            textAnchor="end"
                            fontFamily="monospace"
                          >
                            ₹{Math.round(priceVal).toLocaleString('en-IN')}
                          </text>
                        </g>
                      );
                    })}

                    {/* Bars */}
                    {contracts.map((c, i) => {
                      const barWidth = Math.min(48, (chartW / contracts.length) * 0.6);
                      const slotW = chartW / contracts.length;
                      const x = padding.left + i * slotW + (slotW - barWidth) / 2;
                      const height = ((c.normalized_price - baseline) / range) * chartH;
                      const y = padding.top + chartH - height;

                      const isMin = c.symbol === minContract?.symbol;
                      const isMax = c.symbol === maxContract?.symbol;
                      const fillColor = isMin
                        ? 'var(--accent-green)'
                        : isMax
                        ? 'var(--accent-red)'
                        : 'var(--accent-gold)';

                      const isHovered = hoveredContract?.symbol === c.symbol;

                      return (
                        <g
                          key={c.symbol}
                          onMouseEnter={() => setHoveredContract(c)}
                          onMouseLeave={() => setHoveredContract(null)}
                          style={{ cursor: 'pointer' }}
                        >
                          <rect
                            x={x}
                            y={y}
                            width={barWidth}
                            height={Math.max(4, height)}
                            fill={fillColor}
                            opacity={isHovered ? 1.0 : 0.85}
                            rx="3"
                          />
                          {/* Value above bar */}
                          <text
                            x={x + barWidth / 2}
                            y={y - 6}
                            fill={fillColor}
                            fontSize="10"
                            fontWeight="bold"
                            textAnchor="middle"
                            fontFamily="monospace"
                          >
                            ₹{Math.round(c.normalized_price).toLocaleString('en-IN')}
                          </text>
                          {/* Symbol label on X axis */}
                          <text
                            x={x + barWidth / 2}
                            y={padding.top + chartH + 18}
                            fill="var(--text-main)"
                            fontSize="11"
                            fontWeight="600"
                            textAnchor="middle"
                          >
                            {c.symbol}
                          </text>
                        </g>
                      );
                    })}
                  </svg>

                  {/* Interactive Tooltip */}
                  {hoveredContract && (
                    <div
                      className="chart-tooltip"
                      style={{
                        top: '10px',
                        right: '10px',
                      }}
                    >
                      <div className="font-bold text-sm" style={{ color: 'var(--accent-gold)' }}>
                        {hoveredContract.symbol}
                      </div>
                      <div className="text-xs text-muted">
                        Normalized: ₹{hoveredContract.normalized_price?.toFixed(2)}/10g
                      </div>
                      <div className="text-xs text-muted">
                        Raw Close: ₹{hoveredContract.raw_close?.toFixed(2)}
                      </div>
                      <div className="text-xs text-muted">
                        Volume: {hoveredContract.volume?.toLocaleString('en-IN') || 0}
                      </div>
                      <div className="text-xs text-muted">
                        Spread vs Base: +₹{(hoveredContract.normalized_price - minContract.normalized_price).toFixed(2)}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Key Spread Metrics */}
          <div className="row-2-side">
            <div className="card h-full">
              <div className="card-header">
                <h3 className="card-title">Parity Spread Metrics</h3>
              </div>
              <div className="card-body flex-col gap-4">
                <div className="flex justify-between items-center" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <span className="text-muted text-sm">Target Expiry</span>
                  <span className="font-bold text-gold">{currentExpiry}</span>
                </div>

                <div className="flex justify-between items-center" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <span className="text-muted text-sm">Days to Expiry</span>
                  <span className="font-bold font-mono">{contracts[0]?.days_to_expiry} days</span>
                </div>

                <div className="flex justify-between items-center" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <span className="text-muted text-sm">Cheapest Contract</span>
                  <div>
                    <span className="text-green font-bold">{minContract?.symbol}</span>
                    <span className="text-xs text-muted block font-mono">₹{minContract?.normalized_price?.toFixed(2)}</span>
                  </div>
                </div>

                <div className="flex justify-between items-center" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <span className="text-muted text-sm">Richest Contract</span>
                  <div>
                    <span className="text-red font-bold">{maxContract?.symbol}</span>
                    <span className="text-xs text-muted block font-mono">₹{maxContract?.normalized_price?.toFixed(2)}</span>
                  </div>
                </div>

                <div className="flex justify-between items-center" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
                  <span className="text-muted text-sm">Gross Spread</span>
                  <span className="font-bold text-lg font-mono text-gold">
                    ₹{grossSpread.toFixed(2)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-muted text-sm">Spread Percentage</span>
                  <span className="font-bold font-mono text-gold">
                    {spreadPct.toFixed(2)}%
                  </span>
                </div>

                <div className="reason-box mt-4">
                  <strong>Quantitative Note:</strong> Cross-contract spreads reflect relative value between retail and wholesale tranches for the identical delivery date. A spread of ₹{grossSpread.toFixed(2)}/10g represents theoretical mispricing before transaction friction.
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
