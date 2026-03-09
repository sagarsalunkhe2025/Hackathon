import { useState, useRef, useEffect, useCallback } from 'react';
import {
  sendChatMessage,
  runAnalysis,
  type Message,
  type ChatResponse,
  type ChatSession,
} from './api';
import ChartRenderer from './ChartRenderer';

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

const SESSIONS_KEY = 'role-assistant-sessions';
const ACTIVE_SESSION_KEY = 'role-assistant-active-session';
const THEME_KEY = 'role-assistant-theme';

function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function createNewSession(name?: string): ChatSession {
  const now = Date.now();
  return {
    id: generateSessionId(),
    name: name ?? `Chat ${new Date(now).toLocaleDateString()} ${new Date(now).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatSession[];
    // Strip loading messages
    return parsed.map((s) => ({
      ...s,
      messages: s.messages.filter((m) => !m.loading),
    }));
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]) {
  try {
    // Cap messages per session to avoid storage bloat
    const toSave = sessions.map((s) => ({
      ...s,
      messages: s.messages.filter((m) => !m.loading).slice(-100),
    }));
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(toSave));
  } catch {
    // localStorage full or unavailable
  }
}

function loadActiveSessionId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_SESSION_KEY);
  } catch {
    return null;
  }
}

function migrateOldHistory(): ChatSession | null {
  try {
    const raw = localStorage.getItem('role-assistant-chat-history');
    if (!raw) return null;
    const msgs = JSON.parse(raw) as Message[];
    if (!msgs.length) return null;
    const session = createNewSession('Imported Chat');
    session.messages = msgs.filter((m) => !m.loading);
    localStorage.removeItem('role-assistant-chat-history');
    return session;
  } catch {
    return null;
  }
}

function loadTheme(): 'light' | 'dark' {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
    if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) return 'dark';
  } catch { /* ignore */ }
  return 'light';
}

function initSessions(): { sessions: ChatSession[]; activeId: string } {
  let sessions = loadSessions();
  const migrated = migrateOldHistory();
  if (migrated) sessions = [migrated, ...sessions];
  if (sessions.length === 0) {
    const first = createNewSession();
    sessions = [first];
  }
  const savedId = loadActiveSessionId();
  const activeId = sessions.find((s) => s.id === savedId)?.id ?? sessions[0].id;
  return { sessions, activeId };
}

let msgCounter = 0;
const newId = () => `msg-${++msgCounter}-${Date.now()}`;

export default function App() {
  const [sessionsState] = useState(initSessions);
  const [activeSessionId, setActiveSessionIdRaw] = useState(sessionsState.activeId);
  const [sessions, setSessions] = useState<ChatSession[]>(sessionsState.sessions);
  const [input, setInput] = useState('');
  const [category, setCategory] = useState('');
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>(loadTheme);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);

  const activeSession = sessions.find((s) => s.id === activeSessionId) ?? sessions[0];
  const messages = activeSession?.messages ?? [];

  const setActiveSessionId = (id: string) => {
    setActiveSessionIdRaw(id);
    localStorage.setItem(ACTIVE_SESSION_KEY, id);
  };

  const setMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeSessionId) return s;
        const newMsgs = typeof updater === 'function' ? updater(s.messages) : updater;
        return { ...s, messages: newMsgs, updatedAt: Date.now() };
      })
    );
  };

  /* Apply theme to document */
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  /* Persist sessions to localStorage */
  useEffect(() => {
    saveSessions(sessions);
  }, [sessions]);

  /* auto-scroll */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* focus rename input */
  useEffect(() => {
    if (renamingId) renameInputRef.current?.focus();
  }, [renamingId]);

  const toggleTheme = () => setTheme((t) => (t === 'light' ? 'dark' : 'light'));

  /* ── Session management ── */
  const handleNewChat = () => {
    const newSession = createNewSession();
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
  };

  const handleSwitchSession = (id: string) => {
    if (id === activeSessionId) return;
    setActiveSessionId(id);
  };

  const handleDeleteSession = (id: string) => {
    setSessions((prev) => {
      const remaining = prev.filter((s) => s.id !== id);
      if (remaining.length === 0) {
        const fresh = createNewSession();
        setActiveSessionId(fresh.id);
        return [fresh];
      }
      if (id === activeSessionId) {
        setActiveSessionId(remaining[0].id);
      }
      return remaining;
    });
  };

  const handleStartRename = (id: string, currentName: string) => {
    setRenamingId(id);
    setRenameValue(currentName);
  };

  const handleFinishRename = () => {
    if (renamingId && renameValue.trim()) {
      setSessions((prev) =>
        prev.map((s) => (s.id === renamingId ? { ...s, name: renameValue.trim() } : s))
      );
    }
    setRenamingId(null);
    setRenameValue('');
  };

  const clearChat = () => {
    setMessages([]);
  };

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
        // Build conversation history from previous messages (last 10)
        const history = messages
          .filter((m) => !m.loading)
          .slice(-10)
          .map((m) => ({
            role: m.role,
            content: m.role === 'assistant' ? (m.response?.summary ?? m.content) : m.content,
          }));

        const response = await sendChatMessage({ prompt, category: category || undefined, history });
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
          {/* ── Quick Analyses ── */}
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

          {/* ── Chat Sessions ── */}
          <div className="sidebar-section-row">
            <span className="sidebar-section">Chat Sessions</span>
            <button className="new-chat-btn" onClick={handleNewChat} title="New chat">
              ＋ New
            </button>
          </div>
          <div className="session-list">
            {sessions.map((s) => (
              <div
                key={s.id}
                className={`session-item ${s.id === activeSessionId ? 'active' : ''}`}
                onClick={() => handleSwitchSession(s.id)}
              >
                {renamingId === s.id ? (
                  <input
                    ref={renameInputRef}
                    className="session-rename-input"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={handleFinishRename}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleFinishRename();
                      if (e.key === 'Escape') { setRenamingId(null); setRenameValue(''); }
                    }}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <div className="session-info">
                      <span className="session-name" title={s.name}>💬 {s.name}</span>
                      <span className="session-meta">
                        {s.messages.filter((m) => !m.loading).length} messages
                      </span>
                    </div>
                    <div className="session-actions">
                      <button
                        className="session-action-btn"
                        title="Rename"
                        onClick={(e) => { e.stopPropagation(); handleStartRename(s.id, s.name); }}
                      >
                        ✏️
                      </button>
                      <button
                        className="session-action-btn delete"
                        title="Delete"
                        onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id); }}
                      >
                        🗑️
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
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
          <div className="header-actions">
            {messages.length > 0 && (
              <button className="clear-chat-btn" onClick={clearChat}>
                🗑️ Clear
              </button>
            )}
            <button
              className="theme-toggle"
              onClick={toggleTheme}
              title={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
            >
              {theme === 'light' ? '🌙' : '☀️'}
            </button>
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

      {/* Chart Visualization */}
      {response.chartConfig && data.length > 0 && (
        <ChartRenderer chartConfig={response.chartConfig} data={data} />
      )}

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
