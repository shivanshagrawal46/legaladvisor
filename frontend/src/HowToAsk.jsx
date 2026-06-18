// "How to Ask" — a short, practical guide shown in-app so anyone (incl. the
// CEO) can phrase questions for the most complete, accurate answers.

const card = {
  background: "#fdfbf6", border: "1px solid #e7e2d6", borderRadius: 10,
  padding: "18px 20px", marginBottom: 16,
};
const h = { fontFamily: "'Instrument Serif',Georgia,serif", color: "#234a52" };
const good = { color: "#2e7d32", fontWeight: 600 };
const bad = { color: "#b4441f", fontWeight: 600 };
const mono = {
  fontFamily: "'JetBrains Mono',monospace", fontSize: 13, background: "#f3f1ea",
  border: "1px solid #e7e2d6", borderRadius: 6, padding: "8px 10px",
  display: "block", margin: "6px 0", color: "#1c1e2a",
};
const li = { marginBottom: 6, lineHeight: 1.55 };

export default function HowToAsk() {
  return (
    <div style={{ maxWidth: 860 }}>
      <h2 style={{ ...h, fontSize: 30, margin: "0 0 2px" }}>How to Ask</h2>
      <p style={{ color: "#5b5f6e", marginTop: 0, marginBottom: 22, fontSize: 15 }}>
        Get the most complete, accurate answer — every time. Six simple habits.
      </p>

      <div style={card}>
        <h3 style={{ ...h, fontSize: 19, marginTop: 0 }}>1. Always name the exact property or person</h3>
        <p style={{ margin: "4px 0 8px" }}>
          The system pulls <b>every linked record</b> the moment you name a specific thing
          (address, LLC, or person). Vague words weaken it.
        </p>
        <span style={mono}><span style={good}>✓ Good:</span> "Who owns 26 Appel Dr E, Shirley?"</span>
        <span style={mono}><span style={bad}>✗ Weak:</span> "Who owns that property?"</span>
        <p style={{ margin: "8px 0 0", color: "#5b5f6e" }}>
          Tip: if you know the LLC name or parcel number too, add them — more detail = wider search.
        </p>
      </div>

      <div style={card}>
        <h3 style={{ ...h, fontSize: 19, marginTop: 0 }}>2. Say what you want — and ask for sources</h3>
        <p style={{ margin: "4px 0 8px" }}>End the question with “…with dates, amounts, and the source for each.”</p>
        <span style={mono}>
          "List all mortgages and liens on 12 Mallard Path, with amounts, dates, and source documents."
        </span>
      </div>

      <div style={card}>
        <h3 style={{ ...h, fontSize: 19, marginTop: 0 }}>3. To be sure nothing is missed, add these words</h3>
        <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
          <li style={li}><b>“List all …”</b> or <b>“every …”</b> — shows every match, not just the top one.</li>
          <li style={li}><b>“…and if anything is not in the records, say so.”</b> — makes any gap visible instead of silently skipped.</li>
        </ul>
      </div>

      <div style={card}>
        <h3 style={{ ...h, fontSize: 19, marginTop: 0 }}>4. One topic per question — or number the parts</h3>
        <span style={mono}>
          <span style={good}>✓ Good:</span> "For 230 Ralph Ave: (1) owner, (2) liens, (3) timeline, (4) suspicious transfers."
        </span>
        <span style={mono}><span style={bad}>✗ Avoid:</span> asking about five different properties in one message.</span>
      </div>

      <div style={card}>
        <h3 style={{ ...h, fontSize: 19, marginTop: 0 }}>5. Ready-to-use questions (copy &amp; replace the address)</h3>
        <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
          <li style={li}><b>Ownership:</b> “Who owns <i>[address]</i> and is it connected to David DeRosa or his network?”</li>
          <li style={li}><b>Debts:</b> “List all mortgages, liens, and judgments against <i>[address]</i>, with sources.”</li>
          <li style={li}><b>Timeline:</b> “Give the full timeline of <i>[address]</i>, every event cited.”</li>
          <li style={li}><b>Suspicious transfers:</b> “Are there any suspicious or voidable transfers involving <i>[address]</i>?”</li>
        </ul>
      </div>

      <div style={{ ...card, background: "#234a52", border: "none" }}>
        <p style={{ margin: 0, color: "#fff", fontSize: 15.5, fontWeight: 600 }}>
          Remember: <span style={{ color: "#ffe2a8" }}>Name the exact property → ask for “all, with sources” → one topic per question.</span>
        </p>
      </div>
    </div>
  );
}
