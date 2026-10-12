import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {OWL_BOTTOM, OWL_H, OWL_RIGHT} from './theme';
import {Scene} from './types';

const SWAP = 8;
export const OwlLayer: React.FC<{scenes: Scene[]}> = ({scenes}) => {
  const f = useCurrentFrame();
  let i = scenes.findIndex((s) => f >= s.from && f < s.from + s.frames);
  if (i < 0) {
    if (scenes.length === 0) return null;
    i = 0;
    scenes.forEach((s, k) => { if (s.from <= f) i = k; });
  }
  const local = f - scenes[i].from;
  const inT = i === 0 ? 1 : interpolate(local, [0, SWAP], [0, 1], {extrapolateRight: 'clamp'});
  const owlStyle = (o: number, s: number): React.CSSProperties => ({position: 'absolute', right: OWL_RIGHT,
    bottom: OWL_BOTTOM, height: OWL_H, opacity: o, transform: `scale(${s})`, transformOrigin: 'bottom center',
    filter: 'drop-shadow(0 12px 18px rgba(0,0,0,0.45))'});
  return (
    <AbsoluteFill>
      {i > 0 && inT < 1 ? <Img src={staticFile(scenes[i - 1].owl)} style={owlStyle(1, 1)} /> : null}
      <Img src={staticFile(scenes[i].owl)} style={owlStyle(1, 0.94 + 0.06 * inT)} />
    </AbsoluteFill>
  );
};
