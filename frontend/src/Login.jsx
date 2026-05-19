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
            <span style={{ fontSize: 28 }}>⚖️</span>
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
              prefix={<MailOutlined style={{ color: "#b0b6cc" }} />}
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
              prefix={<LockOutlined style={{ color: "#b0b6cc" }} />}
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
    background: "linear-gradient(135deg, #f0f2f9 0%, #e8eaf6 50%, #f5f6fa 100%)",
    padding: 24,
    position: "relative",
    overflow: "hidden",
  },
  bgPattern: {
    position: "absolute",
    inset: 0,
    backgroundImage: "radial-gradient(circle at 25% 25%, rgba(101,116,196,0.08) 0%, transparent 50%), radial-gradient(circle at 75% 75%, rgba(101,116,196,0.06) 0%, transparent 50%)",
    pointerEvents: "none",
  },
  card: {
    background: "#ffffff",
    borderRadius: 16,
    padding: "44px 40px 36px",
    width: "100%",
    maxWidth: 420,
    boxShadow: "0 4px 32px rgba(101,116,196,0.10), 0 1px 4px rgba(0,0,0,0.04)",
    border: "1px solid rgba(101,116,196,0.12)",
    position: "relative",
    zIndex: 1,
  },
  logoBlock: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    marginBottom: 32,
  },
  logoCircle: {
    width: 64,
    height: 64,
    borderRadius: "50%",
    background: "linear-gradient(135deg, #eef0fb, #e4e7f8)",
    border: "1px solid rgba(101,116,196,0.18)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 14,
    boxShadow: "0 2px 12px rgba(101,116,196,0.12)",
  },
  title: {
    margin: 0,
    color: "#1a1d2e",
    fontWeight: 700,
    letterSpacing: "-0.3px",
  },
  subtitle: {
    color: "#8892b0",
    fontSize: 13,
    marginTop: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: 500,
    color: "#4a5568",
  },
  input: {
    borderRadius: 8,
    borderColor: "#e2e5f0",
    fontSize: 14,
  },
  btn: {
    height: 44,
    borderRadius: 8,
    background: "linear-gradient(135deg, #6574c4, #8b6cc8)",
    border: "none",
    fontSize: 15,
    fontWeight: 600,
    boxShadow: "0 2px 12px rgba(101,116,196,0.3)",
  },
  footer: {
    display: "block",
    textAlign: "center",
    color: "#b0b6cc",
    fontSize: 11,
    marginTop: 24,
  },
};
