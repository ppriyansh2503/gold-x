import React, { useState, useEffect } from 'react';
import Navigation from './Navigation';

export default function Layout({ activeTab, onSelectTab, signalCount = 0, children }) {
  const [isConnected, setIsConnected] = useState(true);
  const [tradeDate, setTradeDate] = useState('2026-09-18');
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/system/status');
        if (res.ok) {
          const json = await res.json();
          setIsConnected(json.database_connected ?? true);
          if (json.trade_dates && json.trade_dates.length > 0) {
            setTradeDate(json.trade_dates[json.trade_dates.length - 1]);
          }
        } else {
          setIsConnected(false);
        }
      } catch {
        setIsConnected(false);
      }
    };

    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);
    const clockInterval = setInterval(() => setNow(new Date()), 1000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(clockInterval);
    };
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-top">
          <div className="brand-wrapper">
            <div className="brand-badge">GOLD-X</div>
            <div className="brand-info">
              <h1>Commodity Parity Terminal</h1>
              <span>MCX Gold Quantitative Intelligence</span>
            </div>
          </div>

          <div className="header-status-bar">
            <div className="status-chip">
              <span className="pulse-dot gold"></span>
              <span>Data Snapshot: <strong>{tradeDate}</strong></span>
            </div>

            <div className="status-chip">
              <span className={`pulse-dot ${isConnected ? 'green' : 'red'}`}></span>
              <span>{isConnected ? 'API & Database Online' : 'System Offline'}</span>
            </div>

            <div className="status-chip" style={{ fontFamily: 'monospace' }}>
              <span>{now.toLocaleTimeString()} IST</span>
            </div>
          </div>
        </div>

        {/* Embedded Navigation Bar */}
        <Navigation
          activeTab={activeTab}
          onSelectTab={onSelectTab}
          signalCount={signalCount}
        />
      </header>

      <main className="main-content">
        {children}
      </main>

      <footer className="footer">
        <div>
          <strong>GOLD-X Analytics Terminal v1.0.0</strong> — Problem Statement 03: Commodity Derivatives Intelligence
        </div>
        <div>
          Normalized Basis: ₹ / 10g 999 Fineness | Data Source: Multi Commodity Exchange of India (MCX) Bhavcopy
        </div>
      </footer>
    </div>
  );
}
