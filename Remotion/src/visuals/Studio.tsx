import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {H, W} from '../theme';

/** Analitik sehnelerin ve giris/cixis kartinin dizayn fonu (#46: kart sehne fotosunu tekrar etmir).
 *  Tund gradient + incə setka + yavas suzen iki isiq - hereket yalniz useCurrentFrame ile. */
export const StudioBackdrop: React.FC<{dim?: number}> = ({dim = 0}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const gx = 30 + 8 * Math.sin(t / 6);
  const gy = 35 + 6 * Math.cos(t / 7);
  const tx = 75 + 7 * Math.cos(t / 8);
  const shift = (t * 6) % 80;
  return (
    <AbsoluteFill style={{background: 'linear-gradient(135deg, #0A0F1E 0%, #111A30 55%, #0B1222 100%)'}}>
      <AbsoluteFill style={{background:
        `radial-gradient(circle at ${gx}% ${gy}%, rgba(255,196,0,0.16) 0%, rgba(255,196,0,0) 38%),` +
        `radial-gradient(circle at ${tx}% 70%, rgba(61,214,196,0.13) 0%, rgba(61,214,196,0) 40%)`}} />
      <svg width={W} height={H} style={{position: 'absolute', opacity: 0.07}}>
        {Array.from({length: Math.ceil(W / 80) + 2}, (_, i) => (
          <line key={`v${i}`} x1={i * 80 - shift} y1={0} x2={i * 80 - shift} y2={H} stroke="#fff" strokeWidth={1} />))}
        {Array.from({length: Math.ceil(H / 80) + 1}, (_, i) => (
          <line key={`h${i}`} x1={0} y1={i * 80} x2={W} y2={i * 80} stroke="#fff" strokeWidth={1} />))}
      </svg>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,0.45) 100%)'}} />
      {dim ? <AbsoluteFill style={{background: `rgba(0,0,0,${dim})`}} /> : null}
    </AbsoluteFill>
  );
};
