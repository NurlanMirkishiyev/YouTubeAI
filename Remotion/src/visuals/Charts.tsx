import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Item, Unit} from '../types';
import {AREA, Body, C, Count, fmt, rise, TITLE_H, useIn} from './common';

const BODY_H = AREA.height - TITLE_H - 24;
const at = (reveal: number[], i: number) => reveal[i] ?? reveal[reveal.length - 1] ?? 0;

/** Sutunlar: hundurluk deyere mutenasib, reqem sayilir; en boyuk sutun sari, qalanlari firuzeyi. */
export const Bars: React.FC<{items: Item[]; unit: Unit; reveal: number[]}> = ({items, unit, reveal}) => {
  const max = Math.max(...items.map((it) => it.value ?? 0), 1);
  const gap = 48;
  const w = Math.min(220, (AREA.width - gap * (items.length + 1)) / items.length);
  const plotH = BODY_H - 150;
  return (
    <Body style={{display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap, paddingBottom: 70}}>
      {items.map((it, i) => (
        <Bar key={it.label} item={it} unit={unit} delay={at(reveal, i)} width={w}
          height={((it.value ?? 0) / max) * plotH} best={it.value === max} />))}
      <div style={{position: 'absolute', left: 40, right: 40, bottom: 68, height: 2, background: C.line}} />
    </Body>
  );
};

const Bar: React.FC<{item: Item; unit: Unit; delay: number; width: number; height: number; best: boolean}> = (
  {item, unit, delay, width, height, best}) => {
  const p = useIn(delay);
  const color = best ? C.accent : C.teal;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', width, position: 'relative'}}>
      <div style={{fontSize: 52, fontWeight: 800, color, marginBottom: 14, ...rise(p, 20)}}>
        {item.value !== null ? <Count value={item.value} unit={item.unit ?? unit} delay={delay} /> : null}
      </div>
      <div style={{width, height: Math.max(6, height * p), borderRadius: '18px 18px 6px 6px',
        background: `linear-gradient(180deg, ${color} 0%, ${color}99 100%)`,
        boxShadow: `0 0 40px ${color}44`}} />
      <div style={{position: 'absolute', bottom: -62, width: width + 40, textAlign: 'center', fontSize: 32,
        fontWeight: 600, color: C.muted, opacity: p}}>{item.label}</div>
    </div>
  );
};

/** Xett: xett noqteden noqteye reveal vaxtlarinda cekilir, noqteler ve deyer etiketleri acilir. */
export const Line: React.FC<{points: Item[]; unit: Unit; reveal: number[]}> = ({points, unit, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vals = points.map((p) => p.value ?? 0);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const padX = 90;
  const plotW = AREA.width - padX * 2;
  const plotH = BODY_H - 170;
  const xy = vals.map((v, i) => [padX + (i / (vals.length - 1)) * plotW,
    60 + (hi === lo ? plotH / 2 : (1 - (v - lo) / (hi - lo)) * plotH)] as const);
  // her seqment oz noqtesinin reveal-i ile 0.6 s-de cekilir
  const segs = xy.slice(1).map((pt, i) => {
    const t = interpolate(frame, [at(reveal, i + 1) - 0.6 * fps, at(reveal, i + 1)], [0, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const [x0, y0] = xy[i];
    return {x0, y0, x1: x0 + (pt[0] - x0) * t, y1: y0 + (pt[1] - y0) * t};
  });
  const area = `M ${xy[0][0]} ${60 + plotH} ` + segs.map((s) => `L ${s.x0} ${s.y0} L ${s.x1} ${s.y1}`).join(' ')
    + ` L ${segs[segs.length - 1].x1} ${60 + plotH} Z`;
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        <defs>
          <linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={C.accent} stopOpacity={0.28} />
            <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((g) => (
          <line key={g} x1={padX} x2={padX + plotW} y1={60 + g * plotH} y2={60 + g * plotH} stroke={C.line} />))}
        <path d={area} fill="url(#lineFill)" />
        {segs.map((s, i) => (
          <line key={i} x1={s.x0} y1={s.y0} x2={s.x1} y2={s.y1} stroke={C.accent} strokeWidth={8}
            strokeLinecap="round" />))}
      </svg>
      {points.map((p, i) => <LinePoint key={p.label} item={p} unit={unit} x={xy[i][0]} y={xy[i][1]}
        labelY={60 + plotH + 26} delay={at(reveal, i)} />)}
    </Body>
  );
};

const LinePoint: React.FC<{item: Item; unit: Unit; x: number; y: number; labelY: number; delay: number}> = (
  {item, unit, x, y, labelY, delay}) => {
  const p = useIn(delay, 14);
  return (
    <>
      <div style={{position: 'absolute', left: x - 14, top: y - 14, width: 28, height: 28, borderRadius: 14,
        background: C.accent, border: '5px solid #111A30', transform: `scale(${p})`}} />
      {item.value !== null ? (
        <div style={{position: 'absolute', left: x - 120, width: 240, top: y - 78, textAlign: 'center',
          fontSize: 40, fontWeight: 800, ...rise(p, 16)}}>{fmt(item.value, item.unit ?? unit)}</div>) : null}
      <div style={{position: 'absolute', left: x - 120, width: 240, top: labelY, textAlign: 'center', fontSize: 30,
        fontWeight: 600, color: C.muted, opacity: p}}>{item.label}</div>
    </>
  );
};

/** Faiz halqasi: halqa deyere qeder dolur, ortada reqem sayilir. */
export const Ring: React.FC<{value: number; label: string; reveal: number[]}> = ({value, label, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const d = at(reveal, 0);
  const t = interpolate(frame, [d, d + 1.2 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const eased = 1 - Math.pow(1 - t, 3);
  const r = 190;
  const circ = 2 * Math.PI * r;
  const p = useIn(d);
  const labelIn = useIn(d + 10);
  return (
    <Body style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 80}}>
      <div style={{position: 'relative', width: 2 * r + 60, height: 2 * r + 60, transform: `scale(${0.85 + 0.15 * p})`,
        opacity: p}}>
        <svg width={2 * r + 60} height={2 * r + 60}>
          <circle cx={r + 30} cy={r + 30} r={r} fill="none" stroke={C.line} strokeWidth={34} />
          <circle cx={r + 30} cy={r + 30} r={r} fill="none" stroke={C.accent} strokeWidth={34} strokeLinecap="round"
            strokeDasharray={`${circ}`} strokeDashoffset={circ * (1 - (value / 100) * eased)}
            transform={`rotate(-90 ${r + 30} ${r + 30})`} />
        </svg>
        <div style={{position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 120, fontWeight: 800}}>
          <Count value={value} unit="%" delay={d} />
        </div>
      </div>
      <div style={{fontSize: 52, fontWeight: 800, maxWidth: 440, lineHeight: 1.15, ...rise(labelIn)}}>{label}</div>
    </Body>
  );
};

/** Bir boyuk reqem: sayilir, altinda izah. */
export const Counter: React.FC<{value: number; unit: Unit; label: string; reveal: number[]}> = (
  {value, unit, label, reveal}) => {
  const d = at(reveal, 0);
  const p = useIn(d);
  const labelIn = useIn(d + 12);
  return (
    <Body style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{fontSize: 230, fontWeight: 800, color: C.accent, lineHeight: 1,
        textShadow: `0 0 60px ${C.accent}55`, transform: `scale(${0.8 + 0.2 * p})`, opacity: p}}>
        <Count value={value} unit={unit} delay={d} />
      </div>
      <div style={{fontSize: 54, fontWeight: 600, marginTop: 30, color: C.text, ...rise(labelIn)}}>{label}</div>
    </Body>
  );
};
