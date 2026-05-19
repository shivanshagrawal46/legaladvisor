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

  if (checking) return (
    <ConfigProvider theme={{ token: { colorPrimary: "#6574c4" } }}>
      <div style={{
        height: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f0f2f9, #e8eaf6)",
      }}>
        <Spin size="large" />
      </div>
    </ConfigProvider>
  );

  if (!user) return (
    <ConfigProvider theme={{ token: { colorPrimary: "#6574c4", borderRadius: 8 } }}>
      <Login onLogin={setUser} />
    </ConfigProvider>
  );

  return <Chat user={user} />;
}
