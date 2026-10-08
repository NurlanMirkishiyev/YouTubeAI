import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Motion} from './types';
import {H, W} from './theme';

// z0 -> z1 zoom, p0 -> p1 ufuqi movqe (-1 sol kenar, +1 sag kenar gorunur), q0 -> q1 saquli (-1 yuxari kenar)
// Faza 3.4 (istifadeci 2026-10-07): diaqonal pan, push, tilt - hamisi sabit suretle
type KB = {z0: number; z1: number; p0: number; p1: number; q0?: number; q1?: number};
const MOTIONS: Record<Motion, KB> = {
  zoom_in: {z0: 1.0, z1: 1.12, p0: 0, p1: 0},
  zoom_out: {z0: 1.12, z1: 1.0, p0: 0, p1: 0},
  pan_lr: {z0: 1.1, z1: 1.12, p0: -1, p1: 1},
  pan_rl: {z0: 1.1, z1: 1.12, p0: 1, p1: -1},
  diag_tl_br: {z0: 1.12, z1: 1.14, p0: -0.8, p1: 0.8, q0: -0.8, q1: 0.8},
  diag_br_tl: {z0: 1.12, z1: 1.14, p0: 0.8, p1: -0.8, q0: 0.8, q1: -0.8},
  push_in: {z0: 1.02, z1: 1.2, p0: 0, p1: 0, q0: 0, q1: -0.3},
  tilt_up: {z0: 1.12, z1: 1.12, p0: 0, p1: 0, q0: 0.9, q1: -0.9},
  tilt_down: {z0: 1.12, z1: 1.12, p0: 0, p1: 0, q0: -0.9, q1: 0.9},
};

/** Ken Burns: CSS transform sub-pixel islenir - ffmpeg zoompan-dakı tam-piksel titremesi yoxdur.
 * Sabit suret (easing yox): inOut her ~7 s-lik sehnenin evvelinde/sonunda fonu dayandirirdi ve
 * kecidlerde "dur-get" ritmi yaradirdi; suret sicrayisini 15 kadrlıq kecid ortusmesi gizledir. */
export const KenBurns: React.FC<{src: string; motion: Motion; blur?: number; dim?: number; flip?: boolean}> = (
  {src, motion, blur = 0, dim = 0, flip = false}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const m = MOTIONS[motion] ?? MOTIONS.zoom_in;
  const t = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const z = m.z0 + (m.z1 - m.z0) * t;
  const p = m.p0 + (m.p1 - m.p0) * t;
  const q = (m.q0 ?? 0) + ((m.q1 ?? 0) - (m.q0 ?? 0)) * t;
  const maxShift = ((z - 1) * W) / 2;          // kenardan bos zolaq cixmasin
  const maxShiftY = ((z - 1) * H) / 2;
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
      <Img src={staticFile(src)} style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform: `translate(${-p * maxShift}px, ${-q * maxShiftY}px) scale(${z})${flip ? ' scaleX(-1)' : ''}`,
        filter: blur ? `blur(${blur}px) brightness(${1 - dim})` : undefined,
        willChange: 'transform'}} />
      <AbsoluteFill style={{background:
        'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.28) 100%)'}} />
    </AbsoluteFill>
  );
};
