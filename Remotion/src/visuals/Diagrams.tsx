import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Item, Unit} from '../types';
import {AREA, Body, C, Count, rise, useIn} from './common';

const at = (reveal: number[], i: number) => reveal[i] ?? reveal[reveal.length - 1] ?? 0;

const Card: React.FC<{children: React.ReactNode; p: number; accent?: boolean; style?: React.CSSProperties}> = (
  {children, p, accent = false, style}) => (
  <div style={{background: accent ? 'rgba(255,196,0,0.12)' : C.card, borderRadius: 26,
    border: `2px solid ${accent ? C.accent : C.line}`, padding: '30px 34px',
    boxShadow: accent ? `0 0 50px ${C.accent}33` : '0 20px 40px rgba(0,0,0,0.25)', ...rise(p), ...style}}>
    {children}
  </div>
);

/** A vs B: iki kart, ortada VS; deyer varsa sayilir. */
export const Compare: React.FC<{left: Item & {note: string}; right: Item & {note: string}; unit: Unit;
  reveal: number[]}> = ({left, right, unit, reveal}) => {
  const pl = useIn(at(reveal, 0));
  const pr = useIn(at(reveal, 1));
  const vs = useIn(at(reveal, 1) - 6, 12);
  const side = (it: Item & {note: string}, p: number, d: number, accent: boolean) => (
    <Card p={p} accent={accent} style={{width: 470, minHeight: 330, display: 'flex', flexDirection: 'column',
      justifyContent: 'center'}}>
      <div style={{fontSize: 40, fontWeight: 800, color: accent ? C.accent : C.teal}}>{it.label}</div>
      {it.value !== null ? (
        <div style={{fontSize: 96, fontWeight: 800, marginTop: 10}}><Count value={it.value} unit={unit} delay={d} /></div>
      ) : null}
      {it.note ? <div style={{fontSize: 32, fontWeight: 600, color: C.muted, marginTop: 14}}>{it.note}</div> : null}
    </Card>
  );
  return (
    <Body style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 70}}>
      {side(left, pl, at(reveal, 0), false)}
      <div style={{position: 'absolute', left: AREA.width / 2 - 52, width: 104, height: 104, borderRadius: 52,
        background: '#0A0F1E', border: `3px solid ${C.accent}`, display: 'flex', alignItems: 'center',
        justifyContent: 'center', fontSize: 38, fontWeight: 800, color: C.accent, transform: `scale(${vs})`,
        zIndex: 2}}>VS</div>
      {side(right, pr, at(reveal, 1), true)}
    </Body>
  );
};

/** Dustur: hedler bir-bir, operatorlar, sonda "=" ve netice karti (sari). */
export const Equation: React.FC<{terms: Item[]; result: Item; op: string; unit: Unit; reveal: number[]}> = (
  {terms, result, op, unit, reveal}) => {
  const parts = [...terms, result];
  const w = Math.min(330, (AREA.width - 90 * terms.length) / parts.length);
  return (
    <Body style={{display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22}}>
      {parts.map((it, i) => {
        const isResult = i === terms.length;
        return (
          <React.Fragment key={`${it.label}${i}`}>
            {i > 0 ? <Sym text={isResult ? '=' : op === '-' ? '−' : op} delay={at(reveal, i) - 4} /> : null}
            <Term item={it} unit={unit} delay={at(reveal, i)} width={w} accent={isResult} />
          </React.Fragment>
        );
      })}
    </Body>
  );
};

const Sym: React.FC<{text: string; delay: number}> = ({text, delay}) => {
  const p = useIn(delay, 12);
  return <div style={{fontSize: 90, fontWeight: 800, color: C.muted, width: 68, textAlign: 'center',
    transform: `scale(${p})`}}>{text}</div>;
};

const Term: React.FC<{item: Item; unit: Unit; delay: number; width: number; accent: boolean}> = (
  {item, unit, delay, width, accent}) => {
  const p = useIn(delay);
  return (
    <Card p={p} accent={accent} style={{width, padding: '34px 20px', textAlign: 'center'}}>
      <div style={{fontSize: item.value !== null ? 34 : 46, fontWeight: 800, color: accent ? C.accent : C.text}}>
        {item.label}</div>
      {item.value !== null ? (
        <div style={{fontSize: 66, fontWeight: 800, marginTop: 8}}><Count value={item.value} unit={unit} delay={delay} /></div>
      ) : null}
    </Card>
  );
};

/** Proses: addim kartlari, aralarinda cekilen oxlar. */
export const Flow: React.FC<{steps: string[]; reveal: number[]}> = ({steps, reveal}) => {
  const arrow = 70;
  const w = (AREA.width - arrow * (steps.length - 1)) / steps.length;
  return (
    <Body style={{display: 'flex', alignItems: 'center'}}>
      {steps.map((s, i) => (
        <React.Fragment key={s}>
          {i > 0 ? <Arrow delay={at(reveal, i) - 8} width={arrow} /> : null}
          <Step text={s} n={i + 1} delay={at(reveal, i)} width={w} last={i === steps.length - 1} />
        </React.Fragment>))}
    </Body>
  );
};

const Arrow: React.FC<{delay: number; width: number}> = ({delay, width}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = interpolate(frame, [delay, delay + 0.35 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <svg width={width} height={40} style={{flexShrink: 0}}>
      <line x1={8} y1={20} x2={8 + (width - 26) * t} y2={20} stroke={C.accent} strokeWidth={6} strokeLinecap="round" />
      <path d={`M ${width - 22} 8 L ${width - 6} 20 L ${width - 22} 32`} fill="none" stroke={C.accent} strokeWidth={6}
        strokeLinecap="round" strokeLinejoin="round" opacity={t >= 1 ? 1 : 0} />
    </svg>
  );
};

const Step: React.FC<{text: string; n: number; delay: number; width: number; last: boolean}> = (
  {text, n, delay, width, last}) => {
  const p = useIn(delay);
  return (
    <Card p={p} accent={last} style={{width, minHeight: 250, padding: '26px 22px', display: 'flex',
      flexDirection: 'column', justifyContent: 'flex-start'}}>
      <div style={{width: 58, height: 58, borderRadius: 29, background: last ? C.accent : C.teal, color: '#0A0F1E',
        fontSize: 32, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 20}}>{n}</div>
      <div style={{fontSize: 36, fontWeight: 800, lineHeight: 1.18}}>{text}</div>
    </Card>
  );
};

/** Zaman xetti: xett cekilir, hadise noqteleri acilir (when yuxarida, label asagida). */
export const Timeline: React.FC<{events: {label: string; when: string}[]; reveal: number[]}> = ({events, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pad = 110;
  const span = AREA.width - pad * 2;
  const xs = events.map((_, i) => pad + (events.length === 1 ? span / 2 : (i / (events.length - 1)) * span));
  const t = interpolate(frame, [at(reveal, 0), at(reveal, events.length - 1)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const y = 220;
  return (
    <Body>
      <div style={{position: 'absolute', left: pad, top: y - 4, width: span, height: 8, borderRadius: 4,
        background: C.line}} />
      <div style={{position: 'absolute', left: pad, top: y - 4, width: span * t, height: 8, borderRadius: 4,
        background: `linear-gradient(90deg, ${C.teal}, ${C.accent})`}} />
      {events.map((e, i) => <Event key={e.label} ev={e} x={xs[i]} y={y} delay={at(reveal, i)}
        last={i === events.length - 1} />)}
    </Body>
  );
};

const Event: React.FC<{ev: {label: string; when: string}; x: number; y: number; delay: number; last: boolean}> = (
  {ev, x, y, delay, last}) => {
  const p = useIn(delay, 14);
  const w = 300;
  return (
    <>
      {ev.when ? <div style={{position: 'absolute', left: x - w / 2, width: w, top: y - 110, textAlign: 'center',
        fontSize: 40, fontWeight: 800, color: last ? C.accent : C.teal, ...rise(p, 20)}}>{ev.when}</div> : null}
      <div style={{position: 'absolute', left: x - 22, top: y - 22, width: 44, height: 44, borderRadius: 22,
        background: last ? C.accent : C.teal, border: '7px solid #0A0F1E', transform: `scale(${p})`}} />
      <div style={{position: 'absolute', left: x - w / 2, width: w, top: y + 52, textAlign: 'center', fontSize: 36,
        fontWeight: 800, lineHeight: 1.2, ...rise(p, 20)}}>{ev.label}</div>
    </>
  );
};

/** Esas fikirler: sari isareli setirler bir-bir surusur. */
export const Keypoints: React.FC<{points: string[]; reveal: number[]}> = ({points, reveal}) => (
  <Body style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 30, paddingLeft: 20}}>
    {points.map((pt, i) => <Point key={pt} text={pt} delay={at(reveal, i)} />)}
  </Body>
);

const Point: React.FC<{text: string; delay: number}> = ({text, delay}) => {
  const p = useIn(delay);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 30, opacity: p,
      transform: `translateX(${interpolate(p, [0, 1], [-60, 0])}px)`}}>
      <div style={{width: 64, height: 64, borderRadius: 18, background: C.accent, flexShrink: 0, display: 'flex',
        alignItems: 'center', justifyContent: 'center'}}>
        <svg width={34} height={34} viewBox="0 0 24 24">
          <path d="M4 12.5 L10 18 L20 6" fill="none" stroke="#0A0F1E" strokeWidth={3.4} strokeLinecap="round"
            strokeLinejoin="round" />
        </svg>
      </div>
      <div style={{fontSize: 52, fontWeight: 800, lineHeight: 1.15}}>{text}</div>
    </div>
  );
};
