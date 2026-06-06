import { useState, useRef, useCallback } from "react";

const API = "http://localhost:8000";

// ─── Helpers ─────────────────────────────────────────────────────────────────
const riskColor = (score) => {
  if (score >= 60) return "#dc2626";
  if (score >= 35) return "#ea580c";
  if (score >= 15) return "#ca8a04";
  return "#16a34a";
};

const clauseTypeLabel = (t) =>
  ({
    indemnity: "Indemnity",
    termination: "Termination",
    ip_assignment: "IP Assignment",
    confidentiality: "Confidentiality",
    non_compete: "Non-Compete",
    liability: "Liability",
    force_majeure: "Force Majeure",
    governing_law: "Governing Law",
    dispute_resolution: "Dispute Resolution",
    payment_terms: "Payment Terms",
    warranty: "Warranty",
    representations: "Representations",
    general: "General",
  }[t] || t);

// ─── Upload Zone ──────────────────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef();

  const handleFile = useCallback(
    async (file) => {
      if (!file || !file.name.endsWith(".pdf")) {
        setError("Please upload a PDF file.");
        return;
      }
      setUploading(true);
      setError(null);
      const form = new FormData();
      form.append("file", file);
      try {
        const res = await fetch(`${API}/upload`, { method: "POST", body: form });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Upload failed");
        }
        const data = await res.json();
        onUpload(data);
      } catch (e) {
        setError(e.message);
      } finally {
        setUploading(false);
      }
    },
    [onUpload]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      onClick={() => inputRef.current.click()}
      style={{
        border: `2px dashed ${dragging ? "#6366f1" : "#d1d5db"}`,
        borderRadius: 12,
        padding: "2.5rem",
        textAlign: "center",
        cursor: "pointer",
        background: dragging ? "#eef2ff" : "#f9fafb",
        transition: "all 0.2s",
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf"
        style={{ display: "none" }}
        onChange={(e) => handleFile(e.target.files[0])}
      />
      <div style={{ fontSize: 40, marginBottom: 8 }}>📄</div>
      {uploading ? (
        <p style={{ color: "#6366f1", fontWeight: 500 }}>Processing PDF...</p>
      ) : (
        <>
          <p style={{ fontWeight: 600, color: "#111827" }}>
            Drop a PDF contract here
          </p>
          <p style={{ color: "#6b7280", fontSize: 14 }}>
            or click to browse · max 50MB
          </p>
        </>
      )}
      {error && (
        <p style={{ color: "#dc2626", marginTop: 8, fontSize: 14 }}>{error}</p>
      )}
    </div>
  );
}

// ─── Document List ────────────────────────────────────────────────────────────
function DocumentList({ docs, selectedId, onSelect }) {
  if (docs.length === 0) return null;
  return (
    <div style={{ marginTop: 20 }}>
      <h3 style={{ fontSize: 13, fontWeight: 600, color: "#6b7280", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        Uploaded Documents
      </h3>
      {docs.map((d) => (
        <div
          key={d.doc_id}
          onClick={() => onSelect(d)}
          style={{
            padding: "10px 14px",
            marginBottom: 6,
            borderRadius: 8,
            border: `1.5px solid ${selectedId === d.doc_id ? "#6366f1" : "#e5e7eb"}`,
            background: selectedId === d.doc_id ? "#eef2ff" : "#fff",
            cursor: "pointer",
            transition: "all 0.15s",
          }}
        >
          <div style={{ fontWeight: 500, fontSize: 14, color: "#111827" }}>
            {d.doc_name}
          </div>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            {d.total_chunks} clauses indexed
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Chat Q&A ─────────────────────────────────────────────────────────────────
function ChatPanel({ docs, selectedDoc }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  const ask = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          doc_id: selectedDoc?.doc_id || null,
        }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", content: data.answer, citations: data.citations, risk_flag: data.risk_flag },
      ]);
    } catch {
      setMessages((m) => [...m, { role: "assistant", content: "Error contacting server.", citations: [] }]);
    } finally {
      setLoading(false);
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 100);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem", background: "#f9fafb", borderRadius: 10, minHeight: 300, marginBottom: 12 }}>
        {messages.length === 0 && (
          <div style={{ color: "#9ca3af", fontSize: 14, textAlign: "center", marginTop: 60 }}>
            Ask a question about your contract(s).
            <br />
            <em style={{ fontSize: 12 }}>
              "Which contract has a longer non-compete?"
            </em>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            <div
              style={{
                maxWidth: "85%",
                marginLeft: m.role === "user" ? "auto" : 0,
                background: m.role === "user" ? "#6366f1" : "#fff",
                color: m.role === "user" ? "#fff" : "#111827",
                padding: "10px 14px",
                borderRadius: m.role === "user" ? "12px 12px 4px 12px" : "12px 12px 12px 4px",
                border: m.role === "assistant" ? "1px solid #e5e7eb" : "none",
                fontSize: 14,
                lineHeight: 1.6,
                whiteSpace: "pre-wrap",
              }}
            >
              {m.risk_flag && (
                <div style={{ background: "#fef2f2", border: "1px solid #fca5a5", borderRadius: 6, padding: "4px 8px", marginBottom: 8, fontSize: 12, color: "#b91c1c" }}>
                  ⚠️ Risk flag detected in cited clauses
                </div>
              )}
              {m.content}
              {m.citations?.length > 0 && (
                <div style={{ marginTop: 10, borderTop: "1px solid #f3f4f6", paddingTop: 8 }}>
                  {m.citations.map((c, ci) => (
                    <div key={ci} style={{ fontSize: 11, color: "#6b7280", marginBottom: 4, background: "#f9fafb", padding: "4px 8px", borderRadius: 4, borderLeft: "3px solid #6366f1" }}>
                      📄 <strong>{c.doc}</strong> · p.{c.page} · {c.clause}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ color: "#9ca3af", fontSize: 14 }}>Analyzing documents...</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div style={{ display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder={selectedDoc ? `Ask about ${selectedDoc.doc_name}...` : "Ask about all documents..."}
          style={{ flex: 1, padding: "10px 14px", borderRadius: 8, border: "1.5px solid #e5e7eb", fontSize: 14, outline: "none" }}
        />
        <button
          onClick={ask}
          disabled={loading || !input.trim()}
          style={{
            padding: "10px 20px",
            borderRadius: 8,
            background: loading ? "#a5b4fc" : "#6366f1",
            color: "#fff",
            border: "none",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
            fontSize: 14,
          }}
        >
          Ask
        </button>
      </div>
    </div>
  );
}

// ─── Clause Extractor ─────────────────────────────────────────────────────────
const CLAUSE_TYPES = [
  "indemnity", "termination", "liability", "ip_assignment",
  "confidentiality", "non_compete", "force_majeure", "governing_law",
];

function ClausePanel({ selectedDoc }) {
  const [clauseType, setClauseType] = useState("indemnity");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const extract = async () => {
    setLoading(true);
    setResults(null);
    const res = await fetch(`${API}/extract-clauses`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clause_type: clauseType, doc_id: selectedDoc?.doc_id || null }),
    });
    const data = await res.json();
    setResults(data);
    setLoading(false);
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <select
          value={clauseType}
          onChange={(e) => setClauseType(e.target.value)}
          style={{ padding: "8px 12px", borderRadius: 8, border: "1.5px solid #e5e7eb", fontSize: 14 }}
        >
          {CLAUSE_TYPES.map((t) => (
            <option key={t} value={t}>{clauseTypeLabel(t)}</option>
          ))}
        </select>
        <button
          onClick={extract}
          disabled={loading}
          style={{ padding: "8px 18px", borderRadius: 8, background: "#0f766e", color: "#fff", border: "none", fontWeight: 600, cursor: "pointer", fontSize: 14 }}
        >
          {loading ? "Extracting..." : "Extract Clauses"}
        </button>
      </div>

      {results && (
        <div>
          <p style={{ fontSize: 13, color: "#6b7280", marginBottom: 12 }}>
            Found <strong>{results.total_found}</strong> {clauseTypeLabel(clauseType).toLowerCase()} clause{results.total_found !== 1 ? "s" : ""}
            {selectedDoc ? ` in ${selectedDoc.doc_name}` : " across all documents"}
          </p>
          {results.clauses.map((c, i) => (
            <div key={i} style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, marginBottom: 12, background: "#fff" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontWeight: 600, fontSize: 13, color: "#111827" }}>{c.clause_name}</span>
                <span style={{ fontSize: 12, color: "#6b7280" }}>📄 {c.doc_name} · p.{c.page}</span>
              </div>
              <div style={{ fontSize: 13, color: "#374151", lineHeight: 1.7, background: "#f9fafb", padding: "10px 12px", borderRadius: 6, whiteSpace: "pre-wrap", fontFamily: "Georgia, serif" }}>
                {c.text}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Risk Panel ───────────────────────────────────────────────────────────────
function RiskPanel({ selectedDoc }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const analyze = async () => {
    if (!selectedDoc) return;
    setLoading(true);
    const res = await fetch(`${API}/risk-score/${selectedDoc.doc_id}`);
    const data = await res.json();
    setResult(data);
    setLoading(false);
  };

  const severityColor = { CRITICAL: "#dc2626", HIGH: "#ea580c", MEDIUM: "#ca8a04", LOW: "#16a34a", CLEAN: "#6b7280" };

  return (
    <div>
      {!selectedDoc ? (
        <p style={{ color: "#9ca3af", fontSize: 14 }}>Select a document to run risk analysis.</p>
      ) : (
        <>
          <button
            onClick={analyze}
            disabled={loading}
            style={{ padding: "10px 20px", borderRadius: 8, background: "#dc2626", color: "#fff", border: "none", fontWeight: 600, cursor: "pointer", fontSize: 14, marginBottom: 20 }}
          >
            {loading ? "Analyzing..." : `Analyze Risk: ${selectedDoc.doc_name}`}
          </button>

          {result && (
            <div>
              {/* Score gauge */}
              <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 12, padding: 20, marginBottom: 16, textAlign: "center" }}>
                <div style={{ fontSize: 56, fontWeight: 800, color: riskColor(result.aggregate_risk_score), lineHeight: 1 }}>
                  {result.aggregate_risk_score}
                </div>
                <div style={{ fontSize: 14, color: "#6b7280" }}>Risk score out of 100</div>
                <div style={{ display: "inline-block", marginTop: 8, padding: "4px 12px", borderRadius: 20, background: `${riskColor(result.aggregate_risk_score)}15`, color: riskColor(result.aggregate_risk_score), fontWeight: 700, fontSize: 13 }}>
                  {result.risk_level}
                </div>
                {/* Flag summary pills */}
                <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 12, flexWrap: "wrap" }}>
                  {Object.entries(result.flag_summary).map(([sev, count]) =>
                    count > 0 ? (
                      <span key={sev} style={{ padding: "3px 10px", borderRadius: 20, background: `${severityColor[sev]}15`, color: severityColor[sev], fontSize: 12, fontWeight: 600 }}>
                        {count} {sev}
                      </span>
                    ) : null
                  )}
                </div>
              </div>

              {/* Recommendations */}
              <div style={{ background: "#fff", border: "1px solid #e5e7eb", borderRadius: 10, padding: 16, marginBottom: 16 }}>
                <h4 style={{ margin: "0 0 10px", fontSize: 14, fontWeight: 600 }}>Recommendations</h4>
                {result.recommendations.map((r, i) => (
                  <div key={i} style={{ fontSize: 13, color: "#374151", marginBottom: 6, lineHeight: 1.6 }}>{r}</div>
                ))}
              </div>

              {/* Flagged clauses */}
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>Flagged Clauses</h4>
              {result.clause_breakdown.filter((c) => c.clause_score > 0).map((c, i) => (
                <div key={i} style={{ border: `1.5px solid ${riskColor(c.clause_score)}40`, borderRadius: 10, padding: 14, marginBottom: 10, background: "#fff" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, alignItems: "center" }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{c.clause_name}</span>
                    <span style={{ fontWeight: 700, color: riskColor(c.clause_score), fontSize: 13 }}>
                      Score: {c.clause_score} · {c.risk_level}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>p.{c.page} · {clauseTypeLabel(c.clause_type)}</div>
                  {c.flags.map((f, fi) => (
                    <div key={fi} style={{ fontSize: 12, color: "#374151", background: "#fef2f2", padding: "4px 8px", borderRadius: 4, marginBottom: 4, borderLeft: `3px solid ${severityColor[f.severity]}` }}>
                      <strong style={{ color: severityColor[f.severity] }}>[{f.severity}]</strong> {f.description}
                    </div>
                  ))}
                  <div style={{ fontSize: 12, color: "#6b7280", marginTop: 8, fontStyle: "italic" }}>
                    {c.text_excerpt}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
const TABS = ["Chat Q&A", "Clause Extractor", "Risk Analyzer"];

export default function App() {
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [activeTab, setActiveTab] = useState(0);

  const handleUpload = (result) => {
    const newDoc = {
      doc_id: result.doc_id,
      doc_name: result.doc_name,
      total_chunks: result.total_chunks,
      clause_types: result.clause_types,
    };
    setDocs((d) => [...d, newDoc]);
    setSelectedDoc(newDoc);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f3f4f6", padding: "24px 16px" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ marginBottom: 24 }}>
          <h1 style={{ fontSize: 26, fontWeight: 800, color: "#111827", margin: 0 }}>
            ⚖️ Legal Document Intelligence
          </h1>
          <p style={{ color: "#6b7280", marginTop: 4, fontSize: 14 }}>
            RAG-powered contract analysis · clause extraction · risk scoring
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "280px 1fr", gap: 20 }}>
          {/* Sidebar */}
          <div>
            <div style={{ background: "#fff", borderRadius: 12, padding: 16, border: "1px solid #e5e7eb" }}>
              <UploadZone onUpload={handleUpload} />
              <DocumentList docs={docs} selectedId={selectedDoc?.doc_id} onSelect={setSelectedDoc} />
            </div>
          </div>

          {/* Main panel */}
          <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e5e7eb", overflow: "hidden" }}>
            {/* Tab bar */}
            <div style={{ display: "flex", borderBottom: "1px solid #e5e7eb" }}>
              {TABS.map((tab, i) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(i)}
                  style={{
                    padding: "12px 20px",
                    background: "none",
                    border: "none",
                    borderBottom: `2px solid ${activeTab === i ? "#6366f1" : "transparent"}`,
                    color: activeTab === i ? "#6366f1" : "#6b7280",
                    fontWeight: activeTab === i ? 600 : 400,
                    cursor: "pointer",
                    fontSize: 14,
                    transition: "all 0.15s",
                  }}
                >
                  {tab}
                </button>
              ))}
              {selectedDoc && (
                <span style={{ marginLeft: "auto", padding: "12px 16px", fontSize: 12, color: "#9ca3af", display: "flex", alignItems: "center" }}>
                  Scope: {selectedDoc.doc_name}
                </span>
              )}
            </div>

            {/* Tab content */}
            <div style={{ padding: 20, minHeight: 400 }}>
              {activeTab === 0 && <ChatPanel docs={docs} selectedDoc={selectedDoc} />}
              {activeTab === 1 && <ClausePanel selectedDoc={selectedDoc} />}
              {activeTab === 2 && <RiskPanel selectedDoc={selectedDoc} />}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
