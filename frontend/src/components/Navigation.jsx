import React from 'react';

const TABS = [
  { id: 'overview', label: 'Market Overview', icon: '📊' },
  { id: 'radar', label: 'Parity Radar', icon: '🎯' },
  { id: 'signals', label: 'Relative-Value Signals', icon: '⚡' },
  { id: 'backtest', label: 'Backtest Engine', icon: '📈' },
  { id: 'lifecycle', label: 'Contract Lifecycle', icon: '⏳' },
  { id: 'status', label: 'System & Data Health', icon: '🛡️' },
];

export default function Navigation({ activeTab, onSelectTab, signalCount = 0 }) {
  return (
    <nav className="nav-tab-bar" aria-label="Terminal Navigation">
      {TABS.map(tab => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab ${isActive ? 'active' : ''}`}
            onClick={() => onSelectTab(tab.id)}
            aria-selected={isActive}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
            {tab.id === 'signals' && signalCount > 0 && (
              <span className="tab-badge">{signalCount}</span>
            )}
          </button>
        );
      })}
    </nav>
  );
}
