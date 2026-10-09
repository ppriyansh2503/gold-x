import React from 'react';
import { useApi } from '../hooks/useApi';

export default function ParityRadar() {
  const { data, loading, error } = useApi('/parity', { pollInterval: 5000 });

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Parity Radar</h2>
      </div>
      <div className="card-body">
        {loading && !data && <div className="spinner"></div>}
        {error && <div className="text-red">Error loading parity data: {error}</div>}
        
        {data && Object.keys(data).length === 0 && (
          <div className="text-muted text-center py-8">No parity data available</div>
        )}

        {data && Object.keys(data).length > 0 && (
          <div className="radar-grid">
            {Object.entries(data).map(([expiry, contracts]) => {
              if (!contracts || contracts.length === 0) return null;
              
              // Find cheapest and most expensive
              let minPrice = Infinity;
              let maxPrice = -Infinity;
              
              contracts.forEach(c => {
                if (c.normalized_price < minPrice) minPrice = c.normalized_price;
                if (c.normalized_price > maxPrice) maxPrice = c.normalized_price;
              });
              
              const spread = maxPrice - minPrice;
              const spreadPct = (spread / minPrice) * 100;

              return (
                <div key={expiry} className="radar-item">
                  <div className="radar-header">
                    <strong>Expiry: {expiry}</strong>
                    <span className="text-muted">Spread: ₹{spread.toFixed(2)} ({spreadPct.toFixed(2)}%)</span>
                  </div>
                  <div className="flex-col gap-2">
                    {contracts.map(c => {
                      let colorClass = '';
                      if (c.normalized_price === minPrice) colorClass = 'text-green';
                      if (c.normalized_price === maxPrice) colorClass = 'text-red';
                      
                      return (
                        <div key={c.symbol} className="contract-row">
                          <span className={colorClass}>{c.symbol}</span>
                          <span className={colorClass}>₹{c.normalized_price.toFixed(2)}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
