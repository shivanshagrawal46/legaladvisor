import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Spin, Tag, Card, Timeline, Descriptions, Button, Tabs, message } from "antd";
import jsPDF from "jspdf";
import { getProperty, getEvidencePacket } from "./api";

const SEV_COLOR = { critical: "red", high: "volcano", medium: "gold", info: "default" };
const EVENT_COLOR = {
  conveyance: "#234a52", mortgage: "#8a6d1f", lien: "#b4441f", judgment: "#9b1c1c",
  lis_pendens: "#7a3ba8", assignment: "#3a6ea5", title_search: "#5b5f6e",
  policy_effective: "#2e7d32", policy_cancelled: "#b4441f", litigation_update: "#7a3ba8",
};
const money = (v) => (v == null || v === "" ? "—" :
  (typeof v === "number" ? "$" + v.toLocaleString() : String(v)));

export default function PropertyDetail() {
  const { propertyId } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getProperty(propertyId).then(r => setD(r.data)).finally(() => setLoading(false));
  }, [propertyId]);

  const exportPacket = async () => {
    const r = await getEvidencePacket(propertyId);
    const blob = new Blob([JSON.stringify(r.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `evidence_${propertyId}.json`; a.click();
    message.success("Evidence packet (JSON) exported");
  };

  // Court-presentable PDF rendering of the same packet (custody + cited
  // timeline + findings), with auto page-breaks and text wrapping.
  const exportPacketPdf = async () => {
    const r = await getEvidencePacket(propertyId);
    const p = r.data || {};
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const M = 40;
    const W = doc.internal.pageSize.getWidth() - M * 2;
    const PH = doc.internal.pageSize.getHeight();
    let y = M;
    const ensure = (h) => { if (y + h > PH - M) { doc.addPage(); y = M; } };
    const line = (text, { size = 10, bold = false, gap = 4, color = [28, 30, 42] } = {}) => {
      doc.setFont("helvetica", bold ? "bold" : "normal");
      doc.setFontSize(size);
      doc.setTextColor(color[0], color[1], color[2]);
      doc.splitTextToSize(String(text ?? ""), W).forEach((w) => {
        ensure(size + gap); doc.text(w, M, y); y += size + gap;
      });
    };
    const heading = (t) => {
      y += 8; ensure(22);
      line(t, { size: 13, bold: true, color: [35, 74, 82] });
      doc.setDrawColor(231, 226, 214); doc.line(M, y, M + W, y); y += 8;
    };

    line("EVIDENCE PACKET — COURT-READY", { size: 16, bold: true, color: [35, 74, 82] });
    line(p.address || p.property_id || propertyId, { size: 12, bold: true });
    line(`Parcel ${p.parcel_id || "—"}  ·  Side: ${p.side || "—"}  ·  Generated ${p.generated_at || ""}`,
      { size: 9, color: [91, 95, 110] });

    heading("Documents & chain of custody");
    (p.documents || []).forEach((dd, i) => {
      line(`${i + 1}. [${dd.source_type || "doc"}] ${dd.source_file || dd.doc_id}`, { bold: true });
      line(`SHA-256: ${dd.sha256 || "—"}   ·   pages: ${dd.pages ?? "—"}   ·   vendor: ${dd.vendor || "—"}`,
        { size: 8.5, color: [91, 95, 110] });
    });
    if (!(p.documents || []).length) line("(none)", { color: [91, 95, 110] });

    if ((p.ownership_intervals || []).length) {
      heading("Ownership timeline (bitemporal)");
      p.ownership_intervals.forEach((iv) => line(
        `${iv.as_of || "?"} → ${iv.until || "present"}   ·   ${iv.owner_name || iv.owner}`
        + (iv.amount ? `   ·   ${iv.amount}` : ""), { size: 9.5 }));
    }

    heading("Event timeline (cited)");
    (p.timeline || []).forEach((ev) => {
      line(`${ev.date || "?"}  [${ev.event_type || ""}]  ${ev.detail || ""}`
        + (ev.amount ? `  (${ev.amount})` : ""), { size: 9.5 });
      if (ev.source_quote) line(`"${ev.source_quote}"`, { size: 8, color: [91, 95, 110] });
    });
    if (!(p.timeline || []).length) line("(none)", { color: [91, 95, 110] });

    heading("Findings");
    (p.findings || []).forEach((f) => {
      line(`• [${(f.severity || "").toUpperCase()}] ${f.title || ""}  (${f.status || "pending"})`, { bold: true });
      (f.evidence || []).forEach((e) => { if (e.quote) line(`"${e.quote}"`, { size: 8, color: [91, 95, 110] }); });
    });
    if (!(p.findings || []).length) line("(none)", { color: [91, 95, 110] });

    doc.save(`evidence_${propertyId}.pdf`);
    message.success("Evidence packet (PDF) exported");
  };

  if (loading) return <Spin />;
  if (!d || d.detail === "property not found") return <p>Property not found.</p>;
  const ds = d.dossier || {};
  const eq = ds.equity || {};

  return (
    <div>
      <Button type="link" onClick={() => nav(-1)} style={{ paddingLeft: 0 }}>← Back</Button>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 4 }}>
        <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 28, margin: 0, color: "#1c1e2a" }}>
          {ds.canonical_address || propertyId}
        </h2>
        {ds.is_david && <Tag color="red">David network</Tag>}
        {d.finding_counts?.critical > 0 && <Tag color="red">{d.finding_counts.critical} critical</Tag>}
      </div>
      <div style={{ color: "#5b5f6e", marginBottom: 18, fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>
        parcel {ds.parcel_id || "—"} · {ds.county || ""}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 18 }}>
        <Card size="small" title="Dossier" style={{ background: "#fdfbf6", borderColor: "#e7e2d6" }}>
          <Descriptions column={1} size="small" colon
            items={[
              { label: "Owner(s)", children: (ds.owners || []).map(o => o.name).join(", ") || "—" },
              { label: "Title reports", children: `${ds.title?.count || 0} (latest ${ds.title?.latest_date || "?"}, ${ds.title?.latest_vendor || ""})` },
              { label: "Insurance", children: ds.insurance?.in_force ? `In force — ${(ds.insurance.insurers || []).join(", ")}` : "None on file" },
              { label: "Equity", children: money(eq.equity) },
              { label: "Market value", children: money(eq.mkt_value) },
              { label: "Mortgage", children: money(eq.mortgage_amount) },
              { label: "Lender", children: eq.lender || "—" },
              { label: "Foreclosure", children: eq.active_foreclosure || "—" },
              { label: "Lis pendens", children: eq.lis_pendens || "—" },
            ]} />
          <div style={{ marginTop: 12, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button type="primary" onClick={exportPacketPdf}>⬇ Evidence packet (PDF)</Button>
            <Button onClick={exportPacket}>⬇ Evidence packet (JSON)</Button>
          </div>
        </Card>

        <Card size="small" title={`Findings (${d.findings?.length || 0})`}
          style={{ background: "#fdfbf6", borderColor: "#e7e2d6" }}>
          {(d.findings || []).length === 0 && <span style={{ color: "#5b5f6e" }}>No findings.</span>}
          {(d.findings || []).map((f) => (
            <div key={f.id} style={{ marginBottom: 10, paddingBottom: 10, borderBottom: "1px solid #efe9dc" }}>
              <Tag color={SEV_COLOR[f.severity]}>{f.severity}</Tag>
              <span style={{ fontWeight: 600 }}>{f.title}</span>
              <div style={{ fontSize: 13, color: "#3a3d4a", marginTop: 4 }}>{f.detail}</div>
              {(f.evidence || [])[0]?.quote && (
                <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontStyle: "italic",
                  fontSize: 13, color: "#5b5f6e", marginTop: 4 }}>“{f.evidence[0].quote}”</div>)}
            </div>
          ))}
        </Card>
      </div>

      <Tabs style={{ marginTop: 20 }} items={[
        { key: "tl", label: `Timeline (${d.timeline?.length || 0})`, children: (
          <Card size="small" style={{ background: "#fdfbf6", borderColor: "#e7e2d6" }}>
            <Timeline mode="left" items={(d.timeline || []).map((e) => ({
              color: EVENT_COLOR[e.event_type] || "#234a52",
              label: <span style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 12 }}>{e.date}</span>,
              children: (
                <div>
                  <Tag>{e.event_type}</Tag>
                  <span style={{ fontWeight: 600 }}>{e.detail}</span>
                  {e.amount && <Tag color="gold" style={{ marginLeft: 6 }}>{e.amount}</Tag>}
                  {e.source_quote && <div style={{ fontFamily: "'Instrument Serif',Georgia,serif",
                    fontStyle: "italic", fontSize: 13, color: "#5b5f6e", marginTop: 2 }}>“{e.source_quote.slice(0, 160)}”</div>}
                </div>) }))} />
          </Card>) },
        { key: "fof", label: "Flow of funds", children: (
          <Card size="small" style={{ background: "#fdfbf6", borderColor: "#e7e2d6" }}>
            <p style={{ color: "#5b5f6e" }}>
              {d.flow_of_funds?.n_events || 0} monetary events · total seen{" "}
              <b>${(d.flow_of_funds?.total_amount_seen || 0).toLocaleString()}</b>
            </p>
            <Timeline items={(d.flow_of_funds?.flows || []).filter(f => f.amount).map((f) => ({
              color: EVENT_COLOR[f.type] || "#234a52",
              children: <span><b>${(f.amount).toLocaleString()}</b> · {f.type} ·{" "}
                <span style={{ color: "#5b5f6e" }}>{f.date}</span> — {f.detail}</span> }))} />
          </Card>) },
      ]} />
    </div>
  );
}