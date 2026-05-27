import { Tag, Tooltip, Button } from "antd";
import {
  SafetyCertificateFilled,
  CheckCircleFilled,
  ExclamationCircleFilled,
  SyncOutlined,
} from "@ant-design/icons";
import { useEvidence } from "./EvidenceContext";

/**
 * VerificationBanner
 *
 * Compact one-line strip at the top of an assistant bubble that shows
 * the outcome of the Sprint-3-finish verifier:
 *
 *   VERIFIED_FIRST_PASS  → "X/X facts verified"            (green)
 *   VERIFIED_AFTER_RETRY → "X/X facts verified after retry" (blue)
 *   KEPT_ORIGINAL        → "X/Y verified — N to review"     (amber)
 *   NO_FACTS             → "No corpus facts cited"          (grey)
 *   FALLBACK             → "Verifier unavailable"           (grey)
 *
 * Clicking the banner (when there are unverified facts) jumps the
 * evidence drawer to the first unverified one.
 */

function jumpTargetIndex(verification) {
  if (!verification?.verdicts) return null;
  const firstBad = verification.verdicts.find(v => v.verdict !== "VERIFIED");
  return firstBad?.source_chunk_id ?? verification.verdicts[0]?.source_chunk_id ?? null;
}

export default function VerificationBanner() {
  const { verification, openEvidence } = useEvidence();
  if (!verification) return null;

  const { outcome, n_facts, n_verified } = verification;
  const n_total = n_facts ?? 0;
  const n_pass = n_verified ?? 0;
  const n_unver = Math.max(0, n_total - n_pass);

  // No facts at all — minimal display.
  if (outcome === "NO_FACTS" || n_total === 0) {
    return (
      <div style={{ ...styles.row, ...styles.grey }}>
        <SafetyCertificateFilled style={{ fontSize: 13, color: "#8892b0" }} />
        <span>No corpus facts cited — this answer is scoping/expertise only.</span>
      </div>
    );
  }

  if (outcome === "FALLBACK") {
    return (
      <div style={{ ...styles.row, ...styles.grey }}>
        <ExclamationCircleFilled style={{ fontSize: 13, color: "#b07a1a" }} />
        <span>Verifier unavailable — citations were not verified.</span>
      </div>
    );
  }

  // VERIFIED_FIRST_PASS or VERIFIED_AFTER_RETRY: green
  if (outcome === "VERIFIED_FIRST_PASS" || outcome === "VERIFIED_AFTER_RETRY") {
    return (
      <Tooltip
        placement="top"
        title={
          outcome === "VERIFIED_AFTER_RETRY"
            ? "All claims verified — some required a re-extraction retry. Click any [#N] to inspect evidence."
            : "All claims verified deterministically against the source quotes. Click any [#N] to inspect evidence."
        }
      >
        <div style={{ ...styles.row, ...styles.green }}>
          <CheckCircleFilled style={{ fontSize: 13 }} />
          <span style={{ fontWeight: 600 }}>
            {n_pass}/{n_total} facts verified
          </span>
          {outcome === "VERIFIED_AFTER_RETRY" && (
            <Tag
              icon={<SyncOutlined spin={false} />}
              style={{ ...styles.tag, background: "#eaf2fc", color: "#3a6cb0", borderColor: "#c2d6f0" }}
            >
              self-corrected
            </Tag>
          )}
        </div>
      </Tooltip>
    );
  }

  // KEPT_ORIGINAL: some facts unverified, lawyer should review.
  const jumpIdx = jumpTargetIndex(verification);
  return (
    <Tooltip
      placement="top"
      title={
        `${n_unver} claim${n_unver === 1 ? "" : "s"} could not be verified against the source — ` +
        `the original answer is shown so you can decide. Click to review the unverified claim${n_unver === 1 ? "" : "s"}.`
      }
    >
      <div
        style={{ ...styles.row, ...styles.amber, cursor: jumpIdx ? "pointer" : "default" }}
        onClick={() => jumpIdx && openEvidence(jumpIdx)}
      >
        <ExclamationCircleFilled style={{ fontSize: 13 }} />
        <span style={{ fontWeight: 600 }}>
          {n_pass}/{n_total} facts verified
        </span>
        <span style={styles.sep}>·</span>
        <span>
          {n_unver} to review
        </span>
        {jumpIdx && (
          <Button
            type="link"
            size="small"
            style={{ marginLeft: "auto", padding: 0, height: "auto", color: "#b07a1a", fontWeight: 600 }}
          >
            review evidence →
          </Button>
        )}
      </div>
    </Tooltip>
  );
}

const styles = {
  row: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "6px 10px",
    borderRadius: 6,
    fontSize: 12,
    marginBottom: 10,
    border: "1px solid",
  },
  green: {
    background: "#f5f9f0",
    borderColor: "#d9f0c7",
    color: "#3c7e1a",
  },
  amber: {
    background: "#fdf5e8",
    borderColor: "#f5dfa0",
    color: "#b07a1a",
  },
  grey: {
    background: "#f5f6fa",
    borderColor: "#ebedf5",
    color: "#6b7498",
  },
  sep: { opacity: 0.55 },
  tag: { marginLeft: 4, fontSize: 10, borderRadius: 4, padding: "0 6px", height: 18, lineHeight: "16px" },
};
