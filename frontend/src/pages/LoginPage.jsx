import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext.jsx";
import { AlertIcon, CalendarIcon, EyeIcon, EyeOffIcon } from "../components/Icons.jsx";

export default function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (status === "loading") return null;
  if (status === "authenticated") return <Navigate to="/rooms" replace />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate(location.state?.from?.pathname ?? "/rooms", { replace: true });
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-card" onSubmit={handleSubmit} noValidate>
        <span className="brand-mark">
          <CalendarIcon width={30} height={30} />
        </span>
        <h1>Room Booking</h1>
        <p className="muted">Sign in to your account</p>

        <label className="field">
          <span>Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>

        <label className="field">
          <span>Password</span>
          <span className="input-with-action">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <button
              type="button"
              className="icon-button"
              onClick={() => setShowPassword((shown) => !shown)}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOffIcon /> : <EyeIcon />}
            </button>
          </span>
        </label>

        <button type="submit" className="button button--primary button--block" disabled={submitting}>
          {submitting ? "Signing in…" : "Login"}
        </button>

        {error && (
          <div className="banner banner--error" role="alert">
            <AlertIcon /> {error}
          </div>
        )}
      </form>
    </div>
  );
}
