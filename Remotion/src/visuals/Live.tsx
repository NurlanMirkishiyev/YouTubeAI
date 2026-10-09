import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Item, Unit} from '../types';
import {DUR, EASE, ease} from '../motion';
import {AREA, Body, C, Count, fmt, GHOST, TITLE_H, useEnter, useIn} from './common';

// #135 (istifadeci 2026-10-10): canli novler - reference video_yarat_v4-un "canli" ruhunda (sayilan reqem,
// cekilen forma, parilti); her reqem danisiqda deyilib (Projects/visuals.py yoxlayir).
const BODY_H = AREA.height - TITLE_H - 24;
const at = (reveal: number[], i: number) => reveal[i] ?? reveal[reveal.length - 1] ?? 0;

/** Selale: gelir sutunu -> her xerc yuxaridan asagi "dusur" -> menfeet sutunu; korpu xetleri seviyyeni gosterir. */
export const Waterfall: React.FC<{start: Item; steps: (Item & {sign: '+' | '-'})[]; end: Item; reveal: number[]}> = (
  {start, steps, end, reveal}) => {
  const frame = useCurrentFrame();
  const levels: number[] = [start.value ?? 0];
  steps.forEach((s) => levels.push(levels[levels.length - 1] + (s.sign === '-' ? -1 : 1) * (s.value ?? 0)));
  const top = Math.max(...levels, end.value ?? 0, 1);
  const n = steps.length + 2;
  const gap = 36;
  const w = Math.min(190, (AREA.width - gap * (n + 1)) / n);
  const ox = Math.max(0, (AREA.width - 160 - (n * w + (n - 1) * gap)) / 2);   // sahenin ortasinda (bayqus sagda)
  const plotH = BODY_H - 170;
  const y = (v: number) => 70 + (1 - v / top) * plotH;
  const cols = [
    {label: start.label, value: start.value ?? 0, unit: start.unit, from: 0, to: start.value ?? 0, color: C.teal, sign: ''},
    ...steps.map((s, i) => ({label: s.label, value: s.value ?? 0, unit: s.unit, from: levels[i], to: levels[i + 1],
      color: s.sign === '-' ? C.coral : C.teal, sign: s.sign === '-' ? '−' : '+'})),
    {label: end.label, value: end.value ?? 0, unit: end.unit, from: 0, to: end.value ?? 0, color: C.accent, sign: ''},
  ];
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        {cols.slice(0, -1).map((c, i) => {
          const t = ease(frame, at(reveal, i + 1), DUR.draw, EASE.inOut);
          const x0 = ox + gap + i * (w + gap) + w;
          return <line key={i} x1={x0} x2={x0 + gap * t} y1={y(c.to)} y2={y(c.to)} stroke={C.muted}
            strokeWidth={3} strokeDasharray="8 8" opacity={0.7} />;
        })}
        <line x1={gap / 2} x2={AREA.width - gap / 2} y1={y(0)} y2={y(0)} stroke={C.line} strokeWidth={2} />
      </svg>
      {cols.map((c, i) => <WaterCol key={i} c={c} x={ox + gap + i * (w + gap)} w={w} y={y} delay={at(reveal, i)}
        labelY={y(0) + 22} />)}
    </Body>
  );
};

const WaterCol: React.FC<{c: {label: string; value: number; unit?: Unit; from: number; to: number; color: string;
  sign: string}; x: number; w: number; y: (v: number) => number; delay: number; labelY: number}> = (
  {c, x, w, y, delay, labelY}) => {
  const frame = useCurrentFrame();
  const enter = useEnter();
  const p = useIn(delay);
  const drop = ease(frame, delay, DUR.draw, EASE.out);
  const hi = Math.max(c.from, c.to);
  const lo = Math.min(c.from, c.to);
  const h = Math.max(6, (y(lo) - y(hi)) * drop);
  return (
    <>
      <div style={{position: 'absolute', left: x, top: y(hi), width: w, height: h, borderRadius: 12,
        background: `linear-gradient(180deg, ${c.color} 0%, ${c.color}AA 100%)`, boxShadow: `0 0 36px ${c.color}44`,
        opacity: GHOST + (1 - GHOST) * p}} />
      <div style={{position: 'absolute', left: x - 30, width: w + 60, top: y(hi) - 64, textAlign: 'center',
        fontSize: 40, fontWeight: 800, color: c.color, ...enter(p, 14)}}>
        {c.sign}<Count value={c.value} unit={c.unit ?? ''} delay={delay} />
      </div>
      <div style={{position: 'absolute', left: x - 30, width: w + 60, top: labelY, textAlign: 'center', fontSize: 28,
        fontWeight: 600, color: C.muted}}>{c.label}</div>
    </>
  );
};

/** Spidometr: eqreb deyere qeder firlanir, hedef zonasi rengli, merkezde reqem sayilir. */
export const Gauge: React.FC<{value: number; max: number; target: number | null; unit: Unit; label: string;
  reveal: number[]}> = ({value, max, target, unit, label, reveal}) => {
  const frame = useCurrentFrame();
  const d = at(reveal, 0);
  const sweep = ease(frame, d, DUR.draw * 2, EASE.back);
  const r = 230;
  const cx = AREA.width / 2 - 120;
  const cy = BODY_H - 150;
  const ang = (v: number) => Math.PI * (1 - Math.min(1, v / max));
  const pt = (a: number, rr: number) => [cx + rr * Math.cos(a), cy - rr * Math.sin(a)] as const;
  const arc = (a0: number, a1: number, rr: number) => {
    const [x0, y0] = pt(a0, rr);
    const [x1, y1] = pt(a1, rr);
    return `M ${x0} ${y0} A ${rr} ${rr} 0 0 1 ${x1} ${y1}`;
  };
  const needle = ang(value * sweep);
  const [nx, ny] = pt(needle, r - 40);
  const labelIn = useIn(d + DUR.staggerLoose);
  const enter = useEnter();
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        <path d={arc(Math.PI, 0, r)} stroke={C.line} strokeWidth={40} fill="none" strokeLinecap="round" />
        <path d={arc(Math.PI, needle, r)} stroke={C.accent} strokeWidth={40} fill="none" strokeLinecap="round"
          style={{filter: `drop-shadow(0 0 18px ${C.accent}88)`}} />
        {target !== null ? <path d={arc(ang(target) + 0.04, ang(target) - 0.04, r + 34)} stroke={C.teal}
          strokeWidth={14} fill="none" /> : null}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={C.text} strokeWidth={10} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={20} fill={C.text} />
      </svg>
      <div style={{position: 'absolute', left: cx - 200, width: 400, top: cy + 26, textAlign: 'center', fontSize: 92,
        fontWeight: 800, color: C.accent, lineHeight: 1}}><Count value={value} unit={unit} delay={d} /></div>
      {target !== null ? <div style={{position: 'absolute', left: cx + r + 60, top: 40, fontSize: 34, fontWeight: 700,
        color: C.teal, ...enter(useIn(at(reveal, 1)), 12)}}>Goal {fmt(target, unit)}</div> : null}
      <div style={{position: 'absolute', left: cx + r + 60, width: 360, top: cy - 60, fontSize: 40,
        fontWeight: 700, ...enter(labelIn, 14)}}>{label}</div>
    </Body>
  );
};

/** 100 noqte: deyer qeder noqte dalga ile yanir (reference xerite noqteleri), yaninda reqem sayilir. */
export const DotGrid: React.FC<{value: number; label: string; reveal: number[]}> = ({value, label, reveal}) => {
  const frame = useCurrentFrame();
  const d = at(reveal, 0);
  const lit = Math.round(value * ease(frame, d, DUR.draw * 2, EASE.out));
  const cell = 48;
  const enter = useEnter();
  const labelIn = useIn(d + DUR.staggerLoose);
  return (
    <Body style={{display: 'flex', alignItems: 'center', gap: 70, paddingLeft: 40}}>
      <div style={{display: 'grid', gridTemplateColumns: `repeat(10, ${cell}px)`, gap: 6}}>
        {Array.from({length: 100}, (_, i) => {
          const on = i < lit;
          const fresh = on && i >= lit - 6;
          return <div key={i} style={{width: cell - 6, height: cell - 6, borderRadius: (cell - 6) / 2,
            background: on ? C.accent : 'rgba(255,255,255,0.10)',
            boxShadow: fresh ? `0 0 18px ${C.accent}` : 'none',
            transform: `scale(${fresh ? 1.15 : 1})`}} />;
        })}
      </div>
      <div>
        <div style={{fontSize: 150, fontWeight: 800, color: C.accent, lineHeight: 1, textShadow: `0 0 50px ${C.accent}55`}}>
          <Count value={value} unit="%" delay={d} /></div>
        <div style={{fontSize: 46, fontWeight: 700, marginTop: 20, maxWidth: 380, ...enter(labelIn, 14)}}>{label}</div>
        <div style={{fontSize: 28, color: C.muted, marginTop: 12, opacity: interpolate(labelIn, [0, 1], [0, 1])}}>
          of every 100</div>
      </div>
    </Body>
  );
};
