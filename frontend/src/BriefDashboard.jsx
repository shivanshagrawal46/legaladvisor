import { useEffect, useState } from "react";
import { Card, Tag, Spin, Empty, List, Typography, Button, Space, message } from "antd";
import { getBrief } from "./api";

const { Title, Text, Paragraph } = Typography;

// The Insight Engine's Daily Brief, surfaced in-app: approaching deadlines,
// what's waiting on us, recent arrivals, pending-findings summary, and the
// prioritized "questions you should ask next".
export default function BriefDashboard() {
  const [brief, setBrief] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    getBrief()
      .then(r => setBrief(r.data))
      .catch(() => message.error("Could not load the brief (is the backend running?)"))
      .finally(() => setLoading(false));
  };
  useEffect(load, []);

  if (loading) return <div style={{ padding: 48, textAlign: "center" }}><Spin size="large" /></div>;
  if (!brief) return <Empty description="No brief available" style={{ marginTop: 64 }} />;

  const daysColor = (d) => (d <= 3 ? "red" : d <= 7 ? "volcano" : "gold");

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: "24px 16px" }}>
      <Space style={{ justifyContent: "space-between", width: "100%", marginBottom: 8 }}>
        <Title level={3} style={{ margin: 0, color: "#234a52" }}>Daily Brief</Title>
        <Space>
          <Text type="secondary">as of {brief.as_of}</Text>
          <Button size="small" onClick={load}>Refresh</Button>
        </Space>
      </Space>
      <Paragraph type="secondary" style={{ marginTop: 0 }}>
        What the investigation should look at — surfaced automatically, no question needed.
      </Paragraph>

      <Card title="Questions you should ask next" style={{ marginBottom: 16 }}
            headStyle={{ background: "#f6faf9" }}>
        <List
          size="small"
          dataSource={brief.questions || []}
          locale={{ emptyText: "No prioritized questions right now." }}
          renderItem={(q, i) => <List.Item>{i + 1}. {q}</List.Item>}
        />
      </Card>

      <Card title={`Approaching deadlines (next ${brief.deadline_days} days)`} style={{ marginBottom: 16 }}>
        <List
          size="small"
          dataSource={brief.deadlines || []}
          locale={{ emptyText: "No deadlines detected in window." }}
          renderItem={(d) => (
            <List.Item>
              <Space>
                <Tag color={daysColor(d.days_out)}>{d.when} · {d.days_out}d</Tag>
                <Text strong>{d.consequence}</Text>
                <Text type="secondary">{d.sentence}</Text>
              </Space>
            </List.Item>
          )}
        />
      </Card>

      <Card title={`Waiting on us (${(brief.open_loops || []).length})`} style={{ marginBottom: 16 }}>
        <List
          size="small"
          dataSource={brief.open_loops || []}
          locale={{ emptyText: "Nothing waiting on us." }}
          renderItem={(f) => <List.Item>{f.title}</List.Item>}
        />
      </Card>

      <Card title={`New arrivals (last ${brief.arrival_days} days)`}>
        <List
          size="small"
          dataSource={brief.arrivals || []}
          locale={{ emptyText: "No new arrivals." }}
          renderItem={(e) => (
            <List.Item>
              <Text type="secondary" style={{ marginRight: 8 }}>{e.date}</Text>
              <Text>{e.subject}</Text>
              <Text type="secondary" style={{ marginLeft: 8 }}>· {e.from}</Text>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
}
