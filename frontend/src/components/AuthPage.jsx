import { useState } from 'react'
import { login, register } from '../api'
import { AlertCircle, Loader } from 'lucide-react'

export default function AuthPage({ onAuth }) {
  const [mode,     setMode]     = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState(null)
  const [success,  setSuccess]  = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null); setSuccess(null); setLoading(true)
    try {
      if (mode === 'login') {
        await login(username.trim().toLowerCase(), password)
        onAuth()
      } else {
        await register(username.trim().toLowerCase(), password)
        setSuccess('Account created — you can now sign in.')
        setMode('login'); setPassword('')
      }
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400&display=swap');
        body { background:#080c18; margin:0; }
        .auth-root {
          min-height:100vh; display:flex; flex-direction:column;
          align-items:center; justify-content:center;
          background:#080c18; padding:24px;
          font-family:'DM Sans',sans-serif;
        }
        .auth-orb {
          position:fixed; pointer-events:none; border-radius:50%; filter:blur(90px);
        }
        .auth-orb-1 { width:500px;height:400px;top:-80px;left:-80px;background:rgba(245,166,35,0.05); }
        .auth-orb-2 { width:350px;height:350px;bottom:-60px;right:-60px;background:rgba(59,130,246,0.04); }
        .auth-brand {
          display:flex;align-items:center;gap:9px;margin-bottom:36px;
          font-family:'Playfair Display',serif;font-size:20px;color:#dde2f0;
        }
        .auth-brand-dot {
          width:8px;height:8px;border-radius:50%;
          background:#f5a623;box-shadow:0 0 10px #f5a623;
        }
        .auth-card {
          position:relative;z-index:1;
          width:100%;max-width:360px;
          background:#0d1225;
          border:1px solid rgba(255,255,255,0.07);
          border-radius:18px;padding:28px;
        }
        .auth-tabs {
          display:flex;gap:4px;padding:4px;
          background:rgba(255,255,255,0.03);
          border:1px solid rgba(255,255,255,0.06);
          border-radius:10px;margin-bottom:24px;
        }
        .auth-tab {
          flex:1;padding:7px;border-radius:7px;border:none;cursor:pointer;
          font-size:12px;font-weight:500;font-family:'DM Sans',sans-serif;
          transition:all 0.15s;background:transparent;color:#4e5a7a;
        }
        .auth-tab.active { background:#f5a623;color:#080c18;font-weight:600; }
        .auth-tab:not(.active):hover { color:#7b87aa; }
        .auth-alert {
          display:flex;align-items:flex-start;gap:8px;
          padding:10px 12px;border-radius:8px;font-size:12px;
          line-height:1.5;margin-bottom:16px;
        }
        .auth-alert.error { background:rgba(248,113,113,0.08);border:1px solid rgba(248,113,113,0.2);color:#f87171; }
        .auth-alert.success { background:rgba(52,211,153,0.08);border:1px solid rgba(52,211,153,0.2);color:#34d399; }
        .auth-field { display:flex;flex-direction:column;gap:6px;margin-bottom:14px; }
        .auth-label {
          font-family:'DM Mono',monospace;font-size:9px;
          letter-spacing:0.14em;text-transform:uppercase;color:#4e5a7a;
        }
        .auth-input {
          background:rgba(255,255,255,0.03);
          border:1px solid rgba(255,255,255,0.08);
          border-radius:9px;padding:10px 14px;
          font-size:13px;color:#dde2f0;outline:none;
          font-family:'DM Sans',sans-serif;
          transition:border-color 0.15s;
        }
        .auth-input::placeholder { color:#4e5a7a; }
        .auth-input:focus { border-color:rgba(245,166,35,0.4); }
        .auth-btn {
          width:100%;padding:11px;border-radius:9px;border:none;cursor:pointer;
          font-size:13px;font-weight:600;font-family:'DM Sans',sans-serif;
          background:#f5a623;color:#080c18;margin-top:6px;
          display:flex;align-items:center;justify-content:center;gap:7px;
          transition:all 0.15s;
        }
        .auth-btn:hover:not(:disabled) { background:#fbbf24;transform:translateY(-1px); }
        .auth-btn:disabled { opacity:0.45;cursor:not-allowed; }
        .auth-hint { font-size:11px;color:#4e5a7a;text-align:center;margin-top:14px;line-height:1.5; }
      `}</style>

      <div className="auth-root">
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />

        <div className="auth-brand">
          <span className="auth-brand-dot" />
          CommentIQ
        </div>

        <div className="auth-card">
          <div className="auth-tabs">
            {['login', 'register'].map(m => (
              <button
                key={m} onClick={() => { setMode(m); setError(null); setSuccess(null); }}
                className={`auth-tab ${mode === m ? 'active' : ''}`}
                style={{ textTransform: 'capitalize' }}
              >{m}</button>
            ))}
          </div>

          {success && <div className="auth-alert success">{success}</div>}
          {error   && (
            <div className="auth-alert error">
              <AlertCircle size={13} style={{ flexShrink:0, marginTop:1 }} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="auth-field">
              <label className="auth-label">Username</label>
              <input className="auth-input" type="text" placeholder="yourname"
                value={username} onChange={e => setUsername(e.target.value)} required autoFocus />
            </div>
            <div className="auth-field">
              <label className="auth-label">Password</label>
              <input className="auth-input" type="password" placeholder="••••••••"
                value={password} onChange={e => setPassword(e.target.value)} required minLength={6} />
            </div>
            <button type="submit" className="auth-btn" disabled={loading || !username || !password}>
              {loading && <Loader size={13} style={{ animation:'spin 0.8s linear infinite' }} />}
              {mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          {mode === 'register' && (
            <p className="auth-hint">Password must be at least 6 characters.</p>
          )}
        </div>
      </div>
    </>
  )
}