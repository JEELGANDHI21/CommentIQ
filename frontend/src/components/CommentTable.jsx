import { ThumbsUp } from 'lucide-react'

const SENT_COLORS = {
  positive: { bg:'rgba(52,211,153,0.08)', border:'rgba(52,211,153,0.18)', text:'#34d399' },
  negative: { bg:'rgba(248,113,113,0.08)', border:'rgba(248,113,113,0.18)', text:'#f87171' },
  neutral:  { bg:'rgba(123,135,170,0.08)', border:'rgba(123,135,170,0.18)', text:'#7b87aa' },
}
const FILTERS = ['all', 'positive', 'negative', 'neutral']

export default function CommentTable({ comments, onFilterChange, activeFilter }) {
  return (
    <>
      <style>{`
        .ct-filters { display:flex;gap:4px;margin-bottom:14px;flex-wrap:wrap; }
        .ct-filter {
          padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,0.07);
          background:transparent;cursor:pointer;font-size:11px;color:#4e5a7a;
          font-family:'DM Sans',sans-serif;transition:all 0.15s;text-transform:capitalize;
        }
        .ct-filter:hover { color:#7b87aa;border-color:rgba(255,255,255,0.12); }
        .ct-filter.active { background:#f5a623;border-color:#f5a623;color:#080c18;font-weight:600; }
        .ct-list {
          display:flex;flex-direction:column;gap:8px;
          max-height:520px;overflow-y:auto;padding-right:2px;
        }
        .ct-card {
          background:rgba(255,255,255,0.02);
          border:1px solid rgba(255,255,255,0.06);
          border-radius:10px;padding:11px 13px;
          transition:border-color 0.15s;
        }
        .ct-card:hover { border-color:rgba(255,255,255,0.1); }
        .ct-top { display:flex;align-items:flex-start;justify-content:space-between;gap:8px; }
        .ct-text { font-size:12px;color:#c8cfe8;line-height:1.55;flex:1; }
        .ct-badge {
          flex-shrink:0;font-size:9px;padding:2px 7px;border-radius:99px;
          font-family:'DM Mono',monospace;font-weight:500;text-transform:capitalize;
          border:1px solid;
        }
        .ct-meta {
          display:flex;align-items:center;gap:8px;margin-top:7px;
          font-size:10px;color:#4e5a7a;font-family:'DM Mono',monospace;
        }
        .ct-likes { display:flex;align-items:center;gap:3px;margin-left:auto; }
        .ct-empty { text-align:center;padding:32px 0;font-size:12px;color:#4e5a7a; }
      `}</style>

      <div className="ct-filters">
        {FILTERS.map(f => (
          <button key={f}
            onClick={() => onFilterChange(f === 'all' ? null : f)}
            className={`ct-filter ${(f === 'all' && !activeFilter) || f === activeFilter ? 'active' : ''}`}>
            {f}
          </button>
        ))}
      </div>

      <div className="ct-list">
        {comments.length === 0 && <div className="ct-empty">No comments found.</div>}
        {comments.map((c, i) => {
          const sc = SENT_COLORS[c.sentiment] || SENT_COLORS.neutral
          return (
            <div key={i} className="ct-card">
              <div className="ct-top">
                <p className="ct-text">{c.text}</p>
                <span className="ct-badge" style={{ background:sc.bg, borderColor:sc.border, color:sc.text }}>
                  {c.sentiment}
                </span>
              </div>
              <div className="ct-meta">
                <span>{c.author}</span>
                <span style={{marginLeft:'auto',fontFamily:'DM Mono,monospace'}}>
                  w={c.weighted_sentiment?.toFixed(3)}
                </span>
                <span className="ct-likes">
                  <ThumbsUp size={9} /> {c.like_count}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </>
  )
}