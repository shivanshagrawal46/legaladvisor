import { Collapse, Tag, Tooltip, Typography } from "antd";
import {
  PaperClipOutlined,
  MailOutlined,
  CalendarOutlined,
  UserOutlined,
  CheckCircleFilled,
  ExclamationCircleFilled,
} from "@ant-design/icons";
import { useEvidence } from "./EvidenceContext";

const { Text } = Typography;

/**
 * Sources
 *
 * Source cards rendered under each assistant message. With Sprint-3-
 * finish, each card optionally carries a `verified_facts[]` payload
 * that tells us which claims this source supports and whether they
 * passed verification. We surface that as a colour-coded badge and
 * make the entire card clickable to open the EvidenceDrawer.
 */

function badgeForFacts(facts) {
  if (!facts || facts.length === 0) return null;
  const total = facts.length;
  const verified = facts.filter(f => f.verdict === "VERIFIED").length;
  const unver = total - verified;
  if (unver === 0) {
    return {
      icon: <CheckCircleFilled />,
      label: total === 1 ? "Supports 1 verified claim" : `Supports ${total} verified claims`,
      bg: "var(--green-tint)",
      border: "var(--green-line)",
      color: "var(--green)",
    };
  }
  return {
    icon: <ExclamationCircleFilled />,
    label: `${verified}/${total} claims verified · ${unver} to review`,
    bg: "var(--gold-tint)",
    border: "var(--gold-line)",
    color: "var(--gold)",
  };
}

function FactsTooltip({ facts }) {
  return (
    <div style={{ maxWidth: 360, fontSize: 12, lineHeight: 1.55 }}>
      {(facts || []).slice(0, 4).map((f, i) => (
        <div key={f.fact_id || i} style={{
          marginTop: i === 0 ? 0 : 8,
          paddingTop: i === 0 ? 0 : 8,
          borderTop: i === 0 ? "none" : "1px solid #ebedf5",
        }}>
          <div style={{
            fontWeight: 600,
            color: f.verdict === "VERIFIED" ? "var(--green)" : "var(--gold)",
            marginBottom: 2,
          }}>
            {f.verdict === "VERIFIED" ? "✓" : "⚠"} {f.claim || "(no claim)"}
          </div>
          {f.verbatim_quote && (
            <div style={{ color: "#5b6285", fontStyle: "italic", fontSize: 11 }}>
              "{f.verbatim_quote.length > 100 ? f.verbatim_quote.slice(0, 100) + "…" : f.verbatim_quote}"
            </div>
          )}
        </div>
      ))}
      {(facts || []).length > 4 && (
        <div style={{ marginTop: 6, color: "var(--muted)", fontSize: 11 }}>
          …and {facts.length - 4} more. Click the card to view all.
        </div>
      )}
    </div>
  );
}

export default function Sources({ items }) {
  const { openEvidence } = useEvidence();
  if (!items || items.length === 0) return null;

  // Sort: sources with verified_facts come first (the ones lawyer cares about).
  const ordered = [...items].sort((a, b) => {
    const fa = (a.verified_facts || []).length;
    const fb = (b.verified_facts || []).length;
    if (fa !== fb) return fb - fa;
    return a.index - b.index;
  });

  const cited = ordered.filter(s => (s.verified_facts || []).length > 0).length;

  const collapseItems = [
    {
      key: "1",
      label: (
        <span style={styles.collapseLabel}>
          <span style={styles.sourceCount}>{items.length}</span>
          Sources retrieved
          {cited > 0 && (
            <span style={styles.citedHint}>
              · {cited} actively cited
            </span>
          )}
        </span>
      ),
      children: (
        <div style={styles.grid}>
          {ordered.map(s => {
            const badge = badgeForFacts(s.verified_facts);
            const clickable = (s.verified_facts || []).length > 0 || (s.body && s.body.length > 0);
            return (
              <div
                key={s.index}
                style={{
                  ...styles.sourceCard,
                  cursor: clickable ? "pointer" : "default",
                  borderColor: badge ? badge.border : "#ebedf5",
                  background: badge ? badge.bg + "33" : "#fafbfe",  // alpha tint
                }}
                className="source-card"
                onClick={() => clickable && openEvidence(s.index)}
              >
                <div style={styles.cardHeader}>
                  <Tag
                    icon={s.type === "attachment" ? <PaperClipOutlined /> : <MailOutlined />}
                    style={{
                      ...styles.typeTag,
                      background: s.type === "attachment" ? "var(--river-tint)" : "var(--surface-inset)",
                      color: s.type === "attachment" ? "var(--river)" : "var(--t2)",
                      borderColor: s.type === "attachment" ? "var(--river-mist)" : "var(--hair-2)",
                    }}
                  >
                    {s.type === "attachment" ? "Attachment" : "Email"}
                  </Tag>
                  <Text style={styles.indexLabel}>[#{s.index}]</Text>
                  {s.rerank_score != null && (
                    <Text style={styles.score}>score {s.rerank_score}</Text>
                  )}
                </div>
                <div style={styles.cardTitle}>{s.title}</div>
                {(s.date || s.from_email) && (
                  <div style={styles.cardMeta}>
                    {s.date && (
                      <span style={styles.metaItem}>
                        <CalendarOutlined style={{ marginRight: 3 }} />
                        {s.date}
                      </span>
                    )}
                    {s.from_email && (
                      <span style={styles.metaItem}>
                        <UserOutlined style={{ marginRight: 3 }} />
                        {s.from_email.length > 30 ? s.from_email.slice(0, 30) + "…" : s.from_email}
                      </span>
                    )}
                    {s.page && <span style={styles.metaItem}>{s.page}</span>}
                  </div>
                )}
                {badge && (
                  <Tooltip
                    title={<FactsTooltip facts={s.verified_facts} />}
                    placement="top"
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
                    <Tag
                      icon={badge.icon}
                      style={{
                        ...styles.factsBadge,
                        background: badge.bg,
                        color: badge.color,
                        borderColor: badge.border,
                      }}
                    >
                      {badge.label}
                    </Tag>
                  </Tooltip>
                )}
              </div>
            );
          })}
        </div>
      ),
    },
  ];

  return (
    <div style={styles.wrap}>
      <Collapse ghost size="small" items={collapseItems} style={styles.collapse} />
    </div>
  );
}

const styles = {
  wrap: { marginTop: 18, borderTop: "1px solid var(--hair)", paddingTop: 4 },
  collapse: { background: "transparent" },
  collapseLabel: {
    display: "flex", alignItems: "center", gap: 8,
    fontSize: 11.5, color: "var(--muted)", fontWeight: 500,
  },
  sourceCount: {
    background: "transparent", color: "var(--muted-2)",
    padding: "0", fontSize: 11.5, fontWeight: 600,
    fontFamily: "'JetBrains Mono', monospace",
  },
  citedHint: { fontSize: 11.5, color: "var(--green)", fontWeight: 500 },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(248px, 1fr))",
    gap: 8, paddingTop: 6,
  },
  sourceCard: {
    background: "var(--surface)",
    border: "1px solid var(--hair)",
    borderRadius: "var(--r-md)",
    padding: "12px 14px",
  },
  cardHeader: {
    display: "flex", alignItems: "center", gap: 7, marginBottom: 6, flexWrap: "wrap",
  },
  typeTag: {
    borderRadius: "var(--pill)", fontSize: 10, fontWeight: 500, lineHeight: "18px", margin: 0,
    padding: "0 9px", border: "1px solid",
  },
  indexLabel: {
    fontSize: 11, fontWeight: 600, color: "var(--brand)", fontFamily: "'JetBrains Mono', monospace",
  },
  score: { fontSize: 10, color: "var(--muted-2)", marginLeft: "auto", fontFamily: "'JetBrains Mono', monospace" },
  cardTitle: {
    fontSize: 13, fontWeight: 500, color: "var(--ink)",
    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
    marginBottom: 4,
  },
  cardMeta: {
    display: "flex", flexWrap: "wrap", gap: "4px 10px",
  },
  metaItem: {
    fontSize: 11, color: "var(--muted-2)",
    display: "flex", alignItems: "center",
  },
  factsBadge: {
    marginTop: 9,
    marginRight: 0,
    borderRadius: "var(--pill)",
    fontSize: 10,
    fontWeight: 500,
    lineHeight: "16px",
    padding: "0 9px",
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    border: "1px solid",
  },
};
