import { useMemo, useState } from "react";
import { Card, Tag, Statistic, Row, Col, Empty, Tooltip, Segmented, Timeline } from "antd";
import {
  ResponsiveContainer, ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RTooltip, Legend,
} from "recharts";
import DocumentViewer from "./DocumentViewer";

// Brand palette (matches index.css / PropertyDetail)
const C = {
  brand: "#234a52", gold: "#8a6d1f", lien: "#b4441f", judgment: "#9b1c1c",
  assignment: "#3a6ea5", conveyance: "#234a52", title: "#5b5f6e", green: "#2e7d32",
  paper: "#fdfbf6", hair: "#e7e2d6", ink: "#1c1e2a", mute: "#5b5f6e",
};
const TYPE_COLOR = {
  conveyance: C.conveyance, mortgage: C.gold, lien: C.lien, judgment: C.judgment,
  lis_pendens: "#7a3ba8", assignment: C.assignment, title_search: C.title,
  cheque: "#0f766e", wire_confirmation: "#1d4ed8", settlement_sheet: "#9333ea",
  bill_invoice: "#a16207",
};
const serif = { fontFamily: "'Instrument Serif',Georgia,serif" };
const mono = { fontFamily: "'JetBrains Mono',monospace" };
const cardStyle = { background: C.paper, borderColor: C.hair };
const usd = (v) => (v == null ? "—" : "$" + Math.round(v).toLocaleString());

// The "activity lanes" — one row per record type, plotted across years.
const LANES = [
  ["conveyance", "Conveyances"], ["mortgage", "Mortgages"], ["lien", "Liens"],
  ["judgment", "Judgments"], ["lis_pendens", "Lis pendens"], ["assignment", "Assignments"],
  ["title_search", "Title searches"], ["money", "Cheques / wires / settlements"],
];
const LANE_ICON = {
  conveyance: "⇄", mortgage: "$", lien: "▲", judgment: "§", lis_pendens: "⚖",
  assignment: "→", title_search: "◆", money: "₵",
};

export default function PropertyGraphView({ data }) {
  const [view, setView] = useState("Financing");
  const [activeYear, setActiveYear] = useState(null);
  const [openDoc, setOpenDoc] = useState(null);
  const g = data || {};
  const s = g.summary || {};

  // ── mortgages bucketed by year (open vs satisfied) ──
  const mortByYear = useMemo(() => {
    const by = {};
    (g.mortgages || []).forEach((m) => {
      const y = m.year || "undated";
      by[y] = by[y] || { year: String(y), open: 0, satisfied: 0, items: [] };
      const amt = m.amount_value || 0;
      if (m.satisfied) by[y].satisfied += amt; else by[y].open += amt;
      by[y].items.push(m);
    });
    return Object.values(by).sort((a, b) => (a.year > b.year ? 1 : -1));
  }, [g.mortgages]);

  // ── all activity as scatter points (x=year, y=lane) ──
  const laneIdx = Object.fromEntries(LANES.map(([k], i) => [k, i]));
  const scatter = useMemo(() => {
    const pts = [];
    const push = (type, year, amount, label, quote, docId) => {
      if (laneIdx[type] == null || !year) return;
      pts.push({ x: Number(year), y: laneIdx[type], z: amount || 1, type, label, quote, docId });
    };
    (g.mortgages || []).forEach((m) => push("mortgage", m.year, m.amount_value,
      `${m.lender || "?"} ${usd(m.amount_value)}${m.satisfied ? " (satisfied)" : ""}`, m.source_quote, m.doc_id));
    (g.conveyances || []).forEach((c) => push("conveyance", c.year, c.amount_value,
      `${c.grantor || "?"} → ${c.grantee || "?"}`, c.source_quote, c.doc_id));
    (g.encumbrances || []).forEach((e) => push(e.kind, e.year, e.amount_value,
      `${e.parties} ${usd(e.amount_value)}`, e.source_quote, e.doc_id));
    (g.title_versions || []).forEach((t) => push("title_search", t.year, 1,
      `${t.vendor || ""} ${t.type}${t.is_latest ? " (latest)" : ""}`, null, t.doc_id));
    (g.money_records || []).forEach((mr) => push("money", mr.year, mr.amount_value,
      `${mr.payer || "?"} → ${mr.payee || "?"} ${usd(mr.amount_value)}`, mr.source_quote, mr.doc_id));
    return pts;
  }, [g]);

  if (!g.property_id) return <Empty description="No graph data." />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      {/* ── KPI strip ── */}
      <Card size="small" style={cardStyle} styles={{ body: { padding: "14px 18px" } }}>
        <Row gutter={[16, 12]}>
          <Col><Statistic title="Title reports" value={s.n_title_reports || 0} /></Col>
          <Col><Statistic title="Mortgages" value={s.n_mortgages || 0} /></Col>
          <Col><Statistic title="Total mortgage debt" value={usd(s.total_mortgage_amount)}
            valueStyle={{ color: C.gold }} /></Col>
          <Col><Statistic title="Open (unsatisfied)" value={usd(s.open_mortgage_amount)}
            valueStyle={{ color: s.open_mortgage_amount ? C.lien : C.green }} /></Col>
          <Col><Statistic title="Conveyances" value={s.n_conveyances || 0} /></Col>
          <Col><Statistic title="Money records" value={s.n_money_records || 0} /></Col>
          <Col><Statistic title="Money traced" value={usd(s.money_total)}
            valueStyle={{ color: C.brand }} /></Col>
          <Col><Statistic title="Span"
            value={s.year_min ? `${s.year_min}–${s.year_max}` : "—"} /></Col>
        </Row>
      </Card>

      <Segmented value={view} onChange={setView}
        options={["Financing", "Activity map", "Title chain", "Money graph", "All documents"]} />

      {/* ── FINANCING: mortgages by year ── */}
      {view === "Financing" && (
        <Card size="small" title="Mortgages & financing by year" style={cardStyle}>
          {mortByYear.length === 0 ? <Empty description="No mortgages on record." /> : (
            <>
              <ResponsiveContainer width="100%" height={320}>
                <ComposedChart data={mortByYear} margin={{ top: 10, right: 20, left: 10, bottom: 4 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ece6d8" />
                  <XAxis dataKey="year" tick={{ fontSize: 12, fontFamily: "monospace" }} />
                  <YAxis tickFormatter={(v) => "$" + (v / 1000) + "k"} tick={{ fontSize: 11 }} />
                  <RTooltip content={<MortTip />} />
                  <Legend />
                  <Bar dataKey="open" name="Open / unsatisfied" stackId="a" fill={C.lien} radius={[3, 3, 0, 0]} />
                  <Bar dataKey="satisfied" name="Satisfied" stackId="a" fill={C.green} radius={[3, 3, 0, 0]} />
                </ComposedChart>
              </ResponsiveContainer>
              <div style={{ marginTop: 12 }}>
                {mortByYear.map((row) => (
                  <div key={row.year} style={{ borderTop: `1px solid ${C.hair}`, padding: "8px 0" }}>
                    <b style={mono}>{row.year}</b>{" "}
                    {row.items.map((m, i) => (
                      <Tooltip key={i} title={m.source_quote || "no quote"}>
                        <Tag color={m.satisfied ? "green" : "volcano"} style={{ margin: 3, cursor: "help" }}>
                          {m.lender || "?"} · {usd(m.amount_value)} {m.satisfied ? "✓" : "○"}
                        </Tag>
                      </Tooltip>
                    ))}
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>
      )}

      {/* ── ACTIVITY MAP: a friendly "story of the property" ── */}
      {view === "Activity map" && (
        <ActivityMap scatter={scatter} g={g} onOpenDoc={setOpenDoc}
          activeYear={activeYear} setActiveYear={setActiveYear} />
      )}

      {/* ── TITLE CHAIN: original → updates ── */}
      {view === "Title chain" && (
        <Card size="small" title="Title report version chain" style={cardStyle}>
          {(g.title_versions || []).length === 0 ? <Empty description="No title reports." /> : (
            <div style={{ display: "flex", gap: 0, flexWrap: "wrap", alignItems: "stretch" }}>
              {g.title_versions.map((t, i) => (
                <div key={t.doc_id} style={{ display: "flex", alignItems: "center" }}>
                  <div onClick={() => t.doc_id && setOpenDoc(t.doc_id)}
                    title="Open document"
                    style={{ border: `1px solid ${t.is_latest ? C.green : C.hair}`, borderRadius: 8,
                    padding: "10px 14px", background: "#fff", minWidth: 180, cursor: "pointer",
                    boxShadow: t.is_latest ? "0 0 0 2px rgba(46,125,50,.15)" : "none" }}>
                    <div style={{ ...mono, fontSize: 12, color: C.mute }}>{t.date || "undated"}</div>
                    <div style={{ fontWeight: 700, color: C.ink }}>
                      {t.type === "full search" ? "Full search" : "Update search"}
                    </div>
                    <div style={{ fontSize: 12, color: C.mute }}>{t.vendor || ""}</div>
                    {t.order_number && <div style={{ ...mono, fontSize: 11 }}>#{t.order_number}</div>}
                    <div style={{ marginTop: 4 }}>
                      {t.is_latest && <Tag color="green">latest</Tag>}
                      <Tag>{t.pages || "?"} pp</Tag>
                    </div>
                  </div>
                  {i < g.title_versions.length - 1 && (
                    <div style={{ color: C.brand, fontSize: 22, padding: "0 8px" }}>→</div>)}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {/* ── MONEY GRAPH: cheques / wires / settlement lines ── */}
      {view === "Money graph" && (
        <Card size="small" title="Money graph — cheques, wires & settlement lines (grounded)"
          style={cardStyle}>
          {(g.money_records || []).length === 0 ? <Empty description="No money records linked to this property." /> : (
            <Timeline items={(g.money_records || []).map((mr) => ({
              color: TYPE_COLOR[mr.doc_category] || C.brand,
              children: (
                <div>
                  <span style={mono}>{mr.date || "?"}</span>{"  "}
                  <b>{usd(mr.amount_value)}</b>{" "}
                  <Tag color="default">{mr.instrument || mr.doc_category || "payment"}</Tag>
                  {mr.instrument_no && <span style={{ ...mono, fontSize: 11 }}>#{mr.instrument_no}</span>}
                  {mr.reconciliation_id && <Tag color="purple" style={{ marginLeft: 4 }}>reconciled</Tag>}
                  <div style={{ color: C.ink }}>
                    {mr.payer || "?"} <span style={{ color: C.mute }}>→</span> {mr.payee || "?"}
                  </div>
                  {mr.memo && <div style={{ fontSize: 12, color: C.mute }}>{mr.memo}</div>}
                  {mr.source_quote && (
                    <div style={{ ...serif, fontStyle: "italic", fontSize: 13, color: C.mute }}>
                      “{String(mr.source_quote).slice(0, 160)}”</div>)}
                </div>) }))} />
          )}
        </Card>
      )}

      {/* ── ALL DOCUMENTS at a glance ── */}
      {view === "All documents" && (
        <Card size="small" title="Every document for this property — at a glance" style={cardStyle}>
          {(g.documents || []).length === 0 ? <Empty description="No documents linked." /> : (
            <Row gutter={[12, 12]}>
              {g.documents.map((d) => (
                <Col key={d.doc_id} xs={24} sm={12} md={8}>
                  <div onClick={() => setOpenDoc(d.doc_id)} title="Open document"
                    style={{ border: `1px solid ${C.hair}`, borderRadius: 8, padding: 12, background: "#fff",
                      height: "100%", cursor: "pointer", transition: "box-shadow .15s" }}
                    onMouseEnter={(e) => (e.currentTarget.style.boxShadow = "0 2px 10px rgba(35,74,82,.16)")}
                    onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}>
                    <Tag color={TYPE_COLOR[d.source_type] ? undefined : "default"}
                      style={{ borderColor: TYPE_COLOR[d.source_type], color: TYPE_COLOR[d.source_type] }}>
                      {d.source_type}
                    </Tag>
                    <div style={{ fontWeight: 600, color: C.ink, marginTop: 4 }}>{d.label}</div>
                    <div style={{ ...mono, fontSize: 12, color: C.mute }}>{d.date || "undated"} · {d.pages || "?"} pp</div>
                    {d.sha256 && <Tooltip title={d.sha256}><code style={{ fontSize: 10, color: C.mute }}>{d.sha256.slice(0, 14)}…</code></Tooltip>}
                    <div style={{ ...mono, fontSize: 11, color: C.brand, marginTop: 6 }}>open ↗</div>
                  </div>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      )}

      <DocumentViewer docId={openDoc} onClose={() => setOpenDoc(null)} />
    </div>
  );
}

function MortTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div style={{ background: "#fff", border: `1px solid ${C.hair}`, borderRadius: 8, padding: 10, maxWidth: 280 }}>
      <div style={{ ...mono, fontWeight: 700 }}>{label}</div>
      {(row.items || []).map((m, i) => (
        <div key={i} style={{ fontSize: 12, marginTop: 4 }}>
          <b>{usd(m.amount_value)}</b> · {m.lender || "?"} {m.satisfied ? "✓ satisfied" : "○ open"}
        </div>
      ))}
    </div>
  );
}

// ── Friendly activity map: a swimlane "when it happened" timeline + a readable
//    year-by-year story. Replaces the old bare scatter-of-dots. ──
const TYPE_LABEL = Object.fromEntries(LANES.map(([k, l]) => [k, l]));

function ActivityMap({ scatter, g, activeYear, setActiveYear, onOpenDoc }) {
  const years = scatter.map((p) => p.x).filter(Boolean);
  const minY = years.length ? Math.min(...years) : null;
  const maxY = years.length ? Math.max(...years) : null;
  const span = Math.max(1, (maxY || 0) - (minY || 0));
  const pos = (y) => (((y - minY) / span) * 100);

  // lanes that actually have events, in canonical order
  const lanes = LANES.filter(([k]) => scatter.some((p) => p.type === k));

  // year axis ticks (distinct years that have activity)
  const tickYears = Array.from(new Set(years)).sort((a, b) => a - b);

  // chronological story: events grouped by year, newest first
  const storyYears = useMemo(() => {
    const by = {};
    scatter.forEach((p) => { (by[p.x] = by[p.x] || []).push(p); });
    return Object.keys(by).map(Number).sort((a, b) => b - a)
      .map((y) => ({ year: y, items: by[y] }));
  }, [scatter]);

  if (!scatter.length) {
    return (
      <Card size="small" title="Property activity map" style={cardStyle}>
        <Empty description="No dated activity (mortgages, conveyances, liens, payments) recorded for this property yet." />
      </Card>
    );
  }

  return (
    <Card size="small" title="Property activity map — when everything happened"
      style={cardStyle}
      extra={<span style={{ ...mono, fontSize: 11, color: C.mute }}>click a year to expand</span>}>
      {/* legend */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginBottom: 14 }}>
        {lanes.map(([k, label]) => (
          <span key={k} style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 12, color: C.ink }}>
            <span style={{ width: 11, height: 11, borderRadius: 3, background: TYPE_COLOR[k] || C.brand, display: "inline-block" }} />
            {label}
          </span>
        ))}
      </div>

      {/* swimlanes: one row per type, markers placed by year */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {lanes.map(([k, label]) => {
          // cluster this lane's events by year
          const byY = {};
          scatter.filter((p) => p.type === k).forEach((p) => { (byY[p.x] = byY[p.x] || []).push(p); });
          const total = scatter.filter((p) => p.type === k).length;
          return (
            <div key={k} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 170, flexShrink: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ width: 22, height: 22, borderRadius: 6, background: TYPE_COLOR[k] || C.brand,
                  color: "#fff", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 13 }}>
                  {LANE_ICON[k] || "•"}
                </span>
                <span style={{ fontSize: 13, color: C.ink }}>{label}</span>
                <Tag style={{ marginLeft: "auto", marginRight: 0 }}>{total}</Tag>
              </div>
              <div style={{ position: "relative", flex: 1, height: 34, borderRadius: 6,
                background: "#fff", border: `1px solid ${C.hair}` }}>
                {/* baseline */}
                <div style={{ position: "absolute", top: "50%", left: 8, right: 8, height: 2,
                  background: "#f0ebdd", transform: "translateY(-50%)" }} />
                {Object.entries(byY).map(([yr, evs]) => {
                  const y = Number(yr);
                  const sz = Math.min(26, 14 + evs.length * 3);
                  const tip = (
                    <div style={{ maxWidth: 260 }}>
                      <b style={mono}>{yr}</b> · {label}
                      {evs.slice(0, 6).map((e, i) => (
                        <div key={i} style={{ fontSize: 12, marginTop: 3 }}>• {e.label}</div>
                      ))}
                      {evs.length > 6 && <div style={{ fontSize: 12, color: C.mute }}>+{evs.length - 6} more…</div>}
                    </div>
                  );
                  return (
                    <Tooltip key={yr} title={tip}>
                      <div onClick={() => setActiveYear(y)}
                        style={{ position: "absolute", top: "50%", left: `calc(${pos(y)}% )`,
                          transform: "translate(-50%,-50%)", width: sz, height: sz, borderRadius: "50%",
                          background: TYPE_COLOR[k] || C.brand, color: "#fff", cursor: "pointer",
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: 11, fontWeight: 700, border: "2px solid #fff",
                          boxShadow: activeYear === y ? `0 0 0 3px ${TYPE_COLOR[k]}55` : "0 1px 3px rgba(0,0,0,.18)" }}>
                        {evs.length > 1 ? evs.length : ""}
                      </div>
                    </Tooltip>
                  );
                })}
              </div>
            </div>
          );
        })}
        {/* year axis */}
        <div style={{ display: "flex", gap: 10, marginTop: 2 }}>
          <div style={{ width: 170, flexShrink: 0 }} />
          <div style={{ position: "relative", flex: 1, height: 18 }}>
            {tickYears.map((y) => (
              <span key={y} style={{ position: "absolute", left: `${pos(y)}%`, transform: "translateX(-50%)",
                ...mono, fontSize: 11, color: C.mute }}>{y}</span>
            ))}
          </div>
        </div>
      </div>

      {/* expanded year detail (click a marker) */}
      {activeYear && <YearDetail year={activeYear} g={g} onClose={() => setActiveYear(null)} />}

      {/* readable chronological story */}
      <div style={{ marginTop: 18, borderTop: `1px solid ${C.hair}`, paddingTop: 12 }}>
        <div style={{ ...serif, fontSize: 16, color: C.ink, marginBottom: 8 }}>Chronology</div>
        {storyYears.map(({ year, items }) => (
          <div key={year} style={{ display: "flex", gap: 14, marginBottom: 10 }}>
            <div style={{ width: 56, flexShrink: 0, ...mono, fontWeight: 700, color: C.brand, fontSize: 14 }}>{year}</div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
              {items.map((e, i) => (
                <div key={i}
                  onClick={() => e.docId && onOpenDoc && onOpenDoc(e.docId)}
                  title={e.docId ? "Open document" : undefined}
                  style={{ background: "#fff", borderRadius: "0 6px 6px 0",
                    padding: "6px 10px", border: `1px solid ${C.hair}`,
                    borderLeft: `3px solid ${TYPE_COLOR[e.type] || C.brand}`,
                    cursor: e.docId ? "pointer" : "default" }}>
                  <Tag style={{ borderColor: TYPE_COLOR[e.type], color: TYPE_COLOR[e.type], background: "transparent" }}>
                    {TYPE_LABEL[e.type] || e.type}
                  </Tag>
                  <span style={{ color: C.ink }}>{e.label}</span>
                  {e.docId && <span style={{ ...mono, fontSize: 11, color: C.brand, marginLeft: 6 }}>open ↗</span>}
                  {e.quote && (
                    <div style={{ ...serif, fontStyle: "italic", fontSize: 12.5, color: C.mute, marginTop: 3 }}>
                      “{String(e.quote).slice(0, 160)}”
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function YearDetail({ year, g, onClose }) {
  const items = [];
  (g.mortgages || []).filter((m) => m.year === year).forEach((m) =>
    items.push({ t: "mortgage", txt: `Mortgage · ${m.lender || "?"} · ${usd(m.amount_value)} ${m.satisfied ? "(satisfied)" : "(open)"}`, q: m.source_quote }));
  (g.conveyances || []).filter((c) => c.year === year).forEach((c) =>
    items.push({ t: "conveyance", txt: `Conveyance · ${c.grantor || "?"} → ${c.grantee || "?"} ${c.amount ? "· " + c.amount : ""}`, q: c.source_quote }));
  (g.encumbrances || []).filter((e) => e.year === year).forEach((e) =>
    items.push({ t: e.kind, txt: `${e.kind} · ${e.parties} ${e.amount ? "· " + e.amount : ""}`, q: e.source_quote }));
  (g.money_records || []).filter((mr) => mr.year === year).forEach((mr) =>
    items.push({ t: "money", txt: `${mr.payer || "?"} → ${mr.payee || "?"} · ${usd(mr.amount_value)}`, q: mr.source_quote }));
  return (
    <div style={{ marginTop: 12, padding: 12, border: `1px solid ${C.hair}`, borderRadius: 8, background: "#fff" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <b style={{ ...serif, fontSize: 18 }}>{year}</b>
        <a onClick={onClose} style={{ color: C.brand, cursor: "pointer" }}>close ✕</a>
      </div>
      {items.length === 0 ? <span style={{ color: C.mute }}>No detail.</span> : items.map((it, i) => (
        <div key={i} style={{ borderTop: `1px solid ${C.hair}`, padding: "6px 0" }}>
          <Tag style={{ borderColor: TYPE_COLOR[it.t], color: TYPE_COLOR[it.t] }}>{it.t}</Tag>
          <span>{it.txt}</span>
          {it.q && <div style={{ ...serif, fontStyle: "italic", fontSize: 12, color: C.mute }}>“{String(it.q).slice(0, 160)}”</div>}
        </div>
      ))}
    </div>
  );
}
