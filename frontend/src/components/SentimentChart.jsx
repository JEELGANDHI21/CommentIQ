import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'

const COLORS = { positive: '#34d399', negative: '#f87171', neutral: '#7b87aa' }
const LABELS = { positive: 'Positive', negative: 'Negative', neutral: 'Neutral' }

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0]
  return (
    <div style={{
      background:'#0d1225',border:'1px solid rgba(255,255,255,0.1)',
      borderRadius:8,padding:'8px 12px',fontSize:12,color:'#dde2f0',
      fontFamily:'DM Mono,monospace'
    }}>
      {LABELS[d.name]} — {d.value}%
    </div>
  )
}

export default function SentimentChart({ positive_pct, negative_pct, neutral_pct,
                                         positive_count, negative_count, neutral_count }) {
  const data = [
    { name: 'positive', value: positive_pct,  count: positive_count },
    { name: 'negative', value: negative_pct,  count: negative_count },
    { name: 'neutral',  value: neutral_pct,   count: neutral_count  },
  ]
  const dominant = data.reduce((a, b) => b.value > a.value ? b : a)

  return (
    <>
      <style>{`
        .sc-wrap { display:flex;align-items:center;gap:28px; }
        .sc-pie  { width:130px;height:130px;flex-shrink:0; }
        .sc-legend { flex:1;display:flex;flex-direction:column;gap:12px; }
        .sc-row  { display:flex;align-items:center;gap:10px; }
        .sc-dot  { width:8px;height:8px;border-radius:2px;flex-shrink:0; }
        .sc-name { font-size:13px;color:#dde2f0;flex:1; }
        .sc-count{ font-size:11px;color:#4e5a7a; }
        .sc-pct  { font-family:'DM Mono',monospace;font-size:12px;color:#7b87aa; }
        .sc-bar-track {
          width:100%;height:2px;background:rgba(255,255,255,0.06);
          border-radius:99px;margin-top:5px;overflow:hidden;
        }
        .sc-bar-fill { height:100%;border-radius:99px;transition:width 1s ease; }
      `}</style>

      <div className="sc-wrap">
        <div className="sc-pie">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" cx="50%" cy="50%"
                innerRadius={38} outerRadius={58} strokeWidth={0} paddingAngle={3}>
                {data.map(d => (
                  <Cell key={d.name} fill={COLORS[d.name]}
                    opacity={d.name === dominant.name ? 1 : 0.5} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="sc-legend">
          {data.map(d => (
            <div key={d.name}>
              <div className="sc-row">
                <div className="sc-dot" style={{ background: COLORS[d.name] }} />
                <span className="sc-name">{LABELS[d.name]}</span>
                <span className="sc-count">{d.count}</span>
                <span className="sc-pct">{d.value.toFixed(1)}%</span>
              </div>
              <div className="sc-bar-track">
                <div className="sc-bar-fill"
                  style={{ width:`${d.value}%`, background:COLORS[d.name], opacity:0.7 }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </>
  )
}