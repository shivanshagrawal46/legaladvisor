import { useState, useEffect } from "react";
import { ConfigProvider, Spin } from "antd";
import { BrowserRouter, Routes, Route, NavLink, Navigate, Outlet } from "react-router-dom";
import Login from "./Login";
import Chat from "./Chat";
import PortfolioGrid from "./PortfolioGrid";
import FindingsDashboard from "./FindingsDashboard";
import PropertyDetail from "./PropertyDetail";
import { getMe } from "./api";

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) { setChecking(false); return; }
    getMe()
      .then(res => setUser(res.data))
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setChecking(false));
  }, []);

  const theme = {
    token: {
      colorPrimary: "#234a52",
      colorLink: "#234a52",
      borderRadius: 4,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      colorBgSpotlight: "#fdfbf6",
      colorTextLightSolid: "#1c1e2a",
    },
    components: {
      Tooltip: {
        colorBgSpotlight: "#fdfbf6",
        colorTextLightSolid: "#1c1e2a",
        borderRadiusOuter: 8,
        borderRadius: 8,
      },
    },
  };

  if (checking) return (
    <ConfigProvider theme={theme}>
      <div style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "radial-gradient(900px 600px at 50% 30%, #f3f1ea 0%, rgba(243,241,234,0) 60%), #fafaf7",
      }}>
        <Spin size="large" />
      </div>
    </ConfigProvider>
  );

  if (!user) return (
    <ConfigProvider theme={theme}>
      <Login onLogin={setUser} />
    </ConfigProvider>
  );

  return (
    <ConfigProvider theme={theme}>
      <BrowserRouter>
        <Routes>
          {/* Chat keeps its own full-screen layout (own sidebar) */}
          <Route path="/chat" element={<Chat user={user} />} />
          {/* Investigation workspace pages share the top-nav shell */}
          <Route element={<Shell user={user} />}>
            <Route path="/portfolio" element={<PortfolioGrid />} />
            <Route path="/findings" element={<FindingsDashboard />} />
            <Route path="/properties/:propertyId" element={<PropertyDetail />} />
          </Route>
          <Route path="*" element={<Navigate to="/portfolio" replace />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

function Shell({ user }) {
  const navItem = ({ isActive }) => ({
    padding: "6px 14px", borderRadius: 6, fontSize: 14, fontWeight: 600,
    textDecoration: "none", color: isActive ? "#fff" : "#234a52",
    background: isActive ? "#234a52" : "transparent",
  });
  return (
    <div style={{ minHeight: "100vh", background:
      "radial-gradient(900px 600px at 50% 0%, #f3f1ea 0%, rgba(243,241,234,0) 60%), #faf8f2" }}>
      <header style={{
        position: "sticky", top: 0, zIndex: 10, display: "flex", alignItems: "center",
        gap: 18, padding: "12px 24px", background: "rgba(253,251,246,0.85)",
        backdropFilter: "blur(8px)", borderBottom: "1px solid #e7e2d6",
      }}>
        <div style={{ fontFamily: "'Instrument Serif', Georgia, serif", fontSize: 20,
          color: "#234a52", fontWeight: 700, letterSpacing: 0.3 }}>
          Mango Tree · Evidence Engine
        </div>
        <nav style={{ display: "flex", gap: 6, marginLeft: 12 }}>
          <NavLink to="/portfolio" style={navItem}>Portfolio</NavLink>
          <NavLink to="/findings" style={navItem}>Findings</NavLink>
          <NavLink to="/chat" style={navItem}>Investigate (Chat)</NavLink>
        </nav>
        <div style={{ marginLeft: "auto", fontSize: 13, color: "#5b5f6e" }}>
          {user?.name || user?.email}
        </div>
      </header>
      <main style={{ maxWidth: 1320, margin: "0 auto", padding: "24px" }}>
        <Outlet />
      </main>
    </div>
  );
}
