import React from 'react';
import ParityRadar from './ParityRadar';
import SignalCard from './SignalCard';
import ContractLifecycle from './ContractLifecycle';
import { useApi } from '../hooks/useApi';

function SummaryStats() {
  const { data, loading, error } = useApi('/backtest-performance/summary');
  
  return (
    <div className="card h-full">
      <div className="card-header">
        <h2 className="card-title">Performance Summary</h2>
      </div>
      <div className="card-body">
        {loading ? (
          <div className="loading-skeleton h-32"></div>
        ) : error ? (
          <div className="text-red">Failed to load summary stats.</div>
        ) : data?.status === 'no_data' ? (
          <div className="text-muted text-center py-8">
            <p>{data.message || 'No normalized price data available.'}</p>
            <p className="text-sm mt-2">Ingest MCX data to compute backtest metrics.</p>
          </div>
        ) : data?.status === 'insufficient_data' ? (
          <div className="text-muted text-center py-6">
            <div className="font-bold mb-2" style={{ color: '#F59E0B' }}>Insufficient Historical Data</div>
            <p className="text-sm">{data.message}</p>
            <p className="text-xs text-muted mt-3">
              Available: {data.days_available} trading day | Baseline window: {data.days_required} days
            </p>
          </div>
        ) : data ? (
          <div className="flex-col gap-4">
            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--spacing-2)' }}>
              <span className="text-muted">Total Signals</span>
              <span className="font-bold">{data.total_signals ?? 0}</span>
            </div>
            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--spacing-2)' }}>
              <span className="text-muted">Tradeable</span>
              <span className="font-bold">{data.tradeable_signals ?? 0}</span>
            </div>
            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--spacing-2)' }}>
              <span className="text-muted">Win Rate</span>
              <span className="font-bold">{((data.win_rate ?? 0) * 100).toFixed(1)}%</span>
            </div>
            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--spacing-2)' }}>
              <span className="text-muted">Net P&L</span>
              <span className={`font-bold ${(data.net_pnl ?? 0) >= 0 ? 'text-green' : 'text-red'}`}>
                ₹{(data.net_pnl ?? 0).toFixed(2)}
              </span>
            </div>
            <div className="flex-row justify-between" style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: 'var(--spacing-2)' }}>
              <span className="text-muted">Sharpe Ratio</span>
              <span className="font-bold">{(data.sharpe_ratio ?? 0).toFixed(2)}</span>
            </div>
            <div className="flex-row justify-between">
              <span className="text-muted">Max Drawdown</span>
              <span className="text-red font-bold">₹{(data.max_drawdown ?? 0).toFixed(2)}</span>
            </div>
          </div>
        ) : (
          <div className="text-muted">No data available</div>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="dashboard-grid">
      <div className="row-1">
        <ParityRadar />
      </div>
      
      <div className="row-2-main">
        <SignalCard />
      </div>
      
      <div className="row-2-side">
        <SummaryStats />
      </div>
      
      <div className="row-3">
        <ContractLifecycle />
      </div>
    </div>
  );
}
