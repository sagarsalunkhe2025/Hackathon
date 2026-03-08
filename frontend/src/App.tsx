import { useState, useRef, useEffect, useCallback } from 'react';
import {
  sendChatMessage,
  runAnalysis,
  type Message,
  type ChatResponse,
} from './api';

/* ───── Analysis sidebar items ───── */
const ANALYSES: { key: string; label: string; description: string }[] = [
  { key: 'duplicates', label: '🔁 Duplicate Roles', description: 'Roles with identical authorizations' },
  { key: 'unused', label: '🗑️ Unused Roles', description: 'Roles not assigned to any user' },
  { key: 'overprivileged', label: '⚠️ Overprivileged Users', description: 'Users with excessive privileges' },
  { key: 'expired', label: '⏰ Expired Assignments', description: 'Role assignments past expiry date' },
  { key: 'orphaned', label: '👻 Orphaned Assignments', description: 'Assignments with no matching role' },
  { key: 'role-distribution', label: '📊 Role Distribution', description: 'Roles by type & application area' },
  { key: 'user-risk-score', label: '🎯 User Risk Scores', description: 'Risk scoring based on role metrics' },
];

const CATEGORIES = [
  { key: '', label: 'All' },
  { key: 'roles', label: 'Roles' },
  { key: 'users', label: 'Users' },
  { key: 'usergroups', label: 'User Groups' },
  { key: 'analysis', label: 'Analysis' },
];

const QUICK_PROMPTS = [
  'Show me all users with more than 10 roles',
  'List roles that grant full transaction code access',
  'Which roles have not been assigned to any user?',
  'Show expired role assignments from the last 30 days',
  'Find duplicate roles with the same authorization hash',
  'Top 10 departments by average role count per user',
];

let msgCounter = 0;
const newId = () => `msg-${++msgCounter}-${Date.now()}`;

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  /* auto-scroll */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* ── handle chat submit ── */
  const handleSubmit = useCallback(
    async (prompt: string) => {
      if (!prompt.trim() || loading) return;

      const userMsg: Message = { id: newId(), role: 'user', content: prompt };
      const loadingMsg: Message = { id: newId(), role: 'assistant', content: '', loading: true };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      setInput('');
      setLoading(true);

      try {
        const response = await sendChatMessage({ prompt, category: category || undefined });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, content: response.summary, response, loading: false }
              : m
          )
        );
      } catch (err) {
        const errResponse: ChatResponse = {
          success: false,
          summary: '',
          error: (err as Error).message,
        };
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, content: 'Error occurred', response: errResponse, loading: false }
              : m
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [category, loading]
  );

  /* ── handle quick analysis ── */
  const handleAnalysis = useCallback(
    async (analysisType: string) => {
      if (loading) return;

      const label = ANALYSES.find((a) => a.key === analysisType)?.label ?? analysisType;
      const userMsg: Message = { id: newId(), role: 'user', content: `Run analysis: ${label}` };
      const loadingMsg: Message = { id: newId(), role: 'assistant', content: '', loading: true };

      setMessages((prev) => [...prev, userMsg, loadingMsg]);
      setLoading(true);

      try {
        const response = await runAnalysis({ analysisType });
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, content: response.summary, response, loading: false }
              : m
          )
        );
      } catch (err) {
        const errResponse: ChatResponse = {
          success: false,
          summary: '',
          error: (err as Error).message,
        };
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, content: 'Error occurred', response: errResponse, loading: false }
              : m
          )
        );
      } finally {
        setLoading(false);
      }
    },
    [loading]
  );

  return (
    <div className="app-container">
      {/* ──── Sidebar ──── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>🛡️ Role Assistant</h1>
          <p>AI-powered role governance analysis</p>
        </div>
        <div className="sidebar-content">
          <div className="sidebar-section">Quick Analyses</div>
          {ANALYSES.map((a) => (
            <button
              key={a.key}
              className="analysis-btn"
              onClick={() => handleAnalysis(a.key)}
              disabled={loading}
            >
              {a.label}
              <span className="desc">{a.description}</span>
            </button>
          ))}
        </div>
      </aside>

      {/* ──── Main ──── */}
      <main className="main-content">
        <header className="main-header">
          <h2>Chat</h2>
          <div className="category-tabs">
            {CATEGORIES.map((c) => (
              <button
                key={c.key}
                className={`category-tab ${category === c.key ? 'active' : ''}`}
                onClick={() => setCategory(c.key)}
              >
                {c.label}
              </button>
            ))}
          </div>
        </header>

        <div className="chat-area">
          {messages.length === 0 && (
            <div className="welcome-message">
              <h3>Welcome to Role Assistant</h3>
              <p>
                Ask questions about SAP roles, users, and permissions in natural language.
                I'll convert your request to SQL, run it, and explain the results.
              </p>
              <div className="quick-prompts">
                {QUICK_PROMPTS.map((p) => (
                  <button key={p} className="quick-prompt" onClick={() => handleSubmit(p)}>
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className="message">
              {msg.role === 'user' ? (
                <div className="message-user">{msg.content}</div>
              ) : msg.loading ? (
                <div className="message-loading">
                  <div className="spinner" />
                  Analyzing your request…
                </div>
              ) : (
                <AssistantMessage response={msg.response} />
              )}
            </div>
          ))}

          <div ref={chatEndRef} />
        </div>

        <div className="input-bar">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSubmit(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about roles, users, permissions…"
              disabled={loading}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              {loading ? 'Analyzing…' : 'Send'}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}

/* ───────────────────────────────────
   Assistant message sub-component
   ─────────────────────────────────── */
function AssistantMessage({ response }: { response?: ChatResponse }) {
  const [showSql, setShowSql] = useState(false);
  const [showAllRows, setShowAllRows] = useState(false);

  if (!response) return null;

  if (!response.success) {
    return <div className="message-assistant error-message">{response.error}</div>;
  }

  const data = response.data ?? [];
  const columns = data.length > 0 ? Object.keys(data[0]) : [];
  const visibleRows = showAllRows ? data : data.slice(0, 25);

  return (
    <div className="message-assistant">
      {/* Summary */}
      <div className="summary-text">{response.summary}</div>

      {/* Insights */}
      {response.insights && response.insights.length > 0 && (
        <div className="insights-container">
          {response.insights.map((insight, i) => (
            <div key={i} className={`insight-card ${insight.severity}`}>
              <div className="insight-title">{insight.title}</div>
              <div className="insight-description">{insight.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* SQL Toggle */}
      {response.sqlQuery && (
        <>
          <button className="sql-toggle" onClick={() => setShowSql(!showSql)}>
            {showSql ? '▼ Hide SQL' : '▶ Show SQL Query'}
          </button>
          {showSql && <pre className="sql-block">{response.sqlQuery}</pre>}
        </>
      )}

      {/* Data Table */}
      {data.length > 0 && (
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleRows.map((row, ri) => (
                <tr key={ri}>
                  {columns.map((col) => (
                    <td key={col} title={String(row[col] ?? '')}>
                      {formatCell(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="data-table-info">
            Showing {visibleRows.length} of {data.length} rows
            {data.length > 25 && !showAllRows && (
              <>
                {' · '}
                <button
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-primary)',
                    cursor: 'pointer',
                    fontSize: 'inherit',
                    textDecoration: 'underline',
                  }}
                  onClick={() => setShowAllRows(true)}
                >
                  Show all
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return String(value);
}
