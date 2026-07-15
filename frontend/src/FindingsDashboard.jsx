import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Segmented, Button, Drawer, Spin, message, Space } from "antd";
import { getFindings, setFindingStatus } from "./api";

const SEV_COLOR = { critical: "red", high: "volcano", medium: "gold", info: "default" };
const TYPE_LABEL = {
  voidable_transfer: "Voidable transfer", anachronism: "Backdating",
  contradiction: "Contradiction", omission: "Omission", encumbrance: "Encumbrance",
  money_conflict: "Money conflict", open_loop: "Open loop (awaiting us)",
  quoted_alteration: "Altered quoted copy",
  llc_timing: "Shell-timing (LLC vs transfer)",
  insurance_cancellation: "Insurance cancelled",
  insurance_insured_change: "Insured changed (MangoTree?)",
  insurance_insurer_change: "Insurer changed",
};

export default function FindingsDashboard() {
  const nav = useNavigate();
  const [data, setData] = useState({ items: [], facets: {} });
  const [loading, setLoading] = useState(true);
  const [sev, setSev] = useState("all");
  const [active, setActive] = useState(null);

  const load = () => {
    setLoading(true);
    const p = {}; if (sev !== "all") p.severity = sev;
    getFindings(p).then(r => setData(r.data)).finally(() => setLoading(false));
  };
  useEffect(load, [sev]);

  const review = async (id, status) => {
    try { await setFindingStatus(id, status); message.success(`Marked ${status}`); load(); }
    catch { message.error("Failed"); }
  };

  const bySev = data.facets?.by_severity || {};
  const columns = [
    { title: "Severity", dataIndex: "severity", width: 110,
      render: (s) => <Tag color={SEV_COLOR[s] || "default"} style={{ fontWeight: 600 }}>{s}</Tag> },
    { title: "Type", dataIndex: "finding_type", width: 150,
      render: (t) => <Tag>{TYPE_LABEL[t] || t}</Tag> },
    { title: "Finding", dataIndex: "title",
      render: (t, r) => <a onClick={() => setActive(r)} style={{ color: "#1c1e2a", fontWeight: 600 }}>{t}</a> },
    { title: "Property", dataIndex: "property_address", width: 220,
      render: (a, r) => a ? <a onClick={() => nav(`/properties/${r.property_id}`)}
        style={{ color: "#234a52" }}>{a}</a> : "—" },
    { title: "Status", dataIndex: "status", width: 110,
      render: (s) => <Tag color={s === "confirmed" ? "green" : s === "rejected" ? "default" : "blue"}>{s}</Tag> },
    { title: "Review", key: "review", width: 170, render: (_, r) => (
      <Space size={4}>
        <Button size="small" type="primary" ghost onClick={() => review(r.id, "confirmed")}>Confirm</Button>
        <Button size="small" onClick={() => review(r.id, "rejected")}>Reject</Button>
      </Space>) },
  ];

  return (
    <div>
      <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 28, color: "#1c1e2a", margin: "0 0 8px" }}>
        Fraud Findings
      </h2>
      <p style={{ color: "#5b5f6e", marginTop: 0 }}>
        Detector output — voidable transfers (UFTA/NY-DCL), backdating, contradictions — each with a verbatim source quote.
      </p>
      <div style={{ marginBottom: 14 }}>
        <Segmented value={sev} onChange={setSev} options={[
          { label: "All", value: "all" },
          { label: `Critical (${bySev.critical || 0})`, value: "critical" },
          { label: `High (${bySev.high || 0})`, value: "high" },
          { label: `Medium (${bySev.medium || 0})`, value: "medium" },
        ]} />
      </div>
      {loading ? <Spin /> : (
        <Table rowKey="id" columns={columns} dataSource={data.items} size="small"
          pagination={{ pageSize: 20 }} style={{ background: "#fff", borderRadius: 8 }} />
      )}
      <Drawer width={560} open={!!active} onClose={() => setActive(null)}
        title={active?.title} styles={{ body: { background: "#fdfbf6" } }}>
        {active && (
          <div>
            <Space style={{ marginBottom: 12 }}>
              <Tag color={SEV_COLOR[active.severity]}>{active.severity}</Tag>
              <Tag>{TYPE_LABEL[active.finding_type] || active.finding_type}</Tag>
              <Tag color="blue">confidence {Math.round((active.confidence || 0) * 100)}%</Tag>
            </Space>
            <p style={{ fontSize: 15, lineHeight: 1.6, color: "#1c1e2a" }}>{active.detail}</p>
            <h4 style={{ marginTop: 18, color: "#234a52" }}>Evidence (verbatim)</h4>
            {(active.evidence || []).map((e, i) => (
              <div key={i} style={{ background: "#fff", border: "1px solid #e7e2d6", borderRadius: 6,
                padding: 12, marginBottom: 10 }}>
                <div style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 15,
                  fontStyle: "italic", color: "#2b2e3a" }}>“{e.quote || "—"}”</div>
                <div style={{ fontFamily: "'JetBrains Mono',monospace", fontSize: 11,
                  color: "#5b5f6e", marginTop: 6 }}>{e.doc_id}{e.note ? ` · ${e.note}` : ""}</div>
              </div>
            ))}
            <Space style={{ marginTop: 12 }}>
              <Button type="primary" ghost onClick={() => { review(active.id, "confirmed"); setActive(null); }}>Confirm</Button>
              <Button onClick={() => { review(active.id, "rejected"); setActive(null); }}>Reject</Button>
              {active.property_id && <Button type="link"
                onClick={() => nav(`/properties/${active.property_id}`)}>Open property →</Button>}
            </Space>
          </div>
        )}
      </Drawer>
    </div>
  );
}