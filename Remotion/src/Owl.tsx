import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {H, OWL_BOTTOM, OWL_MARGIN_X} from './theme';
import {OwlPose, Scene, Side} from './types';

const SWAP = 9;          // poz deyisende cross-fade (kadr)
const SIDE_OUT = 12;     // teref deyisende kohne bayqus cixir
const FADE_END = 10;     // son sehnede outro kartina kecid

type Placed = Scene & {start: number};

/** Yungul, fasilesiz "canli" hereket: nefes, yellenme, uzme. Kesr pikseller - CSS hamar isleyir. */
const idle = (t: number) => ({
  y: 6 * Math.sin((2 * Math.PI * t) / 2.9),
  breathe: 1 + 0.012 * Math.sin((2 * Math.PI * t) / 2.9 + 1.1),
  rot: 1.1 * Math.sin((2 * Math.PI * t) / 4.3),
});

const OwlImg: React.FC<{pose: OwlPose; side: Side; opacity: number; dx: number; dy: number;
  scale: number; rot: number; breathe: number}> = ({pose, side, opacity, dx, dy, scale, rot, breathe}) => {
  const h = pose.height * H;
  const w = (pose.w / pose.h) * h;
  const flip = side === 'right' && pose.flippable ? -1 : 1;
  const pos = side === 'left' ? {left: OWL_MARGIN_X} : {right: OWL_MARGIN_X};
  const lift = Math.max(0, -dy);
  return (
    <>
      <div style={{position: 'absolute', bottom: OWL_BOTTOM - 16, ...pos, width: w, height: 34,
        opacity: opacity * (0.55 - lift * 0.004), transform: `translateX(${dx}px) scaleX(${1 - lift * 0.004})`,
        background: 'radial-gradient(ellipse at center, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 70%)'}} />
      <div style={{position: 'absolute', bottom: OWL_BOTTOM, ...pos, width: w, height: h, opacity,
        transformOrigin: '50% 100%',
        transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg) scale(${scale}) scaleY(${breathe})`}}>
        <Img src={staticFile(`owl/${pose.name}.png`)}
          style={{width: '100%', height: '100%', transform: `scaleX(${flip})`}} />
      </div>
    </>
  );
};

const useTalk = (audio: string, frame: number, fps: number): number => {
  const data = useAudioData(staticFile(audio));
  if (!data) return 0;
  const bins = visualizeAudio({fps, frame, audioData: data, numberOfSamples: 32, smoothing: true});
  const low = bins.slice(0, 8).reduce((a, b) => a + b, 0) / 8;
  return Math.min(1, low * 3.2);
};

export const OwlLayer: React.FC<{scenes: Placed[]; poses: Record<string, OwlPose>; audio: string;
  endFrame: number}> = ({scenes, poses, audio, endFrame}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const talk = useTalk(audio, frame, fps);
  const k = scenes.findIndex((s) => frame >= s.start && frame < s.start + s.frames);
  if (k < 0) return null;
  const cur = scenes[k];
  const prev = k > 0 ? scenes[k - 1] : null;
  const local = frame - cur.start;
  const id = idle(frame / fps);
  const talkY = -talk * 12;
  const base = {rot: id.rot, breathe: id.breathe * (1 + talk * 0.02)};
  const out = interpolate(frame, [endFrame - FADE_END, endFrame], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const enterFrom = !prev || prev.side !== cur.side;
  const delay = prev && prev.side !== cur.side ? SIDE_OUT - 4 : prev ? 0 : 8;
  const sp = spring({frame: local, fps, delay, config: {damping: 14, stiffness: 120}});
  const layers: React.ReactNode[] = [];

  if (prev && (prev.side !== cur.side || prev.pose !== cur.pose)) {
    const p = poses[prev.pose];
    if (prev.side !== cur.side) {
      const t = interpolate(local, [0, SIDE_OUT], [0, 1], {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'});
      const dir = prev.side === 'left' ? -1 : 1;
      layers.push(<OwlImg key="prev" pose={p} side={prev.side} opacity={1 - t} dx={dir * t * 520}
        dy={id.y} scale={1} {...base} />);
    } else {
      const t = interpolate(local, [0, SWAP], [0, 1], {extrapolateRight: 'clamp', extrapolateLeft: 'clamp'});
      layers.push(<OwlImg key="prev" pose={p} side={prev.side} opacity={1 - t} dx={0}
        dy={id.y + talkY} scale={1 - 0.04 * t} {...base} />);
    }
  }
  const c = poses[cur.pose];
  const dir = cur.side === 'left' ? -1 : 1;
  const dx = enterFrom ? interpolate(sp, [0, 1], [dir * 520, 0]) : 0;
  const swapIn = prev && !enterFrom && prev.pose !== cur.pose;
  const opacity = (enterFrom ? Math.min(1, sp * 1.4) : swapIn
    ? interpolate(local, [0, SWAP], [0, 1], {extrapolateRight: 'clamp'}) : 1) * out;
  const scale = swapIn ? interpolate(sp, [0, 1], [0.94, 1]) : 1;
  layers.push(<OwlImg key="cur" pose={c} side={cur.side} opacity={opacity} dx={dx}
    dy={id.y + talkY} scale={scale} {...base} />);
  return <AbsoluteFill>{layers}</AbsoluteFill>;
};
