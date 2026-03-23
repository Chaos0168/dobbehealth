import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", form);
      login(data);
      navigate(data.role === "doctor" ? "/doctor" : "/chat");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.bg}>
      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logo}>🏥</div>
        <h1 style={styles.title}>DOBBE Health</h1>
        <p style={styles.sub}>AI-powered appointment assistant</p>

        <form onSubmit={submit} style={styles.form}>
          <label style={styles.label}>Email</label>
          <input
            name="email" type="email" value={form.email} onChange={handle}
            style={styles.input} placeholder="you@example.com" required
          />

          <label style={styles.label}>Password</label>
          <input
            name="password" type="password" value={form.password} onChange={handle}
            style={styles.input} placeholder="••••••••" required
          />

          {error && <p style={styles.error}>{error}</p>}

          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p style={styles.footer}>
          Don't have an account?{" "}
          <Link to="/register" style={styles.link}>Register</Link>
        </p>

        {/* Demo credentials hint */}
        <div style={styles.hint}>
          <p style={{ margin: 0, fontSize: 12, color: "#6b7280" }}>Demo accounts:</p>
          <p style={{ margin: "4px 0 0", fontSize: 12, color: "#374151" }}>
            Patient: <code>tript@patient.com</code> / <code>password123</code>
          </p>
          <p style={{ margin: "2px 0 0", fontSize: 12, color: "#374151" }}>
            Doctor: <code>dr.ahuja@hospital.com</code> / <code>password123</code>
          </p>
        </div>
      </div>
    </div>
  );
}

const styles = {
  bg: {
    minHeight: "100vh", background: "linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%)",
    display: "flex", alignItems: "center", justifyContent: "center", padding: 16,
  },
  card: {
    background: "#fff", borderRadius: 16, padding: "40px 36px", width: "100%",
    maxWidth: 400, boxShadow: "0 8px 32px rgba(37,99,235,0.12)", textAlign: "center",
  },
  logo: { fontSize: 40, marginBottom: 8 },
  title: { margin: "0 0 4px", fontSize: 26, fontWeight: 700, color: "#1e3a8a" },
  sub: { margin: "0 0 28px", color: "#6b7280", fontSize: 14 },
  form: { textAlign: "left", display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 2, marginTop: 10 },
  input: {
    border: "1.5px solid #e5e7eb", borderRadius: 8, padding: "10px 14px",
    fontSize: 14, outline: "none", transition: "border 0.2s",
    fontFamily: "inherit",
  },
  error: { color: "#dc2626", fontSize: 13, margin: "4px 0 0" },
  btn: {
    marginTop: 20, background: "linear-gradient(135deg,#2563eb,#1d4ed8)",
    color: "#fff", border: "none", borderRadius: 8, padding: "12px",
    fontSize: 15, fontWeight: 600, cursor: "pointer", transition: "opacity 0.2s",
  },
  footer: { marginTop: 20, fontSize: 14, color: "#6b7280" },
  link: { color: "#2563eb", textDecoration: "none", fontWeight: 600 },
  hint: {
    marginTop: 20, background: "#f8fafc", borderRadius: 8, padding: "12px 16px",
    border: "1px solid #e5e7eb", textAlign: "left",
  },
};
