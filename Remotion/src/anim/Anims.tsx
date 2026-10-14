import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Anim} from '../types';
import {Badge, Burst, clamp, fmt, glass, gradText, iconAt, ramp, Shine, txt, useCount, usePal, useSpr} from './kit';
import {Flow, List, Timeline, Versus} from './TextAnims';

// Reqemli animasiyalar (counter, bars, percent) + quote. Her novun 2 varianti var (a.variant); hec biri girisden
// sonra donmur (nefes alan halqa, isiq zolagi, yavas yellenme). Butun yazi/reqem a-dan gelir (danisiqdan).
export type P = {a: Anim};

const Counter: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const shown = useCount(a.value);
  const done = interpolate(f, [52, 58, 66], [1, 1.07, 1], clamp);
  const label = ramp(f, 30, 50);
  const num = (
    <div style={{...txt(a.variant ? 170 : 200), ...gradText(p), transform: `scale(${done})`, whiteSpace: 'nowrap'}}>
      {a.prefix}{fmt(shown)}{a.suffix}
    </div>
  );
  const lab = (
    <div style={{opacity: label, transform: `translateY(${(1 - label) * 24}px)`}}>
      <div style={{...txt(54, 'rgba(255,255,255,0.88)', 600), maxWidth: 900}}>{a.label}</div>
      <div style={{height: 6, borderRadius: 3, marginTop: 16, width: `${label * 260}px`, maxWidth: '100%',
        background: `linear-gradient(90deg, ${p.a1}, ${p.a2})`, boxShadow: `0 0 18px ${p.glow}`,
        marginLeft: a.variant ? 0 : 'auto', marginRight: a.variant ? 0 : 'auto'}} />
    </div>
  );
  if (a.variant) {
    return (
      <div style={{display: 'flex', alignItems: 'center', gap: 56, paddingLeft: 40}}>
        <div style={{position: 'relative'}}><Burst size={520} /><Badge icon={a.icon} size={200} rings /></div>
        <div>{num}{lab}</div>
      </div>
    );
  }
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 18}}>
      <div style={{position: 'relative'}}><Burst size={520} /><Badge icon={a.icon} size={150} rings /></div>
      {num}{lab}
    </div>
  );
};

const BarRow: React.FC<{it: {label: string; value: number}; k: number; max: number; icon?: string}> = ({it, k, max, icon}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const d = 10 + k * 9;
  const grow = ramp(f, d, d + 34);
  const v = useCount(it.value, d, d + 34);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 26, opacity: ramp(f, d - 6, d + 4)}}>
      <Badge icon={icon} size={78} delay={d - 4} />
      <div style={{flex: 1}}>
        <div style={{...txt(38, 'rgba(255,255,255,0.9)', 600), marginBottom: 10}}>{it.label}</div>
        <div style={{display: 'flex', alignItems: 'center', gap: 22}}>
          <div style={{flex: 1, height: 46, borderRadius: 23, background: 'rgba(255,255,255,0.08)', overflow: 'hidden'}}>
            <div style={{position: 'relative', overflow: 'hidden', height: '100%', borderRadius: 23,
              width: `${Math.max(4, grow * (it.value / max) * 100)}%`,
              background: `linear-gradient(90deg, ${k % 2 ? p.a2 : p.tint}, ${p.a1})`, boxShadow: `0 0 26px ${p.glow}`}}>
              <Shine every={90} delay={d + 34} />
            </div>
          </div>
          <div style={{...txt(46), ...gradText(p), minWidth: 150, textAlign: 'right'}}>{fmt(v)}</div>
        </div>
      </div>
    </div>
  );
};

const Column: React.FC<{it: {label: string; value: number}; k: number; max: number; icon?: string}> = ({it, k, max, icon}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const d = 10 + k * 9;
  const grow = ramp(f, d, d + 36);
  const v = useCount(it.value, d, d + 36);
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', width: 230, gap: 14}}>
      <div style={{...txt(52), ...gradText(p), opacity: ramp(f, d + 4, d + 14)}}>{fmt(v)}</div>
      <div style={{height: 400, display: 'flex', alignItems: 'flex-end'}}>
        <div style={{position: 'relative', overflow: 'hidden', width: 140, borderRadius: '22px 22px 6px 6px',
          height: Math.max(10, grow * (it.value / max) * 400),
          background: `linear-gradient(0deg, ${k % 2 ? p.a2 : p.tint}, ${p.a1})`, boxShadow: `0 0 34px ${p.glow}`}}>
          <Shine every={95} delay={d + 36} />
        </div>
      </div>
      <Badge icon={icon} size={70} delay={d} />
      <div style={{...txt(34, 'rgba(255,255,255,0.9)', 600), textAlign: 'center', opacity: ramp(f, d, d + 12)}}>{it.label}</div>
    </div>
  );
};

const Bars: React.FC<P> = ({a}) => {
  const p = usePal();
  const s = useSpr(0, 90);
  const max = Math.max(...a.items.map((i: {value: number}) => i.value)) || 1;
  const card: React.CSSProperties = {...glass(p), padding: a.variant ? '40px 50px' : '44px 54px',
    opacity: s, transform: `translateY(${(1 - s) * 50}px) scale(${0.96 + 0.04 * s})`};
  if (a.variant) {
    return (
      <div style={{...card, display: 'flex', gap: 40, alignItems: 'flex-end'}}>
        {a.items.map((it: {label: string; value: number}, k: number) => <Column key={k} it={it} k={k} max={max} icon={iconAt(a, k)} />)}
      </div>
    );
  }
  return (
    <div style={{...card, width: 1240, display: 'flex', flexDirection: 'column', gap: 30}}>
      {a.items.map((it: {label: string; value: number}, k: number) => <BarRow key={k} it={it} k={k} max={max} icon={iconAt(a, k)} />)}
    </div>
  );
};

const Donut: React.FC<{value: number}> = ({value}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const v = useCount(value, 6, 54);
  const r = 200, c = 2 * Math.PI * r;
  return (
    <svg width={500} height={500} style={{overflow: 'visible'}}>
      <defs>
        <linearGradient id="dg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={p.a2} /><stop offset="1" stopColor={p.a1} /></linearGradient>
      </defs>
      <circle cx={250} cy={250} r={238} fill="none" stroke={p.a2} strokeOpacity={0.35} strokeWidth={2}
        strokeDasharray="4 14" transform={`rotate(${f * 0.5} 250 250)`} />
      <circle cx={250} cy={250} r={r} stroke="rgba(255,255,255,0.09)" strokeWidth={42} fill="none" />
      <circle cx={250} cy={250} r={r} stroke="url(#dg)" strokeWidth={42} fill="none" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} transform="rotate(-90 250 250)"
        style={{filter: `drop-shadow(0 0 18px ${p.glow})`}} />
      <text x={250} y={285} textAnchor="middle" style={txt(112)} fill="#fff">{Math.round(v)}%</text>
    </svg>
  );
};

const Waffle: React.FC<{value: number}> = ({value}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const filled = useCount(value, 6, 60);
  return (
    <div style={{display: 'grid', gridTemplateColumns: 'repeat(10, 38px)', gap: 8}}>
      {Array.from({length: 100}, (_, i) => {
        const on = i < Math.round(filled);
        const pop = on ? interpolate(f - (6 + (i / Math.max(1, value)) * 54), [0, 8], [0.4, 1], clamp) : 1;
        return <div key={i} style={{width: 38, height: 38, borderRadius: 9, transform: `scale(${pop})`,
          background: on ? `linear-gradient(135deg, ${p.a2}, ${p.a1})` : 'rgba(255,255,255,0.08)',
          boxShadow: on ? `0 0 14px ${p.glow}` : 'none'}} />;
      })}
    </div>
  );
};

const Percent: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const s = useSpr(0, 100);
  const lab = ramp(f, 24, 44);
  const v = useCount(a.value, 6, 60);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 80, opacity: s, transform: `scale(${0.9 + 0.1 * s})`}}>
      {a.variant ? <Waffle value={a.value} /> : <Donut value={a.value} />}
      <div style={{maxWidth: 560, opacity: lab, transform: `translateX(${(1 - lab) * 40}px)`}}>
        <Badge icon={a.icon} size={96} delay={20} />
        {a.variant ? <div style={{...txt(150), ...gradText(p), marginTop: 18}}>{Math.round(v)}%</div> : null}
        <div style={{...txt(60), marginTop: 22}}>{a.label}</div>
      </div>
    </div>
  );
};

const Quote: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const words = String(a.text ?? '').split(' ').filter(Boolean);
  const key = words.reduce((best, w, i) => (w.replace(/\W/g, '').length > words[best].replace(/\W/g, '').length ? i : best), 0);
  const size = words.length > 14 ? 62 : 76;
  const mark = ramp(f, 0, 18);
  return (
    <div style={{position: 'relative', maxWidth: 1250, textAlign: a.variant ? 'center' : 'left', paddingLeft: a.variant ? 0 : 50}}>
      <div style={{...txt(300), ...gradText(p), height: 150, lineHeight: 1, marginBottom: 10, opacity: 0.9 * mark,
        transform: `scale(${0.6 + 0.4 * mark})`, transformOrigin: a.variant ? 'center' : 'left'}}>“</div>
      {a.variant ? null : <div style={{position: 'absolute', left: 0, top: 160, bottom: 0, width: 10, borderRadius: 5,
        background: `linear-gradient(${p.a1}, ${p.a2})`, transform: `scaleY(${mark})`, transformOrigin: 'top'}} />}
      <div style={{...txt(size), position: 'relative'}}>
        {words.map((w, k) => {
          const t = ramp(f, 6 + k * 3, 18 + k * 3);
          const hl = k === key ? ramp(f, 14 + words.length * 3, 30 + words.length * 3) : 0;
          return (
            <span key={k} style={{display: 'inline-block', marginRight: size * 0.26, opacity: t, position: 'relative',
              transform: `translateY(${(1 - t) * 30}px)`, filter: `blur(${(1 - t) * 8}px)`, color: hl > 0.5 ? '#0b0f1e' : '#fff'}}>
              {k === key ? <span style={{position: 'absolute', left: -8, right: -8, top: '8%', bottom: '2%', borderRadius: 10,
                background: `linear-gradient(90deg, ${p.a1}, ${p.a2})`, transform: `scaleX(${hl})`, transformOrigin: 'left', zIndex: -1}} /> : null}
              {w}
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const ANIMS: Record<string, React.FC<P>> = {
  counter: Counter, bars: Bars, percent: Percent, quote: Quote, flow: Flow, list: List, versus: Versus, timeline: Timeline,
};
