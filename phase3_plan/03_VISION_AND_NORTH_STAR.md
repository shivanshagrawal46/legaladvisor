# 03 · Vision & North Star — The Trustee-Ready Truth Engine

**Project:** Mango Tree Legal RAG — Fraud Investigation Evidence Platform
**Owner:** Rakesh Sir's team (Mango Tree)
**Status of this document:** Our compass. Read this before any big decision. If a choice doesn't serve this vision, we don't make it.

---

## 1 · The mission (never forget this)

We are **victims of fraud committed by David and his team.** A **trustee has been appointed** in the David matter. **Our recovery — real money for real victims — depends on the trustee's actions.** A trustee can only act well when handed **complete, accurate, timeline-correct, provable** information.

> **This system exists to make sure the trustee (and our team) never misses a single relevant fact about David's properties, money, entities, or conduct — and that every fact we present is backed by a real source we can show a court.**

This is not a generic chatbot. It is an **evidence engine for asset recovery.** Every design decision is measured against one question:

> *"Does this help us hand the trustee the truth — all of it, accurately, with proof and correct timeline?"*

When in doubt, build for **completeness + accuracy + provability + timeline**, in that spirit. We work here as **legal thinkers first, engineers second.**

---

## 2 · Who uses this system

- **Rakesh Sir's team (us)** — internal analysis, full Analysis mode.
- **Our attorneys** — inside the privilege circle.
- **Retained experts / forensic accountants** — build trustee exhibits (timelines, flow-of-funds). Clean mode for anything they'll testify on.
- **The trustee** — the ultimate decision-maker whose action recovers our money. Receives accurate, complete, cited output.

High-level officials will rely on this. The bar is **courtroom-grade**, not demo-grade.

---

## 3 · The non-negotiable principles

1. **Never miss information.** If a fact about a property/person/amount exists anywhere in the corpus, a query about that property/person/amount must surface it. Recall is sacred — this is the whole reason the system exists (humans cannot hold ~6,000 emails + hundreds of documents in their head; the AI can).
2. **Never invent information.** Every fact is grounded in a verbatim source quote + citation. Unverifiable claims are rejected, not shown. (Grounding.)
3. **Always correct on timeline.** Documents, emails, and evidence are ordered by the right dates. The same file at different times can mean different decisions; the system never confuses them.
4. **Drafts vs signed are never confused.** Signed/executed/recorded instruments are **operative and high-value**; drafts are **preserved** and the **difference** is surfaced (drafting history proves intent). We show *both* and label which controls.
5. **Everything is interlinked.** A property connects to its title reports, insurance, deed, mortgage, the LLC that holds it, David's emails about it, the wires that funded it, and the litigation touching it — automatically, without the user naming any document type.
6. **Privilege is protected.** Our privileged strategy never leaks into a shareable output (Clean mode).
7. **Every answer is structured.** Not a paragraph blob — a structured, complete picture: facts, sources, timeline, contradictions, provenance.

---

## 4 · The end state — what "Phase 3 complete" looks like

A user (or the trustee) asks a **plain-language** question — *"What's the full story on 520 East 81st?"* — and the system returns, in seconds:

- **Every linked document**, across all source types, that touches that property — David's emails, title reports (latest + prior), insurance binders, deed, mortgage, equity figures, LLC ownership, court filings.
- A **correct chronological timeline** of what happened, each event cited.
- **Contradictions flagged** — e.g., David's stated price vs the recorded/operative price, with both quoted.
- **Authority-aware framing** — the recorded deed controls over David's email; the latest title search supersedes the prior; the signed instrument outweighs the draft (with the draft's changes noted).
- **Every fact verified** against a verbatim source quote with a citation (and Bates number when available).
- A **provenance + confidence footer** — what was used, which corpus, privileged or not, verified or flagged.
- Optionally, a **timeline exhibit** and an **evidence packet** the trustee/expert can drop into a filing.

No information missed. Nothing invented. Timeline correct. Proof attached.

---

## 5 · All document types we will hold

| Family | Document types |
|---|---|
| **Fraud communications (David)** | emails + attachments with David & team — *party admissions* |
| **Legal correspondence (ours)** | emails + attachments with our attorneys — *privileged* |
| **Property / title** | title reports (full search **+ update/continuation search**), deeds, mortgages, satisfactions, liens, lis pendens |
| **Insurance** | binders, policies, claims, coverage evidence |
| **Corporate** | LLC formation, operating agreements, good-standing certificates |
| **Court / litigation** | DA filings, indictments, court orders, judgments, litigation updates |
| **Financial** | bank records, wires, **equity-in-properties Excel**, tax records, closing statements |
| **General** | contracts, amendments, drafts, spreadsheets, correspondence |

---

## 6 · How everything interlinks (the linkage map)

Canonical entities are the hubs; documents and emails connect through them:

```
            ┌─────────── David (ent_per_001) ───────────┐
            │ aliases, all emails, signatures            │
   SENT_EMAIL │              MEMBER_OF │        GRANTEE_OF │  DEFENDANT_IN
            ▼                          ▼                  ▼              ▼
        You / team            IPA LLC (ent_llc) ──OWNS──► Property ◄─ Case / DA filing
                                                          (ent_prop)
                              ┌──────────────┬────────────┼───────────┬─────────────┐
                       ABOUT_PROPERTY   HAS_MORTGAGE  HAS_INSURANCE  HAS_LIEN   funded by
                              ▼              ▼            ▼            ▼            ▼
                      Title report     Mortgage      Insurance     Lien      Bank wire
                      (full+update)                  binder/policy           (equity Excel)
```

- Ask about **a property** → fan out to every node touching it.
- Ask about **David** → every property, LLC, email, case, wire tied to him.
- Ask about **an amount** → every document/email carrying it (contradiction surface).
- **Multi-hop:** "which LLCs is David in, and which properties do they own, and what's the latest title status of each?" → graph traversal.

Each link is **dated** (`as_of`) and **sourced** (traceable to the exact chunk that proves it).

---

## 7 · Timeline & evidentiary-weight principles (legal core)

- **Multi-axis dates:** document date, effective date, recording date, filing date, execution date — never conflated. Recording date orders property events; filing date orders litigation; email date orders the narrative.
- **Operative vs superseded:** the latest title search and the signed/recorded instrument are **operative**; earlier versions and drafts are **preserved** and shown as lineage with the **diff** highlighted.
- **Authority hierarchy:** court order > recorded deed/mortgage > lien/DA filing > title report > insurance > executed contract > bank/wire > LLC cert > email attachment > email body > **draft / attorney note**.
- **Admissions weigh heavily:** David's own statements (Corpus B) are admissions against interest — surfaced prominently, especially when they contradict the records.
- **Drafts still matter:** low authority ≠ ignore. A deletion between draft and final is "especially revealing" of intent; we keep and surface it.

---

## 8 · Best practices we are following (from research)

- **Hybrid retrieval + RRF + reranking** (industry default 2026) — we exceed the baseline with 5 channels. ✅
- **Contextual chunking** (LLM context per chunk) — we have it; upgrading to 3-tier. ✅
- **Agentic / iterative retrieval** (Harvey "agentic search", Hebbia ISD) — we have an Opus ReAct agent. ✅
- **Entity-anchored, parameterized single agent over many sources** (Harvey's model) — Phase 3 `search_entity_cluster`. ⏳
- **Knowledge graph + entity resolution with canonical IDs** (GraphRAG, Citation-Enforced GraphRAG) — Phase 3. ⏳
- **Grounding / citation enforcement / faithfulness eval** (BigLaw Bench style) — verifier today + eval set in Sprint 6. ⏳
- **Forensic/trustee evidence form** — transaction timelines, flow-of-funds, asset tracing across entities, underlying data identified (FRE 702 / FRCP 26) — Sprint 5 timeline + evidence export. ⏳
- **Legal-tuned embeddings** (`voyage-law-2`) — optional Sprint 6 drop-in. ⏳

---

## 9 · Are we missing anything? (honest gap-check + additions)

Reviewed against the mission. Additions now folded into the plan:

1. **Coreference resolution** (pronouns, "the property", "Id.") — added to Sprint 3. Without it, intra-document links are lost.
2. **Bitemporal edges** (`as_of` + `until`) — added. Ownership/control change over time; "who owned it on the date of the lie?" must work.
3. **Alias-learning loop** — confirmed merges teach the resolver; the graph gets smarter with use.
4. **Omission/silence detection** — a record-proven fact David never mentioned is itself evidence; contradiction detector includes omission type.
5. **Adversarial entity obfuscation** — shells/nominees exposed via behavioral edges (who controls the LLC's email + bank), not just formation paper.
6. **Flow-of-funds tracing** — wires + equity Excel + bank records form a money-movement view across entities (forensic best practice for clawbacks/voidable transfers).
7. **Bates / exhibit numbering** — captured at ingest; citations in Bates form for trustee/court use.
8. **Chain of custody** — `custody{}` + SHA-256 tamper-evidence supports authentication (FRE 901/902).

**Still to confirm (not blockers):** OCR-extraction strictness level; inbound folder layout; privilege certainty per lawyer email; whether equity Excel has clean structured columns (affects how we parse it).

**Decision (Jun 2026): we leave NOTHING on the table — but we choose RELIABLE over RISKY.** The system will be judged by a third party; an incorrect output would shake trust in both the system and our technical credibility. So Sprint 7 commits to single, proven, explainable choices (no experiments):
- **Reranker: LLM-as-reranker** (NOT ColBERT — no fragile new index).
- **Chunking: 3-tier contextual** (NOT late chunking — no unverified model internals).
- **Embeddings: keep voyage-4-large** (NOT voyage-law-2 — never gamble the foundation on an older model without proof; switching could regress).
- **Query decomposition** + **sufficiency/self-reflection** check (recall on complex questions; guard against missing info).
- **Post-generation entity validation** — Claude-compatible equivalent of constrained decoding / KG-Trie. (True KG-Trie needs self-hosted open-weights models — the Anthropic API can't do logit-level control — so we validate entity names against the canonical graph after generation instead. Same goal: zero invented entities.)
- **Faithfulness gate** + **golden-answer regression tests**.
- **Negative-evidence / completeness reporting** — the system states what it does NOT have.
- **OCR-confidence surfacing**, **full audit/provenance export**, **spreadsheet-grid portfolio UI**, **cross-encoder for grey-zone entity merges**.
- **Domain fine-tuning is NOT pursued** (too massive); replaced by strong prompt engineering + few-shot + structured system prompt + verifier.

---

## 10 · How we prove we are world-class (success criteria)

By end of Phase 3, on our private eval set:
- **Recall@10 ≥ 0.9** per major source type (we surface the right documents).
- **Faithfulness ≈ 1.0** (every claim grounded in a cited source; zero unsupported facts).
- **Contradiction recall** on a labeled set of known David discrepancies.
- **Timeline accuracy** on a labeled chronology.
- **Zero privileged leakage** in Clean-mode outputs (automated check).

We focus on **one case in depth** — that is precisely why we can beat a breadth-first system like Harvey here.

---

## 11 · Bulletproofing & Trust Guarantees (the standard every sprint must meet)

The system will be judged by a **non-technical evaluator** who simply wants the best answer and confidence that it never fails or misses anything. We do NOT claim mathematical 100% recall (no honest system can) — instead we guarantee the things that actually protect trust:

1. **Never invents a fact** — the verifier rejects any claim not grounded in a real source quote. *(Hard guarantee.)*
2. **Never silently misses** — the 8-layer retrieval net + sufficiency check + negative-evidence reporting make any gap **visible**, never hidden.
3. **Always provable** — every fact has a clickable source quote (+ Bates number when available).
4. **Honest about gaps** — says "not found" rather than bluffing. A visible gap builds trust; a confident wrong answer destroys it.
5. **Timeline-correct** — multi-axis dates + authority hierarchy + supersession; drafts never confused with signed instruments.
6. **Measured before testing** — the Sprint 6 eval set gives us the scorecard (Recall@10, faithfulness, zero-hallucination rate) **before** any third party touches it.

**The 8-layer retrieval net** — a relevant chunk would have to slip past ALL of these to be missed:
1. 5 retrieval channels (vector + BM25 + exact-phrase + literal regex + filename)
2. Multiple query forms (HyDE + alternate phrasings)
3. Entity-anchored fan-out (retrieves linked evidence even with no shared words)
4. Query decomposition (multi-part questions split and retrieved separately)
5. Reranking (best evidence to the top)
6. Sufficiency / self-reflection ("have I checked every linked source?")
7. Negative-evidence reporting (states what's missing)
8. Verifier grounding (every fact checked against a real quote)

> **Governing principle:** Outstanding retrieval + never confidently wrong + honest about gaps. Every sprint is held to this standard; the non-technical tester experiences "it always gives the best answer and never embarrasses me."

---

## 12 · Guardrails (always on)

- **Grounding:** no verbatim source → no claim.
- **Privilege:** Clean mode filters privileged content at the retrieval layer (structural, not behavioral).
- **Chain of custody:** every doc hashed, sourced, timestamped.
- **Human-in-the-loop:** uncertain entity merges and unverifiable facts go to a review queue, never silently guessed.
- **Idempotency:** every pipeline re-runnable without duplication or corruption.

---

## 13 · One-line North Star

> **Hand the trustee the complete, accurate, timeline-correct, fully-cited truth about David's fraud — every fact a human would miss, none invented — so the victims recover their money.**
