import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Moon, Sun, AlertCircle } from 'lucide-react';
import { DoctorIllustration } from '../components/clinic/DoctorIllustration';
import { useAppStore } from '../store/useAppStore';
import { useAuth } from '../context/AuthContext';
import { login as apiLogin, getMe } from '../api/auth';
import { NetworkError, ApiError } from '../api/client';

// Role → route mapping — must stay in sync with App.jsx route declarations.
const ROLE_ROUTES = {
  nurse:     '/nurse',
  physician: '/physician',
  admin:     '/admin',
};

export default function Login() {
  const navigate        = useNavigate();
  const { login }       = useAuth();
  const darkMode        = useAppStore((s) => s.darkMode);
  const toggleDarkMode  = useAppStore((s) => s.toggleDarkMode);

  const [email,     setEmail]     = useState('');
  const [password,  setPassword]  = useState('');
  const [signingIn, setSigningIn] = useState(false);
  const [error,     setError]     = useState(null); // null | string

  async function handleSignIn(e) {
    e.preventDefault();
    if (signingIn) return;

    setError(null);
    setSigningIn(true);

    try {
      // 1 — Exchange credentials for a token (OAuth2 form-encoded).
      const { access_token } = await apiLogin(email, password);

      // 2 — Fetch the user profile so we know the role.
      //     Store the token in localStorage first so apiFetch() can read it.
      localStorage.setItem('ss_token', access_token);
      const user = await getMe();

      // 3 — Commit to AuthContext (also persists user to localStorage).
      login(access_token, user);

      // 4 — Redirect based on role (backend returns titlecase e.g. "Nurse", "Physician", "Admin").
      const roleKey = user.role?.toLowerCase();
      const destination = ROLE_ROUTES[roleKey] ?? '/nurse';
      navigate(destination, { replace: true });

    } catch (err) {
      if (err instanceof NetworkError) {
        setError("Can't reach the server. Is the backend running?");
      } else if (err instanceof ApiError) {
        if (err.status === 401) {
          setError('Invalid email or password. Please try again.');
        } else {
          setError(`Login failed (${err.status}): ${err.message}`);
        }
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setSigningIn(false);
    }
  }

  return (
    <div className="min-h-screen flex bg-pastel-bg dark:bg-pastel-bgDark transition-colors">
      {/* Left: brand + illustration */}
      <div className="hidden lg:flex flex-1 items-center justify-center relative p-12 bg-pastel-brandLight dark:bg-pastel-brandLightDark">
        <button
          onClick={toggleDarkMode}
          className="absolute top-6 left-6 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/70 dark:bg-white/10 text-pastel-ink dark:text-pastel-inkDark text-[12px] font-medium backdrop-blur-sm"
          aria-pressed={darkMode}
        >
          {darkMode ? <Sun size={13} /> : <Moon size={13} />}
          {darkMode ? 'Light mode' : 'Dark mode'}
        </button>

        <div className="max-w-sm text-center">
          <div className="w-64 h-72 mx-auto mb-4">
            <DoctorIllustration />
          </div>
          <h2 className="text-xl font-semibold text-pastel-ink dark:text-pastel-inkDark mb-2">
            The nurse's gut feeling, quantified
          </h2>
          <p className="text-[13.5px] text-pastel-sub dark:text-pastel-subDark leading-relaxed">
            SilentSepsis catches the trend six hours before the alarm would've gone off — and shows the evidence, not just a score.
          </p>
        </div>
      </div>

      {/* Right: sign-in form */}
      <div className="flex-1 flex items-center justify-center p-8 relative">
        <button
          onClick={toggleDarkMode}
          className="lg:hidden absolute top-6 right-6 flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-pastel-brandLight dark:bg-pastel-brandLightDark text-pastel-ink dark:text-pastel-inkDark text-[12px] font-medium"
          aria-pressed={darkMode}
        >
          {darkMode ? <Sun size={13} /> : <Moon size={13} />}
        </button>

        <form onSubmit={handleSignIn} className="w-full max-w-sm" noValidate>
          <div className="h-9 w-9 rounded-xl bg-pastel-brand flex items-center justify-center text-white text-[15px] font-bold mb-5">S</div>
          <h1 className="text-[22px] font-semibold text-pastel-ink dark:text-pastel-inkDark mb-1">Welcome back</h1>
          <p className="text-[13.5px] text-pastel-sub dark:text-pastel-subDark mb-7">Sign in to your ward dashboard.</p>

          {/* Error banner */}
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 mb-5 px-3.5 py-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-[12.5px] leading-snug"
            >
              <AlertCircle size={14} className="mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <label
            htmlFor="login-email"
            className="block text-[12.5px] font-medium text-pastel-ink dark:text-pastel-inkDark mb-1.5"
          >
            Email
          </label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            placeholder="e.g. n.thomas@hospital.org"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full h-11 px-3.5 mb-4 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark bg-white dark:bg-pastel-cardDark text-[13.5px] text-pastel-ink dark:text-pastel-inkDark outline-none focus:border-pastel-brand transition-colors"
          />

          <label
            htmlFor="login-password"
            className="block text-[12.5px] font-medium text-pastel-ink dark:text-pastel-inkDark mb-1.5"
          >
            Password
          </label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full h-11 px-3.5 mb-6 rounded-xl border border-pastel-brandLight dark:border-pastel-borderDark bg-white dark:bg-pastel-cardDark text-[13.5px] text-pastel-ink dark:text-pastel-inkDark outline-none focus:border-pastel-brand transition-colors"
          />

          <button
            type="submit"
            disabled={signingIn}
            className="w-full h-11 rounded-xl bg-pastel-brand hover:bg-[#0B5D74] text-white text-[13.5px] font-semibold transition-colors flex items-center justify-center gap-2 disabled:opacity-70"
          >
            {signingIn && <span className="h-3.5 w-3.5 rounded-full border-2 border-white/40 border-t-white animate-spin" aria-hidden="true" />}
            {signingIn ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="text-[11.5px] text-pastel-sub dark:text-pastel-subDark text-center mt-5">
            Works offline. Vitals sync when reconnected.
          </p>
        </form>
      </div>
    </div>
  );
}
