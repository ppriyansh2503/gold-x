import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function ContractLifecycle() {
  const { data, loading, error } = useApi('/parity', { pollInterval: 60000 });
  const [sortCol, setSortCol] = useState('symbol');
  const [sortDesc, setSortDesc] = useState(false);

  let contracts = [];
  if (data) {
    Object.values(data).forEach(list => {
      contracts = [...contracts, ...list];
    });
  }

  const handleSort = (col) => {
    if (sortCol === col) {
      setSortDesc(!sortDesc);
    } else {
      setSortCol(col);
      setSortDesc(false);
    }
  };

  const getStatus = (days) => {
    if (days < 0) return 'EXPIRED';
    if (days < 5) return 'TENDER_PERIOD';
    if (days < 30) return 'NEAR_EXPIRY';
    return 'ACTIVE';
  };

  const getLiqRating = (vol) => {
    if (vol > 5000) return 'HIGH';
    if (vol > 1000) return 'MEDIUM';
    return 'LOW';
  };

  if (contracts.length > 0) {
    contracts.sort((a, b) => {
      let valA, valB;
      
      switch (sortCol) {
        case 'symbol': valA = a.symbol; valB = b.symbol; break;
        case 'expiry': valA = new Date(a.expiry); valB = new Date(b.expiry); break;
        case 'dte': 
        case 'status': valA = a.days_to_expiry; valB = b.days_to_expiry; break;
        case 'volume': valA = a.volume || 0; valB = b.volume || 0; break;
        case 'oi': valA = a.open_interest || 0; valB = b.open_interest || 0; break;
        default: valA = a.symbol; valB = b.symbol;
      }

      if (valA < valB) return sortDesc ? 1 : -1;
      if (valA > valB) return sortDesc ? -1 : 1;
      return 0;
    });
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Contract Lifecycle</h2>
      </div>
      <div className="card-body" style={{ padding: 0 }}>
        {loading && !data && <div className="p-6">Loading...</div>}
        {error && <div className="text-red p-6">Error: {error}</div>}
        
        {!loading && !error && contracts.length === 0 && (
          <div className="p-6 text-center text-muted">No contract data available</div>
        )}

        {contracts.length > 0 && (
          <div className="lifecycle-table-container">
            <table className="lifecycle-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('symbol')}>Symbol {sortCol === 'symbol' && (sortDesc ? '↓' : '↑')}</th>
                  <th onClick={() => handleSort('expiry')}>Expiry {sortCol === 'expiry' && (sortDesc ? '↓' : '↑')}</th>
                  <th onClick={() => handleSort('dte')}>DTE {sortCol === 'dte' && (sortDesc ? '↓' : '↑')}</th>
                  <th onClick={() => handleSort('status')}>Status {sortCol === 'status' && (sortDesc ? '↓' : '↑')}</th>
                  <th onClick={() => handleSort('volume')}>Volume {sortCol === 'volume' && (sortDesc ? '↓' : '↑')}</th>
                  <th onClick={() => handleSort('oi')}>OI {sortCol === 'oi' && (sortDesc ? '↓' : '↑')}</th>
                  <th>Liquidity</th>
                </tr>
              </thead>
              <tbody>
                {contracts.map(c => {
                  const status = getStatus(c.days_to_expiry);
                  const liq = getLiqRating(c.volume || 0);
                  
                  return (
                    <tr key={`${c.symbol}-${c.expiry}`}>
                      <td className="font-bold">{c.symbol}</td>
                      <td>{c.expiry}</td>
                      <td>{c.days_to_expiry}</td>
                      <td><span className={`status-badge status-${status.toLowerCase()}`}>{status}</span></td>
                      <td>{c.volume?.toLocaleString() || '-'}</td>
                      <td>{c.open_interest?.toLocaleString() || '-'}</td>
                      <td className={`liq-${liq.toLowerCase()}`}>{liq}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
