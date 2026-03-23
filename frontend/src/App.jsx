import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Login from "./pages/Login";
import Register from "./pages/Register";
import PatientChat from "./pages/PatientChat";
import DoctorDashboard from "./pages/DoctorDashboard";

// Protected route — redirects to /login if not authenticated
function PrivateRoute({ children, requiredRole }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (requiredRole && user.role !== requiredRole) {
    // Wrong role — redirect to correct page
    return <Navigate to={user.role === "doctor" ? "/doctor" : "/chat"} replace />;
  }
  return children;
}

function AppRoutes() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to={user.role === "doctor" ? "/doctor" : "/chat"} /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to={user.role === "doctor" ? "/doctor" : "/chat"} /> : <Register />} />

      <Route path="/chat" element={
        <PrivateRoute requiredRole="patient">
          <PatientChat />
        </PrivateRoute>
      } />

      <Route path="/doctor" element={
        <PrivateRoute requiredRole="doctor">
          <DoctorDashboard />
        </PrivateRoute>
      } />

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
