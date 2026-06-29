import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spin, Tag, Card, Timeline, Descriptions, Button, Tabs, Table, Tooltip, Empty, message } from "antd";
import jsPDF from "jspdf";
import { getProperty, getEvidencePacket, getPropertyGraph } from "./api";
import PropertyGraphView from "./PropertyGraphView";
import DocumentViewer from "./DocumentViewer";

const SEV_COLOR = { critical: "red", high: "volcano", medium: "gold", info: "default" };
const EVENT_COLOR = {
  conveyance: "#234a52", mortgage: "#8a6d1f", lien: "#b4441f", judgment: "#9b1c1c",
  lis_pendens: "#7a3ba8", assignment: "#3a6ea5", title_search: "#5b5f6e",
  policy_effective: "#2e7d32", policy_cancelled: "#b4441f", litigation_update: "#7a3ba8",
};
const money = (v) => (v == null || v === "" ? "—" :
  (typeof v === "number" ? "$" + v.toLocaleString() : String(v)));
const cardStyle = { background: "#fdfbf6", borderColor: "#e7e2d6" };
const serif = { fontFamily: "'Instrument Serif',Georgia,serif" };

// A grounded-facts table: each row expands to its verbatim source quote.
function FactTable({ rows, columns, emptyText = "None on record." }) {
  if (!rows || rows.length === 0)
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />;
  return (
    <Table
      size="small"
      dataSource={rows.map((r, i) => ({ key: i, ...r }))}
      columns={columns}
      pagination={rows.length > 12 ? { pageSize: 12, size: "small" } : false}
      scroll={{ x: "max-content" }}
      expandable={{
        expandedRowRender: (r) => (
          <div style={{ ...serif, fontStyle: "italic", color: "#3a3d4a", padding: "2px 8px" }}>
            “{r.source_quote || "(no quote captured)"}”
          </div>
        ),
        rowExpandable: (r) => !!r.source_quote,
      }}
    />
  );
}

const qcol = { title: "Source", key: "src", width: 80,
  render: (_, r) => r.source_quote
    ? <Tooltip title={r.source_quote}><span style={{ color: "#234a52", cursor: "help" }}>quote ▾</span></Tooltip>
    : "—" };

export default function PropertyDetail() {
  const { propertyId } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);
  const [graph, setGraph] = useState(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [openDoc, setOpenDoc] = useState(null);

  useEffect(() => {
    setLoading(true);
    setGraph(null);
    setGraphLoading(true);
    getProperty(propertyId).then(r => setD(r.data)).finally(() => setLoading(false));
    getPropertyGraph(propertyId).then(r => setGraph(r.data)).finally(() => setGraphLoading(false));
  }, [propertyId]);

  const loadGraph = () => {
    if (graph || graphLoading) return;
    setGraphLoading(true);
    getPropertyGraph(propertyId).then(r => setGraph(r.data)).finally(() => setGraphLoading(false));
  };

  const exportPacket = async () => {
    const r = await getEvidencePacket(propertyId);
    const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `evidence_${propertyId}.json`; a.click();
    message.success("Evidence packet (JSON) exported");
  };

  // Full property dossier PDF — every section the page shows, then a
  // numbered "References & Sources" (chain of custody) at the very end.
  const exportPacketPdf = () => {
    const p = d || {};
    const ds0 = p.dossier || {}, eq0 = ds0.equity || {}, gf0 = ds0.grounded_facts || {};
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const M = 44, W = doc.internal.pageSize.getWidth() - M * 2, PH = doc.internal.pageSize.getHeight();
    let y = M;
    const ensure = (hh) => { if (y + hh > PH - M) { doc.addPage(); y = M; } };
    const line = (text, { size = 10, bold = false, gap = 4, color = [28, 30, 42], indent = 0, font = "times" } = {}) => {
      doc.setFont(font, bold ? "bold" : "normal"); doc.setFontSize(size);
      doc.setTextColor(color[0], color[1], color[2]);
      doc.splitTextToSize(String(text ?? ""), W - indent).forEach((w) => { ensure(size + gap); doc.text(w, M + indent, y); y += size + gap; });
    };
    const heading = (t) => { y += 9; ensure(24); line(t, { size: 13, bold: true, color: [35, 74, 82] }); doc.setDrawColor(231, 226, 214); doc.line(M, y, M + W, y); y += 8; };
    const quote = (q) => { if (q) line(`“${q}”`, { size: 8.5, color: [95, 95, 110], indent: 14, gap: 3 }); };
    const none = () => line("None on record.", { size: 9.5, color: [120, 120, 130] });

    // Header
    line("PROPERTY EVIDENCE DOSSIER — COURT-READY", { size: 15, bold: true, color: [35, 74, 82] });
    line(ds0.canonical_address || propertyId, { size: 12, bold: true });
    line(`Parcel ${ds0.parcel_id || "—"}  ·  ${ds0.county || ""}  ·  Side: ${ds0.side || "—"}  ·  Generated ${new Date().toLocaleString()}`, { size: 9, color: [91, 95, 110], gap: 6 });

    // Identification & ownership
    heading("Identification & ownership");
    line(`Owner(s): ${(ds0.owners || []).map(o => o.name).join(", ") || "—"}`);
    line(`Owner since: ${ds0.current_owner_since || "—"}   ·   Side: ${ds0.side || "—"}`);

    // Financial & status
    heading("Financial & status");
    const M$ = (v) => (typeof v === "number" ? "$" + v.toLocaleString() : (v || "—"));
    line(`Equity: ${M$(eq0.equity)}   ·   Market value: ${M$(eq0.mkt_value)}   ·   Mortgage: ${M$(eq0.mortgage_amount)}`);
    line(`Lender: ${eq0.lender || "—"}   ·   RE taxes owed: ${M$(eq0.re_taxes_owed)}`);
    line(`Foreclosure: ${eq0.active_foreclosure || "—"}   ·   Lis pendens: ${eq0.lis_pendens || "—"}`);
    line(`Insurance: ${ds0.insurance?.in_force ? "In force — " + (ds0.insurance.insurers || []).join(", ") : "None on file"}`);

    // Ownership history
    heading("Ownership history");
    if ((p.ownership || []).length) p.ownership.forEach((o) => line(`${o.as_of || "?"} → ${o.until || "present"}   ·   ${o.owner}` + (o.amount ? `   ·   ${o.amount}` : "")));
    else none();

    // Title reports
    heading("Title reports (full & update searches)");
    if ((p.title_reports || []).length) p.title_reports.forEach((t) => line(`${t.date || "?"}  ·  ${t.type}${t.is_latest ? " (LATEST)" : ""}  ·  ${t.vendor || ""}  ·  order ${t.order_number || "—"}  ·  ${t.pages || "?"} pp`));
    else none();

    // Chain of title
    heading("Chain of title");
    if ((gf0.chain_of_title || []).length) gf0.chain_of_title.forEach((c) => {
      line(`${c.dated || c.recorded || "?"}  ·  ${c.grantor || "?"} → ${c.grantee || "?"}  ·  ${c.instrument_type || ""}  ${c.amount || ""}`, { bold: true, size: 9.5, gap: 3 });
      quote(c.source_quote);
    }); else none();

    // Encumbrances
    const factSection = (title, arr, fmt) => {
      heading(title);
      if ((arr || []).length) arr.forEach((x) => { line(fmt(x), { bold: true, size: 9.5, gap: 3 }); quote(x.source_quote); });
      else none();
    };
    factSection("Mortgages", gf0.mortgages, (x) => `${x.dated || x.recorded || "?"}  ·  ${x.lender || "?"}  ·  borrower ${x.borrower || "?"}  ·  ${x.amount || ""}  ${x.satisfied ? "[satisfied]" : "[open]"}`);
    factSection("Liens", gf0.liens, (x) => `${x.dated || "?"}  ·  ${x.lien_type || ""}  ·  ${x.creditor || "?"}  ·  ${x.amount || ""}`);
    factSection("Judgments", gf0.judgments, (x) => `${x.entered || "?"}  ·  creditor ${x.creditor || "?"}  ·  debtor ${x.debtor || "?"}  ·  ${x.amount || ""}`);
    factSection("Lis pendens", gf0.lis_pendens, (x) => `${x.filed || "?"}  ·  ${x.case || ""}  ·  plaintiff ${x.plaintiff || "?"}`);
    factSection("Assignments", gf0.assignments, (x) => `${x.dated || "?"}  ·  ${x.assignor || "?"} → ${x.assignee || "?"}`);

    // Insurance
    heading("Insurance");
    if ((p.insurance_reports || []).length) p.insurance_reports.forEach((i) => line(`${i.effective_date || "?"} → ${i.expiration_date || "?"}  ·  ${i.insurer || "?"}  ·  ${i.named_insured || ""}  ·  ${i.is_cancellation ? "CANCELLATION" : "coverage"}`));
    else none();

    // Timeline
    heading("Event timeline (cited)");
    if ((p.timeline || []).length) p.timeline.forEach((ev) => { line(`${ev.date || "?"}  [${ev.event_type || ""}]  ${ev.detail || ""}` + (ev.amount ? `  (${ev.amount})` : ""), { size: 9.5, gap: 3 }); quote(ev.source_quote); });
    else none();

    // Flow of funds
    heading("Flow of funds");
    line(`${p.flow_of_funds?.n_events || 0} monetary events · total seen $${(p.flow_of_funds?.total_amount_seen || 0).toLocaleString()}`, { size: 9.5 });
    (p.flow_of_funds?.flows || []).filter(f => f.amount).forEach((f) => line(`$${(f.amount).toLocaleString()}  ·  ${f.type}  ·  ${f.date}  —  ${f.detail || ""}`, { size: 9 }));

    // Findings
    heading("Findings");
    if ((p.findings || []).length) p.findings.forEach((f) => { line(`• [${(f.severity || "").toUpperCase()}] ${f.title || ""}  (${f.status || "pending"})`, { bold: true, size: 9.5, gap: 3 }); line(f.detail || "", { size: 9, indent: 12 }); (f.evidence || []).forEach((e) => quote(e.quote)); });
    else none();

    // References & Sources — chain of custody at the very end
    heading("REFERENCES & SOURCES (chain of custody)");
    if ((p.documents || []).length) p.documents.forEach((dd, i) => {
      line(`[${i + 1}]  [${dd.source_type || "doc"}]  ${dd.source_file || dd.doc_id}`, { bold: true, size: 9.5, gap: 3 });
      line(`SHA-256: ${dd.sha256 || "—"}   ·   pages: ${dd.pages ?? "—"}   ·   vendor: ${dd.vendor || "—"}`, { size: 8.5, color: [110, 110, 120], indent: 14 });
    }); else none();
    y += 8; ensure(18);
    line("Every fact above is grounded in a cited source. Generated by the Mango Tree Evidence Engine.", { size: 8, color: [140, 140, 150] });

    doc.save(`property_dossier_${propertyId}.pdf`);
    message.success("Property dossier (PDF) exported");
  };

  if (loading) return <Spin />;
  if (!d || d.detail === "property not found") return <p>Property not found.</p>;
  const ds = d.dossier || {};
  const eq = ds.equity || {};
  const gf = ds.grounded_facts || {};
  const scoped = ds.fact_counts_scoped || {};

  // count badge for a tab (current-era / total when we have the split)
  const tabLabel = (name, key) => {
    const total = (gf[key] || []).length;
    const sc = scoped[key];
    if (sc && total) return `${name} (${sc.current_owner_era || 0}/${total})`;
    return `${name} (${total})`;
  };

  // ── column sets (lawyer-oriented) ──
  const chainCols = [
    { title: "Dated", dataIndex: "dated", width: 96 },
    { title: "Recorded", dataIndex: "recorded", width: 96 },
    { title: "Grantor (from)", dataIndex: "grantor" },
    { title: "Grantee (to)", dataIndex: "grantee" },
    { title: "Instrument", dataIndex: "instrument_type", width: 120 },
    { title: "Amount", dataIndex: "amount", width: 100 },
    qcol,
  ];
  const mortCols = [
    { title: "Dated", dataIndex: "dated", width: 96 },
    { title: "Recorded", dataIndex: "recorded", width: 96 },
    { title: "Lender", dataIndex: "lender" },
    { title: "Borrower", dataIndex: "borrower" },
    { title: "Amount", dataIndex: "amount", width: 110 },
    { title: "Satisfied", dataIndex: "satisfied", width: 84, render: (v) => v ? <Tag color="green">satisfied</Tag> : <Tag color="volcano">open</Tag> },
    qcol,
  ];
  const lienCols = [
    { title: "Dated", dataIndex: "dated", width: 96 },
    { title: "Type", dataIndex: "lien_type", width: 120 },
    { title: "Creditor", dataIndex: "creditor" },
    { title: "Amount", dataIndex: "amount", width: 110 },
    qcol,
  ];
  const judgCols = [
    { title: "Entered", dataIndex: "entered", width: 96 },
    { title: "Creditor", dataIndex: "creditor" },
    { title: "Debtor", dataIndex: "debtor" },
    { title: "Amount", dataIndex: "amount", width: 110 },
    qcol,
  ];
  const lisCols = [
    { title: "Filed", dataIndex: "filed", width: 96 },
    { title: "Case", dataIndex: "case" },
    { title: "Plaintiff", dataIndex: "plaintiff" },
    qcol,
  ];
  const assignCols = [
    { title: "Dated", dataIndex: "dated", width: 96 },
    { title: "Assignor (from)", dataIndex: "assignor" },
    { title: "Assignee (to)", dataIndex: "assignee" },
    qcol,
  ];
  const titleCols = [
    { title: "Date", dataIndex: "date", width: 130, render: (v, r) => (
      <a onClick={() => r.doc_id && setOpenDoc(r.doc_id)} style={{ color: "#234a52", fontWeight: 600 }}>
        {v || "open"} ↗{r.is_latest && <Tag color="green" style={{ marginLeft: 6 }}>latest</Tag>}
      </a>) },
    { title: "Type", dataIndex: "type", width: 120, render: (v) => <Tag color={v === "full search" ? "blue" : "default"}>{v}</Tag> },
    { title: "Vendor", dataIndex: "vendor" },
    { title: "Effective", dataIndex: "effective_date", width: 100 },
    { title: "Order #", dataIndex: "order_number", width: 110 },
    { title: "Pages", dataIndex: "pages", width: 70, align: "center" },
  ];
  const insCols = [
    { title: "Effective", dataIndex: "effective_date", width: 100 },
    { title: "Expiration", dataIndex: "expiration_date", width: 100 },
    { title: "Insurer", dataIndex: "insurer" },
    { title: "Named insured", dataIndex: "named_insured" },
    { title: "Year", dataIndex: "policy_year", width: 70 },
    { title: "Status", dataIndex: "is_cancellation", width: 110, render: (v) => v ? <Tag color="volcano">cancellation</Tag> : <Tag color="green">coverage</Tag> },
  ];
  const docCols = [
    { title: "Source file", dataIndex: "source_file", render: (v, r) => (
      <a onClick={() => setOpenDoc(r.doc_id)} style={{ color: "#234a52", fontWeight: 600 }}>
        {v || r.doc_id} ↗
      </a>) },
    { title: "Type", dataIndex: "source_type", width: 130 },
    { title: "Pages", dataIndex: "pages", width: 70, align: "center" },
    { title: "SHA-256", dataIndex: "sha256", width: 130, render: (v) => v ? <Tooltip title={v}><code style={{ fontSize: 11 }}>{v.slice(0, 12)}…</code></Tooltip> : "—" },
  ];

  const rows = (key) => (gf[key] || []).map((x) => ({ ...x }));

  const tabs = [
    { key: "map", label: "◆ Property map", children: (
      graphLoading && !graph ? <Spin /> : <PropertyGraphView data={graph} />
    ) },
    { key: "overview", label: "Overview", children: (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card size="small" title="Identification & ownership" style={cardStyle}>
          <Descriptions column={1} size="small" colon items={[
            { label: "Address", children: ds.canonical_address || propertyId },
            { label: "Parcel / APN", children: ds.parcel_id || "—" },
            { label: "County", children: ds.county || "—" },
            { label: "Owner(s)", children: (ds.owners || []).map(o => o.name).join(", ") || "—" },
            { label: "Side", children: ds.side || "—" },
            { label: "Owner since", children: ds.current_owner_since || "—" },
          ]} />
        </Card>
        <Card size="small" title="Financial & status" style={cardStyle}>
          <Descriptions column={1} size="small" colon items={[
            { label: "Equity", children: money(eq.equity) },
            { label: "Market value", children: money(eq.mkt_value) },
            { label: "Mortgage", children: money(eq.mortgage_amount) },
            { label: "Lender", children: eq.lender || "—" },
            { label: "RE taxes owed", children: money(eq.re_taxes_owed) },
            { label: "Foreclosure", children: eq.active_foreclosure || "—" },
            { label: "Lis pendens", children: eq.lis_pendens || "—" },
            { label: "Insurance", children: ds.insurance?.in_force ? `In force — ${(ds.insurance.insurers || []).join(", ")}` : "None on file" },
          ]} />
        </Card>
        <Card size="small" title={`Ownership history (${(d.ownership || []).length})`} style={{ ...cardStyle, gridColumn: "1 / span 2" }}>
          {(d.ownership || []).length === 0 ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No dated ownership chain on record." /> : (
            <Timeline mode="left" items={(d.ownership || []).map((o) => ({
              color: "#234a52",
              label: <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{o.as_of || "?"} → {o.until || "present"}</span>,
              children: <span><b>{o.owner}</b>{o.amount ? <Tag color="gold" style={{ marginLeft: 6 }}>{o.amount}</Tag> : null}</span>,
            }))} />
          )}
        </Card>
      </div>
    ) },
    { key: "title", label: `Title reports (${(d.title_reports || []).length})`, children: (
      <>
        <Card size="small" title="Title reports — full & update searches" style={cardStyle}>
          <FactTable rows={d.title_reports} columns={titleCols} emptyText="No title reports on file." />
        </Card>
        <Card size="small" title={tabLabel("Chain of title", "chain_of_title")} style={{ ...cardStyle, marginTop: 16 }}>
          <FactTable rows={rows("chain_of_title")} columns={chainCols} emptyText="No chain-of-title entries extracted." />
        </Card>
      </>
    ) },
    { key: "enc", label: "Encumbrances", children: (
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card size="small" title={tabLabel("Mortgages", "mortgages")} style={cardStyle}>
          <FactTable rows={rows("mortgages")} columns={mortCols} emptyText="No mortgages on record." />
        </Card>
        <Card size="small" title={tabLabel("Liens", "liens")} style={cardStyle}>
          <FactTable rows={rows("liens")} columns={lienCols} emptyText="No liens on record." />
        </Card>
        <Card size="small" title={tabLabel("Judgments", "judgments")} style={cardStyle}>
          <FactTable rows={rows("judgments")} columns={judgCols} emptyText="No judgments on record." />
        </Card>
        <Card size="small" title={tabLabel("Lis pendens", "lis_pendens")} style={cardStyle}>
          <FactTable rows={rows("lis_pendens")} columns={lisCols} emptyText="No lis pendens on record." />
        </Card>
        <Card size="small" title={tabLabel("Assignments", "assignments")} style={cardStyle}>
          <FactTable rows={rows("assignments")} columns={assignCols} emptyText="No assignments on record." />
        </Card>
      </div>
    ) },
    { key: "ins", label: `Insurance (${(d.insurance_reports || []).length})`, children: (
      <Card size="small" title="Insurance — policies & evidence of coverage" style={cardStyle}>
        <FactTable rows={d.insurance_reports} columns={insCols} emptyText="No insurance on file." />
      </Card>
    ) },
    { key: "tl", label: `Timeline (${d.timeline?.length || 0})`, children: (
      <Card size="small" style={cardStyle}>
        <Timeline mode="left" items={(d.timeline || []).map((e) => ({
          color: EVENT_COLOR[e.event_type] || "#234a52",
          label: <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{e.date}</span>,
          children: (
            <div>
              <Tag>{e.event_type}</Tag>
              <span style={{ fontWeight: 600 }}>{e.detail}</span>
              {e.amount && <Tag color="gold" style={{ marginLeft: 6 }}>{e.amount}</Tag>}
              {e.source_quote && <div style={{ ...serif, fontStyle: "italic", fontSize: 13, color: "#5b5f6e", marginTop: 2 }}>“{e.source_quote.slice(0, 200)}”</div>}
            </div>) }))} />
      </Card>
    ) },
    { key: "fof", label: "Flow of funds", children: (
      <Card size="small" style={cardStyle}>
        <p style={{ color: "#5b5f6e" }}>
          {d.flow_of_funds?.n_events || 0} monetary events · total seen{" "}
          <b>${(d.flow_of_funds?.total_amount_seen || 0).toLocaleString()}</b>
        </p>
        <Timeline items={(d.flow_of_funds?.flows || []).filter(f => f.amount).map((f) => ({
          color: EVENT_COLOR[f.type] || "#234a52",
          children: <span><b>${(f.amount).toLocaleString()}</b> · {f.type} · <span style={{ color: "#5b5f6e" }}>{f.date}</span> — {f.detail}</span> }))} />
      </Card>
    ) },
    { key: "find", label: `Findings (${d.findings?.length || 0})`, children: (
      <Card size="small" style={cardStyle}>
        {(d.findings || []).length === 0 && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No findings." />}
        {(d.findings || []).map((f) => (
          <div key={f.id} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid #efe9dc" }}>
            <Tag color={SEV_COLOR[f.severity]}>{f.severity}</Tag>
            <span style={{ fontWeight: 600 }}>{f.title}</span>
            <Tag style={{ marginLeft: 6 }}>{f.status || "pending"}</Tag>
            <div style={{ fontSize: 13, color: "#3a3d4a", marginTop: 4 }}>{f.detail}</div>
            {(f.evidence || [])[0]?.quote && (
              <div style={{ ...serif, fontStyle: "italic", fontSize: 13, color: "#5b5f6e", marginTop: 4 }}>“{f.evidence[0].quote}”</div>)}
          </div>
        ))}
      </Card>
    ) },
    { key: "docs", label: `Documents (${(d.documents || []).length})`, children: (
      <Card size="small" title="Source documents & chain of custody" style={cardStyle}>
        <FactTable rows={d.documents} columns={docCols} emptyText="No source documents linked." />
      </Card>
    ) },
  ];

  return (
    <div>
      <Button type="link" onClick={() => nav(-1)} style={{ paddingLeft: 0 }}>← Back to portfolio</Button>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4, flexWrap: "wrap" }}>
        <h2 style={{ ...serif, fontSize: 28, margin: 0, color: "#1c1e2a" }}>{ds.canonical_address || propertyId}</h2>
        {ds.is_david && <Tag color="red">David network</Tag>}
        {ds.side && !ds.is_david && <Tag>{ds.side}</Tag>}
        {d.finding_counts?.critical > 0 && <Tag color="red">{d.finding_counts.critical} critical</Tag>}
        {d.finding_counts?.high > 0 && <Tag color="volcano">{d.finding_counts.high} high</Tag>}
      </div>
      <div style={{ color: "#5b5f6e", marginBottom: 14, fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
        parcel {ds.parcel_id || "—"} · {ds.county || ""} · {(ds.title?.count || 0)} title reports · {(d.documents || []).length} source docs
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <Button onClick={exportPacketPdf} style={{ background: "#fff", color: "#234a52", borderColor: "#234a52", fontWeight: 600 }}>⬇ Evidence packet (PDF)</Button>
        <Button onClick={exportPacket} style={{ background: "#fff", color: "#234a52", borderColor: "#234a52" }}>⬇ Evidence packet (JSON)</Button>
      </div>

      <Tabs items={tabs} defaultActiveKey="map"
        onChange={(k) => { if (k === "map") loadGraph(); }} />

      <DocumentViewer docId={openDoc} onClose={() => setOpenDoc(null)} />
    </div>
  );
}
