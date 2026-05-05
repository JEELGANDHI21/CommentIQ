import { useState, useEffect, useRef } from 'react'
import { startAnalysis, pollStatus, fetchComments, fetchUsage, isLoggedIn, logout, getUsername } from './api'
import AuthPage from './components/AuthPage'
import UrlForm from './components/UrlForm'
import ProgressTracker from './components/ProgressTracker'
import SentimentChart from './components/SentimentChart'
import CommentTable from './components/CommentTable'
import ReportCard from './components/ReportCard'
import { RotateCcw, AlertCircle, LogOut, Zap } from 'lucide-react'

export default function App() {
  const [authed, setAuthed] = useState(isLoggedIn())
  const [usage, setUsage] = useState(null)
  const [phase, setPhase] = useState('idle')
  const [job, setJob] = useState(null)
  const [result, setResult] = useState(null)
  const [comments, setComments] = useState([])
  const [activeFilter, setActiveFilter] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    if (authed) fetchUsage().then(setUsage).catch(() => {})
  }, [authed])

  useEffect(() => {
    if (!job || phase !== 'running') return
    pollRef.current = setInterval(async () => {
      try {
        const status = await pollStatus(job.job_id)
        setJob(status)
        if (status.status === 'done') {
          clearInterval(pollRef.current)
          setResult(status.result)
          setPhase('done')
          loadComments(status.result?.video_id, null)
          fetchUsage().then(setUsage).catch(() => {})
        } else if (status.status === 'error') {
          clearInterval(pollRef.current)
          setError(status.error || 'Pipeline failed.')
          setPhase('error')
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setError(e.message)
        setPhase('error')
      }
    }, 2500)
    return () => clearInterval(pollRef.current)
  }, [job?.job_id, phase])

  async function loadComments(videoId, sentiment) {
    try {
      const data = await fetchComments(videoId, sentiment, 50)
      setComments(data)
    } catch (err) { console.error(err) }
  }

  async function handleSubmit(url, maxComments, threshold) {
    setPhase('running'); setError(null); setResult(null); setComments([])
    try {
      const j = await startAnalysis(url, maxComments, threshold)
      setJob(j)
    } catch (e) { setError(e.message); setPhase('error') }
  }

  function handleFilterChange(sentiment) {
    setActiveFilter(sentiment)
    if (result?.video_id) loadComments(result.video_id, sentiment)
  }

  function handleReset() {
    clearInterval(pollRef.current)
    setPhase('idle'); setJob(null); setResult(null)
    setComments([]); setError(null); setActiveFilter(null)
  }

  function handleLogout() { logout(); setAuthed(false); handleReset() }

  if (!authed) return <AuthPage onAuth={() => setAuthed(true)} />

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,700;1,700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');

        :root {
          --bg:     #080c18;
          --bg2:    #0d1225;
          --bg3:    #121830;
          --border: rgba(255,255,255,0.06);
          --border2:rgba(255,255,255,0.1);
          --amber:  #f5a623;
          --amber2: #fbbf24;
          --text:   #dde2f0;
          --muted:  #4e5a7a;
          --muted2: #7b87aa;
          --green:  #34d399;
          --red:    #f87171;
          --r: 14px;
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: var(--bg);
          color: var(--text);
          font-family: 'DM Sans', system-ui, sans-serif;
          -webkit-font-smoothing: antialiased;
          min-height: 100vh;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }

        /* ─ Animations ─ */
        @keyframes fadeUp {
          from { opacity:0; transform:translateY(20px); }
          to   { opacity:1; transform:translateY(0); }
        }
        @keyframes glow {
          0%,100% { opacity:1; } 50% { opacity:0.35; }
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse {
          0%   { box-shadow: 0 0 0 0 rgba(245,166,35,0.6); }
          70%  { box-shadow: 0 0 0 12px rgba(245,166,35,0); }
          100% { box-shadow: 0 0 0 0 rgba(245,166,35,0); }
        }
        @keyframes shimmer {
          from { background-position: -200% center; }
          to   { background-position: 200% center; }
        }

        .fade-up { animation: fadeUp 0.55s cubic-bezier(.22,1,.36,1) both; }

        /* ─ Header ─ */
        .hdr {
          position: sticky; top: 0; z-index: 100;
          height: 54px;
          display: flex; align-items: center;
          border-bottom: 1px solid var(--border);
          background: rgba(8,12,24,0.9);
          backdrop-filter: blur(24px);
        }
        .hdr-inner {
          width: 100%; max-width: 1120px; margin: 0 auto;
          padding: 0 28px;
          display: flex; align-items: center; justify-content: space-between;
        }
        .logo {
          display: flex; align-items: center; gap: 9px;
          font-family: 'Playfair Display', serif;
          font-size: 17px; letter-spacing: 0.01em; color: var(--text);
          text-decoration: none;
        }
        .logo-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--amber);
          box-shadow: 0 0 10px var(--amber);
          animation: glow 2.5s ease-in-out infinite;
          flex-shrink: 0;
        }
        .hdr-right { display: flex; align-items: center; gap: 12px; }
        .hdr-divider { width: 1px; height: 20px; background: var(--border2); }

        .usage-pill {
          display: flex; align-items: center; gap: 5px;
          font-family: 'DM Mono', monospace; font-size: 10px;
          padding: 3px 9px; border-radius: 99px;
          border: 1px solid rgba(245,166,35,0.2);
          background: rgba(245,166,35,0.07);
          color: var(--amber); cursor: default;
          transition: all 0.2s;
        }
        .usage-pill.warn  { border-color:rgba(251,191,36,0.3); background:rgba(251,191,36,0.1); color:var(--amber2); }
        .usage-pill.danger{ border-color:rgba(248,113,113,0.3); background:rgba(248,113,113,0.08); color:var(--red); }

        .hdr-user {
          font-family: 'DM Mono', monospace; font-size: 11px;
          color: var(--muted2);
        }

        .btn-icon {
          width: 30px; height: 30px; border-radius: 8px;
          border: 1px solid var(--border);
          background: transparent; cursor: pointer;
          display: flex; align-items: center; justify-content: center;
          color: var(--muted2); transition: all 0.15s;
        }
        .btn-icon:hover { border-color: var(--border2); color: var(--text); background: rgba(255,255,255,0.04); }
        .btn-icon.danger:hover { border-color: rgba(248,113,113,0.3); color: var(--red); }

        .btn-ghost-sm {
          display: flex; align-items: center; gap: 5px;
          font-size: 11px; color: var(--muted2); background: none;
          border: 1px solid var(--border); border-radius: 8px;
          padding: 5px 11px; cursor: pointer; font-family: 'DM Sans', sans-serif;
          transition: all 0.15s;
        }
        .btn-ghost-sm:hover { border-color: var(--border2); color: var(--text); }

        /* ─ Main ─ */
        .main {
          position: relative;
          max-width: 1120px; margin: 0 auto; padding: 0 28px 100px;
        }

        /* Ambient orbs */
        .orb {
          position: fixed; pointer-events: none; z-index: 0;
          border-radius: 50%; filter: blur(80px);
        }
        .orb-1 { width: 500px; height: 400px; top: -100px; left: -100px; background: rgba(245,166,35,0.045); }
        .orb-2 { width: 400px; height: 400px; bottom: 0; right: -100px; background: rgba(59,130,246,0.04); }

        /* ─ Hero ─ */
        .hero {
          position: relative; z-index: 1;
          padding-top: 100px;
          display: flex; flex-direction: column; align-items: center;
          text-align: center; gap: 0;
        }

        .eyebrow {
          display: inline-flex; align-items: center; gap: 6px;
          font-family: 'DM Mono', monospace; font-size: 9px;
          letter-spacing: 0.18em; text-transform: uppercase;
          color: var(--amber);
          padding: 5px 12px; border-radius: 99px;
          border: 1px solid rgba(245,166,35,0.22);
          background: rgba(245,166,35,0.07);
          margin-bottom: 28px;
        }
        .eyebrow-dot { width: 4px; height: 4px; border-radius: 50%; background: var(--amber); }

        .hero-title {
          font-family: 'Playfair Display', serif;
          font-size: clamp(44px, 7vw, 76px);
          line-height: 1.08; font-weight: 700;
          color: var(--text); margin-bottom: 20px;
        }
        .hero-title em {
          font-style: italic;
          background: linear-gradient(135deg, var(--amber) 0%, var(--amber2) 100%);
          -webkit-background-clip: text; -webkit-text-fill-color: transparent;
          background-clip: text;
        }
        .hero-sub {
          font-size: 14px; color: var(--muted2); line-height: 1.7;
          max-width: 380px; margin-bottom: 44px;
        }

        .hero-form-wrap {
          width: 100%; max-width: 600px; margin-bottom: 44px;
          position: relative;
        }

        .tech-pills {
          display: flex; gap: 6px; flex-wrap: wrap; justify-content: center;
        }
        .tech-pill {
          font-family: 'DM Mono', monospace; font-size: 10px;
          padding: 3px 10px; border-radius: 99px;
          border: 1px solid var(--border);
          background: rgba(255,255,255,0.02);
          color: var(--muted2);
        }

        /* ─ Running ─ */
        .running-wrap {
          position: relative; z-index: 1;
          padding-top: 90px;
          display: flex; flex-direction: column; align-items: center; gap: 44px;
        }
        .running-title-row {
          display: flex; align-items: center; gap: 12px;
        }
        .pulse-dot {
          width: 9px; height: 9px; border-radius: 50%;
          background: var(--amber); flex-shrink: 0;
          animation: pulse 1.8s ease-in-out infinite;
        }
        .running-title {
          font-family: 'DM Mono', monospace; font-size: 11px;
          letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted2);
        }

        /* ─ Error ─ */
        .err-wrap {
          position: relative; z-index: 1;
          padding-top: 80px;
          display: flex; flex-direction: column; align-items: center; gap: 16px;
        }
        .err-box {
          display: flex; align-items: flex-start; gap: 12px;
          background: rgba(248,113,113,0.07);
          border: 1px solid rgba(248,113,113,0.18);
          border-radius: var(--r); padding: 16px 20px;
          max-width: 480px; color: var(--red); font-size: 13px; line-height: 1.5;
        }
        .err-icon { flex-shrink: 0; margin-top: 1px; }

        /* ─ Results ─ */
        .results-wrap {
          position: relative; z-index: 1;
          padding-top: 36px;
          display: grid;
          grid-template-columns: 1fr 340px;
          gap: 16px;
          align-items: start;
        }
        @media (max-width: 860px) {
          .results-wrap { grid-template-columns: 1fr; }
        }
        .results-col { display: flex; flex-direction: column; gap: 16px; }

        /* ─ Panel ─ */
        .panel {
          background: var(--bg2);
          border: 1px solid var(--border);
          border-radius: var(--r); padding: 22px;
        }
        .panel-hd {
          font-family: 'DM Mono', monospace; font-size: 9px;
          letter-spacing: 0.15em; text-transform: uppercase;
          color: var(--muted); margin-bottom: 18px;
          display: flex; align-items: center; gap: 6px;
        }
        .panel-hd::before {
          content: ''; width: 3px; height: 3px; border-radius: 50%;
          background: var(--amber); flex-shrink: 0;
        }
      `}</style>

      {/* Ambient orbs */}
      <div className="orb orb-1" />
      <div className="orb orb-2" />

      {/* Header */}
      <header className="hdr">
        <div className="hdr-inner">
          <div className="logo">
            <span className="logo-dot" />
            CommentIQ
          </div>

          <div className="hdr-right">
            {phase !== 'idle' && (
              <button onClick={handleReset} className="btn-ghost-sm">
                <RotateCcw size={11} strokeWidth={2.5} />
                New analysis
              </button>
            )}

            {usage && (
              <div
                className={`usage-pill ${usage.remaining === 0 ? 'danger' : usage.remaining <= 3 ? 'warn' : ''}`}
                title={`${usage.used} used · resets ${usage.reset_at} UTC`}
              >
                <Zap size={9} strokeWidth={3} />
                {usage.remaining}/{usage.limit} today
              </div>
            )}

            <div className="hdr-divider" />
            <span className="hdr-user">{getUsername()}</span>
            <button onClick={handleLogout} className="btn-icon danger" title="Sign out">
              <LogOut size={13} strokeWidth={2} />
            </button>
          </div>
        </div>
      </header>

      {/* Main */}
      <div className="main">

        {/* IDLE */}
        {phase === 'idle' && (
          <div className="hero fade-up">
            <div className="eyebrow">
              <span className="eyebrow-dot" />
              AI-Powered YouTube Analysis
            </div>
            <h1 className="hero-title">
              What does the<br /><em>internet</em> think?
            </h1>
            <p className="hero-sub">
              Drop any YouTube URL. We collect comments, filter noise,
              classify sentiment with RoBERTa, and generate an AI report.
            </p>
            <div className="hero-form-wrap">
              <UrlForm onSubmit={handleSubmit} loading={false} />
            </div>
            <div className="tech-pills">
              {['RoBERTa', 'MiniLM-L6', 'OpenRouter', 'FastAPI'].map(t => (
                <span key={t} className="tech-pill">{t}</span>
              ))}
            </div>
          </div>
        )}

        {/* RUNNING */}
        {phase === 'running' && (
          <div className="running-wrap fade-up">
            <div className="running-title-row">
              <span className="pulse-dot" />
              <span className="running-title">Pipeline running</span>
            </div>
            <ProgressTracker
              stage={job?.stage ?? 0}
              progressPct={job?.progress_pct ?? 0}
              status={job?.status ?? 'running'}
            />
          </div>
        )}

        {/* ERROR */}
        {phase === 'error' && (
          <div className="err-wrap fade-up">
            <div className="err-box">
              <AlertCircle size={17} className="err-icon" />
              <span>{error}</span>
            </div>
            <button onClick={handleReset} className="btn-ghost-sm">Try again</button>
          </div>
        )}

        {/* DONE */}
        {phase === 'done' && result && (
          <div className="results-wrap fade-up">
            <div className="results-col">
              <ReportCard result={result} />
              <div className="panel">
                <div className="panel-hd">Sentiment breakdown</div>
                <SentimentChart {...result} />
              </div>
            </div>
            <div className="panel" style={{ height: 'fit-content' }}>
              <div className="panel-hd">Top comments</div>
              <CommentTable
                comments={comments}
                onFilterChange={handleFilterChange}
                activeFilter={activeFilter}
              />
            </div>
          </div>
        )}
      </div>
    </>
  )
}