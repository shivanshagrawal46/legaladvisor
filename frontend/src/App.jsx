import { useState, useEffect } from "react";
import { ConfigProvider, Spin } from "antd";
import Login from "./Login";
import Chat from "./Chat";
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
      <Chat user={user} />
    </ConfigProvider>
  );
}
