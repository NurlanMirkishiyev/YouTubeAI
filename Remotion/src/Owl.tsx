import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {H, OWL_BOTTOM, OWL_MARGIN_X} from './theme';
import {OwlPose, Scene, Side} from './types';

// Poz ani deyisir (cross-fade iki bayqusu ust-uste gosterirdi): fon kecidinin ortasinda - kesik
// fonun slide/fade-i ile ortulur. Kecid 15 kadrdir (Root transitionFrames).
const SWAP_AT = 7;
const FADE_IN = 8;       // ilk sehnede gorunme
const FADE_END = 10;     // son sehnede outro kartina kecid

type Placed = Scene & {start: number};

/** Istifadeci 2026-09-27: personaj sabit dayansin, terpenmesin - yalniz her sehnede ona uygun
 *  poz sekli gosterilir. Nefes/yellenme/danisiq/spring girisi ve teref deyisme silinib. */
const OwlImg: React.FC<{pose: OwlPose; side: Side; opacity: number}> = ({pose, side, opacity}) => {
  const h = pose.height * H;
  const w = (pose.w / pose.h) * h;
  const flip = side === 'right' && pose.flippable ? -1 : 1;
  const pos = side === 'left' ? {left: OWL_MARGIN_X} : {right: OWL_MARGIN_X};
  return (
    <>
      <div style={{position: 'absolute', bottom: OWL_BOTTOM - 16, ...pos, width: w, height: 34,
        opacity: opacity * 0.55,
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 70%)'}} />
      <div style={{position: 'absolute', bottom: OWL_BOTTOM, ...pos, width: w, height: h, opacity}}>
        <Img src={staticFile(`owl/${pose.name}.png`)}
          style={{width: '100%', height: '100%', transform: `scaleX(${flip})`}} />
      </div>
    </>
  );
};

export const OwlLayer: React.FC<{scenes: Placed[]; poses: Record<string, OwlPose>; endFrame: number}> = (
  {scenes, poses, endFrame}) => {
  const frame = useCurrentFrame();
  const k = scenes.findIndex((s) => frame >= s.start && frame < s.start + s.frames);
  if (k < 0) return null;
  const cur = scenes[k];
  const prev = k > 0 ? scenes[k - 1] : null;
  const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const show = interpolate(frame, [scenes[0].start, scenes[0].start + FADE_IN], [0, 1], clamp)
    * interpolate(frame, [endFrame - FADE_END, endFrame], [1, 0], clamp);
  const shown = prev && frame - cur.start < SWAP_AT ? prev : cur;
  return (
    <AbsoluteFill>
      <OwlImg pose={poses[shown.pose]} side={shown.side} opacity={show} />
    </AbsoluteFill>
  );
};
