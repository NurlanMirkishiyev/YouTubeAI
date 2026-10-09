import React, {createContext, useContext} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT} from '../fonts';
import {DUR, EASE, ease, springIn, SPRING} from '../motion';
import {TypeText} from '../Text';
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

export const decimals = (v: number) => (Number.isInteger(v) ? 0 : Math.min(2, (String(v).split('.')[1] ?? '').length));

export const fmt = (v: number, unit: Unit = '', digits = decimals(v)) => {
  const s = v.toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits});
  return unit === '$' ? `$${s}` : unit === '%' ? `${s}%` : s;
};

/** 0..1 spring (motion.ts tokenleri) - element reveal kadrinda (sehne basindan) acilir. */
export const useIn = (delay: number, kind: keyof typeof SPRING = 'soft') => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return springIn(frame, fps, delay, kind);
};

/** Reqem 0-dan deyerine qeder sayilir (DUR.count, expo-out). Faza 2.5: oz sozune qeder skeletde "—". */
export const Count: React.FC<{value: number; unit: Unit; delay: number; style?: React.CSSProperties}> = (
  {value, unit, delay, style}) => {
  const frame = useCurrentFrame();
  const t = ease(frame, delay, DUR.count);
  const text = frame < delay ? '—' : fmt(value * t, unit, decimals(value));
  return <span style={{fontVariantNumeric: 'tabular-nums', ...style}}>{text}</span>;
};

/** #134 (reference video_yarat_v4 Chart): xett cekilerken ucunda parlayan "bas" noqte ve onunla hereket eden canli
 *  deyer nisani. Yalniz seqment cekilerken gorunur (0 < t < 1) - noqteye catanda noqtenin oz etiketi acilir. */
export const LiveHead: React.FC<{xy: readonly (readonly [number, number])[]; vals: number[]; progress: number[];
  unit: Unit; colorOf: (seg: number) => string; width: number}> = ({xy, vals, progress, unit, colorOf, width}) => {
  const frame = useCurrentFrame();
  const seg = progress.findIndex((t) => t > 0 && t < 1);
  if (seg < 0) return null;
  const t = progress[seg];
  const [x0, y0] = xy[seg];
  const [x1, y1] = xy[seg + 1];
  const x = x0 + (x1 - x0) * t;
  const y = y0 + (y1 - y0) * t;
  const value = vals[seg] + (vals[seg + 1] - vals[seg]) * t;
  const color = colorOf(seg);
  const glow = 22 + 10 * Math.sin(frame / 3);
  const left = Math.min(width - 260, x + 24);
  return (
    <>
      <div style={{position: 'absolute', left: x - 16, top: y - 16, width: 32, height: 32, borderRadius: 16,
        background: color, boxShadow: `0 0 ${glow}px ${color}, 0 0 ${glow * 2}px ${color}66`}} />
      <div style={{position: 'absolute', left, top: y - 96, padding: '8px 18px', borderRadius: 14,
        background: 'rgba(10,16,32,0.85)', border: `2px solid ${color}`, fontSize: 46, fontWeight: 800, color,
        fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>
        {fmt(value, unit, decimals(vals[seg + 1]))}
      </div>
    </>
  );
};

/** Faza 2.5 (istifadeci 2026-10-07): bos chart baslangici yoxdur - element acilmamis skelet kimi (GHOST) gorunur. */
export const GHOST = 0.28;

/** Faza 3.2: giris variantlari - Python motion.py secir (seed = slug), burada uslub. */
export const VariantCtx = createContext<string | null>(null);
const POP = new Set(['scale_pop', 'pop_terms', 'pop_steps', 'pop_sweep', 'center_burst', 'marker_drop', 'pop_events']);
const MASK = new Set(['mask_reveal', 'column_wipe', 'region_sweep', 'draw_fill', 'wipe', 'axes_curve_point']);
const SLIDE = new Set(['left_to_right', 'slide_terms', 'slide_steps', 'slide_events', 'split', 'slide_in', 'track_in']);
const CENTER = new Set(['center_out', 'face_off', 'gauge_fill']);

export const enterStyle = (variant: string | null, p: number, px = 40): React.CSSProperties => {
  const opacity = GHOST + (1 - GHOST) * p;
  const v = variant ?? 'rise';
  if (POP.has(v)) return {opacity, transform: `scale(${0.6 + 0.4 * EASE.back(Math.min(1, p))})`};
  if (MASK.has(v)) return {opacity, clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`};
  if (SLIDE.has(v)) return {opacity, transform: `translateX(${interpolate(p, [0, 1], [-px * 1.6, 0])}px)`};
  if (CENTER.has(v)) return {opacity, transform: `scaleX(${0.4 + 0.6 * p})`};
  if (v === 'flip') return {opacity, transform: `perspective(900px) rotateY(${(1 - p) * 75}deg)`};
  if (v === 'digit_roll') return {opacity, transform: `translateY(${interpolate(p, [0, 1], [px * 1.5, 0])}px)`,
    clipPath: `inset(${(1 - p) * 40}% 0 0 0)`};
  return {opacity, transform: `translateY(${interpolate(p, [0, 1], [px, 0])}px)`};
};

/** Komponentin giris uslubu (VariantCtx-den). */
export const useEnter = () => {
  const v = useContext(VariantCtx);
  return (p: number, px = 40) => enterStyle(v, p, px);
};

/** Kohne ad (Faza 2): variantsiz "rise". */
export const rise = (p: number, px = 40): React.CSSProperties => enterStyle(null, p, px);

export const TitleVariantCtx = createContext<string>('slide_up');

export const Title: React.FC<{text: string}> = ({text}) => {
  const p = useIn(0);
  const variant = useContext(TitleVariantCtx);
  const body = variant === 'typewriter' ? <TypeText text={text} start={0} /> : text;
  const style = variant === 'mask_reveal' ? enterStyle('mask_reveal', p) : enterStyle('rise', p, 24);
  return (
    <div style={{position: 'absolute', left: 0, top: 0, height: TITLE_H, display: 'flex', alignItems: 'center',
      ...(variant === 'typewriter' ? {} : style)}}>
      <div style={{width: 10, height: 58, borderRadius: 5, background: C.accent, marginRight: 24,
        transform: `scaleY(${p})`}} />
      <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 54, color: C.text, letterSpacing: -0.5}}>{body}</div>
    </div>
  );
};

export const Body: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
  <div style={{position: 'absolute', left: 0, top: TITLE_H + 24, width: AREA.width,
    height: AREA.height - TITLE_H - 24, fontFamily: FONT, color: C.text, ...style}}>{children}</div>
);

/** #55: chart sehnesinde bolme adi - AREA-nin ustunde (y 100-150), basliqdan 25 px yuxari, kicik ve sari. */
export const KICKER_TOP = 100;
export const Kicker: React.FC<{text: string; variant?: string | null}> = ({text, variant}) => {
  const p = useIn(0);
  const v = variant ?? 'fade_slide';
  return (
    <div style={{position: 'absolute', left: AREA.left + 34, top: KICKER_TOP, fontFamily: FONT, fontWeight: 700,
      fontSize: 30, letterSpacing: v === 'track_in' ? 3 + 10 * (1 - p) : 3, textTransform: 'uppercase',
      color: C.accent, ...(v === 'typewriter' ? {} : enterStyle(v === 'track_in' ? 'rise' : v, p, 12))}}>
      {v === 'typewriter' ? <TypeText text={text} start={0} /> : text}
    </div>
  );
};
