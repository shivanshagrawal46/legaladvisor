import { useState, useMemo, useRef, useEffect } from "react";
import { Button, Tooltip, Modal, Typography, Input, message } from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  LogoutOutlined,
  EditOutlined,
  SearchOutlined,
  CheckOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import { deleteSession, renameSession } from "./api";

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

export default function Sidebar({ sessions, activeId, onSelect, onNew, onDelete, onRename, userName }) {
  const [deletingId, setDeletingId] = useState(null);
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editValue, setEditValue] = useState("");
  const [savingId, setSavingId] = useState(null);
  const editRef = useRef(null);

  useEffect(() => {
    if (editingId && editRef.current) {
      editRef.current.focus({ cursor: "all" });
    }
  }, [editingId]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sessions;
    return sessions.filter(s =>
      (s.title || "New conversation").toLowerCase().includes(q)
    );
  }, [sessions, query]);

  function startEdit(e, s) {
    e.stopPropagation();
    setEditingId(s.session_id);
    setEditValue(s.title || "");
  }

  function cancelEdit(e) {
    if (e) e.stopPropagation();
    setEditingId(null);
    setEditValue("");
  }

  async function saveEdit(e, id) {
    if (e) e.stopPropagation();
    const title = editValue.trim();
    if (!title) { cancelEdit(); return; }
    setSavingId(id);
    try {
      await renameSession(id, title);
      onRename?.(id, title.slice(0, 80));
      setEditingId(null);
      setEditValue("");
    } catch (_) {
      message.error("Could not rename conversation");
    }
    setSavingId(null);
  }

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
            className="newchat-btn"
            icon={<PlusOutlined />}
            onClick={onNew}
            style={styles.newBtn}
          />
        </Tooltip>
      </div>

      {/* Search */}
      <div style={styles.searchWrap}>
        <Input
          allowClear
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search conversations"
          prefix={<SearchOutlined style={{ color: "var(--muted-2)", fontSize: 13 }} />}
          style={styles.searchInput}
        />
      </div>

      {/* Sessions */}
      <div style={styles.sectionLabel}>
        <span style={styles.sectionLabelText}>Conversations</span>
        {sessions.length > 0 && (
          <span className="mono" style={styles.countBadge}>
            {query.trim() ? `${filtered.length}/${sessions.length}` : sessions.length}
          </span>
        )}
      </div>

      <div style={styles.listWrap}>
        {sessions.length === 0 && (
          <div style={styles.emptyState}>
            <MessageOutlined style={{ fontSize: 20, color: "var(--t5)", marginBottom: 8 }} />
            <Text style={{ color: "var(--muted-2)", fontSize: 12 }}>No conversations yet</Text>
          </div>
        )}
        {sessions.length > 0 && filtered.length === 0 && (
          <div style={styles.emptyState}>
            <SearchOutlined style={{ fontSize: 18, color: "var(--t5)", marginBottom: 8 }} />
            <Text style={{ color: "var(--muted-2)", fontSize: 12 }}>No matches</Text>
          </div>
        )}
        {filtered.map(s => {
          const isEditing = editingId === s.session_id;
          return (
          <div
            key={s.session_id}
            className="session-item"
            style={{
              ...styles.item,
              ...(s.session_id === activeId ? styles.itemActive : {}),
            }}
            onClick={() => { if (!isEditing) onSelect(s.session_id); }}
          >
            <div style={styles.itemIcon}>
              <MessageOutlined style={{ fontSize: 12, color: s.session_id === activeId ? "var(--river)" : "var(--muted-2)" }} />
            </div>
            <div style={styles.itemContent}>
              {isEditing ? (
                <Input
                  ref={editRef}
                  size="small"
                  value={editValue}
                  maxLength={80}
                  onClick={e => e.stopPropagation()}
                  onChange={e => setEditValue(e.target.value)}
                  onPressEnter={e => saveEdit(e, s.session_id)}
                  onKeyDown={e => { if (e.key === "Escape") cancelEdit(e); }}
                  style={styles.editInput}
                />
              ) : (
                <>
                  <div style={styles.itemTitle}>{s.title || "New conversation"}</div>
                  <div style={styles.itemMeta} className="mono">{formatDate(s.updated_at)}</div>
                </>
              )}
            </div>
            {isEditing ? (
              <div style={styles.editActions} onClick={e => e.stopPropagation()}>
                <Button
                  type="text"
                  size="small"
                  icon={<CheckOutlined />}
                  loading={savingId === s.session_id}
                  onClick={e => saveEdit(e, s.session_id)}
                  style={styles.editBtn}
                />
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={cancelEdit}
                  style={styles.editBtn}
                />
              </div>
            ) : (
              <div style={styles.itemActions}>
                <Tooltip title="Rename" placement="top">
                  <Button
                    type="text"
                    size="small"
                    className="session-del"
                    icon={<EditOutlined />}
                    onClick={e => startEdit(e, s)}
                    style={styles.deleteBtn}
                  />
                </Tooltip>
                <Tooltip title="Delete" placement="top">
                  <Button
                    type="text"
                    size="small"
                    className="session-del"
                    icon={<DeleteOutlined />}
                    loading={deletingId === s.session_id}
                    onClick={e => confirmDelete(e, s.session_id)}
                    style={styles.deleteBtn}
                  />
                </Tooltip>
              </div>
            )}
          </div>
          );
        })}
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
    width: 320,
    minWidth: 320,
    background: "var(--surface-2)",
    borderRight: "1px solid var(--hair)",
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "20px 18px 18px",
    borderBottom: "1px solid var(--hair)",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 11,
  },
  brandIcon: {
    width: 34,
    height: 34,
    borderRadius: "var(--r-sm)",
    background: "var(--surface)",
    border: "1px solid var(--hair)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: 16,
  },
  brandName: {
    fontWeight: 600,
    fontSize: 14.5,
    color: "var(--ink)",
    lineHeight: 1.25,
    letterSpacing: "-0.005em",
  },
  brandSub: {
    fontSize: 9.5,
    color: "var(--muted-2)",
    letterSpacing: "0.16em",
    textTransform: "uppercase",
    fontWeight: 600,
    marginTop: 3,
  },
  newBtn: {
    color: "var(--brand)",
    borderRadius: "var(--r-sm)",
    width: 32,
    height: 32,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  searchWrap: {
    padding: "12px 16px 4px",
  },
  searchInput: {
    borderRadius: "var(--r-sm)",
    background: "var(--surface)",
    fontSize: 13,
  },
  sectionLabel: {
    padding: "14px 20px 10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  },
  sectionLabelText: {
    fontSize: 10,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    color: "var(--muted-2)",
  },
  countBadge: {
    background: "transparent",
    color: "var(--muted-2)",
    padding: "1px 0",
    fontSize: 10.5,
    fontWeight: 600,
  },
  listWrap: {
    flex: 1,
    overflowY: "auto",
    padding: "2px 10px 8px",
  },
  emptyState: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "40px 16px",
    opacity: 0.7,
  },
  item: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    borderRadius: "var(--r-sm)",
    padding: "9px 11px",
    marginBottom: 1,
    cursor: "pointer",
    position: "relative",
  },
  itemActive: {
    background: "var(--surface)",
    border: "1px solid var(--hair)",
    boxShadow: "var(--sh-sm)",
  },
  itemIcon: {
    width: 22,
    height: 22,
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
    color: "var(--t1)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  itemMeta: {
    fontSize: 11,
    color: "var(--muted-2)",
    marginTop: 2,
  },
  itemActions: {
    display: "flex",
    alignItems: "center",
    gap: 2,
    flexShrink: 0,
  },
  editActions: {
    display: "flex",
    alignItems: "center",
    gap: 2,
    flexShrink: 0,
  },
  deleteBtn: {
    color: "var(--muted-2)",
    flexShrink: 0,
    width: 22,
    height: 22,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 0,
    fontSize: 11,
  },
  editBtn: {
    color: "var(--muted-2)",
    flexShrink: 0,
    width: 22,
    height: 22,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 0,
    fontSize: 11,
  },
  editInput: {
    fontSize: 13,
    padding: "2px 6px",
    borderRadius: "var(--r-sm)",
  },
  userFooter: {
    padding: "14px 16px",
    borderTop: "1px solid var(--hair)",
    display: "flex",
    alignItems: "center",
    gap: 11,
    background: "var(--paper)",
  },
  userAvatar: {
    width: 32,
    height: 32,
    borderRadius: "50%",
    background: "var(--brand)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#f8f5ee",
    fontWeight: 600,
    fontSize: 12,
    flexShrink: 0,
    letterSpacing: "0.03em",
  },
  userInfo: {
    flex: 1,
    minWidth: 0,
  },
  userName: {
    fontSize: 13,
    fontWeight: 600,
    color: "var(--ink)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
  },
  userEmail: {
    fontSize: 10.5,
    color: "var(--muted-2)",
    whiteSpace: "nowrap",
    overflow: "hidden",
    textOverflow: "ellipsis",
    display: "block",
  },
  logoutBtn: {
    color: "var(--muted-2)",
    flexShrink: 0,
  },
};
