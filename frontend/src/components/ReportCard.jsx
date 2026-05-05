import { TrendingUp, TrendingDown, Award, MessageSquare } from 'lucide-react'

function Section({ icon: Icon, label, text, color }) {
  return (
    <div style={{
      borderLeft:`2px solid ${color}`,
      paddingLeft:16, marginBottom:20,
    }}>
      <div style={{ display:'flex',alignItems:'center',gap:6,marginBottom:6 }}>
        <Icon size={12} color={color} />
        <span style={{ fontFamily:'DM Mono,monospace',fontSize:9,letterSpacing:'0.13em',
          textTransform:'uppercase',color:'#4e5a7a' }}>{label}</span>
      </div>
      <p style={{ fontSize:13,color:'#c8cfe8',lineHeight:1.65 }}>{text}</p>
    </div>
  )
}

function QuoteCard({ label, text, meta }) {
  return (
    <div style={{
      background:'rgba(255,255,255,0.02)',
      border:'1px solid rgba(255,255,255,0.06)',
      borderRadius:10,padding:'12px 14px',marginBottom:8,
    }}>
      <div style={{ fontFamily:'DM Mono,monospace',fontSize:9,
        letterSpacing:'0.12em',textTransform:'uppercase',color:'#4e5a7a',marginBottom:7 }}>
        {label}
      </div>
      <blockquote style={{ fontSize:12,color:'#b0bbd8',lineHeight:1.6,
        fontStyle:'italic',borderLeft:'2px solid rgba(245,166,35,0.3)',paddingLeft:10 }}>
        "{text}"
      </blockquote>
      {meta && <div style={{ fontSize:10,color:'#4e5a7a',marginTop:6,
        fontFamily:'DM Mono,monospace' }}>{meta}</div>}
    </div>
  )
}

export default function ReportCard({ result }) {
  const {
    title, channel, view_count,
    ai_overall_sentiment, ai_praise_themes, ai_criticism_themes, ai_verdict,
    top_liked_comment, top_liked_count,
    most_positive_comment, most_positive_polarity,
    most_negative_comment, most_negative_polarity,
    avg_weighted_sentiment,
  } = result

  return (
    <div style={{
      background:'#0d1225',border:'1px solid rgba(255,255,255,0.07)',
      borderRadius:16,padding:24,
    }}>
      {/* Video meta */}
      <div style={{ marginBottom:22,paddingBottom:18,
        borderBottom:'1px solid rgba(255,255,255,0.06)' }}>
        <h2 style={{ fontFamily:'Playfair Display,serif',fontSize:20,
          color:'#dde2f0',lineHeight:1.3,marginBottom:6 }}>{title}</h2>
        <div style={{ display:'flex',alignItems:'center',gap:12,flexWrap:'wrap' }}>
          <span style={{ fontSize:12,color:'#4e5a7a' }}>{channel}</span>
          <span style={{ fontSize:12,color:'#4e5a7a' }}>·</span>
          <span style={{ fontSize:12,color:'#4e5a7a' }}>{view_count?.toLocaleString()} views</span>
          <span style={{ fontSize:12,color:'#4e5a7a' }}>·</span>
          <span style={{ fontFamily:'DM Mono,monospace',fontSize:10,
            color:'#f5a623',background:'rgba(245,166,35,0.08)',
            border:'1px solid rgba(245,166,35,0.18)',borderRadius:99,
            padding:'2px 8px' }}>
            avg sentiment {avg_weighted_sentiment?.toFixed(3)}
          </span>
        </div>
      </div>

      {/* AI Narrative */}
      <Section icon={MessageSquare} label="Overall"    text={ai_overall_sentiment} color="rgba(255,255,255,0.2)" />
      <Section icon={TrendingUp}   label="Praised"    text={ai_praise_themes}     color="#34d399" />
      <Section icon={TrendingDown} label="Criticised" text={ai_criticism_themes}  color="#f87171" />
      <Section icon={Award}        label="Verdict"    text={ai_verdict}           color="#f5a623" />

      {/* Notable comments */}
      <div style={{ marginTop:22,paddingTop:18,borderTop:'1px solid rgba(255,255,255,0.06)' }}>
        <div style={{ fontFamily:'DM Mono,monospace',fontSize:9,letterSpacing:'0.14em',
          textTransform:'uppercase',color:'#4e5a7a',marginBottom:10 }}>
          Notable comments
        </div>
        <QuoteCard
          label={`Most liked · ${top_liked_count?.toLocaleString()} likes`}
          text={top_liked_comment}
        />
        <QuoteCard
          label="Most positive"
          text={most_positive_comment}
          meta={`polarity ${most_positive_polarity?.toFixed(3)}`}
        />
        <QuoteCard
          label="Most negative"
          text={most_negative_comment}
          meta={`polarity ${most_negative_polarity?.toFixed(3)}`}
        />
      </div>
    </div>
  )
}