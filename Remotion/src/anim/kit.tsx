import React, {createContext, useContext} from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT, Palette, PALETTES} from '../theme';
import {Icon} from './Icon';

// Animasiyalarin ortaq "premium" dili: tema, yay hereketi, suse kart, gradient yazi, ikon nisani, parilti.
export const ThemeCtx = createContext<Palette>(PALETTES.royal);
export const usePal = (): Palette => useContext(ThemeCtx);
export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
export const EASE = Easing.bezier(0.16, 1, 0.3, 1);

export const useSpr = (delay = 0, stiff = 110, damping = 14): number => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping, stiffness: stiff, mass: 0.8}});
};

export const ramp = (f: number, a: number, b: number): number => interpolate(f, [a, b], [0, 1], {...clamp, easing: EASE});

export const txt = (size: number, color = '#fff', weight = 800): React.CSSProperties =>
  ({fontFamily: FONT, fontWeight: weight, fontSize: size, color, lineHeight: 1.12, letterSpacing: -0.5});

export const gradText = (p: Palette): React.CSSProperties => ({backgroundImage: `linear-gradient(180deg, ${p.a2} 0%, ${p.a1} 70%)`,
  WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', filter: `drop-shadow(0 0 28px ${p.glow})`});

export const glass = (p: Palette, active = 0): React.CSSProperties => ({
  position: 'relative', overflow: 'hidden', borderRadius: 28,
  background: 'linear-gradient(150deg, rgba(255,255,255,0.13) 0%, rgba(255,255,255,0.035) 100%)',
  border: `1.5px solid ${active ? p.a1 : 'rgba(255,255,255,0.17)'}`,
  boxShadow: `0 30px 70px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.22), 0 0 ${30 + 30 * active}px ${p.glow}`,
});

/** Kartin ustunden vaxtasiri kecen isiq zolagi. */
export const Shine: React.FC<{every?: number; delay?: number}> = ({every = 110, delay = 0}) => {
  const f = useCurrentFrame();
  const t = ((f - delay) % every + every) % every / 40;
  if (f < delay || t > 1) return null;
  return <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
    background: `linear-gradient(110deg, transparent ${t * 140 - 40}%, rgba(255,255,255,0.22) ${t * 140 - 20}%, transparent ${t * 140}%)`}} />;
};

/** Yuvarlaq gradient nisan icinde cizilen ikon + nefes alan halqalar. */
export const Badge: React.FC<{icon?: string; size: number; delay?: number; rings?: boolean}> = ({icon, size, delay = 0, rings}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const s = useSpr(delay, 160, 11);
  const draw = ramp(f, delay + 6, delay + 30);
  const ring = (k: number) => {
    const t = ((f - delay - k * 22) % 66) / 66;
    return f - delay < k * 22 ? null : <div key={k} style={{position: 'absolute', inset: 0, borderRadius: '50%',
      border: `3px solid ${p.a1}`, opacity: (1 - t) * 0.6, transform: `scale(${1 + t * 0.9})`}} />;
  };
  return (
    <div style={{position: 'relative', width: size, height: size, flexShrink: 0, transform: `scale(${s})`}}>
      {rings ? [0, 1, 2].map(ring) : null}
      <div style={{position: 'absolute', inset: 0, borderRadius: '50%',
        background: `radial-gradient(circle at 30% 25%, ${p.a2}, ${p.a1} 55%, ${p.tint} 100%)`,
        boxShadow: `0 0 ${size * 0.35}px ${p.glow}, inset 0 -${size * 0.06}px ${size * 0.12}px rgba(0,0,0,0.25)`,
        display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <Icon name={icon} size={size * 0.52} color="#0b0f1e" t={draw} stroke={2.1} />
      </div>
    </div>
  );
};

/** Merkezden yayilan, yavas firlanan isiq suaalari (VS, sayac arxasi). */
export const Burst: React.FC<{size: number; delay?: number; rays?: number}> = ({size, delay = 0, rays = 14}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const o = ramp(f, delay, delay + 20);
  return (
    <div style={{position: 'absolute', width: size, height: size, left: '50%', top: '50%', pointerEvents: 'none',
      transform: `translate(-50%, -50%) rotate(${f * 0.4}deg) scale(${0.6 + 0.4 * o})`, opacity: 0.55 * o,
      background: `repeating-conic-gradient(from 0deg, ${p.a1}55 0deg ${180 / rays}deg, transparent ${180 / rays}deg ${360 / rays}deg)`,
      WebkitMaskImage: 'radial-gradient(circle, #000 0%, transparent 68%)', maskImage: 'radial-gradient(circle, #000 0%, transparent 68%)'}} />
  );
};

export const fmt = (v: number): string => (Number.isInteger(v) ? v.toLocaleString('en-US')
  : v.toLocaleString('en-US', {maximumFractionDigits: 2}));

/** Reqemin ease-out ile sayilmasi (son deyer deqiq). */
export const useCount = (value: number, from = 8, to = 52): number => {
  const f = useCurrentFrame();
  const v = interpolate(f, [from, to], [0, value], {...clamp, easing: Easing.out(Easing.cubic)});
  return Number.isInteger(value) ? Math.round(v) : Math.round(v * 100) / 100;
};

export const iconAt = (a: {icon?: string; icons?: string[]}, k: number): string | undefined => a.icons?.[k] ?? a.icon;
