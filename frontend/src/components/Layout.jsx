import React, { useState, useEffect } from 'react';

export default function Layout({ children }) {
  const [isConnected, setIsConnected] = useState(false);
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    // Health check: ping root endpoint
    const checkHealth = async () => {
      try {
        const res = await fetch('/api/parity');
        setIsConnected(res.ok);
      } catch {
        setIsConnected(false);
      }
    };

    checkHealth();
    const healthInterval = setInterval(checkHealth, 30000);
    const clockInterval = setInterval(() => setNow(new Date()), 60000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(clockInterval);
    };
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-title">
          <h1>GOLD-X</h1>
          <span className="header-subtitle">Quantitative Parity Intelligence</span>
        </div>
        <div className="status-indicator">
          <div className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></div>
          <span>{isConnected ? 'API Connected' : 'Disconnected'}</span>
        </div>
      </header>

      <main className="main-content">
        {children}
      </main>

      <footer className="footer">
        System Time: {now.toLocaleString()} | GOLD-X Arbitrage Engine v1.0
      </footer>
    </div>
  );
}
