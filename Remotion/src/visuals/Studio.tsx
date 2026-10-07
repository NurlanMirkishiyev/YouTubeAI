import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {H, W} from '../theme';

/** Analitik sehnelerin ve giris/cixis kartinin dizayn fonu (#46: kart sehne fotosunu tekrar etmir).
 *  Faza 3.5 (istifadeci 2026-10-07): brend palitrasi daxilinde 4 variant - epizoda bir defe secilir (motion.py).
 *  Hereket yalniz useCurrentFrame ile, yavas (diqqeti chart-dan almir). */
const BASE = 'linear-gradient(135deg, #0A0F1E 0%, #111A30 55%, #0B1222 100%)';
const VIGNETTE = 'radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.45) 100%)';

const Grid: React.FC<{step: number; shift: number; opacity: number; diagonal?: boolean}> = (
  {step, shift, opacity, diagonal = false}) => (
  <svg width={W} height={H} style={{position: 'absolute', opacity}}>
    {Array.from({length: Math.ceil(W / step) + 2}, (_, i) => (
      <line key={`v${i}`} x1={i * step - shift} y1={0} x2={i * step - shift + (diagonal ? H * 0.4 : 0)} y2={H}
        stroke="#fff" strokeWidth={1} />))}
    {Array.from({length: Math.ceil(H / step) + 1}, (_, i) => (
      <line key={`h${i}`} x1={0} y1={i * step} x2={W} y2={i * step} stroke="#fff" strokeWidth={1} />))}
  </svg>
);

export const StudioBackdrop: React.FC<{dim?: number; variant?: string | null}> = ({dim = 0, variant}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const v = variant ?? 'studio';
  let layer: React.ReactNode;
  if (v === 'aurora') {
    const a = 30 + 10 * Math.sin(t / 7);
    layer = <AbsoluteFill style={{background:
      `linear-gradient(${120 + 8 * Math.sin(t / 9)}deg, rgba(61,214,196,0) ${a}%, rgba(61,214,196,0.12) ${a + 12}%, ` +
      `rgba(255,196,0,0.10) ${a + 26}%, rgba(255,196,0,0) ${a + 40}%)`}} />;
  } else if (v === 'blueprint') {
    layer = <>
      <AbsoluteFill style={{background: 'radial-gradient(circle at 20% 15%, rgba(61,214,196,0.14) 0%, rgba(61,214,196,0) 45%)'}} />
      <Grid step={40} shift={(t * 3) % 40} opacity={0.05} />
      <Grid step={200} shift={(t * 3) % 200} opacity={0.08} diagonal />
    </>;
  } else if (v === 'spotlight') {
    const x = 35 + 6 * Math.sin(t / 8);
    layer = <AbsoluteFill style={{background:
      `radial-gradient(ellipse 55% 70% at ${x}% 40%, rgba(255,196,0,0.13) 0%, rgba(255,196,0,0.04) 45%, rgba(0,0,0,0) 70%)`}} />;
  } else {
    const gx = 30 + 8 * Math.sin(t / 6);
    const gy = 35 + 6 * Math.cos(t / 7);
    const tx = 75 + 7 * Math.cos(t / 8);
    layer = <>
      <AbsoluteFill style={{background:
        `radial-gradient(circle at ${gx}% ${gy}%, rgba(255,196,0,0.16) 0%, rgba(255,196,0,0) 38%),` +
        `radial-gradient(circle at ${tx}% 70%, rgba(61,214,196,0.13) 0%, rgba(61,214,196,0) 40%)`}} />
      <Grid step={80} shift={(t * 6) % 80} opacity={0.07} />
    </>;
  }
  return (
    <AbsoluteFill style={{background: BASE}}>
      {layer}
      <AbsoluteFill style={{background: VIGNETTE}} />
      {dim ? <AbsoluteFill style={{background: `rgba(0,0,0,${dim})`}} /> : null}
    </AbsoluteFill>
  );
};
