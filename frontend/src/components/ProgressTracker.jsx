import { Check, Circle, Loader } from 'lucide-react'

const STAGES = [
  { n: 1, label: 'Collecting comments',         desc: 'YouTube API + AI summary' },
  { n: 2, label: 'Filtering relevant comments', desc: 'Cosine similarity matching' },
  { n: 3, label: 'Analysing sentiment',         desc: 'RoBERTa classification' },
  { n: 4, label: 'Generating AI report',        desc: 'OpenRouter synthesis' },
]

export default function ProgressTracker({ stage, progressPct, status }) {
  return (
    <>
      <style>{`
        .pt-wrap { width:100%;max-width:460px; }
        .pt-bar-track {
          height:2px;background:rgba(255,255,255,0.06);
          border-radius:99px;margin-bottom:36px;overflow:hidden;
        }
        .pt-bar-fill {
          height:100%;border-radius:99px;
          background:linear-gradient(90deg,#f5a623,#fbbf24);
          transition:width 0.7s cubic-bezier(.22,1,.36,1);
          box-shadow:0 0 8px rgba(245,166,35,0.5);
        }
        .pt-stages { display:flex;flex-direction:column;gap:0; }
        .pt-stage {
          display:flex;align-items:flex-start;gap:16px;
          padding:14px 0;
          border-bottom:1px solid rgba(255,255,255,0.04);
          transition:opacity 0.3s;
        }
        .pt-stage:last-child { border-bottom:none; }
        .pt-stage.pending { opacity:0.25; }
        .pt-icon-wrap {
          width:28px;height:28px;border-radius:8px;
          display:flex;align-items:center;justify-content:center;
          flex-shrink:0;margin-top:1px;
        }
        .pt-icon-wrap.done    { background:rgba(52,211,153,0.12);border:1px solid rgba(52,211,153,0.2); }
        .pt-icon-wrap.active  { background:rgba(245,166,35,0.12);border:1px solid rgba(245,166,35,0.25); }
        .pt-icon-wrap.pending { background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07); }
        .pt-text { flex:1; }
        .pt-label {
          font-size:13px;font-weight:500;color:#dde2f0;margin-bottom:3px;
        }
        .pt-desc { font-size:11px;color:#4e5a7a; }
        .pt-dots {
          display:flex;align-items:center;gap:3px;margin-top:6px;
        }
        .pt-dot {
          width:3px;height:3px;border-radius:50%;background:#f5a623;
          animation:dotPulse 1.2s ease-in-out infinite;
        }
        .pt-dot:nth-child(2) { animation-delay:0.15s; }
        .pt-dot:nth-child(3) { animation-delay:0.3s; }
        @keyframes dotPulse {
          0%,100%{opacity:1;transform:scale(1)}
          50%{opacity:0.3;transform:scale(0.6)}
        }
        @keyframes spinIcon { to{transform:rotate(360deg)} }
      `}</style>

      <div className="pt-wrap">
        <div className="pt-bar-track">
          <div className="pt-bar-fill" style={{ width: `${progressPct ?? 0}%` }} />
        </div>

        <div className="pt-stages">
          {STAGES.map(s => {
            const done    = stage > s.n || status === 'done'
            const active  = stage === s.n && status === 'running'
            const pending = !done && !active

            return (
              <div key={s.n} className={`pt-stage ${pending ? 'pending' : ''}`}>
                <div className={`pt-icon-wrap ${done ? 'done' : active ? 'active' : 'pending'}`}>
                  {done   && <Check size={13} color="#34d399" strokeWidth={2.5} />}
                  {active && <Loader size={13} color="#f5a623" style={{ animation:'spinIcon 0.9s linear infinite' }} />}
                  {pending && <Circle size={13} color="#4e5a7a" />}
                </div>
                <div className="pt-text">
                  <div className="pt-label">{s.label}</div>
                  <div className="pt-desc">{s.desc}</div>
                  {active && (
                    <div className="pt-dots">
                      <div className="pt-dot" />
                      <div className="pt-dot" />
                      <div className="pt-dot" />
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </>
  )
}