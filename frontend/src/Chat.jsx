import { useState, useEffect, useRef, useCallback, useMemo, memo } from "react";
import { Link } from "react-router-dom";
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

const AIMessage = memo(function AIMessage({ msg, isStreaming, onInterrupt }) {
  return (
    <EvidenceProvider sources={msg.sources} verification={msg.verification}>
      <div style={styles.aiRow} className="msg-in">
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
});

const UserMessage = memo(function UserMessage({ content }) {
  return (
    <div style={styles.userRow} className="msg-in">
      <div style={styles.userBubble}>
        <Text style={styles.userText}>{content}</Text>
      </div>
      <div style={styles.userAvatar}>
        <UserOutlined style={{ fontSize: 14, color: "var(--river)" }} />
      </div>
    </div>
  );
});

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

    // Seed a "loading" placeholder so the welcome screen does NOT flash
    // while we fetch the conversation history from the server.
    setSessionStates(prev => prev[sid] ? prev : { ...prev, [sid]: { ...EMPTY_SESSION, loaded: false } });

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

  // Show welcome only on an empty, non-streaming, *loaded* session.
  // Without the `loaded` guard the welcome screen flashes for ~1s every
  // time the user clicks a conversation that hasn't been hydrated yet.
  const showWelcome = activeId === null || (active.loaded && active.messages.length === 0 && !active.streaming);
  const showSessionLoading = activeId !== null && !active.loaded && active.messages.length === 0 && !active.streaming;
  const msgCount = active.messages.filter(m => m.role === "user").length;

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#234a52",
          colorLink: "#234a52",
          borderRadius: 4,
          fontFamily: "'Inter', -apple-system, sans-serif",
          colorBgSpotlight: "#fdfbf6",
          colorTextLightSolid: "#1c1e2a",
        },
        components: {
          Tooltip: {
            colorBgSpotlight: "#fdfbf6",
            colorTextLightSolid: "#1c1e2a",
            borderRadiusOuter: 8,
            borderRadius: 8,
          },
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
              <Text style={styles.topbarSub}>Fraud Investigation</Text>
              {/* Jump to the investigation workspace pages */}
              <nav style={styles.topbarNav}>
                <Link to="/portfolio" style={styles.navLink}>Portfolio</Link>
                <Link to="/findings" style={styles.navLink}>Findings</Link>
              </nav>
            </div>
            <div style={styles.topbarRight}>
              <Tag
                icon={<span style={{ ...styles.statusDot, background: wsReady ? "var(--green)" : "var(--gold)" }} />}
                style={{
                  ...styles.statusTag,
                  background: wsReady ? "var(--green-tint)" : "var(--gold-tint)",
                  borderColor: wsReady ? "var(--green-line)" : "var(--gold-line)",
                  color: wsReady ? "var(--green)" : "var(--gold)",
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
                  <span style={{ fontSize: 32 }}>⚖️</span>
                </div>
                <div style={styles.welcomeTitle}>Good day, {user.name.split(" ")[0]}.</div>
                <Text style={styles.welcomeText}>
                  Ask anything about the case — filings, dates, amounts, parties, timelines.
                  Every answer is verified against the source record.
                </Text>
                <div style={styles.suggestGrid}>
                  {SUGGESTED.map(s => (
                    <button
                      key={s}
                      className="suggestion-btn"
                      style={styles.suggestion}
                      onClick={() => handleSend(s)}
                    >
                      <span style={styles.suggestionArrow} className="suggestion-arrow">→</span>
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {showSessionLoading && (
              <div style={styles.loadingState}>
                <div className="skel-line" style={{ width: "62%", margin: "0 auto 10px" }} />
                <div className="skel-line" style={{ width: "82%", margin: "0 auto 10px" }} />
                <div className="skel-line" style={{ width: "48%", margin: "0 auto" }} />
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
                    className="send-btn"
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
  layout: { display: "flex", height: "100vh", overflow: "hidden", background: "var(--paper)" },
  main: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", background: "var(--paper)" },
  topbar: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "16px 36px", background: "rgba(248,245,238,0.78)",
    borderBottom: "1px solid var(--hair)", flexShrink: 0,
    backdropFilter: "saturate(180%) blur(14px)",
    WebkitBackdropFilter: "saturate(180%) blur(14px)",
  },
  topbarLeft: { display: "flex", alignItems: "baseline", gap: 14 },
  topbarNav: { display: "flex", alignItems: "center", gap: 4, marginLeft: 6 },
  navLink: {
    padding: "4px 12px", borderRadius: 6, fontSize: 13, fontWeight: 600,
    textDecoration: "none", color: "#234a52", background: "rgba(35,74,82,0.07)",
    border: "1px solid rgba(35,74,82,0.15)", whiteSpace: "nowrap",
  },
  topbarTitle: { fontWeight: 600, fontSize: 15.5, color: "var(--ink)", letterSpacing: "-0.005em" },
  topbarSub: {
    fontSize: 10, color: "var(--muted-2)", textTransform: "uppercase", letterSpacing: "0.16em", fontWeight: 600,
    paddingLeft: 14, borderLeft: "1px solid var(--hair-2)",
  },
  topbarRight: { display: "flex", alignItems: "center", gap: 8 },
  statusDot: { display: "inline-block", width: 6, height: 6, borderRadius: "50%", marginRight: 6 },
  statusTag: { fontSize: 11, borderRadius: "var(--pill)", display: "inline-flex", alignItems: "center", fontWeight: 500, padding: "2px 10px", border: "1px solid" },
  modelTag: { fontSize: 11, borderRadius: "var(--pill)", background: "var(--brand-soft)", borderColor: "var(--brand-mist)", color: "var(--brand)", fontWeight: 500, padding: "2px 10px" },
  voyageTag: { fontSize: 11, borderRadius: "var(--pill)", background: "var(--paper-2)", borderColor: "var(--hair-2)", color: "var(--muted)", fontWeight: 500, padding: "2px 10px" },
  messages: { flex: 1, overflowY: "auto", padding: "32px 0 12px" },
  loadingState: {
    maxWidth: 880,
    margin: "0 auto",
    padding: "60px 36px",
    width: "100%",
  },
  welcome: {
    display: "flex", flexDirection: "column", alignItems: "center",
    padding: "72px 24px 32px", maxWidth: 680, margin: "0 auto", width: "100%", textAlign: "center",
  },
  welcomeIconWrap: {
    width: 64, height: 64, borderRadius: "var(--r-lg)",
    background: "var(--surface)",
    border: "1px solid var(--hair)",
    display: "flex", alignItems: "center", justifyContent: "center",
    marginBottom: 28, boxShadow: "var(--sh-sm)",
  },
  welcomeTitle: { fontSize: "clamp(28px, 3.6vw, 38px)", fontWeight: 500, color: "var(--ink)", marginBottom: 16, letterSpacing: "-0.025em", lineHeight: 1.15 },
  welcomeText: { color: "var(--muted)", fontSize: 15, lineHeight: 1.65, marginBottom: 40, maxWidth: 460 },
  suggestGrid: { display: "flex", flexDirection: "column", gap: 8, width: "100%", maxWidth: 540 },
  suggestion: {
    background: "var(--surface)", border: "1px solid var(--hair)", borderRadius: "var(--r-md)",
    padding: "14px 18px", color: "var(--t2)", fontSize: 13.5, textAlign: "left",
    cursor: "pointer", display: "flex", alignItems: "center", gap: 12,
    fontFamily: "Inter, sans-serif", fontWeight: 450,
  },
  suggestionArrow: { fontSize: 14, color: "var(--muted-2)", flexShrink: 0, transition: "transform var(--fast), color var(--fast)" },
  aiRow: {
    display: "flex", alignItems: "flex-start", gap: 14,
    padding: "14px 36px", maxWidth: 880, margin: "0 auto", width: "100%",
  },
  aiAvatar: {
    fontSize: 16, flexShrink: 0, lineHeight: 1,
    width: 32, height: 32, borderRadius: "var(--r-sm)",
    background: "var(--surface)",
    border: "1px solid var(--hair)",
    display: "flex", alignItems: "center", justifyContent: "center",
    marginTop: 4,
  },
  aiBubble: {
    flex: 1, background: "transparent", border: "none",
    borderRadius: 0, padding: "4px 0 0",
    minWidth: 0,
  },
  timelineTag: {
    marginBottom: 12, background: "var(--paper-2)",
    borderColor: "var(--hair-2)", color: "var(--muted)",
    borderRadius: "var(--pill)", fontSize: 10.5, fontWeight: 500,
    padding: "0 10px",
  },
  userRow: {
    display: "flex", alignItems: "flex-start", justifyContent: "flex-end",
    gap: 12, padding: "14px 36px", maxWidth: 880, margin: "0 auto", width: "100%",
  },
  userBubble: {
    background: "var(--user-bubble)",
    border: "1px solid var(--user-bubble-border)",
    borderRadius: "var(--r-md)",
    padding: "11px 16px",
    maxWidth: "70%",
  },
  userText: { fontSize: 14.5, color: "var(--ink)", lineHeight: 1.6, fontWeight: 450 },
  userAvatar: {
    width: 32, height: 32, borderRadius: "var(--r-sm)",
    background: "var(--surface)", border: "1px solid var(--hair)",
    display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0, marginTop: 4,
  },
  dots: { display: "flex", gap: 5, alignItems: "center", padding: "4px 0" },
  dot: { width: 6, height: 6, borderRadius: "50%", background: "var(--brand)", display: "inline-block", opacity: 0.45 },
  inputArea: { padding: "12px 36px 24px", flexShrink: 0, background: "transparent" },
  inputCard: {
    background: "var(--surface)", border: "1px solid var(--hair-2)",
    borderRadius: "var(--r-md)", padding: "13px 16px 11px",
    boxShadow: "var(--sh-sm)",
    maxWidth: 820, margin: "0 auto",
    transition: "border-color var(--med), box-shadow var(--med)",
  },
  textarea: {
    fontSize: 15, color: "var(--ink)", background: "transparent",
    resize: "none", lineHeight: 1.6, padding: "4px 6px",
  },
  inputFooter: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    marginTop: 9, paddingTop: 10, borderTop: "1px solid var(--hair)",
  },
  inputHint: { fontSize: 11, color: "var(--muted-2)" },
  sendBtn: {
    background: "var(--brand)",
    border: "none",
    boxShadow: "var(--sh-sm)",
  },
};
