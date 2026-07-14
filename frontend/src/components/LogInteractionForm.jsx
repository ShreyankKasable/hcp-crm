import React, { useEffect, useRef } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { clearRecentlyUpdated } from '../store/interactionSlice';

// The form is a DISPLAY-BOUND MIRROR of agent state. Inputs are read-only on
// the demo path — the rep drives everything through the chat. This is the
// enforcement of the assignment's one hard rule: never fill the form by hand.

const S = {
  panel: {
    flex: '1 1 62%',
    backgroundColor: '#fff',
    borderRadius: 8,
    border: '1px solid #dadce0',
    padding: 24,
    height: 'calc(100vh - 96px)',
    overflowY: 'auto',
  },
  h1: { fontSize: 22, fontWeight: 700, marginBottom: 20 },
  section: { fontSize: 13, fontWeight: 600, color: '#5f6368', margin: '18px 0 10px' },
  row: { display: 'flex', gap: 16, marginBottom: 4 },
  field: { flex: 1, marginBottom: 14 },
  label: { display: 'block', fontSize: 13, fontWeight: 600, marginBottom: 6, color: '#3c4043' },
  input: {
    width: '100%', padding: '10px 12px', border: '1px solid #dadce0',
    borderRadius: 6, fontSize: 14, backgroundColor: '#fff', color: '#202124',
  },
  textarea: {
    width: '100%', padding: '10px 12px', border: '1px solid #dadce0',
    borderRadius: 6, fontSize: 14, minHeight: 72, resize: 'vertical',
    backgroundColor: '#fff', color: '#202124',
  },
  chipRow: { display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 4 },
  chip: {
    fontSize: 13, padding: '4px 10px', backgroundColor: '#e8f0fe',
    color: '#1967d2', borderRadius: 12,
  },
  muted: { fontSize: 13, color: '#9aa0a6', fontStyle: 'italic' },
  sentimentRow: { display: 'flex', gap: 24, marginTop: 4 },
  sentimentOpt: { display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 },
};

function highlightClass(field, recentlyUpdated) {
  return recentlyUpdated.includes(field) ? 'ai-filled' : '';
}

export default function LogInteractionForm() {
  const form = useSelector((s) => s.interaction.form);
  const recentlyUpdated = useSelector((s) => s.interaction.recentlyUpdated);
  const dispatch = useDispatch();
  const timer = useRef(null);

  useEffect(() => {
    if (recentlyUpdated.length) {
      clearTimeout(timer.current);
      timer.current = setTimeout(() => dispatch(clearRecentlyUpdated()), 1300);
    }
  }, [recentlyUpdated, dispatch]);

  const list = (arr) =>
    arr && arr.length ? (
      <div style={S.chipRow}>
        {arr.map((x, i) => (
          <span key={i} style={S.chip}>{x}</span>
        ))}
      </div>
    ) : (
      <span style={S.muted}>None added.</span>
    );

  return (
    <div style={S.panel}>
      <div style={S.h1}>Log HCP Interaction</div>

      <div style={S.section}>INTERACTION DETAILS</div>

      <div style={S.row}>
        <div style={S.field}>
          <label style={S.label}>HCP Name</label>
          <input
            style={S.input}
            className={highlightClass('hcpName', recentlyUpdated)}
            value={form.hcpName}
            placeholder="Search or select HCP..."
            readOnly
          />
        </div>
        <div style={S.field}>
          <label style={S.label}>Interaction Type</label>
          <input
            style={S.input}
            className={highlightClass('interactionType', recentlyUpdated)}
            value={form.interactionType}
            readOnly
          />
        </div>
      </div>

      <div style={S.row}>
        <div style={S.field}>
          <label style={S.label}>Date</label>
          <input
            style={S.input}
            className={highlightClass('date', recentlyUpdated)}
            value={form.date}
            readOnly
          />
        </div>
        <div style={S.field}>
          <label style={S.label}>Time</label>
          <input
            style={S.input}
            className={highlightClass('time', recentlyUpdated)}
            value={form.time}
            readOnly
          />
        </div>
      </div>

      <div style={S.field}>
        <label style={S.label}>Attendees</label>
        {list(form.attendees)}
      </div>

      <div style={S.field}>
        <label style={S.label}>Topics Discussed</label>
        <textarea
          style={S.textarea}
          className={highlightClass('topicsDiscussed', recentlyUpdated)}
          value={form.topicsDiscussed}
          placeholder="Enter key discussion points..."
          readOnly
        />
      </div>

      <div style={S.section}>MATERIALS SHARED / SAMPLES DISTRIBUTED</div>
      <div style={S.field}>
        <label style={S.label}>Materials Shared</label>
        <div className={highlightClass('materialsShared', recentlyUpdated)}>
          {list(form.materialsShared)}
        </div>
      </div>
      <div style={S.field}>
        <label style={S.label}>Samples Distributed</label>
        <div className={highlightClass('samplesDistributed', recentlyUpdated)}>
          {list(form.samplesDistributed)}
        </div>
      </div>

      <div style={S.section}>OBSERVED / INFERRED HCP SENTIMENT</div>
      <div
        style={S.sentimentRow}
        className={highlightClass('sentiment', recentlyUpdated)}
      >
        {['positive', 'neutral', 'negative'].map((s) => (
          <label key={s} style={S.sentimentOpt}>
            <input type="radio" checked={form.sentiment === s} readOnly />
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </label>
        ))}
      </div>

      <div style={{ ...S.field, marginTop: 18 }}>
        <label style={S.label}>Outcomes</label>
        <textarea
          style={S.textarea}
          className={highlightClass('outcomes', recentlyUpdated)}
          value={form.outcomes}
          placeholder="Key outcomes or agreements..."
          readOnly
        />
      </div>

      <div style={S.field}>
        <label style={S.label}>Follow-up Actions</label>
        <div className={highlightClass('followUpActions', recentlyUpdated)}>
          {list(form.followUpActions)}
        </div>
      </div>
    </div>
  );
}