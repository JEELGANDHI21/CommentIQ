import { useState } from 'react'
import { Search, SlidersHorizontal } from 'lucide-react'

export default function UrlForm({ onSubmit, loading }) {
  const [url,         setUrl]         = useState('')
  const [maxComments, setMaxComments] = useState(300)
  const [threshold,   setThreshold]   = useState(0.20)
  const [showOptions, setShowOptions] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!url.trim()) return
    onSubmit(url.trim(), maxComments, threshold)
  }

  return (
    <>
      <style>{`
        .url-form { width:100%; }
        .url-input-row {
          display:flex;align-items:center;gap:0;
          background:rgba(255,255,255,0.04);
          border:1px solid rgba(255,255,255,0.1);
          border-radius:12px;padding:6px 6px 6px 16px;
          transition:border-color 0.2s,box-shadow 0.2s;
        }
        .url-input-row:focus-within {
          border-color:rgba(245,166,35,0.5);
          box-shadow:0 0 0 3px rgba(245,166,35,0.08);
        }
        .url-icon { color:#4e5a7a;flex-shrink:0;margin-right:10px; }
        .url-input {
          flex:1;background:transparent;border:none;outline:none;
          font-size:14px;color:#dde2f0;font-family:'DM Sans',sans-serif;
        }
        .url-input::placeholder { color:#4e5a7a; }
        .url-submit {
          flex-shrink:0;
          background:#f5a623;color:#080c18;
          border:none;border-radius:8px;
          padding:9px 20px;font-size:13px;font-weight:600;
          cursor:pointer;font-family:'DM Sans',sans-serif;
          transition:all 0.15s;white-space:nowrap;
        }
        .url-submit:hover:not(:disabled) { background:#fbbf24;transform:translateY(-1px); }
        .url-submit:disabled { opacity:0.4;cursor:not-allowed; }
        .url-options-toggle {
          display:flex;align-items:center;gap:5px;justify-content:center;
          margin-top:10px;
          font-size:11px;color:#4e5a7a;background:none;border:none;cursor:pointer;
          font-family:'DM Sans',sans-serif;transition:color 0.15s;
        }
        .url-options-toggle:hover { color:#7b87aa; }
        .url-options {
          margin-top:10px;
          background:rgba(255,255,255,0.02);
          border:1px solid rgba(255,255,255,0.07);
          border-radius:12px;padding:16px;
          display:grid;grid-template-columns:1fr 1fr;gap:16px;
        }
        .opt-label {
          font-family:'DM Mono',monospace;font-size:9px;
          letter-spacing:0.13em;text-transform:uppercase;
          color:#4e5a7a;display:block;margin-bottom:7px;
        }
        .opt-input {
          width:100%;background:rgba(255,255,255,0.04);
          border:1px solid rgba(255,255,255,0.08);
          border-radius:7px;padding:7px 11px;
          font-size:12px;color:#dde2f0;outline:none;
          font-family:'DM Sans',sans-serif;
          transition:border-color 0.15s;
        }
        .opt-input:focus { border-color:rgba(245,166,35,0.3); }
        .opt-slider-row { display:flex;align-items:center;gap:8px; }
        .opt-slider {
          flex:1;accent-color:#f5a623;height:3px;
        }
        .opt-val {
          font-family:'DM Mono',monospace;font-size:11px;
          color:#7b87aa;min-width:30px;text-align:right;
        }
      `}</style>

      <form className="url-form" onSubmit={handleSubmit}>
        <div className="url-input-row">
          <Search size={15} className="url-icon" />
          <input
            className="url-input"
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="Paste a YouTube URL…"
            disabled={loading}
          />
          <button type="submit" className="url-submit" disabled={loading || !url.trim()}>
            {loading ? 'Running…' : 'Analyse →'}
          </button>
        </div>

        <button type="button" className="url-options-toggle" onClick={() => setShowOptions(v => !v)}>
          <SlidersHorizontal size={10} strokeWidth={2.5} />
          {showOptions ? 'Hide options' : 'Advanced options'}
        </button>

        {showOptions && (
          <div className="url-options">
            <div>
              <span className="opt-label">Max comments</span>
              <input className="opt-input" type="number" min={50} max={1000} step={50}
                value={maxComments} onChange={e => setMaxComments(Number(e.target.value))} />
            </div>
            <div>
              <span className="opt-label">Relevance threshold</span>
              <div className="opt-slider-row">
                <input className="opt-slider" type="range" min={0.10} max={0.40} step={0.05}
                  value={threshold} onChange={e => setThreshold(Number(e.target.value))} />
                <span className="opt-val">{threshold.toFixed(2)}</span>
              </div>
            </div>
          </div>
        )}
      </form>
    </>
  )
}