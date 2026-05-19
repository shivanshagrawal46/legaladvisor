import { useState } from "react";
import { Button, Tooltip, Modal, Typography, Badge } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  LogoutOutlined,
  ScissorOutlined,
} from "@ant-design/icons";
import { deleteSession } from "./api";

const { Text } = Typography;

function formatDate(iso) {
  const d = new Date(iso);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function Sidebar({ sessions, activeId, onSelect, onNew, onDelete, userName }) {
  const [deletingId, setDeletingId] = useState(null);

  function confirmDelete(e, id) {
    e.stopPropagation();
    Modal.confirm({
      title: "Delete conversation?",
      content: "This cannot be undone.",
      okText: "Delete",
      okType: "danger",
      cancelText: "Cancel",
      centered: true,
      icon: <DeleteOutlined />,
      onOk: async () => {
        setDeletingId(id);
        try {
          await deleteSession(id);
          onDelete(id);
        } catch (_) {}
        setDeletingId(null);
      },
    });
  }

  const initials = (userName || "R").split(" ").map(w => w[0]).join("").toUpperCase().slice(0, 2);

  return (
    <aside style={styles.aside}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.brand}>
          <div style={styles.brandIcon}>⚖️</div>
          <div>
            <div style={styles.brandName}>Legal Advisor</div>
            <div style={styles.brandSub}>Fraud Investigation</div>
          </div>
        </div>
        <Tooltip title="New conversation" placement="right">
          <Button
            type="text"
            icon={<PlusOutlined />}
            onClick={onNew}
            style={styles.newBtn}
          />
        </Tooltip>
      </div>

      {/* Sessions */}
      <div style={styles.sectionLabel}>
        <MessageOutlined style={{ fontSize: 10, marginRight: 5 }} />
        CONVERSATIONS
        {sessions.length > 0 && (
          <span style={styles.countBadge}>{sessions.length}</span>
        )}
      </div>

      <div style={styles.listWrap}>
        {sessions.length === 0 && (
          <div style={styles.emptyState}>
            <MessageOutlined style={{ fontSize: 20, color: "#c5c9dc", marginBottom: 8 }} />
            <Text style={{ color: "#b0b6cc", fontSize: 12 }}>No conversations yet</Text>
          </div>
        )}
        {sessions.map(s => (
          <div
            key={s.session_id}
            className="session-item"
            style={{
              ...styles.item,
              ...(s.session_id === activeId ? styles.itemActive : {}),
            }}
            onClick={() => onSelect(s.session_id)}
          >
            <div style={styles.itemIcon}>
              <MessageOutlined style={{ fontSize: 12, color: s.session_id === activeId ? "#6574c4" : "#b0b6cc" }} />
            </div>
            <div style={styles.itemContent}>
              <div style={styles.itemTitle}>{s.title || "New conversation"}</div>
              <div style={styles.itemMeta}>{formatDate(s.updated_at)}</div>
            </div>
            <Tooltip title="Delete" placement="right">
              <Button
                type="text"
                size="small"
                icon={<DeleteOutlined />}
                loading={deletingId === s.session_id}
                onClick={e => confirmDelete(e, s.session_id)}
                style={styles.deleteBtn}
              />
            </Tooltip>
          </div>
        ))}
      </div>

      {/* User footer */}
      <div style={styles.userFooter}>
        <div style={styles.userAvatar}>{initials}</div>
        <div style={styles.userInfo}>
          <div style={styles.userName}>{userName || "User"}</div>
          <Text style={styles.userEmail}>{localStorage.getItem("user_email") || ""}</Text>
        </div>
        <Tooltip title="Sign out" placement="top">
          <Button
            type="text"
            size="small"
            icon={<LogoutOutlined />}
            style={styles.logoutBtn}
            onClick={() => { localStorage.clear(); window.location.reload(); }}
          />
        </Tooltip>
      </div>
    </aside>
  );
}

const styles = {
  aside: {
    width: 268,
    minWidth: 268,
    background: "#ffffff",
    borderRight: "1px solid #ebedf5",
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
    boxShadow: "1px 0 0 #ebedf5",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "18px 16px 14px",
    borderBottom: "1px solid #f0f2f9",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 10,
  },
  brandIcon: {
    width: 34,
    height: 34,
    borderRadius: 8,
    background: "linear-gradient(135deg, #eef0fb, #e4e7f8)",
    border: "1px solid rgba(101,116,196,0.15)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
  },
  brandName: {
    fontWeight: 700,
    fontSize: 14,
    color: "#1a1d2e",
    lineHeight: 1.3,
  },
  brandSub: {
    fontSize: 10,
    color: "#b0b6cc",
    letterSpacing: "0.02em",
  },
  newBtn: {
    color: "#6574c4",
    borderRadius: 8,
    width: 32,
    height: 32,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  sectionLabel: {
    padding: "14px 16px 8px",
    fontSize: 10,
    fontWeight: 600,
    color: "#b0b6cc",
    letterSpacing: "0.08em",
    display: "flex",
    alignItems: "center",
  },
  countBadge: {
    marginLeft: "auto",
    background: "#f0f2f9",
    color: "#8892b0",
    borderRadius: 10,
    padding: "1px 7px",
    fontSize: 10,
    fontWeight: 600,
  },
  listWrap: {
    flex: 1,
    overflowY: "auto",
    padding: "4px 8px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "32px 16px",
    opacity: 0.7,
  },
  item: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    borderRadius: 8,
    padding: "9px 10px",
    marginBottom: 2,
    cursor: "pointer",
    transition: "background 0.15s",
    position: "relative",
  },
  itemActive: {
    background: "#eef0fb",
  },
  itemIcon: {
    width: 26,
    height: 26,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  },
  itemContent: {
    flex: 1,
    minWidth: 0,
  },
  itemTitle: {
    fontSize: 13,
    fontWeight: 500,
    color: "#2d3152",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  itemMeta: {
    fontSize: 11,
    color: "#b0b6cc",
    marginTop: 1,
  },
  deleteBtn: {
    opacity: 0.4,
    color: "#8892b0",
    flexShrink: 0,
    width: 24,
    height: 24,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 0,
    fontSize: 11,
  },
  userFooter: {
    padding: "12px 14px",
    borderTop: "1px solid #f0f2f9",
    display: "flex",
    alignItems: "center",
    gap: 10,
    background: "#fafbfe",
  },
  userAvatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #6574c4, #8b6cc8)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#fff",
    fontWeight: 700,
    fontSize: 12,
    flexShrink: 0,
    boxShadow: "0 2px 6px rgba(101,116,196,0.3)",
  },
  userInfo: {
    flex: 1,
    minWidth: 0,
  },
  userName: {
    fontSize: 13,
    fontWeight: 600,
    color: "#2d3152",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  userEmail: {
    fontSize: 10,
    color: "#b0b6cc",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    display: "block",
  },
  logoutBtn: {
    color: "#b0b6cc",
    flexShrink: 0,
  },
};
