import { useMemo, useState } from "react";
import { Card, Tag, Statistic, Row, Col, Empty, Tooltip, Segmented, Timeline } from "antd";
import {
  ResponsiveContainer, ComposedChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RTooltip, Legend, ScatterChart, Scatter, ZAxis, Cell,
} from "recharts";

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

export default function PropertyGraphView({ data }) {
  const [view, setView] = useState("Financing");
  const [activeYear, setActiveYear] = useState(null);
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

  const yearDomain = useMemo(() => {
    const ys = scatter.map((p) => p.x).filter(Boolean);
    return ys.length ? [Math.min(...ys) - 1, Math.max(...ys) + 1] : [2010, 2026];
  }, [scatter]);

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

      {/* ── ACTIVITY MAP: everything across years in lanes ── */}
      {view === "Activity map" && (
        <Card size="small" title="Property activity map — every event across time"
          style={cardStyle} extra={<span style={{ ...mono, fontSize: 11, color: C.mute }}>click a point</span>}>
          <ResponsiveContainer width="100%" height={420}>
            <ScatterChart margin={{ top: 10, right: 24, left: 60, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ece6d8" />
              <XAxis type="number" dataKey="x" name="Year" domain={yearDomain}
                allowDecimals={false} tick={{ fontSize: 12, fontFamily: "monospace" }} />
              <YAxis type="number" dataKey="y" name="Type" domain={[-0.5, LANES.length - 0.5]}
                ticks={LANES.map((_, i) => i)} tickFormatter={(i) => LANES[i] ? LANES[i][1] : ""}
                tick={{ fontSize: 11 }} width={150} />
              <ZAxis type="number" dataKey="z" range={[60, 600]} />
              <RTooltip content={<DotTip />} cursor={{ strokeDasharray: "3 3" }} />
              <Scatter data={scatter} onClick={(p) => setActiveYear(p?.x)}>
                {scatter.map((p, i) => (
                  <Cell key={i} fill={TYPE_COLOR[p.type] || C.brand} fillOpacity={0.78} />
                ))}
              </Scatter>
            </ScatterChart>
          </ResponsiveContainer>
          {activeYear && <YearDetail year={activeYear} g={g} onClose={() => setActiveYear(null)} />}
        </Card>
      )}

      {/* ── TITLE CHAIN: original → updates ── */}
      {view === "Title chain" && (
        <Card size="small" title="Title report version chain" style={cardStyle}>
          {(g.title_versions || []).length === 0 ? <Empty description="No title reports." /> : (
            <div style={{ display: "flex", gap: 0, flexWrap: "wrap", alignItems: "stretch" }}>
              {g.title_versions.map((t, i) => (
                <div key={t.doc_id} style={{ display: "flex", alignItems: "center" }}>
                  <div style={{ border: `1px solid ${t.is_latest ? C.green : C.hair}`, borderRadius: 8,
                    padding: "10px 14px", background: "#fff", minWidth: 180,
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
                  <div style={{ border: `1px solid ${C.hair}`, borderRadius: 8, padding: 12, background: "#fff", height: "100%" }}>
                    <Tag color={TYPE_COLOR[d.source_type] ? undefined : "default"}
                      style={{ borderColor: TYPE_COLOR[d.source_type], color: TYPE_COLOR[d.source_type] }}>
                      {d.source_type}
                    </Tag>
                    <div style={{ fontWeight: 600, color: C.ink, marginTop: 4 }}>{d.label}</div>
                    <div style={{ ...mono, fontSize: 12, color: C.mute }}>{d.date || "undated"} · {d.pages || "?"} pp</div>
                    {d.sha256 && <Tooltip title={d.sha256}><code style={{ fontSize: 10, color: C.mute }}>{d.sha256.slice(0, 14)}…</code></Tooltip>}
                  </div>
                </Col>
              ))}
            </Row>
          )}
        </Card>
      )}
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

function DotTip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div style={{ background: "#fff", border: `1px solid ${C.hair}`, borderRadius: 8, padding: 10, maxWidth: 300 }}>
      <Tag color="default" style={{ borderColor: TYPE_COLOR[p.type], color: TYPE_COLOR[p.type] }}>{p.type}</Tag>
      <span style={mono}> {p.x}</span>
      <div style={{ fontWeight: 600, marginTop: 4 }}>{p.label}</div>
      {p.quote && <div style={{ ...serif, fontStyle: "italic", fontSize: 12, color: C.mute, marginTop: 4 }}>“{String(p.quote).slice(0, 140)}”</div>}
    </div>
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
