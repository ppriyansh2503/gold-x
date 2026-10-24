import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

const SPECS = [
  { symbol: 'GOLD', name: 'Gold (Standard / Big)', quoteUnit: '10 grams', lotSize: '1 kg (1000g)', purity: '995 / 1000', tickSize: '₹1.00', delivery: '1 kg bar' },
  { symbol: 'GOLDM', name: 'Gold Mini', quoteUnit: '10 grams', lotSize: '100 grams', purity: '995 / 1000', tickSize: '₹1.00', delivery: '100g bar' },
  { symbol: 'GOLDGUINEA', name: 'Gold Guinea', quoteUnit: '8 grams', lotSize: '8 grams', purity: '999 / 1000', tickSize: '₹1.00', delivery: '8g coin' },
  { symbol: 'GOLDPETAL', name: 'Gold Petal', quoteUnit: '1 gram', lotSize: '1 gram', purity: '999 / 1000', tickSize: '₹1.00', delivery: '1g coin' },
  { symbol: 'GOLDTEN', name: 'Gold Ten', quoteUnit: '10 grams', lotSize: '10 grams', purity: '999 / 1000', tickSize: '₹1.00', delivery: '10g bar' },
];

export default function ContractLifecycle() {
  const { data, loading, error } = useApi('/parity', { pollInterval: 30000 });
  const [searchTerm, setSearchTerm] = useState('');
  const [sortCol, setSortCol] = useState('days_to_expiry');
  const [sortAsc, setSortAsc] = useState(true);
  const [showSpecsModal, setShowSpecsModal] = useState(false);

  let contracts = [];
  if (data) {
    Object.values(data).forEach(list => {
      contracts = [...contracts, ...list];
    });
  }

  const getStatus = (days) => {
    if (days < 0) return 'EXPIRED';
    if (days <= 5) return 'TENDER_PERIOD';
    if (days <= 30) return 'NEAR_EXPIRY';
    return 'ACTIVE';
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ACTIVE': return 'badge-active';
      case 'NEAR_EXPIRY': return 'badge-near-expiry';
      case 'TENDER_PERIOD': return 'badge-tender';
      case 'EXPIRED': return 'badge-expired';
      default: return 'badge-active';
    }
  };

  const getLiqRating = (vol) => {
    if (vol >= 5000) return { label: 'HIGH', class: 'text-green' };
    if (vol >= 1000) return { label: 'MEDIUM', class: 'text-gold' };
    return { label: 'LOW', class: 'text-red' };
  };

  // Filter
  const filtered = contracts.filter(c => {
    if (searchTerm && !c.symbol.toLowerCase().includes(searchTerm.toLowerCase()) && !c.expiry.includes(searchTerm)) {
      return false;
    }
    return true;
  });

  // Sort
  filtered.sort((a, b) => {
    let valA = a[sortCol];
    let valB = b[sortCol];
    if (sortCol === 'status') {
      valA = getStatus(a.days_to_expiry);
      valB = getStatus(b.days_to_expiry);
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

  return (
    <div className="flex-col gap-6">
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Contract Maturity & Lifecycle Matrix</h2>
            <p className="card-subtitle">
              Tracking days-to-expiry (DTE) from observation date, physical delivery tender windows, and volume liquidity
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowSpecsModal(true)}
            >
              📋 MCX Contract Specs
            </button>
          </div>
        </div>

        <div className="card-body">
          <div className="flex justify-between items-center mb-4" style={{ flexWrap: 'wrap', gap: '10px' }}>
            <input
              type="text"
              placeholder="Search contract symbol or expiry (e.g. GOLDM, 2026-10)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-control"
              style={{ minWidth: '320px' }}
            />
            <span className="text-xs text-muted">
              Showing {filtered.length} of {contracts.length} contracts
            </span>
          </div>

          <div className="table-container">
            <table className="financial-table">
              <thead>
                <tr>
                  <th className="sortable" onClick={() => handleSort('symbol')}>
                    Symbol {sortCol === 'symbol' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('expiry')}>
                    Expiry Date {sortCol === 'expiry' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('days_to_expiry')}>
                    DTE (Trade Date) {sortCol === 'days_to_expiry' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('status')}>
                    Lifecycle Status {sortCol === 'status' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('volume')}>
                    Volume {sortCol === 'volume' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th className="sortable" onClick={() => handleSort('open_interest')}>
                    Open Interest {sortCol === 'open_interest' && (sortAsc ? '▲' : '▼')}
                  </th>
                  <th>Liquidity Depth</th>
                  <th>Normalized Close</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(c => {
                  const status = getStatus(c.days_to_expiry);
                  const liq = getLiqRating(c.volume || 0);

                  return (
                    <tr key={`${c.symbol}-${c.expiry}`}>
                      <td className="font-bold">{c.symbol}</td>
                      <td>{c.expiry}</td>
                      <td className="font-mono font-bold">{c.days_to_expiry} days</td>
                      <td>
                        <span className={`badge ${getStatusBadge(status)}`}>
                          {status.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td className="font-mono">{c.volume?.toLocaleString('en-IN') || '0'}</td>
                      <td className="font-mono">{c.open_interest?.toLocaleString('en-IN') || '0'}</td>
                      <td>
                        <span className={`font-bold text-xs ${liq.class}`}>
                          ● {liq.label}
                        </span>
                      </td>
                      <td className="font-mono text-gold font-bold">
                        ₹{c.normalized_price?.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* MCX Contract Specifications Modal */}
      {showSpecsModal && (
        <div className="modal-overlay" onClick={() => setShowSpecsModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="card-header">
              <h3 className="card-title">Official MCX Gold Contract Specifications</h3>
              <button
                type="button"
                className="btn-secondary"
                style={{ padding: '4px 10px', fontSize: 'var(--font-xs)' }}
                onClick={() => setShowSpecsModal(false)}
              >
                ✕ Close
              </button>
            </div>
            <div className="card-body">
              <div className="table-container mb-4">
                <table className="financial-table">
                  <thead>
                    <tr>
                      <th>Contract</th>
                      <th>Quotation Unit</th>
                      <th>Trading Lot Size</th>
                      <th>Deliverable Purity</th>
                      <th>Tick Size</th>
                      <th>Physical Delivery</th>
                    </tr>
                  </thead>
                  <tbody>
                    {SPECS.map(s => (
                      <tr key={s.symbol}>
                        <td className="font-bold text-gold">{s.symbol}</td>
                        <td>{s.quoteUnit}</td>
                        <td className="font-mono font-bold">{s.lotSize}</td>
                        <td>{s.purity}</td>
                        <td>{s.tickSize}</td>
                        <td>{s.delivery}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="reason-box">
                <strong>Normalization Rule:</strong> All prices are mathematically mapped to a standard basis of 10 grams of 999 fineness:
                <br />
                <code>P_normalized = P_raw × (10 / QuoteUnitGrams) × (999 / DeliverablePurity)</code>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
