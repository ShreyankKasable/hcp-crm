import { createSlice } from '@reduxjs/toolkit';
import { v4 as uuidv4 } from 'uuid';

const todayISO = new Date().toISOString().split('T')[0];
const nowTime = new Date().toTimeString().slice(0, 5);

const emptyForm = {
  hcpName: '',
  interactionType: 'Meeting',
  date: todayISO,
  time: nowTime,
  attendees: [],
  topicsDiscussed: '',
  materialsShared: [],
  samplesDistributed: [],
  sentiment: 'neutral',
  outcomes: '',
  followUpActions: [],
};

const initialState = {
  sessionId: uuidv4(), // minted once per app load
  form: { ...emptyForm },
  // fields the agent just touched — used for the "AI is filling" highlight
  recentlyUpdated: [],
  chat: [
    {
      role: 'assistant',
      text:
        'Log interaction details here (e.g., "Met Dr. Smith, discussed ' +
        'Product X efficacy, positive sentiment, shared brochure") or ask for help.',
    },
  ],
  isThinking: false,
};

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    // The core wire: merge an agent-produced patch into the form.
    // Absent keys are left untouched (that's how edit changes only some fields).
    setFromAgent: (state, action) => {
      const patch = action.payload || {};
      Object.entries(patch).forEach(([key, value]) => {
        state.form[key] = value;
      });
      state.recentlyUpdated = Object.keys(patch);
    },
    clearRecentlyUpdated: (state) => {
      state.recentlyUpdated = [];
    },
    appendUserMessage: (state, action) => {
      state.chat.push({ role: 'user', text: action.payload });
    },
    appendAssistantMessage: (state, action) => {
      state.chat.push({ role: 'assistant', text: action.payload });
    },
    setThinking: (state, action) => {
      state.isThinking = action.payload;
    },
    resetForm: (state) => {
      state.form = { ...emptyForm };
      state.recentlyUpdated = [];
    },
  },
});

export const {
  setFromAgent,
  clearRecentlyUpdated,
  appendUserMessage,
  appendAssistantMessage,
  setThinking,
  resetForm,
} = interactionSlice.actions;

export default interactionSlice.reducer;