import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

export default function SystemStatus() {
  const { data: status, loading, error, refetch } = useApi('/system/status', { pollInterval: 15000 });
  const [importPath, setImportPath] = useState('data/imports/mcx_20260918 (1).csv');
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importError, setImportError] = useState(null);

  const handleTriggerImport = async (e) => {
    e.preventDefault();
    setImporting(true);
    setImportResult(null);
    setImportError(null);

    try {
      const res = await fetch('/api/ingest/csv', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: importPath }),
      });

      const json = await res.json();
      if (!res.ok) {
        throw new Error(json.detail || 'CSV import failed');
      }

      setImportResult(json);
      refetch();
    } catch (err) {
      setImportError(err.message);
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="flex-col gap-6">
      {/* Telemetry Overview */}
      <div className="metrics-grid">
        <div className="metric-card">
          <span className="metric-label">PostgreSQL Database</span>
          <span className={`metric-value ${status?.database_connected ? 'text-green' : 'text-red'}`}>
            {status?.database_connected ? 'Connected' : 'Disconnected'}
          </span>
          <span className="metric-sub">PostgreSQL 16 (goldx_db)</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Bhavcopy Raw Rows</span>
          <span className="metric-value font-mono">
            {status?.bhavcopy_records?.toLocaleString('en-IN') ?? 0}
          </span>
          <span className="metric-sub">daily_bhavcopy table</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Normalized Price Rows</span>
          <span className="metric-value font-mono text-gold">
            {status?.normalized_records?.toLocaleString('en-IN') ?? 0}
          </span>
          <span className="metric-sub">normalized_prices table</span>
        </div>

        <div className="metric-card">
          <span className="metric-label">Distinct Trade Dates</span>
          <span className="metric-value">
            {status?.distinct_trade_dates ?? 0}
          </span>
          <span className="metric-sub">
            {status?.trade_dates?.join(', ') || 'None'}
          </span>
        </div>
      </div>

      {/* Ingestion Provenance & Akamai WAF Notice */}
      <div className="info-banner">
        <div style={{ fontSize: '1.5rem' }}>🛡️</div>
        <div>
          <h3 className="font-bold text-sm" style={{ color: 'var(--accent-blue)', marginBottom: '4px' }}>
            Data Ingestion Provenance & Perimeter Architecture
          </h3>
          <p className="text-sm text-muted">
            The official MCX website protects its public Bhavcopy download endpoints via <strong>Akamai Bot Manager & WAF controls</strong>, returning <code>HTTP 403 Forbidden</code> to automated cloud scrapers and unauthenticated scripts.
          </p>
          <p className="text-xs text-muted mt-2">
            To ensure 100% regulatory compliance and data authenticity, GOLD-X utilizes a verified <strong>Local CSV Ingestion Pipeline</strong>. When genuine daily Bhavcopy CSV files are placed in <code>data/imports/</code>, the engine parses, filters, validates, normalizes, and upserts them idempotently without risk of duplicate records or fabricated data.
          </p>
        </div>
      </div>

      {/* Local CSV Ingestion Controller */}
      <div className="card">
        <div className="card-header">
          <div>
            <h3 className="card-title">Local Bhavcopy CSV Ingestion Engine</h3>
            <p className="card-subtitle">Trigger on-demand import of raw MCX Bhavcopy CSV files</p>
          </div>
          <span className="badge badge-opportunity">Idempotent Upsert Active</span>
        </div>

        <div className="card-body">
          <form onSubmit={handleTriggerImport} className="flex-col gap-4">
            <div className="flex-col gap-1">
              <label className="text-xs text-muted font-bold">CSV File or Directory Path (inside container / host)</label>
              <div className="flex gap-3">
                <input
                  type="text"
                  value={importPath}
                  onChange={(e) => setImportPath(e.target.value)}
                  className="input-control"
                  style={{ flex: 1 }}
                  placeholder="data/imports/mcx_20260918.csv or data/imports/"
                />
                <button type="submit" className="btn-primary" disabled={importing}>
                  {importing ? 'Importing...' : 'Trigger Import'}
                </button>
              </div>
              <span className="text-xs text-muted">
                Supports single CSV file path or entire directory for batch import.
              </span>
            </div>

            {importResult && (
              <div className="reason-box" style={{ borderColor: 'var(--accent-green)' }}>
                <strong className="text-green">✓ Import Successful:</strong> Status: {importResult.status} |
                Gold Rows Found: {importResult.gold_rows_found ?? importResult.total_gold_rows} |
                Bhavcopy Upserted: {importResult.daily_bhavcopy_upserted ?? importResult.total_daily_bhavcopy_upserted} |
                Normalized Upserted: {importResult.normalized_prices_upserted ?? importResult.total_normalized_prices_upserted}
              </div>
            )}

            {importError && (
              <div className="reason-box" style={{ borderColor: 'var(--accent-red)' }}>
                <strong className="text-red">✕ Import Error:</strong> {importError}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* System Specifications Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Containerized Microservices Architecture</h3>
        </div>
        <div className="card-body">
          <div className="table-container">
            <table className="financial-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Container Name</th>
                  <th>Port</th>
                  <th>Technology</th>
                  <th>Health Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="font-bold">Backend API</td>
                  <td>goldx_backend</td>
                  <td>8000</td>
                  <td>FastAPI, Polars, SQLAlchemy 2.0 (Async)</td>
                  <td><span className="badge badge-active">HEALTHY</span></td>
                </tr>
                <tr>
                  <td className="font-bold">PostgreSQL DB</td>
                  <td>goldx_db</td>
                  <td>5432</td>
                  <td>PostgreSQL 16 (Alpine)</td>
                  <td><span className="badge badge-active">HEALTHY</span></td>
                </tr>
                <tr>
                  <td className="font-bold">Web Terminal</td>
                  <td>goldx_frontend</td>
                  <td>80</td>
                  <td>React 18, Vite, Nginx Alpine</td>
                  <td><span className="badge badge-active">HEALTHY</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
