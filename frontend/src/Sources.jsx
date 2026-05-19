import { useState } from "react";
import { Collapse, Tag, Typography } from "antd";
import { PaperClipOutlined, MailOutlined, CalendarOutlined, UserOutlined } from "@ant-design/icons";

const { Text } = Typography;

export default function Sources({ items }) {
  if (!items || items.length === 0) return null;

  const collapseItems = [
    {
      key: "1",
      label: (
        <span style={styles.collapseLabel}>
          <span style={styles.sourceCount}>{items.length}</span>
          Sources cited
        </span>
      ),
      children: (
        <div style={styles.grid}>
          {items.map(s => (
            <div key={s.index} style={styles.sourceCard}>
              <div style={styles.cardHeader}>
                <Tag
                  icon={s.type === "attachment" ? <PaperClipOutlined /> : <MailOutlined />}
                  style={{
                    ...styles.typeTag,
                    background: s.type === "attachment" ? "#eef0fb" : "#edf8f2",
                    color: s.type === "attachment" ? "#6574c4" : "#3a8c5c",
                    borderColor: s.type === "attachment" ? "#d4d9f0" : "#b7e4c7",
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
                      {s.from_email}
                    </span>
                  )}
                  {s.page && <span style={styles.metaItem}>{s.page}</span>}
                </div>
              )}
            </div>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div style={styles.wrap}>
      <Collapse
        ghost
        size="small"
        items={collapseItems}
        style={styles.collapse}
      />
    </div>
  );
}

const styles = {
  wrap: {
    marginTop: 14,
    borderTop: "1px solid #ebedf5",
    paddingTop: 10,
  },
  collapse: {
    background: "transparent",
  },
  collapseLabel: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 12,
    color: "#8892b0",
    fontWeight: 500,
  },
  sourceCount: {
    background: "#eef0fb",
    color: "#6574c4",
    borderRadius: 10,
    padding: "1px 7px",
    fontSize: 11,
    fontWeight: 600,
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: 8,
    paddingTop: 4,
  },
  sourceCard: {
    background: "#fafbfe",
    border: "1px solid #ebedf5",
    borderRadius: 8,
    padding: "10px 12px",
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 6,
    flexWrap: "wrap",
  },
  typeTag: {
    borderRadius: 4,
    fontSize: 11,
    fontWeight: 500,
    lineHeight: "20px",
    margin: 0,
  },
  indexLabel: {
    fontSize: 11,
    fontWeight: 700,
    color: "#6574c4",
    fontFamily: "monospace",
  },
  score: {
    fontSize: 10,
    color: "#c5c9dc",
    marginLeft: "auto",
  },
  cardTitle: {
    fontSize: 12,
    fontWeight: 500,
    color: "#2d3152",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    marginBottom: 4,
  },
  cardMeta: {
    display: "flex",
    flexWrap: "wrap",
    gap: "4px 10px",
  },
  metaItem: {
    fontSize: 11,
    color: "#b0b6cc",
    display: "flex",
    alignItems: "center",
  },
};
