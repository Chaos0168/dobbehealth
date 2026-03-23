import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../api";

export default function Register() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "", email: "", password: "", role: "patient",
    phone: "", specialization: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", form);
      login(data);
      navigate(data.role === "doctor" ? "/doctor" : "/chat");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.bg}>
      <div style={styles.card}>
        <div style={styles.logo}>🏥</div>
        <h1 style={styles.title}>Create Account</h1>
        <p style={styles.sub}>Join DOBBE Health</p>

        <form onSubmit={submit} style={styles.form}>
          <label style={styles.label}>Full Name</label>
          <input name="name" value={form.name} onChange={handle} style={styles.input}
            placeholder="Tript Sachdeva" required />

          <label style={styles.label}>Email</label>
          <input name="email" type="email" value={form.email} onChange={handle}
            style={styles.input} placeholder="you@example.com" required />

          <label style={styles.label}>Password</label>
          <input name="password" type="password" value={form.password} onChange={handle}
            style={styles.input} placeholder="Minimum 6 characters" required />

          <label style={styles.label}>Phone (optional)</label>
          <input name="phone" value={form.phone} onChange={handle}
            style={styles.input} placeholder="+91-9999999999" />

          <label style={styles.label}>I am a</label>
          <div style={styles.roleRow}>
            {["patient", "doctor"].map((r) => (
              <button key={r} type="button"
                style={{ ...styles.roleBtn, ...(form.role === r ? styles.roleBtnActive : {}) }}
                onClick={() => setForm({ ...form, role: r })}>
                {r === "patient" ? "👤 Patient" : "👨‍⚕️ Doctor"}
              </button>
            ))}
          </div>

          {form.role === "doctor" && (
            <>
              <label style={styles.label}>Specialization</label>
              <input name="specialization" value={form.specialization} onChange={handle}
                style={styles.input} placeholder="e.g. General Physician, Cardiologist" required />
            </>
          )}

          {error && <p style={styles.error}>{error}</p>}

          <button type="submit" disabled={loading} style={styles.btn}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p style={styles.footer}>
          Already have an account?{" "}
          <Link to="/login" style={styles.link}>Sign in</Link>
        </p>
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
    maxWidth: 420, boxShadow: "0 8px 32px rgba(37,99,235,0.12)", textAlign: "center",
  },
  logo: { fontSize: 40, marginBottom: 8 },
  title: { margin: "0 0 4px", fontSize: 24, fontWeight: 700, color: "#1e3a8a" },
  sub: { margin: "0 0 24px", color: "#6b7280", fontSize: 14 },
  form: { textAlign: "left", display: "flex", flexDirection: "column", gap: 4 },
  label: { fontSize: 13, fontWeight: 600, color: "#374151", marginBottom: 2, marginTop: 10 },
  input: {
    border: "1.5px solid #e5e7eb", borderRadius: 8, padding: "10px 14px",
    fontSize: 14, outline: "none", fontFamily: "inherit",
  },
  roleRow: { display: "flex", gap: 10, marginTop: 4 },
  roleBtn: {
    flex: 1, padding: "10px", border: "2px solid #e5e7eb", borderRadius: 8,
    background: "#f9fafb", cursor: "pointer", fontSize: 14, fontWeight: 500,
    transition: "all 0.15s",
  },
  roleBtnActive: {
    border: "2px solid #2563eb", background: "#eff6ff", color: "#1d4ed8", fontWeight: 700,
  },
  error: { color: "#dc2626", fontSize: 13, margin: "4px 0 0" },
  btn: {
    marginTop: 20, background: "linear-gradient(135deg,#2563eb,#1d4ed8)",
    color: "#fff", border: "none", borderRadius: 8, padding: "12px",
    fontSize: 15, fontWeight: 600, cursor: "pointer",
  },
  footer: { marginTop: 20, fontSize: 14, color: "#6b7280" },
  link: { color: "#2563eb", textDecoration: "none", fontWeight: 600 },
};
