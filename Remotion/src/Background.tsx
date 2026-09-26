import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Motion} from './types';
import {W} from './theme';

// z0 -> z1 zoom, p0 -> p1 ufuqi movqe (-1 sol kenar, +1 sag kenar gorunur)
const MOTIONS: Record<Motion, {z0: number; z1: number; p0: number; p1: number}> = {
  zoom_in: {z0: 1.0, z1: 1.12, p0: 0, p1: 0},
  zoom_out: {z0: 1.12, z1: 1.0, p0: 0, p1: 0},
  pan_lr: {z0: 1.1, z1: 1.12, p0: -1, p1: 1},
  pan_rl: {z0: 1.1, z1: 1.12, p0: 1, p1: -1},
};

/** Ken Burns: CSS transform sub-pixel islenir - ffmpeg zoompan-dakı tam-piksel titremesi yoxdur.
 * Sabit suret (easing yox): inOut her ~7 s-lik sehnenin evvelinde/sonunda fonu dayandirirdi ve
 * kecidlerde "dur-get" ritmi yaradirdi; suret sicrayisini 15 kadrlıq kecid ortusmesi gizledir. */
export const KenBurns: React.FC<{src: string; motion: Motion; blur?: number; dim?: number}> = (
  {src, motion, blur = 0, dim = 0}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const m = MOTIONS[motion];
  const t = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const z = m.z0 + (m.z1 - m.z0) * t;
  const p = m.p0 + (m.p1 - m.p0) * t;
  const maxShift = ((z - 1) * W) / 2;          // kenardan bos zolaq cixmasin
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: '#000'}}>
      <Img src={staticFile(src)} style={{
        width: '100%', height: '100%', objectFit: 'cover',
        transform: `translateX(${-p * maxShift}px) scale(${z})`,
        filter: blur ? `blur(${blur}px) brightness(${1 - dim})` : undefined,
        willChange: 'transform'}} />
      <AbsoluteFill style={{background:
        'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.28) 100%)'}} />
    </AbsoluteFill>
  );
};
