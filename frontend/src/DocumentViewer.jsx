import { useEffect, useState } from "react";
import { Modal, Segmented, Tag, Spin, Empty, Button, Tooltip, message } from "antd";
import { getDocument, getDocumentFileBlob } from "./api";

const C = { brand: "#234a52", paper: "#fdfbf6", hair: "#e7e2d6", ink: "#1c1e2a", mute: "#5b5f6e" };
const mono = { fontFamily: "'JetBrains Mono',monospace" };
const serif = { fontFamily: "'Instrument Serif',Georgia,serif" };

const isPdf = (n) => /\.pdf$/i.test(n || "");
const isImg = (n) => /\.(png|jpe?g|gif|webp|tif?f|bmp)$/i.test(n || "");

// A full-document viewer: shows the original file (PDF/image) inline when we can
// serve it, plus the complete frontier-OCR transcript. Opened by clicking any
// document anywhere in the property pages.
export default function DocumentViewer({ docId, onClose }) {
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState("Original");
  const [blobUrl, setBlobUrl] = useState(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState(false);

  useEffect(() => {
    if (!docId) return;
    setLoading(true); setMeta(null); setBlobUrl(null); setFileError(false);
    getDocument(docId)
      .then((r) => {
        setMeta(r.data);
        setView(r.data.has_original ? "Original" : "Transcript (OCR)");
      })
      .catch(() => message.error("Could not load document"))
      .finally(() => setLoading(false));
  }, [docId]);

  // lazy-load the original file as an authenticated blob, embed via object URL
  useEffect(() => {
    if (view !== "Original" || !meta?.has_original || blobUrl || fileLoading) return;
    setFileLoading(true);
    getDocumentFileBlob(docId)
      .then((r) => setBlobUrl(URL.createObjectURL(r.data)))
      .catch(() => setFileError(true))
      .finally(() => setFileLoading(false));
  }, [view, meta, docId, blobUrl, fileLoading]);

  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);

  const fname = meta?.original_filename || meta?.label || "document";

  const download = () => {
    if (blobUrl) { const a = document.createElement("a"); a.href = blobUrl; a.download = fname; a.click(); return; }
    getDocumentFileBlob(docId).then((r) => {
      const u = URL.createObjectURL(r.data);
      const a = document.createElement("a"); a.href = u; a.download = fname; a.click();
      setTimeout(() => URL.revokeObjectURL(u), 4000);
    }).catch(() => message.error("Original file not available"));
  };

  const options = [];
  if (meta?.has_original) options.push("Original");
  options.push("Transcript (OCR)");

  return (
    <Modal
      open={!!docId}
      onCancel={onClose}
      footer={null}
      width="92vw"
      style={{ top: 24, maxWidth: 1100 }}
      styles={{ body: { padding: 0, background: C.paper } }}
      title={
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", paddingRight: 28 }}>
          <span style={{ ...serif, fontSize: 19, color: C.ink }}>{fname}</span>
          {meta?.source_type && <Tag color="default">{meta.source_type}</Tag>}
          {meta?.is_latest && <Tag color="green">latest</Tag>}
        </div>
      }
    >
      {loading ? (
        <div style={{ padding: 48, textAlign: "center" }}><Spin /></div>
      ) : !meta ? (
        <div style={{ padding: 32 }}><Empty description="Document not found." /></div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", height: "80vh" }}>
          {/* meta strip */}
          <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
            padding: "10px 18px", borderBottom: `1px solid ${C.hair}`, fontSize: 13, color: C.mute }}>
            {meta.date && <span><b style={{ color: C.ink }}>Date</b> {meta.date}</span>}
            {meta.vendor && <span><b style={{ color: C.ink }}>Vendor</b> {meta.vendor}</span>}
            {meta.order_number && <span><b style={{ color: C.ink }}>Order</b> #{meta.order_number}</span>}
            {meta.pages != null && <span><b style={{ color: C.ink }}>Pages</b> {meta.pages}</span>}
            {meta.sha256 && (
              <Tooltip title={meta.sha256}>
                <code style={{ ...mono, fontSize: 11 }}>sha {meta.sha256.slice(0, 14)}…</code>
              </Tooltip>
            )}
            <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
              <Segmented size="small" value={view} onChange={setView} options={options} />
              {meta.has_original && (
                <Button size="small" onClick={download}
                  style={{ background: "#fff", color: C.brand, borderColor: C.brand }}>⬇ Download</Button>
              )}
            </div>
          </div>

          {/* body */}
          <div style={{ flex: 1, overflow: "hidden" }}>
            {view === "Original" ? (
              fileLoading ? (
                <div style={{ padding: 48, textAlign: "center" }}><Spin tip="Loading original…" /></div>
              ) : fileError || !blobUrl ? (
                <div style={{ padding: 32 }}>
                  <Empty description="Original file could not be loaded — see the transcript instead." />
                </div>
              ) : isPdf(fname) ? (
                <iframe title="original" src={blobUrl} style={{ width: "100%", height: "100%", border: "none" }} />
              ) : isImg(fname) ? (
                <div style={{ height: "100%", overflow: "auto", textAlign: "center", background: "#33373f" }}>
                  <img alt={fname} src={blobUrl} style={{ maxWidth: "100%" }} />
                </div>
              ) : (
                <div style={{ padding: 32, textAlign: "center" }}>
                  <Empty description={`Inline preview not supported for "${fname}".`}>
                    <Button type="primary" onClick={download} style={{ background: C.brand }}>⬇ Download to view</Button>
                  </Empty>
                </div>
              )
            ) : (
              <div style={{ height: "100%", overflow: "auto", padding: "16px 22px" }}>
                {meta.text ? (
                  <pre style={{ ...mono, whiteSpace: "pre-wrap", wordBreak: "break-word",
                    fontSize: 12.5, lineHeight: 1.55, color: C.ink, margin: 0 }}>{meta.text}</pre>
                ) : <Empty description="No transcript text." />}
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
