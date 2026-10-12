import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT} from '../theme';
import {Anim} from '../types';

type P = {a: Anim};
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const txt = (size: number, color = COLORS.text, weight = 800): React.CSSProperties =>
  ({fontFamily: FONT, fontWeight: weight, fontSize: size, color, lineHeight: 1.15});

const useIn = (delay = 0) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping: 16, stiffness: 120}});
};
// variant 0: asagidan qalxir; variant 1: soldan surusur
const enter = (v: number, t: number): React.CSSProperties =>
  v ? {opacity: t, transform: `translateX(${(1 - t) * -80}px)`} : {opacity: t, transform: `translateY(${(1 - t) * 60}px)`};
const fmt = (v: number) => (Number.isInteger(v) ? v.toLocaleString('en-US') : v.toLocaleString('en-US', {maximumFractionDigits: 2}));

const Counter: React.FC<P> = ({a}) => {
  const f = useCurrentFrame();
  const t = useIn();
  const v = interpolate(f, [5, 45], [0, a.value], clamp);
  const shown = Number.isInteger(a.value) ? Math.round(v) : Math.round(v * 100) / 100;
  return (
    <div style={{textAlign: 'center', ...enter(a.variant, t)}}>
      <div style={txt(190, COLORS.accent)}>{a.prefix}{fmt(shown)}{a.suffix}</div>
      <div style={txt(56, COLORS.soft, 600)}>{a.label}</div>
    </div>
  );
};

const Bars: React.FC<P> = ({a}) => {
  const f = useCurrentFrame();
  const max = Math.max(...a.items.map((i: any) => i.value)) || 1;
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 34, width: 1150}}>
      {a.items.map((it: any, k: number) => {
        const t = interpolate(f, [8 + k * 8, 38 + k * 8], [0, 1], clamp);
        return (
          <div key={k} style={{opacity: Math.min(1, t * 3)}}>
            <div style={txt(42, COLORS.soft, 600)}>{it.label}</div>
            <div style={{display: 'flex', alignItems: 'center', gap: 20}}>
              <div style={{height: 64, borderRadius: 10, background: k % 2 ? COLORS.accent : COLORS.bar,
                width: `${t * (it.value / max) * 80}%`, opacity: a.variant ? t : 1}} />
              <div style={txt(48)}>{fmt(it.value)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

const Percent: React.FC<P> = ({a}) => {
  const f = useCurrentFrame();
  const p = interpolate(f, [6, 50], [0, a.value], clamp);
  const r = 190, c = 2 * Math.PI * r;
  const t = useIn();
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 70, ...enter(a.variant, t)}}>
      <svg width={460} height={460}>
        <circle cx={230} cy={230} r={r} stroke="#24365e" strokeWidth={40} fill="none" />
        <circle cx={230} cy={230} r={r} stroke={COLORS.accent} strokeWidth={40} fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - p / 100)} transform="rotate(-90 230 230)" />
        <text x={230} y={262} textAnchor="middle" style={txt(96)} fill="#fff">{Math.round(p)}%</text>
      </svg>
      <div style={{...txt(60), maxWidth: 520}}>{a.label}</div>
    </div>
  );
};

// flow: 4 addim SAFE_RIGHT-dan sola sigsin (1920 - 470 - 80 = 1370 px): 4x280 (border-box) + 3 ox + 6 ara
const FLOW = {3: {box: 330, font: 46, gap: 28, arrow: 70}, 4: {box: 280, font: 34, gap: 16, arrow: 56}};
const Steps: React.FC<{items: string[]; arrows: boolean; variant: number}> = ({items, arrows, variant}) => {
  const f = useCurrentFrame();
  const fl = items.length >= 4 ? FLOW[4] : FLOW[3];
  return (
    <div style={{display: 'flex', flexDirection: arrows ? 'row' : 'column', alignItems: arrows ? 'center' : 'flex-start', gap: arrows ? fl.gap : 28}}>
      {items.map((s, k) => {
        const t = interpolate(f, [k * 12, k * 12 + 14], [0, 1], clamp);
        return (
          <React.Fragment key={k}>
            {arrows && k > 0 ? <div style={{...txt(fl.arrow, COLORS.accent), opacity: t}}>→</div> : null}
            <div style={{...enter(variant, t), ...txt(arrows ? fl.font : 58), background: arrows ? '#1d2c4f' : 'transparent',
              padding: arrows ? '22px 24px' : 0, borderRadius: 16, maxWidth: arrows ? fl.box : 1100,
              boxSizing: 'border-box', minWidth: 0, overflowWrap: 'break-word'}}>
              {arrows ? s : <span><span style={{color: COLORS.accent}}>●</span> {s}</span>}
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

const Versus: React.FC<P> = ({a}) => {
  const l = useIn(), r = useIn(10), m = useIn(20);
  const box = (s: string, t: number, side: number): React.CSSProperties => ({...txt(58), width: 520, padding: 40,
    textAlign: 'center', borderRadius: 20, background: side ? '#3a2a12' : '#152a52', opacity: t,
    transform: a.variant ? `scale(${0.8 + 0.2 * t})` : `translateX(${(1 - t) * (side ? 120 : -120)}px)`});
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 40}}>
      <div style={box(a.left, l, 0)}>{a.left}</div>
      <div style={{...txt(80, COLORS.accent), opacity: m}}>VS</div>
      <div style={box(a.right, r, 1)}>{a.right}</div>
    </div>
  );
};

const Timeline: React.FC<P> = ({a}) => {
  const f = useCurrentFrame();
  const line = interpolate(f, [0, 40], [0, 100], clamp);
  return (
    <div style={{width: 1200, position: 'relative', height: 300}}>
      <div style={{position: 'absolute', top: 140, left: 0, height: 8, width: `${line}%`, background: COLORS.soft}} />
      {a.events.map((e: string, k: number) => {
        const n = a.events.length;
        const x = (k / Math.max(1, n - 1)) * 100;
        const shift = n < 2 ? '0%' : k === 0 ? '0%' : k === n - 1 ? '-100%' : '-50%';
        const align = k === n - 1 && n > 1 ? 'right' : k === 0 || n < 2 ? 'left' : 'center';
        const t = interpolate(f, [10 + k * 12, 24 + k * 12], [0, 1], clamp);
        return (
          <div key={k} style={{position: 'absolute', left: `${x}%`, top: a.variant && k % 2 ? 175 : 30, opacity: t, width: 260,
            transform: `translateX(${shift})`, textAlign: align}}>
            <div style={{width: 34, height: 34, borderRadius: 17, background: COLORS.accent,
              marginTop: a.variant && k % 2 ? -52 : 92,
              marginLeft: align === 'right' ? 'auto' : align === 'center' ? 'auto' : 0,
              marginRight: align === 'center' ? 'auto' : 0}} />
            <div style={{...txt(38), marginTop: 12}}>{e}</div>
          </div>
        );
      })}
    </div>
  );
};

const Quote: React.FC<P> = ({a}) => {
  const f = useCurrentFrame();
  const words = String(a.text ?? '').split(' ');
  return (
    <div style={{...txt(76), maxWidth: 1250, borderLeft: `12px solid ${COLORS.accent}`, paddingLeft: 40}}>
      {words.map((w, k) => {
        const t = interpolate(f, [k * 2, k * 2 + 8], [0, 1], clamp);
        return <span key={k} style={{opacity: t, display: 'inline-block', marginRight: 18,
          transform: a.variant ? `translateY(${(1 - t) * 24}px)` : `scale(${0.85 + 0.15 * t})`}}>{w}</span>;
      })}
    </div>
  );
};

export const ANIMS: Record<string, React.FC<P>> = {
  counter: Counter, bars: Bars, percent: Percent, versus: Versus, timeline: Timeline, quote: Quote,
  flow: ({a}) => <Steps items={a.steps} arrows variant={a.variant} />,
  list: ({a}) => <Steps items={a.items} arrows={false} variant={a.variant} />,
};
