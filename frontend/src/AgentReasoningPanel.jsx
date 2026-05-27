import { useState, useMemo, useEffect } from "react";
import { Collapse, Tag, Tooltip, Progress, Typography, Button } from "antd";
import {
  RobotOutlined,
  SearchOutlined,
  FileTextOutlined,
  ApartmentOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
  CheckCircleFilled,
  ExclamationCircleFilled,
  LoadingOutlined,
  StopOutlined,
  CaretRightOutlined,
} from "@ant-design/icons";

const { Text } = Typography;

/**
 * AgentReasoningPanel
 *
 * Renders the Sprint-4 agent's investigative trace above the assistant
 * answer. Components:
 *
 *   ┌─────────────────────────────────────────────────────────┐
 *   │  [Agent] Investigating · 3/8 calls · 12s · [Stop]      │   ← header
 *   │  ▾ Reasoning trace                                       │   ← collapsed
 *   └─────────────────────────────────────────────────────────┘
 *
 * When expanded, an AntD Steps-like list shows each tool call with
 * the input + a one-line summary. Live spinner on the current step.
 * Each step is expandable for the full tool_input / new chunks.
 */

const TOOL_ICON = {
  "(seed) search":         <SearchOutlined />,
  "search":                <SearchOutlined />,
  "search_by_filename":    <FileTextOutlined />,
  "search_timeframe":      <ClockCircleOutlined />,
  "fetch_full_document":   <FileTextOutlined />,
  "find_quote":            <SearchOutlined />,
  "find_latest_version":   <ApartmentOutlined />,
  "compare_versions":      <ApartmentOutlined />,
  "verify_claim":          <SafetyCertificateOutlined />,
  "submit_final_answer":   <CheckCircleFilled />,
};

const TOOL_LABEL = {
  "(seed) search":       "Seed retrieval",
  "search":              "Search corpus",
  "search_by_filename":  "Filename lookup",
  "search_timeframe":    "Date-range search",
  "fetch_full_document": "Fetch full document",
  "find_quote":          "Find verbatim quote",
  "find_latest_version": "Find document versions",
  "compare_versions":    "Compare versions",
  "verify_claim":        "Verify claim",
  "submit_final_answer": "Submit final answer",
};


function StepIcon({ step, isCurrent }) {
  if (step.error) {
    return <ExclamationCircleFilled style={{ color: "#b03a3a" }} />;
  }
  if (step.type === "submit_final_answer" || step.tool_name === "submit_final_answer") {
    return <CheckCircleFilled style={{ color: "#3c7e1a" }} />;
  }
  if (isCurrent) {
    return <LoadingOutlined style={{ color: "#6574c4" }} spin />;
  }
  return <span style={{ color: "#6574c4" }}>{TOOL_ICON[step.tool_name] || <RobotOutlined />}</span>;
}


function ToolInputBlock({ input }) {
  if (!input || Object.keys(input).length === 0) {
    return <Text type="secondary" style={{ fontSize: 11 }}>(no arguments)</Text>;
  }
  return (
    <div style={styles.toolInput}>
      {Object.entries(input).map(([k, v]) => (
        <div key={k} style={styles.toolInputRow}>
          <span style={styles.toolInputKey}>{k}:</span>
          <span style={styles.toolInputVal}>
            {typeof v === "string"
              ? (v.length > 200 ? v.slice(0, 200) + "…" : v)
              : JSON.stringify(v)}
          </span>
        </div>
      ))}
    </div>
  );
}


function StepRow({ step, isCurrent, isLast }) {
  const [expanded, setExpanded] = useState(false);
  const toolName = step.tool_name || "(planning)";
  const label = TOOL_LABEL[toolName] || toolName;
  const newCount = (step.new_chunk_indices || []).length;

  return (
    <div style={styles.stepRow}>
      <div style={styles.stepGutter}>
        <div style={{ ...styles.stepDot, background: step.error ? "#fdecec" : (isCurrent ? "#eef0fb" : "#f5f9f0") }}>
          <StepIcon step={step} isCurrent={isCurrent} />
        </div>
        {!isLast && <div style={styles.stepConnector} />}
      </div>
      <div style={styles.stepBody}>
        <button
          type="button"
          onClick={() => setExpanded(e => !e)}
          style={styles.stepHeader}
          className="agent-step-header"
        >
          <span style={styles.stepNum}>#{step.step_num}</span>
          <span style={styles.stepLabel}>{label}</span>
          {newCount > 0 && (
            <Tag style={styles.newChunksTag}>+{newCount} chunk{newCount > 1 ? "s" : ""}</Tag>
          )}
          {step.elapsed_ms != null && (
            <span style={styles.elapsedTag}>{(step.elapsed_ms / 1000).toFixed(1)}s</span>
          )}
          <CaretRightOutlined
            style={{
              ...styles.caret,
              transform: expanded ? "rotate(90deg)" : "rotate(0deg)",
            }}
          />
        </button>
        <div style={styles.stepSummary}>
          {step.summary || "(no summary)"}
        </div>
        {expanded && (
          <div style={styles.stepDetails}>
            <Text style={styles.detailsLabel}>Input</Text>
            <ToolInputBlock input={step.tool_input} />
            {step.new_chunk_indices && step.new_chunk_indices.length > 0 && (
              <>
                <Text style={styles.detailsLabel}>New chunks added</Text>
                <div style={styles.chunkRefs}>
                  {step.new_chunk_indices.slice(0, 20).map(i => (
                    <span key={i} style={styles.chunkRef}>[#{i}]</span>
                  ))}
                  {step.new_chunk_indices.length > 20 && (
                    <span style={{ color: "#8892b0", fontSize: 11 }}>
                      +{step.new_chunk_indices.length - 20} more
                    </span>
                  )}
                </div>
              </>
            )}
            {step.error && (
              <>
                <Text style={styles.detailsLabel}>Error</Text>
                <div style={styles.errorBox}>{step.error}</div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}


export default function AgentReasoningPanel({
  agent,                  // { plan, steps[], done, trace } — see Chat.jsx
  isStreaming,
  onInterrupt,
}) {
  if (!agent) return null;

  const steps = agent.steps || [];
  const plan = agent.plan;
  const done = agent.done;
  const trace = agent.trace;

  // When live: still streaming — find the current step.
  const isLive = isStreaming && !done && !trace;
  const currentStepIdx = isLive ? steps.length - 1 : -1;

  // Compose status text + cost
  const budget = (trace?.budget) || (plan?.budget) || null;
  const toolCallsUsed = done?.tool_calls
    ?? trace?.budget?.tool_calls_used
    ?? steps.filter(s => s.type === "tool_call").length;
  const maxCalls = budget?.max_tool_calls || 8;

  // Live wall-clock timer for the running agent (ticks every 1s). The
  // backend only emits cumulative `elapsed_s` AFTER a step completes,
  // so a slow Opus call between steps would otherwise leave the timer
  // frozen for minutes. We anchor on the first time we see the panel
  // and tick locally until the agent reports its own elapsed.
  const [liveElapsedMs, setLiveElapsedMs] = useState(0);
  const [liveStartedAt] = useState(() => Date.now());
  useEffect(() => {
    if (!isStreaming || done) return;
    const id = setInterval(() => {
      setLiveElapsedMs(Date.now() - liveStartedAt);
    }, 1000);
    return () => clearInterval(id);
  }, [isStreaming, done, liveStartedAt]);

  // Order of preference: final done payload → backend cumulative → local
  // live tick. Each layer is NaN-guarded so we never render `NaNs`.
  const _backendElapsedMs =
    typeof trace?.budget?.elapsed_s === "number"
      ? trace.budget.elapsed_s * 1000
      : null;
  const elapsedMs =
    (typeof done?.elapsed_ms === "number" ? done.elapsed_ms : null)
    ?? _backendElapsedMs
    ?? (isStreaming ? liveElapsedMs : null);

  const headerColor = done?.outcome === "VERIFIED_FIRST_PASS" ? "#3c7e1a"
                    : done?.outcome === "VERIFIED_AFTER_RETRY" ? "#3a6cb0"
                    : done?.outcome === "KEPT_ORIGINAL" ? "#b07a1a"
                    : done?.outcome === "FALLBACK" ? "#b03a3a"
                    : "#6574c4";

  const statusText = useMemo(() => {
    if (isLive) {
      const currentStep = steps[steps.length - 1];
      const currentLabel = currentStep ? (TOOL_LABEL[currentStep.tool_name] || currentStep.tool_name) : "Planning…";
      return `Agent investigating · ${currentLabel}`;
    }
    if (done?.outcome) {
      const labels = {
        VERIFIED_FIRST_PASS:  "Investigation complete · all facts verified",
        VERIFIED_AFTER_RETRY: "Investigation complete · verified after retry",
        KEPT_ORIGINAL:        "Investigation complete · some facts unverified",
        FALLBACK:             "Investigation closed under budget pressure",
        NO_FACTS:             "Investigation complete · no corpus facts cited",
      };
      return labels[done.outcome] || "Investigation complete";
    }
    return "Agent investigating…";
  }, [isLive, steps, done]);

  const pct = Math.min(100, Math.round((toolCallsUsed / maxCalls) * 100));

  // Default collapsed when done, expanded while live so the user can
  // watch in real time.
  const defaultOpenKeys = isLive ? ["trace"] : [];

  return (
    <div style={styles.wrap}>
      <div style={{ ...styles.header, borderLeft: `3px solid ${headerColor}` }}>
        <div style={styles.headerLeft}>
          {isLive ? (
            <LoadingOutlined style={{ color: headerColor, fontSize: 14 }} spin />
          ) : (
            <RobotOutlined style={{ color: headerColor, fontSize: 14 }} />
          )}
          <Text style={{ ...styles.headerTitle, color: headerColor }}>{statusText}</Text>
        </div>

        <div style={styles.headerRight}>
          <Tooltip title={`${toolCallsUsed} of ${maxCalls} tool calls used`}>
            <div style={styles.costMeter}>
              <Progress
                percent={pct}
                showInfo={false}
                size="small"
                strokeColor={pct >= 90 ? "#b07a1a" : "#6574c4"}
                trailColor="#ebedf5"
                style={{ width: 60, lineHeight: 1 }}
              />
              <Text style={styles.meterLabel}>{toolCallsUsed}/{maxCalls}</Text>
            </div>
          </Tooltip>
          {elapsedMs != null && Number.isFinite(elapsedMs) && (
            <Text style={styles.elapsedText}>
              <ClockCircleOutlined style={{ marginRight: 3 }} />
              {(elapsedMs / 1000).toFixed(1)}s
            </Text>
          )}
          {isLive && onInterrupt && (
            <Tooltip title="Stop the agent and finalise with what it has">
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                onClick={onInterrupt}
                style={styles.stopBtn}
              >
                Stop
              </Button>
            </Tooltip>
          )}
        </div>
      </div>

      {steps.length > 0 && (
        <Collapse
          ghost
          size="small"
          defaultActiveKey={defaultOpenKeys}
          items={[
            {
              key: "trace",
              label: (
                <Text style={styles.collapseLabel}>
                  Reasoning trace · {steps.length} step{steps.length === 1 ? "" : "s"}
                </Text>
              ),
              children: (
                <div style={styles.stepList}>
                  {steps.map((s, i) => (
                    <StepRow
                      key={`${s.step_num}-${i}`}
                      step={s}
                      isCurrent={i === currentStepIdx}
                      isLast={i === steps.length - 1}
                    />
                  ))}
                </div>
              ),
            },
          ]}
          style={styles.collapse}
        />
      )}
    </div>
  );
}

const styles = {
  wrap: {
    marginBottom: 12,
    background: "#fafbfe",
    border: "1px solid #ebedf5",
    borderRadius: 8,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "8px 12px",
    background: "#ffffff",
    borderBottom: "1px solid #ebedf5",
    gap: 12,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    minWidth: 0,
    flex: 1,
  },
  headerTitle: {
    fontSize: 12,
    fontWeight: 600,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  headerRight: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    flexShrink: 0,
  },
  costMeter: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  meterLabel: {
    fontSize: 11,
    color: "#8892b0",
    fontFamily: "monospace",
    fontWeight: 600,
  },
  elapsedText: {
    fontSize: 11,
    color: "#8892b0",
    display: "inline-flex",
    alignItems: "center",
  },
  stopBtn: {
    fontSize: 11,
    height: 22,
    padding: "0 8px",
  },
  collapseLabel: {
    fontSize: 11,
    color: "#8892b0",
    fontWeight: 500,
  },
  collapse: {
    background: "transparent",
  },
  stepList: {
    paddingTop: 4,
    paddingLeft: 4,
  },
  stepRow: {
    display: "flex",
    gap: 10,
    paddingBottom: 8,
  },
  stepGutter: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    flexShrink: 0,
    width: 22,
  },
  stepDot: {
    width: 22,
    height: 22,
    borderRadius: "50%",
    border: "1px solid #ebedf5",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 11,
    flexShrink: 0,
  },
  stepConnector: {
    width: 1,
    flex: 1,
    background: "#e6e9f2",
    minHeight: 16,
    marginTop: 2,
  },
  stepBody: {
    flex: 1,
    minWidth: 0,
    paddingBottom: 4,
  },
  stepHeader: {
    width: "100%",
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "transparent",
    border: "none",
    cursor: "pointer",
    padding: "2px 0",
    fontFamily: "Inter, sans-serif",
    textAlign: "left",
  },
  stepNum: {
    fontSize: 10,
    color: "#b0b6cc",
    fontFamily: "monospace",
    fontWeight: 700,
    minWidth: 20,
  },
  stepLabel: {
    fontSize: 12,
    fontWeight: 600,
    color: "#1a1d2e",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  newChunksTag: {
    fontSize: 10,
    background: "#eef0fb",
    color: "#6574c4",
    borderColor: "#d4d9f0",
    borderRadius: 3,
    padding: "0 4px",
    height: 16,
    lineHeight: "14px",
    margin: 0,
  },
  elapsedTag: {
    fontSize: 10,
    color: "#b0b6cc",
    marginLeft: "auto",
  },
  caret: {
    fontSize: 10,
    color: "#b0b6cc",
    transition: "transform 0.15s",
  },
  stepSummary: {
    fontSize: 11,
    color: "#6b7498",
    paddingLeft: 28,
    paddingTop: 2,
    lineHeight: 1.55,
  },
  stepDetails: {
    marginTop: 8,
    marginLeft: 28,
    padding: "8px 10px",
    background: "#ffffff",
    border: "1px solid #ebedf5",
    borderRadius: 6,
  },
  detailsLabel: {
    fontSize: 10,
    fontWeight: 700,
    color: "#8892b0",
    letterSpacing: 0.5,
    display: "block",
    marginBottom: 4,
    marginTop: 6,
  },
  toolInput: {
    marginBottom: 4,
  },
  toolInputRow: {
    display: "flex",
    gap: 6,
    fontSize: 11,
    lineHeight: 1.5,
    fontFamily: "'Fira Code', monospace",
  },
  toolInputKey: {
    color: "#6574c4",
    flexShrink: 0,
  },
  toolInputVal: {
    color: "#3d4566",
    wordBreak: "break-word",
  },
  chunkRefs: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
  },
  chunkRef: {
    background: "#eef0fb",
    color: "#6574c4",
    borderRadius: 3,
    padding: "0 5px",
    fontSize: 10,
    fontFamily: "monospace",
    fontWeight: 600,
    lineHeight: "16px",
  },
  errorBox: {
    fontSize: 11,
    color: "#b03a3a",
    background: "#fdecec",
    border: "1px solid #f5c0c0",
    borderRadius: 4,
    padding: "6px 8px",
  },
};
