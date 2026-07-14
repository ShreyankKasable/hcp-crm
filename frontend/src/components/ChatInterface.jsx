import React, { useState, useRef, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import axios from 'axios';
import {
  setFromAgent,
  appendUserMessage,
  appendAssistantMessage,
  setThinking,
} from '../store/interactionSlice';

const API = 'http://localhost:8000/api/chat';

const S = {
  panel: {
    flex: '1 1 38%', backgroundColor: '#f8f9fa', borderRadius: 8,
    border: '1px solid #dadce0', display: 'flex', flexDirection: 'column',
    height: 'calc(100vh - 96px)',
  },
  header: {
    padding: 16, borderBottom: '1px solid #dadce0', backgroundColor: '#fff',
    borderTopLeftRadius: 8, borderTopRightRadius: 8,
  },
  title: {
    fontSize: 16, fontWeight: 700, color: '#1a73e8',
    display: 'flex', alignItems: 'center', gap: 8,
  },
  subtitle: { fontSize: 12, color: '#5f6368', marginTop: 4 },
  messages: {
    flex: 1, overflowY: 'auto', padding: 16, display: 'flex',
    flexDirection: 'column', gap: 12,
  },
  bubble: (role) => ({
    maxWidth: '88%', padding: '10px 14px', borderRadius: 12, fontSize: 14,
    lineHeight: 1.45, whiteSpace: 'pre-wrap',
    alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
    backgroundColor: role === 'user' ? '#1a73e8' : '#fff',
    color: role === 'user' ? '#fff' : '#3c4043',
    border: role === 'assistant' ? '1px solid #e8eaed' : 'none',
    boxShadow: role === 'assistant' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none',
  }),
  inputArea: {
    padding: 16, borderTop: '1px solid #dadce0', backgroundColor: '#fff',
    display: 'flex', gap: 8, alignItems: 'flex-end',
    borderBottomLeftRadius: 8, borderBottomRightRadius: 8,
  },
  textarea: {
    flex: 1, padding: '10px 12px', border: '1px solid #dadce0', borderRadius: 8,
    fontSize: 14, resize: 'none', minHeight: 44, maxHeight: 120, outline: 'none',
  },
  logBtn: {
    backgroundColor: '#1a73e8', color: '#fff', border: 'none', borderRadius: 8,
    padding: '10px 22px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
};

export default function ChatInterface() {
  const [input, setInput] = useState('');
  const dispatch = useDispatch();
  const sessionId = useSelector((s) => s.interaction.sessionId);
  const chat = useSelector((s) => s.interaction.chat);
  const isThinking = useSelector((s) => s.interaction.isThinking);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [chat, isThinking]);

  const send = async () => {
    const message = input.trim();
    if (!message || isThinking) return;
    setInput('');
    dispatch(appendUserMessage(message));
    dispatch(setThinking(true));
    try {
      const res = await axios.post(API, { session_id: sessionId, message });
      const { assistant_text, form_patch } = res.data;
      // THE ONE WIRE: the agent's patch drives the form.
      if (form_patch && Object.keys(form_patch).length) {
        dispatch(setFromAgent(form_patch));
      }
      dispatch(appendAssistantMessage(assistant_text || 'Done.'));
    } catch (e) {
      dispatch(appendAssistantMessage(
        'Something went wrong reaching the assistant. Check the backend is running.'
      ));
    } finally {
      dispatch(setThinking(false));
    }
  };

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={S.panel}>
      <div style={S.header}>
        <div style={S.title}><span>🤖</span> AI Assistant</div>
        <div style={S.subtitle}>Log interaction via chat</div>
      </div>

      <div style={S.messages} ref={scrollRef}>
        {chat.map((m, i) => (
          <div key={i} style={S.bubble(m.role)}>{m.text}</div>
        ))}
        {isThinking && (
          <div style={{ ...S.bubble('assistant'), color: '#5f6368', fontStyle: 'italic' }}>
            Thinking…
          </div>
        )}
      </div>

      <div style={S.inputArea}>
        <textarea
          style={S.textarea}
          placeholder="Describe interaction..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
        />
        <button style={S.logBtn} onClick={send} disabled={isThinking}>Log</button>
      </div>
    </div>
  );
}