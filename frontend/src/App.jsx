import React, { useState } from 'react';
import Layout from './components/Layout';
import MarketOverview from './components/MarketOverview';
import ParityRadar from './components/ParityRadar';
import SignalCard from './components/SignalCard';
import BacktestView from './components/BacktestView';
import ContractLifecycle from './components/ContractLifecycle';
import SystemStatus from './components/SystemStatus';
import { useApi } from './hooks/useApi';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const { data: signals } = useApi('/signals', { pollInterval: 30000 });

  const signalCount = signals ? signals.length : 0;

  return (
    <Layout
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      signalCount={signalCount}
    >
      {activeTab === 'overview' && (
        <MarketOverview onNavigateTab={setActiveTab} />
      )}
      {activeTab === 'radar' && (
        <ParityRadar />
      )}
      {activeTab === 'signals' && (
        <SignalCard />
      )}
      {activeTab === 'backtest' && (
        <BacktestView />
      )}
      {activeTab === 'lifecycle' && (
        <ContractLifecycle />
      )}
      {activeTab === 'status' && (
        <SystemStatus />
      )}
    </Layout>
  );
}

export default App;
