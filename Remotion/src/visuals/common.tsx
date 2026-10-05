import React from 'react';
import {interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT} from '../fonts';
import {ACCENT} from '../theme';

// Analitik sehne palitrasi: tund "data studio" + sari aksent (brend) + firuzeyi ikinci reng
export const C = {
  accent: ACCENT,
  teal: '#3DD6C4',
  coral: '#FF6B5A',
  text: '#FFFFFF',
  muted: '#9AA4BF',
  card: 'rgba(255,255,255,0.055)',
  line: 'rgba(255,255,255,0.12)',
};

// Chart sahesi: bayqus sagda (~1370 px-den), altyazi asagida (~870 px-den), lower-third yuxarida
export const AREA = {left: 90, top: 175, width: 1220, height: 660};
export const TITLE_H = 96;

export type Unit = '$' | '%' | '';

const decimals = (v: number) => (Number.isInteger(v) ? 0 : Math.min(2, (String(v).split('.')[1] ?? '').length));

export const fmt = (v: number, unit: Unit = '', digits = decimals(v)) => {
  const s = v.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  return unit === '$' ? `$${s}` : unit === '%' ? `${s}%` : s;
};

/** 0..1 spring - element reveal kadrinda (sehne basindan) acilir. */
export const useIn = (delay: number, damping = 200) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame, fps, delay, config: {damping}});
};

/** Reqem 0-dan deyerine qeder sayilir (reveal-dan ~0.9 s). */
export const Count: React.FC<{value: number; unit: Unit; delay: number; style?: React.CSSProperties}> = (
  {value, unit, delay, style}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = interpolate(frame, [delay, delay + 0.9 * fps], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const eased = 1 - Math.pow(1 - t, 3);
  return <span style={{fontVariantNumeric: 'tabular-nums', ...style}}>{fmt(value * eased, unit, decimals(value))}</span>;
};

export const Title: React.FC<{text: string}> = ({text}) => {
  const p = useIn(2);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, height: TITLE_H, display: 'flex', alignItems: 'center',
      opacity: p, transform: `translateY(${interpolate(p, [0, 1], [24, 0])}px)`}}>
      <div style={{width: 10, height: 58, borderRadius: 5, background: C.accent, marginRight: 24,
        transform: `scaleY(${p})`}} />
      <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 54, color: C.text, letterSpacing: -0.5}}>{text}</div>
    </div>
  );
};

export const Body: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <div style={{position: 'absolute', left: 0, top: TITLE_H + 24, width: AREA.width,
    height: AREA.height - TITLE_H - 24, fontFamily: FONT, color: C.text, ...style}}>{children}</div>
);

export const rise = (p: number, px = 40): React.CSSProperties => ({
  opacity: p, transform: `translateY(${interpolate(p, [0, 1], [px, 0])}px)`,
});

/** #55: chart sehnesinde bolme adi - AREA-nin ustunde (y 100-150), basliqdan 25 px yuxari, kicik ve sari. */
export const KICKER_TOP = 100;
export const Kicker: React.FC<{text: string}> = ({text}) => {
  const p = useIn(0);
  return (
    <div style={{position: 'absolute', left: AREA.left + 34, top: KICKER_TOP, fontFamily: FONT, fontWeight: 700,
      fontSize: 30, letterSpacing: 3, textTransform: 'uppercase', color: C.accent, ...rise(p, 12)}}>{text}</div>
  );
};
