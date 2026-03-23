import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ReactMarkdown from "react-markdown";
import api from "../api";
import { v4 as uuidv4 } from "uuid";

const QUICK_QUERIES = [
  { label: "Today's Schedule", prompt: "How many appointments do I have today?" },
  { label: "Yesterday's Stats", prompt: "How many patients visited yesterday?" },
  { label: "Tomorrow's Schedule", prompt: "What appointments do I have tomorrow?" },
  { label: "Fever Cases (30d)", prompt: "How many patients with fever in the last 30 days?" },
  { label: "This Week", prompt: "Give me a summary of appointments this week" },
];

export default function DoctorDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sessionId] = useState(() => uuidv4());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [slackSent, setSlackSent] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async (text, toSlack = false) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    setSlackSent(false);

    try {
      const endpoint = toSlack ? "/doctor/report/send-slack" : "/doctor/report";
      const { data } = await api.post(endpoint, { message: msg, session_id: sessionId });
      const reply = data.report || data.report;
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      if (toSlack) {
        setSlackSent(true);
        const slackStatus = data.slack || "✅ Report sent to Slack!";
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: `📨 **${slackStatus}**` },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  return (
    <div style={styles.shell}>
      {/* ── Left Panel ───────────────────────────────────────── */}
      <div style={styles.leftPanel}>
        {/* Header */}
        <div style={styles.panelHeader}>
          <span style={{ fontSize: 22 }}>🏥</span>
          <div>
            <p style={styles.headerTitle}>DOBBE Health</p>
            <p style={styles.headerSub}>Doctor Dashboard</p>
          </div>
        </div>

        {/* Doctor info */}
        <div style={styles.doctorCard}>
          <div style={styles.docAvatar}>👨‍⚕️</div>
          <div>
            <p style={styles.docName}>{user?.name}</p>
            <p style={styles.docRole}>Doctor</p>
          </div>
        </div>

        {/* Quick query buttons */}
        <p style={styles.sectionLabel}>Quick Queries</p>
        {QUICK_QUERIES.map((q) => (
          <button key={q.label} onClick={() => sendMessage(q.prompt)} style={styles.quickBtn}>
            {q.label}
          </button>
        ))}

        {/* Send to Slack button */}
        <div style={styles.slackSection}>
          <p style={styles.sectionLabel}>Send to Slack</p>
          {messages.filter((m) => m.role === "assistant").length > 0 ? (
            <button
              onClick={() => {
                const lastUserMsg = [...messages].reverse().find((m) => m.role === "user");
                if (lastUserMsg) sendMessage(lastUserMsg.content, true);
              }}
              style={styles.slackBtn}
              disabled={loading}>
              {slackSent ? "✅ Sent to Slack!" : "📨 Send Last Report to Slack"}
            </button>
          ) : (
            <p style={styles.slackHint}>Generate a report first</p>
          )}
        </div>

        <button onClick={() => { logout(); navigate("/login"); }} style={styles.logoutBtn}>
          Sign out
        </button>
      </div>

      {/* ── Report Area ───────────────────────────────────────── */}
      <div style={styles.reportArea}>
        <div style={styles.reportHeader}>
          <span style={{ fontWeight: 700, color: "#1e3a8a", fontSize: 16 }}>
            AI Report Assistant
          </span>
          <span style={styles.badge}>Powered by Llama 4 · MCP Agent</span>
        </div>

        <div style={styles.messages}>
          {messages.length === 0 && (
            <div style={styles.empty}>
              <p style={{ fontSize: 36 }}>📊</p>
              <p style={{ fontWeight: 700, color: "#1e3a8a", fontSize: 20 }}>
                Good day, {user?.name?.replace("Dr. ", "")}
              </p>
              <p style={{ color: "#6b7280", fontSize: 14, textAlign: "center", maxWidth: 360 }}>
                Ask me about your appointment schedule, patient statistics, or any clinical query.
                Use the quick buttons on the left or type your question below.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={m.role === "user" ? styles.userRow : styles.botRow}>
              {m.role === "assistant" && <div style={styles.botAvatar}>🤖</div>}
              <div style={m.role === "user" ? styles.userBubble : styles.botBubble}>
                {m.role === "assistant" ? (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p style={{ margin: "0 0 8px", lineHeight: 1.6 }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ul>,
                      li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                      strong: ({ children }) => <strong style={{ color: "#1e3a8a" }}>{children}</strong>,
                      code: ({ children }) => <code style={{ background: "#f1f5f9", padding: "2px 6px", borderRadius: 4, fontSize: 13 }}>{children}</code>,
                    }}>
                    {m.content}
                  </ReactMarkdown>
                ) : m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div style={styles.botRow}>
              <div style={styles.botAvatar}>🤖</div>
              <div style={styles.typing}>
                <span style={styles.dot} />
                <span style={{ ...styles.dot, animationDelay: "0.2s" }} />
                <span style={{ ...styles.dot, animationDelay: "0.4s" }} />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div style={styles.inputRow}>
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey} rows={1}
            placeholder="e.g. How many patient with fever this week?"
            style={styles.textarea}
          />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()} style={styles.sendBtn}>
            ➤
          </button>
        </div>
        <p style={styles.hint}>Press Enter to send</p>
      </div>
    </div>
  );
}

const styles = {
  shell: { display: "flex", height: "100vh", fontFamily: "'Segoe UI', sans-serif" },

  // Left panel
  leftPanel: { width: 240, background: "#1e3a8a", display: "flex", flexDirection: "column", padding: "0 0 16px", flexShrink: 0 },
  panelHeader: { display: "flex", alignItems: "center", gap: 10, padding: "20px 16px 16px", borderBottom: "1px solid #1d4ed8" },
  headerTitle: { margin: 0, color: "#fff", fontWeight: 700, fontSize: 15 },
  headerSub: { margin: "2px 0 0", color: "#93c5fd", fontSize: 11 },
  doctorCard: { display: "flex", alignItems: "center", gap: 10, padding: "14px 16px", borderBottom: "1px solid #1d4ed8", marginBottom: 8 },
  docAvatar: { width: 36, height: 36, background: "#2563eb", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 },
  docName: { margin: 0, color: "#fff", fontWeight: 600, fontSize: 13 },
  docRole: { margin: "2px 0 0", color: "#93c5fd", fontSize: 11 },
  sectionLabel: { padding: "8px 16px 4px", color: "#93c5fd", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600, margin: 0 },
  quickBtn: { margin: "3px 10px", padding: "9px 12px", background: "transparent", border: "1px solid #3b82f6", color: "#bfdbfe", borderRadius: 7, cursor: "pointer", fontSize: 12, fontWeight: 500, textAlign: "left" },
  slackSection: { marginTop: 16, flex: 1 },
  slackBtn: { margin: "4px 10px", padding: "10px 12px", background: "#4a154b", border: "1px solid #7c3aed", color: "#e9d5ff", borderRadius: 7, cursor: "pointer", fontSize: 12, fontWeight: 600, width: "calc(100% - 20px)" },
  slackHint: { padding: "0 16px", color: "#4b5563", fontSize: 11, margin: 0 },
  logoutBtn: { margin: "8px 10px 0", padding: "8px", background: "transparent", border: "1px solid #3b82f6", color: "#93c5fd", borderRadius: 6, cursor: "pointer", fontSize: 12 },

  // Report area
  reportArea: { flex: 1, display: "flex", flexDirection: "column", background: "#f8fafc" },
  reportHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", background: "#fff", borderBottom: "1px solid #e5e7eb" },
  badge: { fontSize: 11, color: "#7c3aed", background: "#f3e8ff", padding: "4px 10px", borderRadius: 20, fontWeight: 600 },
  messages: { flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: 16 },
  empty: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: 8, paddingTop: 80 },

  userRow: { display: "flex", justifyContent: "flex-end" },
  botRow: { display: "flex", alignItems: "flex-start", gap: 10 },
  botAvatar: { width: 32, height: 32, background: "#dbeafe", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 },
  userBubble: { maxWidth: "65%", background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "#fff", borderRadius: "16px 16px 4px 16px", padding: "12px 16px", fontSize: 14 },
  botBubble: { maxWidth: "80%", background: "#fff", border: "1px solid #e5e7eb", borderRadius: "4px 16px 16px 16px", padding: "14px 18px", fontSize: 14, color: "#374151", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" },
  typing: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: "4px 16px 16px 16px", padding: "14px 18px", display: "flex", gap: 5, alignItems: "center" },
  dot: { width: 8, height: 8, background: "#93c5fd", borderRadius: "50%", display: "inline-block", animation: "bounce 1s infinite" },

  inputRow: { display: "flex", gap: 12, padding: "16px 24px 8px", background: "#fff", borderTop: "1px solid #e5e7eb", alignItems: "flex-end" },
  textarea: { flex: 1, border: "1.5px solid #e5e7eb", borderRadius: 10, padding: "12px 16px", fontSize: 14, fontFamily: "inherit", resize: "none", outline: "none", maxHeight: 100 },
  sendBtn: { width: 44, height: 44, background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "#fff", border: "none", borderRadius: 10, fontSize: 18, cursor: "pointer", flexShrink: 0 },
  hint: { textAlign: "center", fontSize: 11, color: "#9ca3af", padding: "0 0 10px", margin: 0 },
};
