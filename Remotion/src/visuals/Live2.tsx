import React from 'react';
import {useCurrentFrame} from 'remotion';
import {Item, Unit} from '../types';
import {DUR, EASE, ease} from '../motion';
import {AREA, Body, C, Count, GHOST, TITLE_H, useEnter, useIn} from './common';

// #135 (istifadeci 2026-10-10): canli novler - terezi, huni, uz-uze (reqemsiz de isleyir)
const BODY_H = AREA.height - TITLE_H - 24;
const at = (reveal: number[], i: number) => reveal[i] ?? reveal[reveal.length - 1] ?? 0;
type Side = Item & {note: string};

const Pan: React.FC<{side: Side; x: number; y: number; delay: number; color: string}> = ({side, x, y, delay, color}) => {
  const enter = useEnter();
  const p = useIn(delay);
  return (
    <div style={{position: 'absolute', left: x - 200, top: y, width: 400, textAlign: 'center', ...enter(p, 20)}}>
      <div style={{margin: '0 auto', width: 340, height: 18, borderRadius: 9, background: color,
        boxShadow: `0 0 30px ${color}66`}} />
      <div style={{marginTop: 22, fontSize: 46, fontWeight: 800, color}}>{side.label}</div>
      {side.value !== null ? <div style={{fontSize: 64, fontWeight: 800}}>
        <Count value={side.value} unit={side.unit ?? ''} delay={delay} /></div> : null}
      {side.note ? <div style={{fontSize: 30, color: C.muted, marginTop: 6}}>{side.note}</div> : null}
    </div>
  );
};

/** Terezi: iki teref acilir, sonra dirsek agir terefe eyilir (spring overshoot). */
export const Balance: React.FC<{left: Side; right: Side; heavier: 'left' | 'right'; reveal: number[]}> = (
  {left, right, heavier, reveal}) => {
  const frame = useCurrentFrame();
  const tilt = ease(frame, at(reveal, 1), DUR.draw * 2, EASE.back) * (heavier === 'left' ? -9 : 9);
  const cx = AREA.width / 2 - 60;
  const beamY = 120;
  const half = 360;
  const rad = (tilt * Math.PI) / 180;
  const ly = beamY - Math.sin(rad) * half;
  const ry = beamY + Math.sin(rad) * half;
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        <polygon points={`${cx - 60},${BODY_H - 40} ${cx + 60},${BODY_H - 40} ${cx},${beamY + 10}`}
          fill="rgba(255,255,255,0.08)" stroke={C.line} strokeWidth={3} />
        <line x1={cx - half * Math.cos(rad)} y1={ly} x2={cx + half * Math.cos(rad)} y2={ry} stroke={C.text}
          strokeWidth={10} strokeLinecap="round" />
        <circle cx={cx} cy={beamY} r={16} fill={C.accent} />
      </svg>
      <Pan side={left} x={cx - half * Math.cos(rad)} y={ly + 24} delay={at(reveal, 0)}
        color={heavier === 'left' ? C.accent : C.teal} />
      <Pan side={right} x={cx + half * Math.cos(rad)} y={ry + 24} delay={at(reveal, 1)}
        color={heavier === 'right' ? C.accent : C.teal} />
    </Body>
  );
};

/** Huni: her merhele yuxaridan daralaraq dolur, eni deyere mutenasib, itki faizi kenarda gorunmur (yalniz deyilenler). */
export const Funnel: React.FC<{stages: Item[]; unit: Unit; reveal: number[]}> = ({stages, unit, reveal}) => {
  const frame = useCurrentFrame();
  const top = Math.max(...stages.map((s) => s.value ?? 0), 1);
  const rowH = Math.min(120, (BODY_H - 40) / stages.length - 16);
  const maxW = AREA.width - 520;
  return (
    <Body style={{display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 10}}>
      {stages.map((s, i) => {
        const grow = ease(frame, at(reveal, i), DUR.draw, EASE.out);
        const w = Math.max(160, ((s.value ?? 0) / top) * maxW);
        const color = i === stages.length - 1 ? C.accent : C.teal;
        return (
          <div key={s.label} style={{display: 'flex', alignItems: 'center', height: rowH}}>
            <div style={{width: maxW, display: 'flex', justifyContent: 'center'}}>
              <div style={{width: 160 + (w - 160) * grow, height: rowH, borderRadius: 18,
                opacity: GHOST + (1 - GHOST) * grow,
                background: `linear-gradient(90deg, ${color}55, ${color}, ${color}55)`, boxShadow: `0 0 36px ${color}44`,
                display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 52, fontWeight: 800,
                color: '#0B1222'}}>
                {s.value !== null ? <Count value={s.value} unit={s.unit ?? unit} delay={at(reveal, i)} /> : null}
              </div>
            </div>
            <div style={{marginLeft: 36, fontSize: 40, fontWeight: 700, color, opacity: GHOST + (1 - GHOST) * grow}}>
              {s.label}</div>
          </div>
        );
      })}
    </Body>
  );
};

/** Uz-uze: iki kart kenarlardan gelib ortada "VS" ile toqqusur (scale pop), boyuk reqemli teref parlayir. */
export const Versus: React.FC<{left: Side; right: Side; reveal: number[]}> = ({left, right, reveal}) => {
  const frame = useCurrentFrame();
  const hit = ease(frame, at(reveal, 1), DUR.draw, EASE.back);
  const win = left.value !== null && right.value !== null ? (left.value >= right.value ? 'left' : 'right') : null;
  const card = (s: Side, side: 'left' | 'right', delay: number) => {
    const p = ease(frame, delay, DUR.draw, EASE.out);
    const color = win === side ? C.accent : C.teal;
    const dx = (1 - p) * (side === 'left' ? -120 : 120);
    return (
      <div style={{width: 440, padding: '46px 30px', borderRadius: 28, background: C.card, textAlign: 'center',
        border: `3px solid ${color}`, boxShadow: win === side ? `0 0 60px ${color}55` : 'none',
        transform: `translateX(${dx}px)`, opacity: GHOST + (1 - GHOST) * p}}>
        <div style={{fontSize: 48, fontWeight: 800, color}}>{s.label}</div>
        {s.value !== null ? <div style={{fontSize: 100, fontWeight: 800, marginTop: 14}}>
          <Count value={s.value} unit={s.unit ?? ''} delay={delay} /></div> : null}
        {s.note ? <div style={{fontSize: 30, color: C.muted, marginTop: 10}}>{s.note}</div> : null}
      </div>
    );
  };
  return (
    <Body style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 40, paddingRight: 80}}>
      {card(left, 'left', at(reveal, 0))}
      <div style={{fontSize: 72, fontWeight: 900, color: C.accent, transform: `scale(${0.4 + 0.6 * hit})`,
        textShadow: `0 0 40px ${C.accent}`}}>VS</div>
      {card(right, 'right', at(reveal, 1))}
    </Body>
  );
};
