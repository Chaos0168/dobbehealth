import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import ReactMarkdown from "react-markdown";
import api from "../api";
import { v4 as uuidv4 } from "uuid";

export default function PatientChat() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(() => uuidv4());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  // Load session list for sidebar
  useEffect(() => {
    api.get("/chat/sessions").then((r) => setSessions(r.data)).catch(() => {});
  }, []);

  // Load messages when session changes
  useEffect(() => {
    if (!sessionId) return;
    api.get(`/chat/history/${sessionId}`).then((r) => {
      setMessages(
        r.data.map((m) => ({ role: m.role, content: m.content }))
      );
    }).catch(() => setMessages([]));
  }, [sessionId]);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const newChat = () => {
    setSessionId(uuidv4());
    setMessages([]);
  };

  const send = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);

    try {
      const { data } = await api.post("/chat/", { message: text, session_id: sessionId });
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
      // Refresh session list
      api.get("/chat/sessions").then((r) => setSessions(r.data)).catch(() => {});
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div style={styles.shell}>
      {/* ── Sidebar ──────────────────────────────────────────── */}
      <div style={styles.sidebar}>
        <div style={styles.sideHeader}>
          <span style={{ fontSize: 20 }}>🏥</span>
          <span style={styles.sideTitle}>DOBBE Health</span>
        </div>

        <button onClick={newChat} style={styles.newChatBtn}>+ New Chat</button>

        <div style={styles.sideSection}>Past Conversations</div>
        <div style={{ overflowY: "auto", flex: 1 }}>
          {sessions.map((s) => (
            <div
              key={s.session_id}
              onClick={() => setSessionId(s.session_id)}
              style={{
                ...styles.sessionItem,
                ...(s.session_id === sessionId ? styles.sessionActive : {}),
              }}>
              <p style={styles.sessionPreview}>{s.preview}</p>
              <p style={styles.sessionTime}>
                {new Date(s.time).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>

        <div style={styles.sideFooter}>
          <div style={styles.userChip}>
            <span style={styles.avatar}>👤</span>
            <span style={styles.userName}>{user?.name}</span>
          </div>
          <button onClick={() => { logout(); navigate("/login"); }} style={styles.logoutBtn}>
            Sign out
          </button>
        </div>
      </div>

      {/* ── Chat Area ─────────────────────────────────────────── */}
      <div style={styles.chatArea}>
        {/* Header */}
        <div style={styles.chatHeader}>
          <span style={{ fontWeight: 700, color: "#1e3a8a", fontSize: 16 }}>
            AI Appointment Assistant
          </span>
          <span style={styles.badge}>🟢 Online</span>
        </div>

        {/* Messages */}
        <div style={styles.messages}>
          {messages.length === 0 && (
            <div style={styles.empty}>
              <p style={{ fontSize: 32 }}>👋</p>
              <p style={{ fontWeight: 600, color: "#1e3a8a", fontSize: 18 }}>
                Hi {user?.name?.split(" ")[0]}!
              </p>
              <p style={{ color: "#6b7280", fontSize: 14, maxWidth: 340, textAlign: "center" }}>
                I can help you book appointments, check doctor availability,
                and manage your schedule.
              </p>
              <div style={styles.suggestions}>
                {[
                  "Check Dr. Ahuja's availability for tomorrow",
                  "Book an appointment with Dr. Sharma on Friday",
                  "Show me all available doctors",
                ].map((s) => (
                  <button key={s} onClick={() => setInput(s)} style={styles.suggBtn}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} style={m.role === "user" ? styles.userRow : styles.botRow}>
              {m.role === "assistant" && (
                <div style={styles.botAvatar}>🤖</div>
              )}
              <div style={m.role === "user" ? styles.userBubble : styles.botBubble}>
                {m.role === "assistant" ? (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p style={{ margin: "0 0 8px" }}>{children}</p>,
                      ul: ({ children }) => <ul style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ul>,
                      li: ({ children }) => <li style={{ marginBottom: 4 }}>{children}</li>,
                      strong: ({ children }) => <strong style={{ color: "#1e3a8a" }}>{children}</strong>,
                    }}>
                    {m.content}
                  </ReactMarkdown>
                ) : (
                  m.content
                )}
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

        {/* Input */}
        <div style={styles.inputRow}>
          <textarea
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey} rows={1}
            placeholder="Ask about appointments, availability..."
            style={styles.textarea}
          />
          <button onClick={send} disabled={loading || !input.trim()} style={styles.sendBtn}>
            ➤
          </button>
        </div>
        <p style={styles.hint}>Press Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  );
}

const styles = {
  shell: { display: "flex", height: "100vh", fontFamily: "'Segoe UI', sans-serif", background: "#f8fafc" },

  // Sidebar
  sidebar: { width: 260, background: "#1e3a8a", display: "flex", flexDirection: "column", flexShrink: 0 },
  sideHeader: { display: "flex", alignItems: "center", gap: 10, padding: "20px 16px 12px", borderBottom: "1px solid #1d4ed8" },
  sideTitle: { color: "#fff", fontWeight: 700, fontSize: 16 },
  newChatBtn: {
    margin: "12px 12px 4px", padding: "10px", background: "#2563eb",
    color: "#fff", border: "1px solid #3b82f6", borderRadius: 8,
    cursor: "pointer", fontSize: 13, fontWeight: 600,
  },
  sideSection: { padding: "12px 16px 6px", color: "#93c5fd", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 },
  sessionItem: { padding: "10px 16px", cursor: "pointer", borderRadius: 6, margin: "2px 8px", transition: "background 0.15s" },
  sessionActive: { background: "#2563eb" },
  sessionPreview: { margin: 0, color: "#e0f2fe", fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  sessionTime: { margin: "2px 0 0", color: "#93c5fd", fontSize: 11 },
  sideFooter: { padding: "12px 16px", borderTop: "1px solid #1d4ed8" },
  userChip: { display: "flex", alignItems: "center", gap: 8, marginBottom: 8 },
  avatar: { fontSize: 18 },
  userName: { color: "#e0f2fe", fontSize: 13, fontWeight: 600 },
  logoutBtn: { width: "100%", padding: "8px", background: "transparent", border: "1px solid #3b82f6", color: "#93c5fd", borderRadius: 6, cursor: "pointer", fontSize: 12 },

  // Chat
  chatArea: { flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" },
  chatHeader: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 24px", background: "#fff", borderBottom: "1px solid #e5e7eb" },
  badge: { fontSize: 12, color: "#16a34a", background: "#dcfce7", padding: "4px 10px", borderRadius: 20, fontWeight: 600 },
  messages: { flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 },
  empty: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, gap: 8, paddingTop: 60 },
  suggestions: { display: "flex", flexDirection: "column", gap: 8, marginTop: 12, width: "100%", maxWidth: 380 },
  suggBtn: { padding: "10px 16px", background: "#fff", border: "1.5px solid #dbeafe", borderRadius: 8, cursor: "pointer", fontSize: 13, color: "#1d4ed8", textAlign: "left", fontWeight: 500 },

  // Messages
  userRow: { display: "flex", justifyContent: "flex-end" },
  botRow: { display: "flex", alignItems: "flex-start", gap: 10 },
  botAvatar: { width: 32, height: 32, background: "#dbeafe", borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, flexShrink: 0 },
  userBubble: { maxWidth: "70%", background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "#fff", borderRadius: "16px 16px 4px 16px", padding: "12px 16px", fontSize: 14, lineHeight: 1.5 },
  botBubble: { maxWidth: "75%", background: "#fff", border: "1px solid #e5e7eb", borderRadius: "4px 16px 16px 16px", padding: "12px 16px", fontSize: 14, lineHeight: 1.6, color: "#374151", boxShadow: "0 1px 4px rgba(0,0,0,0.06)" },
  typing: { background: "#fff", border: "1px solid #e5e7eb", borderRadius: "4px 16px 16px 16px", padding: "14px 18px", display: "flex", gap: 5, alignItems: "center" },
  dot: { width: 8, height: 8, background: "#93c5fd", borderRadius: "50%", display: "inline-block", animation: "bounce 1s infinite" },

  // Input
  inputRow: { display: "flex", gap: 12, padding: "16px 24px 8px", background: "#fff", borderTop: "1px solid #e5e7eb", alignItems: "flex-end" },
  textarea: { flex: 1, border: "1.5px solid #e5e7eb", borderRadius: 10, padding: "12px 16px", fontSize: 14, fontFamily: "inherit", resize: "none", outline: "none", maxHeight: 120, lineHeight: 1.5 },
  sendBtn: { width: 44, height: 44, background: "linear-gradient(135deg,#2563eb,#1d4ed8)", color: "#fff", border: "none", borderRadius: 10, fontSize: 18, cursor: "pointer", flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center" },
  hint: { textAlign: "center", fontSize: 11, color: "#9ca3af", padding: "0 0 10px", margin: 0 },
};
