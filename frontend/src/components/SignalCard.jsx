import React from 'react';
import { useApi } from '../hooks/useApi';

export default function SignalCard() {
  const { data: signals, loading, error } = useApi('/signals', { pollInterval: 10000 });

  if (loading && !signals) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="card-title">Trading Signals</h2></div>
        <div className="card-body flex justify-center items-center"><div className="spinner"></div></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-header"><h2 className="card-title">Trading Signals</h2></div>
        <div className="card-body text-red">Error loading signals: {error}</div>
      </div>
    );
  }

  const activeSignals = signals?.filter(s => s.action !== 'NO_TRADE') || [];
  const hasZScores = signals?.some(s => s.z_score !== null && s.z_score !== undefined);

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">Trading Signals</h2>
      </div>
      <div className="card-body">
        {!signals || signals.length === 0 ? (
          <div className="text-muted text-center py-8">
            <p>No signal data available</p>
            <p className="text-sm mt-2">Ingest MCX data to calculate cross-contract arbitrage signals.</p>
          </div>
        ) : !hasZScores ? (
          <div className="calm-state">
            <div className="calm-state-icon" style={{ borderColor: 'var(--text-muted)', color: 'var(--text-muted)' }}>ℹ</div>
            <h3>Baseline Formation Period</h3>
            <p>Rolling Z-score requires at least 20 trading days of history. Current cross-contract spreads are displayed in the Parity Radar above.</p>
          </div>
        ) : activeSignals.length === 0 ? (
          <div className="calm-state">
            <div className="calm-state-icon">✓</div>
            <h3>No Actionable Signals</h3>
            <p>All spreads within cost-adjusted bounds</p>
          </div>
        ) : (
          <div className="flex-col gap-6">
            {activeSignals.map((signal, idx) => {
              const { contract_a, contract_b, action, z_score, net_edge, cost_breakdown, verdict } = signal;
              const isPositive = net_edge > 0;
              const isTradeable = verdict === 'YES' && isPositive;

              return (
                <div key={idx} className="border p-4 rounded-md" style={{ borderColor: 'var(--border-color)', borderWidth: '1px', borderStyle: 'solid', borderRadius: 'var(--radius-md)'}}>
                  <div className="flex-row justify-between items-center mb-4 border-b pb-4" style={{ borderBottomColor: 'var(--border-color)', borderBottomStyle: 'solid', borderBottomWidth: '1px'}}>
                    <div>
                      <span className={`signal-badge ${action.toLowerCase()}`}>{action}</span>
                      <h3 className="text-lg font-bold mt-2">{contract_a} vs {contract_b}</h3>
                    </div>
                    <div className="text-right">
                      <div className="text-muted text-sm">Z-Score</div>
                      <div className="text-xl font-bold">{z_score?.toFixed(2)}</div>
                    </div>
                  </div>

                  <h4 className="font-bold mb-2">Cost Autopsy</h4>
                  <table className="cost-table">
                    <tbody>
                      <tr>
                        <td>Gross Spread</td>
                        <td>₹{cost_breakdown?.gross_spread?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>Exchange Fees</td>
                        <td>₹{cost_breakdown?.exchange_fees?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>Brokerage</td>
                        <td>₹{cost_breakdown?.brokerage?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>STT</td>
                        <td>₹{cost_breakdown?.stt?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>GST</td>
                        <td>₹{cost_breakdown?.gst?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>Slippage</td>
                        <td>₹{cost_breakdown?.slippage?.toFixed(2)}</td>
                      </tr>
                      <tr>
                        <td>Liquidity Penalty</td>
                        <td>₹{cost_breakdown?.liquidity_penalty?.toFixed(2)}</td>
                      </tr>
                      <tr className="total-row">
                        <td>Total Costs</td>
                        <td>₹{cost_breakdown?.total_costs?.toFixed(2)}</td>
                      </tr>
                      <tr className="total-row">
                        <td>Net Edge</td>
                        <td className={isPositive ? 'text-green' : 'text-red'}>₹{net_edge?.toFixed(2)}</td>
                      </tr>
                    </tbody>
                  </table>

                  <div className="mt-4 pt-4 border-t" style={{ borderTopColor: 'var(--border-color)', borderTopStyle: 'solid', borderTopWidth: '1px'}}>
                    <div className="flex-row items-center gap-2">
                      <span className="font-bold">Tradeable Verdict:</span>
                      {isTradeable ? (
                        <span className="text-green font-bold">YES</span>
                      ) : (
                        <span className="text-red font-bold">NO - {net_edge <= 0 ? 'Negative Net Edge' : 'Does not meet criteria'}</span>
                      )}
                    </div>
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
