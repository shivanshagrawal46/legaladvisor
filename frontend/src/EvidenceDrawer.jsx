import { useMemo, useState, useEffect } from "react";
import { Drawer, Tag, Typography, Empty, Tooltip, Segmented } from "antd";
import {
  PaperClipOutlined,
  MailOutlined,
  CalendarOutlined,
  UserOutlined,
  CheckCircleFilled,
  ExclamationCircleFilled,
  FileTextOutlined,
  CopyOutlined,
} from "@ant-design/icons";
import { useEvidence } from "./EvidenceContext";

const { Text, Paragraph } = Typography;

/**
 * EvidenceDrawer
 *
 * Right-side slide-in drawer that shows source-level evidence on demand.
 * Drives off EvidenceContext — the drawer is mounted once per assistant
 * message bubble, and opens whenever a citation chip / source card /
 * verification-banner button fires `openEvidence(idx, factId?)`.
 *
 * Layout:
 *   ┌──────────────────────────────────────────────┐
 *   │  [#3] Settlement Agreement.pdf · 2023-07-18  │   ← header
 *   │  [VERIFIED 3/3]                              │
 *   ├──────────────────────────────────────────────┤
 *   │  CLAIMS THIS SOURCE SUPPORTS                 │
 *   │  ┌──────────────────────────────────────────┐│
 *   │  │ ✓ Settlement amount is $450,000          ││
 *   │  │   "the total settlement amount of …"      ││
 *   │  └──────────────────────────────────────────┘│
 *   │  …                                            │
 *   ├──────────────────────────────────────────────┤
 *   │  FULL SOURCE TEXT                             │
 *   │  (chunk body, with matched spans highlighted) │
 *   └──────────────────────────────────────────────┘
 */

function verdictBadge(verdict) {
  if (verdict === "VERIFIED") {
    return {
      icon: <CheckCircleFilled />,
      label: "Verified",
      bg: "#f0f7eb",
      border: "#c8e2b3",
      color: "#3c7e1a",
    };
  }
  if (verdict === "CITATION_INVALID") {
    return {
      icon: <ExclamationCircleFilled />,
      label: "Invalid citation",
      bg: "#fdecec",
      border: "#f5c0c0",
      color: "#b03a3a",
    };
  }
  return {
    icon: <ExclamationCircleFilled />,
    label: "Unverified — review",
    bg: "#fdf5e8",
    border: "#f5dfa0",
    color: "#b07a1a",
  };
}

/**
 * Build a render-ready array of {text, highlight, isQuote} segments
 * for the chunk body, with the matched_span of each verified fact
 * highlighted in-place. We do a simple case-insensitive substring scan
 * (matched_span was extracted from THIS chunk by the verifier, so the
 * substring will be present unless OCR normalisation made it differ —
 * in that case we fall back to highlighting nothing, which is fine).
 */
function buildHighlightedBody(body, verdicts) {
  if (!body) return [{ text: "", highlight: false }];
  if (!verdicts || verdicts.length === 0) {
    return [{ text: body, highlight: false }];
  }

  // Collect distinct, non-overlapping highlight ranges. We use
  // matched_span when available; fall back to verbatim_quote.
  const ranges = [];
  for (const v of verdicts) {
    // Skip CITATION_INVALID (nothing to highlight in this chunk).
    if (v.verdict === "CITATION_INVALID") continue;
    const candidates = [v.matched_span, v.verbatim_quote].filter(Boolean);
    let placed = false;
    for (const cand of candidates) {
      // First try exact substring match on the body.
      const needle = cand.trim();
      if (needle.length < 8) continue;
      const lcBody = body.toLowerCase();
      const idx = lcBody.indexOf(needle.toLowerCase());
      if (idx >= 0) {
        ranges.push({
          start: idx,
          end: idx + needle.length,
          verdict: v.verdict,
          factId: v.fact_id,
        });
        placed = true;
        break;
      }
      // Fall back: try the first 60-char chunk of the candidate
      // (matched_span returned by the verifier sometimes has slight
      // edges that don't match the raw body).
      const slice = needle.slice(0, 60);
      const idx2 = lcBody.indexOf(slice.toLowerCase());
      if (idx2 >= 0) {
        ranges.push({
          start: idx2,
          end: idx2 + slice.length,
          verdict: v.verdict,
          factId: v.fact_id,
        });
        placed = true;
        break;
      }
    }
    // If nothing matches the body, we silently don't highlight — the
    // verbatim is still shown in the claim card above.
    void placed;
  }

  if (ranges.length === 0) {
    return [{ text: body, highlight: false }];
  }

  // Sort + merge overlapping ranges.
  ranges.sort((a, b) => a.start - b.start);
  const merged = [];
  for (const r of ranges) {
    const last = merged[merged.length - 1];
    if (last && r.start <= last.end) {
      last.end = Math.max(last.end, r.end);
      // If any merged range is UNVERIFIED, downgrade to UNVERIFIED for the
      // merged highlight.
      if (r.verdict !== "VERIFIED") last.verdict = r.verdict;
    } else {
      merged.push({ ...r });
    }
  }

  const segs = [];
  let cursor = 0;
  for (const r of merged) {
    if (r.start > cursor) {
      segs.push({ text: body.slice(cursor, r.start), highlight: false });
    }
    segs.push({
      text: body.slice(r.start, r.end),
      highlight: true,
      verdict: r.verdict,
      factId: r.factId,
    });
    cursor = r.end;
  }
  if (cursor < body.length) {
    segs.push({ text: body.slice(cursor), highlight: false });
  }
  return segs;
}

function copyText(text) {
  try {
    navigator.clipboard?.writeText?.(text);
  } catch (_) {}
}

export default function EvidenceDrawer() {
  const {
    open,
    activeIndex,
    activeFactId,
    closeEvidence,
    getSource,
    getVerdictsFor,
    verification,
  } = useEvidence();

  // Tabs for browsing other sources without closing/reopening.
  const [tabIndex, setTabIndex] = useState(activeIndex);
  useEffect(() => {
    if (activeIndex != null) setTabIndex(activeIndex);
  }, [activeIndex, open]);

  const idx = tabIndex ?? activeIndex;
  const src = idx != null ? getSource(idx) : null;
  const verdicts = idx != null ? getVerdictsFor(idx) : [];

  // Build tab options from all sources that exist — but show a badge
  // marking which ones have unverified claims so the lawyer can jump
  // straight there.
  const tabOptions = useMemo(() => {
    return [];
  }, []);
  void tabOptions;

  const segments = useMemo(
    () => buildHighlightedBody(src?.body || "", verdicts),
    [src?.body, verdicts]
  );

  const titleNode = src ? (
    <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
      <Tag
        icon={src.type === "attachment" ? <PaperClipOutlined /> : <MailOutlined />}
        style={{
          background: src.type === "attachment" ? "#eef0fb" : "#edf8f2",
          color: src.type === "attachment" ? "#6574c4" : "#3a8c5c",
          borderColor: src.type === "attachment" ? "#d4d9f0" : "#b7e4c7",
          margin: 0,
          flexShrink: 0,
        }}
      >
        {src.type === "attachment" ? "Attachment" : "Email"}
      </Tag>
      <Text strong style={{ fontSize: 15, color: "#1a1d2e", flexShrink: 0 }}>
        [#{src.index}]
      </Text>
      <Text style={{
        fontSize: 14,
        color: "#3d4566",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        minWidth: 0,
      }}>
        {src.title}
      </Text>
    </div>
  ) : (
    <Text>Evidence</Text>
  );

  // Build the segmented control across all sources that have any
  // verified claim, plus a separator marker for the active one. To keep
  // it manageable we cap the visible tabs at ~12.
  const sourceTabs = useMemo(() => {
    const seen = new Set();
    const out = [];
    if (verification?.verdicts) {
      for (const v of verification.verdicts) {
        const i = v.source_chunk_id;
        if (typeof i !== "number" || seen.has(i)) continue;
        seen.add(i);
        const vs = verdicts && i === idx
          ? verdicts
          : (verification.verdicts || []).filter(x => x.source_chunk_id === i);
        const unver = vs.some(x => x.verdict !== "VERIFIED");
        out.push({
          label: (
            <span>
              #{i}{unver ? " ⚠" : ""}
            </span>
          ),
          value: i,
        });
      }
    }
    return out.slice(0, 12);
  }, [verification, idx, verdicts]);

  return (
    <Drawer
      open={open}
      onClose={closeEvidence}
      title={titleNode}
      width={Math.min(640, Math.round(window.innerWidth * 0.6))}
      placement="right"
      destroyOnClose
      maskClosable
      styles={{
        body: { padding: "16px 22px 24px", background: "#fbfbfd" },
        header: { borderBottom: "1px solid #ebedf5", padding: "12px 20px" },
      }}
    >
      {!src ? (
        <Empty description="No source attached to that citation" />
      ) : (
        <>
          {/* Quick metadata row */}
          <div style={styles.metaRow}>
            {src.date && (
              <span style={styles.metaItem}>
                <CalendarOutlined style={{ marginRight: 4 }} />
                {src.date}
              </span>
            )}
            {src.from_email && (
              <span style={styles.metaItem}>
                <UserOutlined style={{ marginRight: 4 }} />
                {src.from_email}
              </span>
            )}
            {src.page && (
              <span style={styles.metaItem}>
                <FileTextOutlined style={{ marginRight: 4 }} />
                {src.page}
              </span>
            )}
            {src.rerank_score != null && (
              <span style={{ ...styles.metaItem, color: "#b0b6cc" }}>
                rerank {src.rerank_score}
              </span>
            )}
          </div>

          {/* Source picker — only when more than one source has facts */}
          {sourceTabs.length > 1 && (
            <div style={{ marginTop: 12, marginBottom: 14 }}>
              <Text style={styles.sectionLabel}>JUMP TO SOURCE</Text>
              <div style={{ marginTop: 6 }}>
                <Segmented
                  size="small"
                  options={sourceTabs}
                  value={tabIndex}
                  onChange={setTabIndex}
                />
              </div>
            </div>
          )}

          {/* Claims this source supports */}
          {verdicts.length > 0 && (
            <div style={styles.section}>
              <Text style={styles.sectionLabel}>
                {verdicts.length === 1
                  ? "1 CLAIM CITED FROM THIS SOURCE"
                  : `${verdicts.length} CLAIMS CITED FROM THIS SOURCE`}
              </Text>
              <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
                {verdicts.map(v => {
                  const badge = verdictBadge(v.verdict);
                  const isActiveFact = activeFactId && v.fact_id === activeFactId;
                  return (
                    <div
                      key={v.fact_id}
                      style={{
                        ...styles.claimCard,
                        borderColor: isActiveFact ? "#6574c4" : "#ebedf5",
                        boxShadow: isActiveFact ? "0 2px 8px rgba(101,116,196,0.18)" : "none",
                      }}
                    >
                      <div style={styles.claimHeader}>
                        <Tag
                          icon={badge.icon}
                          style={{
                            background: badge.bg,
                            color: badge.color,
                            borderColor: badge.border,
                            margin: 0,
                            fontWeight: 600,
                          }}
                        >
                          {badge.label}
                        </Tag>
                        {v.score != null && v.verdict === "VERIFIED" && (
                          <Text style={{ fontSize: 11, color: "#b0b6cc", marginLeft: "auto" }}>
                            confidence {Math.round(v.score)}%
                          </Text>
                        )}
                      </div>
                      <Paragraph style={styles.claimText}>
                        {v.claim || "(no claim text)"}
                      </Paragraph>
                      {v.verbatim_quote && (
                        <div style={{
                          ...styles.verbatim,
                          borderLeftColor: v.verdict === "VERIFIED" ? "#7fc04d" : "#e8b14a",
                        }}>
                          <span style={{ flex: 1 }}>"{v.verbatim_quote}"</span>
                          <Tooltip title="Copy quote">
                            <button
                              className="icon-btn"
                              onClick={() => copyText(v.verbatim_quote)}
                            >
                              <CopyOutlined />
                            </button>
                          </Tooltip>
                        </div>
                      )}
                      {v.verdict !== "VERIFIED" && v.reason && (
                        <div style={styles.reason}>
                          {v.reason}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Full source text */}
          <div style={styles.section}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <Text style={styles.sectionLabel}>FULL SOURCE TEXT</Text>
              <Tooltip title="Copy source text">
                <button
                  className="icon-btn"
                  onClick={() => copyText(src.body || "")}
                  style={{ fontSize: 12, color: "#8892b0" }}
                >
                  <CopyOutlined /> copy
                </button>
              </Tooltip>
            </div>
            <div style={styles.bodyBox}>
              {segments.map((s, i) =>
                s.highlight ? (
                  <span
                    key={i}
                    style={{
                      background: s.verdict === "VERIFIED" ? "#e9f5d8" : "#fdeec3",
                      borderBottom: `2px solid ${s.verdict === "VERIFIED" ? "#7fc04d" : "#e8b14a"}`,
                      padding: "0 1px",
                    }}
                  >
                    {s.text}
                  </span>
                ) : (
                  <span key={i}>{s.text}</span>
                )
              )}
              {src.body_truncated && (
                <div style={styles.truncationNote}>
                  Source text was truncated to 8,000 characters for display.
                  Full chunk is preserved in the database.
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </Drawer>
  );
}

const styles = {
  metaRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: "4px 14px",
    paddingBottom: 4,
  },
  metaItem: {
    fontSize: 12,
    color: "#6b7498",
    display: "inline-flex",
    alignItems: "center",
  },
  section: {
    marginTop: 18,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: 700,
    letterSpacing: 0.6,
    color: "#8892b0",
  },
  claimCard: {
    background: "#ffffff",
    border: "1px solid #ebedf5",
    borderRadius: 10,
    padding: "12px 14px",
    transition: "border-color 0.15s, box-shadow 0.15s",
  },
  claimHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8,
  },
  claimText: {
    margin: 0,
    fontSize: 13,
    color: "#1a1d2e",
    lineHeight: 1.6,
  },
  verbatim: {
    marginTop: 8,
    padding: "8px 10px",
    background: "#fbfbfd",
    borderLeft: "3px solid #7fc04d",
    borderRadius: "0 6px 6px 0",
    fontSize: 12,
    color: "#3d4566",
    fontStyle: "italic",
    lineHeight: 1.55,
    display: "flex",
    alignItems: "flex-start",
    gap: 6,
  },
  reason: {
    marginTop: 8,
    padding: "6px 10px",
    fontSize: 12,
    color: "#b07a1a",
    background: "#fdf8ee",
    borderRadius: 6,
  },
  bodyBox: {
    marginTop: 8,
    padding: "12px 14px",
    background: "#ffffff",
    border: "1px solid #ebedf5",
    borderRadius: 10,
    fontSize: 13,
    lineHeight: 1.7,
    color: "#3d4566",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    fontFamily: "'Fira Code', 'SF Mono', monospace",
    maxHeight: "calc(100vh - 380px)",
    overflowY: "auto",
  },
  truncationNote: {
    marginTop: 10,
    padding: "8px 10px",
    fontSize: 11,
    color: "#b07a1a",
    background: "#fdf8ee",
    borderRadius: 6,
  },
};
