import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Tag, Input, Segmented, Spin, Statistic, Card, Tooltip, Button, message } from "antd";
import { getProperties, getDashboard, portfolioCell } from "./api";

const money = (v) => (v == null || v === "" ? "—" :
  (typeof v === "number" ? "$" + v.toLocaleString() : String(v)));

export default function PortfolioGrid() {
  const nav = useNavigate();
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [scope, setScope] = useState("All");
  const [adhoc, setAdhoc] = useState([]); // [{question, cells:{pid:{status,answer,basis}}}]

  const addColumn = async (question) => {
    question = (question || "").trim();
    if (!question) return;
    const col = { question, cells: {} };
    setAdhoc((c) => [...c, col]);
    const idx = adhoc.length;
    message.info(`Computing "${question}" for ${rows.length} properties…`);
    // progressive map-reduce (cached server-side); cap concurrency at ~4
    const queue = [...rows];
    const worker = async () => {
      while (queue.length) {
        const r = queue.shift();
        try {
          const res = await portfolioCell(r.property_id, question);
          setAdhoc((cols) => cols.map((c, i) => i === idx
            ? { ...c, cells: { ...c.cells, [r.property_id]: res.data } } : c));
        } catch {
          setAdhoc((cols) => cols.map((c, i) => i === idx
            ? { ...c, cells: { ...c.cells, [r.property_id]: { status: "error", answer: "—" } } } : c));
        }
      }
    };
    await Promise.all([worker(), worker(), worker(), worker()]);
    message.success("Column complete");
  };

  useEffect(() => { getDashboard().then(r => setStats(r.data)).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true);
    const params = { limit: 1000 };
    if (scope === "David") params.is_david = true;
    if (q) params.q = q;
    getProperties(params)
      .then(r => setRows(r.data.rows))
      .finally(() => setLoading(false));
  }, [q, scope]);

  const columns = [
    { title: "Property", dataIndex: "address", key: "address", fixed: "left", width: 280,
      render: (v, r) => (
        <a onClick={() => nav(`/properties/${r.property_id}`)}
           style={{ color: "#234a52", fontWeight: 600 }}>{v || r.property_id}</a>) },
    { title: "Owner(s)", dataIndex: "owners", key: "owners", width: 220,
      render: (o) => (o || []).slice(0, 2).map((n, i) =>
        <Tag key={i} color="default" style={{ marginBottom: 2 }}>{n}</Tag>) },
    { title: "Side", dataIndex: "side", key: "side", width: 130,
      filters: [{ text: "David", value: "david_network" }, { text: "Third party", value: "third_party" },
                { text: "Co-victim", value: "co_victim" }, { text: "Ours", value: "our_side" }],
      onFilter: (val, r) => r.side === val,
      render: (s) => <Tag color={s === "david_network" ? "red" : s === "co_victim" ? "blue" :
        s === "our_side" ? "green" : "default"}>{(s || "unknown").replace("_", " ")}</Tag> },
    { title: "Title", dataIndex: "title_count", key: "title", width: 90, align: "center",
      sorter: (a, b) => a.title_count - b.title_count,
      render: (n, r) => <Tooltip title={`latest ${r.latest_title_date || "?"}`}>{n}</Tooltip> },
    { title: "Insurance", dataIndex: "insurance_in_force", key: "ins", width: 110, align: "center",
      render: (v) => v ? <Tag color="green">in force</Tag> : <Tag>none</Tag> },
    { title: "Equity", dataIndex: "equity", key: "equity", width: 130, align: "right",
      sorter: (a, b) => (a.equity || 0) - (b.equity || 0), render: money },
    { title: "Mortgage", dataIndex: "mortgage_amount", key: "mort", width: 130, align: "right", render: money },
    { title: "Foreclosure", dataIndex: "active_foreclosure", key: "fc", width: 120,
      render: (v) => v && String(v).toLowerCase().includes("yes")
        ? <Tag color="volcano">{v}</Tag> : (v ? <Tag>{v}</Tag> : "—") },
    { title: "Litigation", dataIndex: "litigation_count", key: "lit", width: 100, align: "center",
      render: (n) => n ? <Tag color="purple">{n}</Tag> : "—" },
    { title: "Facts", dataIndex: "fact_counts", key: "facts", width: 220,
      render: (fc, r) => {
        if (!fc) return "—";
        const scoped = r.fact_counts_scoped || {};
        const parts = [["chain_of_title", "deeds"], ["mortgages", "mtg"], ["liens", "liens"],
                       ["judgments", "judg"], ["lis_pendens", "lis"]];
        return parts.filter(([k]) => fc[k]).map(([k, lbl]) => {
          const sc = scoped[k];
          // For encumbrances we know current-vs-prior: show current-era count
          // (with the cumulative total + prior-owner split in the tooltip) so
          // a high historical total doesn't read as a current liability.
          if (sc) {
            const cur = sc.current_owner_era || 0;
            const tip = `${fc[k]} total recorded · ${cur} current-owner era · ` +
              `${sc.prior_owner || 0} prior-owner · ${sc.undated || 0} undated` +
              (r.current_owner_since ? ` (owner since ${r.current_owner_since})` : "");
            return <Tooltip key={k} title={tip}>
              <Tag color={cur ? "volcano" : "default"} style={{ marginBottom: 2 }}>
                {lbl}:{cur}<span style={{ opacity: 0.5 }}>/{fc[k]}</span>
              </Tag></Tooltip>;
          }
          return <Tag key={k} style={{ marginBottom: 2 }}>{lbl}:{fc[k]}</Tag>;
        }); } },
  ];

  const adhocColumns = adhoc.map((col, i) => ({
    title: <Tooltip title={col.question}>{`❓ ${col.question.slice(0, 22)}${col.question.length > 22 ? "…" : ""}`}</Tooltip>,
    key: `adhoc${i}`, width: 240,
    render: (_, r) => {
      const cell = col.cells[r.property_id];
      if (!cell) return <Spin size="small" />;
      if (cell.status === "error") return <span style={{ color: "#b4441f" }}>—</span>;
      return <Tooltip title={cell.basis || ""}><span style={{ fontSize: 13 }}>{cell.answer}</span></Tooltip>;
    },
  }));
  const allColumns = [...columns, ...adhocColumns];

  return (
    <div>
      <h2 style={{ fontFamily: "'Instrument Serif',Georgia,serif", fontSize: 28, color: "#1c1e2a", margin: "0 0 16px" }}>
        Property Portfolio
      </h2>
      {stats && (
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginBottom: 18 }}>
          <StatCard label="Properties" value={stats.property_dossiers} />
          <StatCard label="David-network" value={stats.entities?.david} accent="#b4441f" />
          <StatCard label="Findings" value={stats.findings?.total}
            sub={`${stats.findings?.by_severity?.critical || 0} critical`} accent="#b4441f" />
          <StatCard label="Dated events" value={stats.events?.total} />
          <StatCard label="Documents" value={stats.documents?.total} />
          <StatCard label="Linked chunks" value={stats.chunks?.linked} />
        </div>
      )}
      <div style={{ display: "flex", gap: 12, marginBottom: 12, alignItems: "center" }}>
        <Segmented value={scope} onChange={setScope} options={["David", "All"]} />
        <Input.Search placeholder="Search address…" allowClear style={{ maxWidth: 280 }}
          onSearch={setQ} onChange={(e) => !e.target.value && setQ("")} />
        <Input.Search placeholder='Ask a column, e.g. "Is it in foreclosure?"' enterButton="+ Column"
          style={{ maxWidth: 380 }} onSearch={addColumn} />
        <span style={{ color: "#5b5f6e", fontSize: 13 }}>{rows.length} properties</span>
      </div>
      {loading ? <Spin /> : (
        <Table rowKey="property_id" columns={allColumns} dataSource={rows} size="small"
          scroll={{ x: 1500 }} pagination={{ pageSize: 25, showSizeChanger: true }}
          style={{ background: "#fff", borderRadius: 8 }} />
      )}
    </div>
  );
}

function StatCard({ label, value, sub, accent }) {
  return (
    <Card size="small" style={{ minWidth: 150, background: "#fdfbf6", borderColor: "#e7e2d6" }}>
      <Statistic title={label} value={value ?? "—"}
        valueStyle={{ color: accent || "#234a52", fontWeight: 700 }} />
      {sub && <div style={{ fontSize: 12, color: "#b4441f", marginTop: 2 }}>{sub}</div>}
    </Card>
  );
}