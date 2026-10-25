import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Refrigerator,
  UserRound,
  Mail,
  LockKeyhole,
  Eye,
  EyeOff,
  Loader2,
  Leaf,
} from 'lucide-react';
import { authApi } from '../services/api';
import './LoginNeumorphic.css';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [isSignup, setIsSignup] = useState(false);
  const [email, setEmail] = useState('demo@smartfridge.com');
  const [password, setPassword] = useState('SmartFridge123!');
  const [showPassword, setShowPassword] = useState(false);
  const [fullName, setFullName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [showSignupPassword, setShowSignupPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Login failed. Check your credentials and backend connection.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    try {
      await authApi.register({
        full_name: fullName.trim(),
        email: signupEmail.trim(),
        password: signupPassword,
      });
      // Use the existing auth context so the new account gets the same session flow as login.
      await login(signupEmail.trim(), signupPassword);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Sign-up failed. Check your details or try another email address.'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const switchMode = (signup: boolean) => {
    setError('');
    setIsSignup(signup);
  };

  return (
    <main className="sf-auth-page">
      <div className={`sf-auth-scene ${isSignup ? 'sf-auth-scene--signup' : ''}`}>
        <div className={`sf-auth-card ${isSignup ? 'sf-auth-card--flipped' : ''}`}>
          <section className="sf-auth-face sf-auth-front" aria-hidden={isSignup}>
            <form className="sf-auth-form" onSubmit={handleSubmit}>
              <div className="sf-auth-brand">
                <span className="sf-auth-logo"><Refrigerator size={27} strokeWidth={1.8} /></span>
                <span>SMART FRIDGE AI</span>
              </div>
              <h1>Welcome back</h1>
              <p className="sf-auth-subtitle">Sign in to manage your fridge and food alerts</p>

              <div className="sf-auth-input">
                <UserRound size={19} aria-hidden="true" />
                <input
                  id="sf-login-email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email address"
                  aria-label="Email address"
                  tabIndex={isSignup ? -1 : 0}
                />
              </div>

              <div className="sf-auth-input">
                <LockKeyhole size={19} aria-hidden="true" />
                <input
                  id="sf-login-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  aria-label="Password"
                  tabIndex={isSignup ? -1 : 0}
                />
                <button
                  className="sf-auth-eye"
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  tabIndex={isSignup ? -1 : 0}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {error && !isSignup && <div role="alert" className="sf-auth-error">{error}</div>}

              <button className="sf-auth-submit" type="submit" disabled={submitting} tabIndex={isSignup ? -1 : 0}>
                {submitting && !isSignup && <Loader2 size={18} className="sf-auth-spinner" />}
                {submitting && !isSignup ? 'Signing in…' : 'Sign in'}
              </button>

              <p className="sf-auth-demo-note">Demo credentials are prefilled for local testing.</p>
              <p className="sf-auth-switch">
                New to Smart Fridge AI?{' '}
                <button type="button" onClick={() => switchMode(true)} tabIndex={isSignup ? -1 : 0}>Create account</button>
              </p>
            </form>
          </section>

          <section className="sf-auth-face sf-auth-back" aria-hidden={!isSignup}>
            <form className="sf-auth-form sf-auth-form--signup" onSubmit={handleSignup}>
              <div className="sf-auth-brand">
                <span className="sf-auth-logo"><Leaf size={27} strokeWidth={1.8} /></span>
                <span>JOIN SMART FRIDGE</span>
              </div>
              <h1>Create account</h1>
              <p className="sf-auth-subtitle">A smarter, fresher kitchen starts here</p>

              <div className="sf-auth-input">
                <UserRound size={19} aria-hidden="true" />
                <input
                  id="sf-signup-name"
                  type="text"
                  autoComplete="name"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Full name"
                  aria-label="Full name"
                  tabIndex={isSignup ? 0 : -1}
                />
              </div>

              <div className="sf-auth-input">
                <Mail size={19} aria-hidden="true" />
                <input
                  id="sf-signup-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder="Email address"
                  aria-label="Email address"
                  tabIndex={isSignup ? 0 : -1}
                />
              </div>

              <div className="sf-auth-input">
                <LockKeyhole size={19} aria-hidden="true" />
                <input
                  id="sf-signup-password"
                  type={showSignupPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={signupPassword}
                  onChange={(e) => setSignupPassword(e.target.value)}
                  placeholder="Password (8+ characters)"
                  aria-label="Create password"
                  tabIndex={isSignup ? 0 : -1}
                />
                <button
                  className="sf-auth-eye"
                  type="button"
                  onClick={() => setShowSignupPassword((value) => !value)}
                  aria-label={showSignupPassword ? 'Hide password' : 'Show password'}
                  tabIndex={isSignup ? 0 : -1}
                >
                  {showSignupPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>

              {error && isSignup && <div role="alert" className="sf-auth-error">{error}</div>}

              <button className="sf-auth-submit" type="submit" disabled={submitting} tabIndex={isSignup ? 0 : -1}>
                {submitting && isSignup && <Loader2 size={18} className="sf-auth-spinner" />}
                {submitting && isSignup ? 'Creating account…' : 'Create account'}
              </button>

              <p className="sf-auth-switch">
                Already have an account?{' '}
                <button type="button" onClick={() => switchMode(false)} tabIndex={isSignup ? 0 : -1}>Sign in</button>
              </p>
            </form>
          </section>
        </div>
      </div>
      <p className="sf-auth-footer">Fresh food. Smarter living.</p>
    </main>
  );
};

export default Login;
