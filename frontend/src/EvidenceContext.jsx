import { createContext, useContext, useState, useCallback, useMemo } from "react";

/**
 * EvidenceContext
 *
 * A lightweight, message-scoped React context used by:
 *   - <CitationChip/>       (clicks the [#N] inside the answer prose)
 *   - <Sources/>            (clicks a source card)
 *   - <VerificationBanner/> (clicks "review unverified")
 *
 * The provider wraps a single assistant message bubble. When a chip is
 * clicked, it calls `openEvidence({ sourceIndex, factId? })` and the
 * EvidenceDrawer (also mounted inside the same provider) reacts.
 *
 * Why scope to one message? Because each assistant turn has its own
 * `sources[]` and `verification` payload — globally shared state would
 * mix sources from different turns when scrolling through history.
 */

const EvidenceContext = createContext(null);

export function EvidenceProvider({ sources, verification, children }) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(null);
  const [activeFactId, setActiveFactId] = useState(null);

  const openEvidence = useCallback((sourceIndex, factId = null) => {
    setActiveIndex(sourceIndex);
    setActiveFactId(factId);
    setOpen(true);
  }, []);

  const closeEvidence = useCallback(() => {
    setOpen(false);
  }, []);

  // Lookup helpers exposed to consumers.
  const value = useMemo(() => {
    const byIndex = new Map();
    (sources || []).forEach(s => byIndex.set(s.index, s));

    // Build per-source-index verdict map even if the verification
    // payload is the source of truth — both Sources and citation chips
    // consume it.
    const verdictsByIndex = new Map();
    (verification?.verdicts || []).forEach(v => {
      if (typeof v.source_chunk_id !== "number") return;
      if (!verdictsByIndex.has(v.source_chunk_id)) {
        verdictsByIndex.set(v.source_chunk_id, []);
      }
      verdictsByIndex.get(v.source_chunk_id).push(v);
    });

    const getSource = (idx) => byIndex.get(idx) || null;
    const getVerdictsFor = (idx) => verdictsByIndex.get(idx) || [];
    const getOverallVerdictFor = (idx) => {
      const vs = verdictsByIndex.get(idx);
      if (!vs || vs.length === 0) return null;
      // Worst-case: if any verdict is not VERIFIED, the chip badges
      // as unverified (lawyer should review).
      if (vs.every(v => v.verdict === "VERIFIED")) return "VERIFIED";
      if (vs.some(v => v.verdict === "CITATION_INVALID")) return "CITATION_INVALID";
      return "UNVERIFIED";
    };

    return {
      sources: sources || [],
      verification: verification || null,
      open,
      activeIndex,
      activeFactId,
      openEvidence,
      closeEvidence,
      getSource,
      getVerdictsFor,
      getOverallVerdictFor,
    };
  }, [sources, verification, open, activeIndex, activeFactId,
      openEvidence, closeEvidence]);

  return (
    <EvidenceContext.Provider value={value}>
      {children}
    </EvidenceContext.Provider>
  );
}

export function useEvidence() {
  const ctx = useContext(EvidenceContext);
  // Allow components to be used in messages without verification (e.g. v1
  // legacy answers) — return a no-op stub instead of throwing.
  if (!ctx) {
    return {
      sources: [],
      verification: null,
      open: false,
      activeIndex: null,
      activeFactId: null,
      openEvidence: () => {},
      closeEvidence: () => {},
      getSource: () => null,
      getVerdictsFor: () => [],
      getOverallVerdictFor: () => null,
    };
  }
  return ctx;
}
