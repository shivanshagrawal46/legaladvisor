import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button, Input, Tooltip, Tag, Typography, ConfigProvider } from "antd";
import {
  SendOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useWebSocket } from "./useWebSocket";
import Sources from "./Sources";
import Sidebar from "./Sidebar";
import { getSessions, createSession, getSession } from "./api";
import { EvidenceProvider } from "./EvidenceContext";
import { renderWithCitations } from "./CitationChip";
import EvidenceDrawer from "./EvidenceDrawer";
import VerificationBanner from "./VerificationBanner";
import AgentReasoningPanel from "./AgentReasoningPanel";

const { Text } = Typography;
const { TextArea } = Input;

const SUGGESTED = [
  "What is the amount in confession of judgement?",
  "When was the settlement agreement filed?",
  "Show me the timeline of this case from 2021 to 2025",
  "What properties are involved in this dispute?",
  "What was the progress when Boris/Mandelbaum was the attorney?",
];

const EMPTY_SESSION = {
  messages: [],
  streaming: false,
  buffer: "",
  sources: null,
  verification: null,
  // Sprint-4: live agent reasoning state. Populated from agent_plan /
  // agent_step / agent_done WS frames. On `done` this is merged into
  // the saved assistant message so history replay still shows it.
  agent: null,             // { plan, steps[], done, trace } | null
  mode: "normal",
  loaded: false,
};

// ReactMarkdown component overrides: intercept text-bearing elements
// and rewrite "[#N]" tokens into clickable <CitationChip/> elements.
// We override paragraph, list-item, table-cell, blockquote, headings,
// and emphasis — i.e. every place Markdown emits a text node — so chips
// render no matter where the LLM placed them.
const MD_COMPONENTS = {
  p:          ({ node, children, ...p }) => <p {...p}>{renderWithCitations(children)}</p>,
  li:         ({ node, children, ...p }) => <li {...p}>{renderWithCitations(children)}</li>,
  td:         ({ node, children, ...p }) => <td {...p}>{renderWithCitations(children)}</td>,
  th:         ({ node, children, ...p }) => <th {...p}>{renderWithCitations(children)}</th>,
  blockquote: ({ node, children, ...p }) => <blockquote {...p}>{renderWithCitations(children)}</blockquote>,
  strong:     ({ node, children, ...p }) => <strong {...p}>{renderWithCitations(children)}</strong>,
  em:         ({ node, children, ...p }) => <em {...p}>{renderWithCitations(children)}</em>,
  h1:         ({ node, children, ...p }) => <h1 {...p}>{renderWithCitations(children)}</h1>,
  h2:         ({ node, children, ...p }) => <h2 {...p}>{renderWithCitations(children)}</h2>,
  h3:         ({ node, children, ...p }) => <h3 {...p}>{renderWithCitations(children)}</h3>,
  h4:         ({ node, children, ...p }) => <h4 {...p}>{renderWithCitations(children)}</h4>,
};

function TypingDots() {
  return (
    <div style={styles.dots}>
      {[0, 0.2, 0.4].map((delay, i) => (
        <span
          key={i}
          className="bounce-dot"
          style={{ ...styles.dot, animationDelay: `${delay}s` }}
        />
      ))}
    </div>
  );
}

function AIMessage({ msg, isStreaming, onInterrupt }) {
  return (
    <EvidenceProvider sources={msg.sources} verification={msg.verification}>
      <div style={styles.aiRow}>
        <div style={styles.aiAvatar}>⚖️</div>
        <div style={styles.aiBubble}>
          {msg.mode === "timeline" && (
            <Tag icon={<ClockCircleOutlined />} style={styles.timelineTag}>
              Timeline mode
            </Tag>
          )}
          {/* Sprint-4: agent reasoning panel above the answer */}
          {msg.agent && (
            <AgentReasoningPanel
              agent={msg.agent}
              isStreaming={isStreaming}
              onInterrupt={isStreaming ? onInterrupt : null}
            />
          )}
          {/* Sprint-3-finish: show verification summary above the answer. */}
          {msg.verification && !isStreaming && <VerificationBanner />}

          {msg.content ? (
            <div className="md-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={MD_COMPONENTS}>
                {msg.content}
              </ReactMarkdown>
              {isStreaming && <span className="typing-cursor" />}
            </div>
          ) : (
            (msg.agent && isStreaming) ? null : <TypingDots />
          )}
          {msg.sources && <Sources items={msg.sources} />}
        </div>
      </div>
      {/* Drawer is mounted inside the provider so it gets the right
          message-scoped sources + verification. AntD `Drawer` portals
          itself out to <body>, so this won't break layout. */}
      <EvidenceDrawer />
    </EvidenceProvider>
  );
}

function UserMessage({ content }) {
  return (
    <div style={styles.userRow}>
      <div style={styles.userBubble}>
        <Text style={styles.userText}>{content}</Text>
      </div>
      <div style={styles.userAvatar}>
        <UserOutlined style={{ fontSize: 14, color: "#6574c4" }} />
      </div>
    </div>
  );
}

export default function Chat({ user }) {
  // ── Session list (left sidebar) ─────────────────────────────────────────────
  const [sessions, setSessions] = useState([]);

  // ── Per-session UI state — the KEY fix: never share state across sessions ──
  // Shape: { [session_id]: { messages, streaming, buffer, sources, mode, loaded } }
  const [sessionStates, setSessionStates] = useState({});
  const [activeId, setActiveId] = useState(null);

  // Track which session is currently receiving the stream so token/sources
  // frames (which don't include session_id) get routed correctly.
  const streamingSidRef = useRef(null);

  // Active session's derived state for rendering
  const active = activeId ? (sessionStates[activeId] || EMPTY_SESSION) : EMPTY_SESSION;

  const [input, setInput] = useState("");
  const [wsReady, setWsReady] = useState(false);
  const bottomRef = useRef(null);

  // Helper: patch a single session's state without disturbing others
  const patchSession = useCallback((sid, patch) => {
    if (!sid) return;
    setSessionStates(prev => {
      const cur = prev[sid] || EMPTY_SESSION;
      const next = typeof patch === "function" ? patch(cur) : { ...cur, ...patch };
      return { ...prev, [sid]: next };
    });
  }, []);

  // ── WebSocket message handler ──────────────────────────────────────────────
  const handleMessage = useCallback((data) => {
    if (data.type === "auth_ok") {
      setWsReady(true);
    } else if (data.type === "start") {
      const sid = data.session_id;
      streamingSidRef.current = sid;
      patchSession(sid, {
        streaming: true,
        buffer: "",
        sources: null,
        verification: null,
        // Sprint-4: if the backend tells us the agent is engaged, seed
        // an empty agent panel so the UI shows the "Investigating…"
        // header BEFORE the first agent_plan frame arrives.
        agent: data.agent_enabled ? { plan: null, steps: [], done: null, trace: null } : null,
        mode: data.mode || "normal",
      });
    } else if (data.type === "agent_plan") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      const { type: _t, ...plan } = data;
      patchSession(sid, cur => ({
        ...cur,
        agent: { ...(cur.agent || { steps: [], done: null, trace: null }), plan },
      }));
    } else if (data.type === "agent_step") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      const { type: _t, ...step } = data;
      patchSession(sid, cur => {
        const agent = cur.agent || { plan: null, steps: [], done: null, trace: null };
        return { ...cur, agent: { ...agent, steps: [...(agent.steps || []), step] } };
      });
    } else if (data.type === "agent_forced_finalize") {
      // Informational — we already show the "investigation closed
      // under budget pressure" status when the done frame arrives.
      // No state mutation needed.
    } else if (data.type === "agent_done") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      const { type: _t, ...done } = data;
      patchSession(sid, cur => ({
        ...cur,
        agent: { ...(cur.agent || { plan: null, steps: [], trace: null }), done },
      }));
    } else if (data.type === "agent_trace") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      patchSession(sid, cur => ({
        ...cur,
        agent: { ...(cur.agent || { plan: null, steps: [], done: null }), trace: data.trace },
      }));
    } else if (data.type === "token") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      patchSession(sid, cur => ({ ...cur, buffer: cur.buffer + data.text }));
    } else if (data.type === "sources") {
      const sid = streamingSidRef.current;
      if (!sid) return;
      patchSession(sid, { sources: data.items });
    } else if (data.type === "verification") {
      // Sprint-3-finish: capture the verifier outcome so the bubble can
      // render the green/amber banner + citation chips with verdicts.
      const sid = streamingSidRef.current;
      if (!sid) return;
      const { type: _ignore, ...payload } = data;
      patchSession(sid, { verification: payload });
    } else if (data.type === "done") {
      const sid = data.session_id;
      patchSession(sid, cur => ({
        ...cur,
        streaming: false,
        buffer: "",
        sources: null,
        verification: null,
        agent: null,
        mode: "normal",
        messages: [
          ...cur.messages,
          {
            role: "assistant",
            content: cur.buffer,
            sources: cur.sources,
            verification: cur.verification,
            // Sprint-4: persist the agent panel state with the message
            // so opening the bubble in a future session replay still
            // shows the reasoning trace.
            agent: cur.agent,
            mode: cur.mode,
          },
        ],
      }));
      streamingSidRef.current = null;
      loadSessions();   // refresh sidebar (title might have changed)
    } else if (data.type === "error") {
      const sid = streamingSidRef.current;
      if (sid) {
        patchSession(sid, cur => ({
          ...cur,
          streaming: false,
          buffer: "",
          messages: [...cur.messages, { role: "assistant", content: `**Error:** ${data.message}` }],
        }));
      }
      streamingSidRef.current = null;
    }
  }, [patchSession]);

  const { connect, send } = useWebSocket({
    onMessage: handleMessage,
    onOpen: () => send({ token: localStorage.getItem("token") }),
    onClose: () => setWsReady(false),
  });

  useEffect(() => { connect(); }, [connect]);

  // Auto-scroll on new content — but only when looking at the active session
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [active.messages.length, active.buffer, activeId]);

  // ── Sessions list ──────────────────────────────────────────────────────────
  async function loadSessions() {
    try {
      const res = await getSessions();
      setSessions(res.data);
    } catch (_) {}
  }
  useEffect(() => { loadSessions(); }, []);

  async function handleNewChat() {
    const res = await createSession();
    const sid = res.data.session_id;
    // seed an empty cached state for the new session
    patchSession(sid, { ...EMPTY_SESSION, loaded: true });
    setActiveId(sid);
    await loadSessions();
  }

  async function handleSelectSession(sid) {
    if (sid === activeId) return;
    setActiveId(sid);

    const cur = sessionStates[sid];

    // If we have local cached state (especially mid-stream or freshly chatted),
    // keep it. Otherwise load history from DB.
    if (cur && cur.loaded) return;

    try {
      const res = await getSession(sid);
      // History replay must rehydrate sources + verification so the
      // citation chips and evidence drawer keep working on saved chats.
      const msgs = (res.data.messages || []).map(m => ({
        role: m.role,
        content: m.content,
        sources: m.sources || null,
        verification: m.verification || null,
        // Sprint-4: restore agent panel from persisted agent_trace.
        // Trace contains the full step list — synthesise a `done`-like
        // summary so the panel header still works on replay.
        agent: m.agent_trace ? {
          plan: null,
          steps: m.agent_trace.steps || [],
          trace: m.agent_trace,
          done: m.agent_trace.final_answer ? {
            outcome: m.agent_trace.final_answer.outcome,
            n_facts: (m.verification?.n_facts) || 0,
            n_verified: (m.verification?.n_verified) || 0,
            tool_calls: m.agent_trace.budget?.tool_calls_used,
            elapsed_ms: (m.agent_trace.budget?.elapsed_s || 0) * 1000,
          } : null,
        } : null,
        mode: m.mode || "normal",
      }));
      patchSession(sid, { ...EMPTY_SESSION, messages: msgs, loaded: true });
    } catch (_) {}
  }

  function handleDeleteSession(sid) {
    setSessions(s => s.filter(x => x.session_id !== sid));
    setSessionStates(s => {
      const { [sid]: _, ...rest } = s;
      return rest;
    });
    if (activeId === sid) setActiveId(null);
  }

  // ── Send question ──────────────────────────────────────────────────────────
  async function handleSend(text) {
    const q = (text || input).trim();
    if (!q) return;
    // Allow asking a new question even if ANOTHER session is streaming —
    // but only block if THIS exact session is currently streaming.
    if (active.streaming) return;

    setInput("");

    let sid = activeId;
    if (!sid) {
      const res = await createSession();
      sid = res.data.session_id;
      setActiveId(sid);
      patchSession(sid, { ...EMPTY_SESSION, loaded: true });
      await loadSessions();
    }

    // Optimistically append the user message AND flip streaming on right
    // away. Without this, the user sees nothing happening for ~30 s while
    // retrieval + Claude run on the backend before the first `start` frame.
    // streamingSidRef is also set so any race-condition early tokens get
    // routed to the right session.
    streamingSidRef.current = sid;
    patchSession(sid, cur => ({
      ...cur,
      messages: [...cur.messages, { role: "user", content: q }],
      streaming: true,
      buffer: "",
      sources: null,
      verification: null,
      agent: null,
      mode: "normal",
    }));

    send({ type: "question", text: q, session_id: sid });
  }

  // Sprint-4: send an out-of-band interrupt frame. The backend sets
  // budget.interrupt_requested = True on the running agent, which
  // forces the next iteration to finalize with what it has.
  const handleInterrupt = useCallback(() => {
    const sid = streamingSidRef.current;
    if (!sid) return;
    send({ type: "interrupt", session_id: sid });
  }, [send]);

  // Show welcome only on an empty, non-streaming session
  const showWelcome = activeId === null || (active.messages.length === 0 && !active.streaming);
  const msgCount = active.messages.filter(m => m.role === "user").length;

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#6574c4",
          borderRadius: 8,
          fontFamily: "Inter, -apple-system, sans-serif",
        },
      }}
    >
      <div style={styles.layout}>
        <Sidebar
          sessions={sessions}
          activeId={activeId}
          onSelect={handleSelectSession}
          onNew={handleNewChat}
          onDelete={handleDeleteSession}
          userName={user.name}
        />

        <div style={styles.main}>
          {/* Top bar */}
          <div style={styles.topbar}>
            <div style={styles.topbarLeft}>
              <div style={styles.topbarTitle}>Legal Advisor</div>
              <Text style={styles.topbarSub}>Fraud Investigation Assistant</Text>
            </div>
            <div style={styles.topbarRight}>
              <Tag
                icon={<span style={{ ...styles.statusDot, background: wsReady ? "#52c41a" : "#faad14" }} />}
                style={{
                  ...styles.statusTag,
                  background: wsReady ? "#f5f9f0" : "#fdf5e8",
                  borderColor: wsReady ? "#d9f0c7" : "#f5dfa0",
                  color: wsReady ? "#52a940" : "#b07a1a",
                }}
              >
                {wsReady ? "Live" : "Connecting"}
              </Tag>
              <Tag icon={<RobotOutlined />} style={styles.modelTag}>
                Claude Sonnet 4.6
              </Tag>
              <Tag icon={<ThunderboltOutlined />} style={styles.voyageTag}>
                Voyage AI
              </Tag>
            </div>
          </div>

          {/* Messages */}
          <div style={styles.messages}>
            {showWelcome && (
              <div style={styles.welcome}>
                <div style={styles.welcomeIconWrap}>
                  <span style={{ fontSize: 36 }}>⚖️</span>
                </div>
                <div style={styles.welcomeTitle}>Good day, {user.name.split(" ")[0]}</div>
                <Text style={styles.welcomeText}>
                  Ask anything about the fraud case — court filings, dates, amounts, parties, timelines.
                </Text>
                <div style={styles.suggestGrid}>
                  {SUGGESTED.map(s => (
                    <button
                      key={s}
                      className="suggestion-btn"
                      style={styles.suggestion}
                      onClick={() => handleSend(s)}
                    >
                      <span style={styles.suggestionArrow}>→</span>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {active.messages.map((m, i) =>
              m.role === "user"
                ? <UserMessage key={i} content={m.content} />
                : <AIMessage key={i} msg={m} isStreaming={false} />
            )}

            {/* Streaming bubble — ONLY on the active session if it's streaming.
                We pass sources/verification/agent so once they arrive (before
                the `done` frame) chips + sources + reasoning panel render live. */}
            {active.streaming && (
              <AIMessage
                msg={{
                  role: "assistant",
                  content: active.buffer,
                  sources: active.sources,
                  verification: active.verification,
                  agent: active.agent,
                  mode: active.mode,
                }}
                isStreaming={true}
                onInterrupt={handleInterrupt}
              />
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div style={styles.inputArea}>
            <div style={styles.inputCard}>
              <TextArea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
                }}
                placeholder="Ask the legal advisor… (Enter to send, Shift+Enter for new line)"
                autoSize={{ minRows: 1, maxRows: 6 }}
                variant="borderless"
                disabled={active.streaming || !wsReady}
                style={styles.textarea}
              />
              <div style={styles.inputFooter}>
                <Text style={styles.inputHint}>
                  {active.streaming
                    ? active.buffer
                      ? "✍️ Claude is writing the answer…"
                      : "🔍 Retrieving evidence & consulting Claude…"
                    : msgCount > 0
                    ? `${msgCount} question${msgCount > 1 ? "s" : ""} in this session · Enter to send`
                    : "Enter to send · Shift+Enter for new line"}
                </Text>
                <Tooltip title={!wsReady ? "Connecting…" : active.streaming ? "Processing…" : "Send"}>
                  <Button
                    type="primary"
                    shape="circle"
                    icon={<SendOutlined />}
                    onClick={() => handleSend()}
                    disabled={!input.trim() || active.streaming || !wsReady}
                    style={styles.sendBtn}
                  />
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ConfigProvider>
  );
}

const styles = {
  layout: { display: "flex", height: "100vh", overflow: "hidden", background: "#f5f6fa" },
  main: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
  topbar: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "12px 28px", background: "#ffffff",
    borderBottom: "1px solid #ebedf5", flexShrink: 0,
    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
  },
  topbarLeft: { display: "flex", alignItems: "center", gap: 10 },
  topbarTitle: { fontWeight: 700, fontSize: 15, color: "#1a1d2e" },
  topbarSub: {
    fontSize: 12, color: "#b0b6cc",
    borderLeft: "1px solid #ebedf5", paddingLeft: 10, marginLeft: 2,
  },
  topbarRight: { display: "flex", alignItems: "center", gap: 6 },
  statusDot: { display: "inline-block", width: 6, height: 6, borderRadius: "50%", marginRight: 5 },
  statusTag: { fontSize: 11, borderRadius: 20, display: "flex", alignItems: "center", fontWeight: 500 },
  modelTag: { fontSize: 11, borderRadius: 20, background: "#eef0fb", borderColor: "#d4d9f0", color: "#6574c4", fontWeight: 500 },
  voyageTag: { fontSize: 11, borderRadius: 20, background: "#fdf5e8", borderColor: "#f5dfa0", color: "#b07a1a", fontWeight: 500 },
  messages: { flex: 1, overflowY: "auto", padding: "24px 0" },
  welcome: {
    display: "flex", flexDirection: "column", alignItems: "center",
    padding: "48px 24px 24px", maxWidth: 620, margin: "0 auto", width: "100%", textAlign: "center",
  },
  welcomeIconWrap: {
    width: 72, height: 72, borderRadius: 16,
    background: "linear-gradient(135deg, #eef0fb, #e4e7f8)",
    border: "1px solid rgba(101,116,196,0.15)",
    display: "flex", alignItems: "center", justifyContent: "center",
    marginBottom: 18, boxShadow: "0 4px 16px rgba(101,116,196,0.12)",
  },
  welcomeTitle: { fontSize: 22, fontWeight: 700, color: "#1a1d2e", marginBottom: 8 },
  welcomeText: { color: "#8892b0", fontSize: 14, lineHeight: 1.65, marginBottom: 28 },
  suggestGrid: { display: "flex", flexDirection: "column", gap: 8, width: "100%" },
  suggestion: {
    background: "#ffffff", border: "1px solid #ebedf5", borderRadius: 10,
    padding: "12px 16px", color: "#3d4566", fontSize: 13, textAlign: "left",
    cursor: "pointer", display: "flex", alignItems: "center", gap: 10,
    fontFamily: "Inter, sans-serif", transition: "all 0.15s",
    boxShadow: "0 1px 3px rgba(0,0,0,0.03)",
  },
  suggestionArrow: { fontSize: 14, color: "#b0b6cc", flexShrink: 0 },
  aiRow: {
    display: "flex", alignItems: "flex-start", gap: 12,
    padding: "8px 28px", maxWidth: 880, margin: "0 auto", width: "100%",
  },
  aiAvatar: { fontSize: 22, flexShrink: 0, paddingTop: 4, lineHeight: 1 },
  aiBubble: {
    flex: 1, background: "#ffffff", border: "1px solid #ebedf5",
    borderRadius: "4px 12px 12px 12px", padding: "14px 18px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.04)", minWidth: 0,
  },
  timelineTag: {
    marginBottom: 12, background: "#fdf8ee",
    borderColor: "#f5dfa0", color: "#b07a1a",
    borderRadius: 4, fontSize: 11, fontWeight: 600,
  },
  userRow: {
    display: "flex", alignItems: "flex-start", justifyContent: "flex-end",
    gap: 10, padding: "8px 28px", maxWidth: 880, margin: "0 auto", width: "100%",
  },
  userBubble: {
    background: "linear-gradient(135deg, #6574c4, #8b6cc8)",
    borderRadius: "12px 4px 12px 12px", padding: "12px 16px",
    maxWidth: "72%", boxShadow: "0 2px 8px rgba(101,116,196,0.2)",
  },
  userText: { fontSize: 14, color: "#ffffff", lineHeight: 1.65 },
  userAvatar: {
    width: 32, height: 32, borderRadius: "50%",
    background: "#eef0fb", border: "1px solid #d4d9f0",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0, paddingTop: 4,
  },
  dots: { display: "flex", gap: 5, alignItems: "center", padding: "4px 0" },
  dot: { width: 7, height: 7, borderRadius: "50%", background: "#c5c9dc", display: "inline-block" },
  inputArea: { padding: "16px 28px 20px", background: "#f5f6fa", flexShrink: 0 },
  inputCard: {
    background: "#ffffff", border: "1px solid #e2e5f0",
    borderRadius: 12, padding: "12px 14px 10px",
    boxShadow: "0 2px 12px rgba(101,116,196,0.08)",
    maxWidth: 824, margin: "0 auto",
  },
  textarea: {
    fontSize: 14, color: "#1a1d2e", background: "transparent",
    resize: "none", lineHeight: 1.65, padding: "2px 6px",
  },
  inputFooter: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    marginTop: 8, paddingTop: 8, borderTop: "1px solid #f0f2f9",
  },
  inputHint: { fontSize: 11, color: "#c5c9dc" },
  sendBtn: {
    background: "linear-gradient(135deg, #6574c4, #8b6cc8)",
    border: "none", boxShadow: "0 2px 8px rgba(101,116,196,0.3)",
  },
};
