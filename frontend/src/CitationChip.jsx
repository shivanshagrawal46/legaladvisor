import { Tooltip } from "antd";
import { CheckCircleFilled, ExclamationCircleFilled, MinusCircleFilled } from "@ant-design/icons";
import { useEvidence } from "./EvidenceContext";

/**
 * CitationChip
 *
 * Replaces "[#N]" tokens inside the assistant's prose with a clickable
 * chip. Clicking opens the evidence drawer at source #N. Colour reflects
 * the Sprint-3-finish verifier verdict:
 *
 *   VERIFIED         → green  (quote confirmed in chunk)
 *   UNVERIFIED       → amber  (quote not found, lawyer should review)
 *   CITATION_INVALID → red    (citation #N doesn't exist — shouldn't happen)
 *   null  (no verifier data)  → neutral (legacy v1 answer / no verifier run)
 *
 * Hover tooltip previews the verbatim quote(s) and verdict reason.
 */

const STYLES = {
  VERIFIED: {
    bg: "var(--green-tint)",
    border: "var(--green-line)",
    color: "var(--green)",
    icon: <CheckCircleFilled style={{ fontSize: 9 }} />,
  },
  UNVERIFIED: {
    bg: "var(--gold-tint)",
    border: "var(--gold-line)",
    color: "var(--gold)",
    icon: <ExclamationCircleFilled style={{ fontSize: 9 }} />,
  },
  CITATION_INVALID: {
    bg: "var(--red-tint)",
    border: "var(--red-line)",
    color: "var(--red)",
    icon: <ExclamationCircleFilled style={{ fontSize: 9 }} />,
  },
  NEUTRAL: {
    bg: "var(--river-tint)",
    border: "var(--river-mist)",
    color: "var(--river)",
    icon: <MinusCircleFilled style={{ fontSize: 9, opacity: 0.55 }} />,
  },
};

function shortQuote(q, max = 110) {
  if (!q) return "";
  q = q.replace(/\s+/g, " ").trim();
  return q.length > max ? q.slice(0, max) + "…" : q;
}

export default function CitationChip({ index }) {
  const { openEvidence, getSource, getVerdictsFor, getOverallVerdictFor, verification } = useEvidence();
  const src = getSource(index);
  const verdicts = getVerdictsFor(index);
  // If no verification ran at all on this message, render neutral.
  const overall = verification ? (getOverallVerdictFor(index) || "NEUTRAL") : "NEUTRAL";
  const style = STYLES[overall] || STYLES.NEUTRAL;

  // Build tooltip content — single verdict reads one row, multiple stack.
  const tipBody = (
    <div style={{ maxWidth: 360, fontSize: 12, lineHeight: 1.55, color: "var(--ink)" }}>
      {src ? (
        <div style={{ marginBottom: verdicts.length ? 8 : 0, fontWeight: 600, color: "var(--ink)", display: "flex", alignItems: "baseline", gap: 6 }}>
          <span className="mono" style={{ color: "var(--brand)", fontSize: 11 }}>[#{index}]</span>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{src.title}</span>
          {src.date ? <span className="mono" style={{ marginLeft: "auto", color: "var(--muted-2)", fontWeight: 400, fontSize: 10.5, flexShrink: 0 }}>{src.date}</span> : null}
        </div>
      ) : (
        <div style={{ marginBottom: 4, fontWeight: 600, color: "var(--red)" }}>
          [#{index}] — source not found
        </div>
      )}
      {verdicts.length === 0 && src ? (
        <div style={{ color: "var(--muted)" }}>No verifier facts attributed to this source.</div>
      ) : null}
      {verdicts.slice(0, 3).map((v, i) => (
        <div key={v.fact_id || i} style={{
          marginTop: i === 0 ? 0 : 8,
          paddingTop: i === 0 ? 0 : 8,
          borderTop: i === 0 ? "none" : "1px solid var(--hair)",
        }}>
          <div style={{ color: "var(--t2)", marginBottom: 3 }}>
            {v.claim ? shortQuote(v.claim, 140) : "(no claim text)"}
          </div>
          {v.verbatim_quote && (
            <div style={{
              color: "var(--muted)",
              fontStyle: "italic",
              borderLeft: "2px solid " + (v.verdict === "VERIFIED" ? "var(--green)" : "var(--gold)"),
              paddingLeft: 8,
              fontSize: 11,
            }}>
              "{shortQuote(v.verbatim_quote)}"
            </div>
          )}
          {v.verdict !== "VERIFIED" && v.reason && (
            <div style={{ marginTop: 3, color: "var(--gold)", fontSize: 11 }}>
              ⚠ {v.reason}
            </div>
          )}
        </div>
      ))}
      {verdicts.length > 3 && (
        <div style={{ marginTop: 6, color: "var(--muted)", fontSize: 11 }}>
          …and {verdicts.length - 3} more — click to view all
        </div>
      )}
      <div style={{ marginTop: 8, color: "var(--muted)", fontSize: 10 }}>
        Click to open evidence panel →
      </div>
    </div>
  );

  return (
    <Tooltip
      title={tipBody}
      placement="top"
      mouseEnterDelay={0.25}
      color="#fdfbf6"
      overlayInnerStyle={{
        color: "var(--ink)",
        border: "1px solid var(--hair)",
        borderRadius: 8,
        padding: "11px 13px",
        boxShadow: "var(--sh-md)",
        fontSize: 12,
        lineHeight: 1.55,
        minHeight: 0,
      }}
    >
      <button
        type="button"
        onClick={() => openEvidence(index)}
        className="citation-chip"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 3,
          padding: "0 7px",
          height: 18,
          margin: "0 1px",
          background: style.bg,
          border: `1px solid ${style.border}`,
          borderRadius: "var(--pill)",
          color: style.color,
          fontSize: 10.5,
          fontWeight: 500,
          fontFamily: "'JetBrains Mono', monospace",
          cursor: "pointer",
          lineHeight: 1,
          verticalAlign: "baseline",
          whiteSpace: "nowrap",
          transition: "background var(--fast)",
        }}
      >
        {style.icon}
        <span>#{index}</span>
      </button>
    </Tooltip>
  );
}

/**
 * Helper used by ReactMarkdown's `components.text` slot.
 * Walks a text node, splits on /\[#(\d+)\]/g, and yields the
 * surrounding text + <CitationChip/> elements in order.
 *
 * We can't just attach `text` because remark-gfm splits already; we
 * intercept paragraph (`p`) and list-item (`li`) and let inline
 * processing handle the chips.
 */
export function renderWithCitations(children) {
  // children is a single string OR an array of strings/elements.
  const transformOne = (node, keyBase) => {
    if (typeof node !== "string") return node;
    const out = [];
    const re = /\[#(\d+)\]/g;
    let last = 0;
    let m;
    let i = 0;
    while ((m = re.exec(node)) !== null) {
      if (m.index > last) {
        out.push(node.slice(last, m.index));
      }
      out.push(<CitationChip key={`${keyBase}-c${i++}`} index={parseInt(m[1], 10)} />);
      last = m.index + m[0].length;
    }
    if (last < node.length) {
      out.push(node.slice(last));
    }
    return out.length === 0 ? node : out;
  };

  if (Array.isArray(children)) {
    return children.map((c, i) => transformOne(c, `t${i}`));
  }
  return transformOne(children, "t0");
}
