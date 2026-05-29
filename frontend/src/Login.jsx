import { useState } from "react";
import { Form, Input, Button, Alert, Typography } from "antd";
import { MailOutlined, LockOutlined } from "@ant-design/icons";
import { login } from "./api";

const { Title, Text } = Typography;

export default function Login({ onLogin }) {
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleFinish({ email, password }) {
    setError("");
    setLoading(true);
    try {
      const res = await login(email, password);
      localStorage.setItem("token", res.data.access_token);
      localStorage.setItem("user_name", res.data.name);
      localStorage.setItem("user_email", res.data.email);
      onLogin(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid email or password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      {/* Subtle background pattern */}
      <div style={styles.bgPattern} />

      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logoBlock}>
          <div style={styles.logoCircle}>
            <span style={{ fontSize: 26 }}>⚖️</span>
          </div>
          <Title level={3} style={styles.title}>Mango Tree</Title>
          <Text style={styles.subtitle}>Legal Advisor · Fraud Investigation</Text>
        </div>

        {error && (
          <Alert
            message={error}
            type="error"
            showIcon
            style={{ marginBottom: 20, borderRadius: 8 }}
          />
        )}

        <Form layout="vertical" onFinish={handleFinish} autoComplete="off">
          <Form.Item
            name="email"
            label={<span style={styles.label}>Email address</span>}
            rules={[{ required: true, message: "Please enter your email" }]}
          >
            <Input
              prefix={<MailOutlined style={{ color: "var(--muted-2)" }} />}
              placeholder="you@example.com"
              size="large"
              style={styles.input}
            />
          </Form.Item>

          <Form.Item
            name="password"
            label={<span style={styles.label}>Password</span>}
            rules={[{ required: true, message: "Please enter your password" }]}
            style={{ marginBottom: 24 }}
          >
            <Input.Password
              prefix={<LockOutlined style={{ color: "var(--muted-2)" }} />}
              placeholder="••••••••••"
              size="large"
              style={styles.input}
            />
          </Form.Item>

          <Button
            type="primary"
            htmlType="submit"
            size="large"
            loading={loading}
            block
            style={styles.btn}
          >
            Sign In
          </Button>
        </Form>

        <Text style={styles.footer}>
          Powered by Claude Sonnet 4.6 · Voyage AI · MongoDB Atlas
        </Text>
      </div>
    </div>
  );
}

const styles = {
  page: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "var(--paper)",
    padding: 24,
    position: "relative",
    overflow: "hidden",
  },
  bgPattern: {
    position: "absolute",
    inset: 0,
    backgroundImage: "radial-gradient(900px 600px at 25% 18%, rgba(35,74,82,0.05) 0%, transparent 55%), radial-gradient(800px 500px at 82% 88%, rgba(164,122,46,0.04) 0%, transparent 55%)",
    pointerEvents: "none",
  },
  card: {
    background: "var(--surface)",
    borderRadius: "var(--r-lg)",
    padding: "48px 44px 36px",
    width: "100%",
    maxWidth: 416,
    boxShadow: "var(--sh-md)",
    border: "1px solid var(--hair)",
    position: "relative",
    zIndex: 1,
  },
  logoBlock: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    marginBottom: 36,
  },
  logoCircle: {
    width: 60,
    height: 60,
    borderRadius: "var(--r-md)",
    background: "var(--paper-2)",
    border: "1px solid var(--hair-2)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 18,
  },
  title: {
    margin: 0,
    color: "var(--ink)",
    fontWeight: 600,
    fontSize: 22,
    letterSpacing: "-0.015em",
  },
  subtitle: {
    color: "var(--muted)",
    fontSize: 13,
    marginTop: 6,
  },
  label: {
    fontSize: 12.5,
    fontWeight: 500,
    color: "var(--t2)",
  },
  input: {
    borderRadius: "var(--r-sm)",
    borderColor: "var(--hair-2)",
    fontSize: 14,
  },
  btn: {
    height: 44,
    borderRadius: "var(--r-sm)",
    background: "var(--brand)",
    border: "none",
    fontSize: 14.5,
    fontWeight: 500,
    boxShadow: "var(--sh-sm)",
  },
  footer: {
    display: "block",
    textAlign: "center",
    color: "var(--muted-2)",
    fontSize: 11,
    marginTop: 28,
  },
};
