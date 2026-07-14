import React from 'react';
import LogInteractionForm from './components/LogInteractionForm';
import ChatInterface from './components/ChatInterface';

const S = {
  app: { padding: 24, minHeight: '100vh' },
  split: { display: 'flex', gap: 20, alignItems: 'stretch' },
};

export default function App() {
  return (
    <div style={S.app}>
      <div style={S.split}>
        <LogInteractionForm />
        <ChatInterface />
      </div>
    </div>
  );
}