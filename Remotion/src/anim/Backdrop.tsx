import React from 'react';
import {AbsoluteFill, random, useCurrentFrame} from 'remotion';
import {usePal} from './kit';

// Animasiya sehnesinin canli fonu: tema gradienti, uzen isiq kureleri, axan perspektiv tor, hissecikler,
// vaxtasiri kecen isiq zolagi, vinyetka. Blur filtri yoxdur (render suretli qalsin) - yalniz gradientler.
const ORBS = [{x: 0.22, y: 0.3, r: 760, sx: 0.011, sy: 0.008, k: 'a1'}, {x: 0.7, y: 0.65, r: 900, sx: 0.007, sy: 0.012, k: 'a2'},
  {x: 0.5, y: 0.1, r: 620, sx: 0.013, sy: 0.006, k: 'a1'}] as const;
const DOTS = Array.from({length: 34}, (_, i) => ({x: random(`x${i}`), y: random(`y${i}`), s: 2 + random(`s${i}`) * 4,
  v: 0.25 + random(`v${i}`) * 0.7, ph: random(`p${i}`) * 6.28}));

export const Backdrop: React.FC<{seed: number}> = ({seed}) => {
  const p = usePal();
  const f = useCurrentFrame() + seed * 97;
  const sweep = (f % 240) / 240;
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: `radial-gradient(ellipse at 35% 35%, ${p.bg2} 0%, ${p.bg1} 70%)`}}>
      {ORBS.map((o, i) => (
        <div key={i} style={{position: 'absolute', width: o.r, height: o.r, borderRadius: '50%',
          left: `calc(${(o.x + 0.08 * Math.sin(f * o.sx + i)) * 100}% - ${o.r / 2}px)`,
          top: `calc(${(o.y + 0.07 * Math.cos(f * o.sy + i * 2)) * 100}% - ${o.r / 2}px)`,
          background: `radial-gradient(circle, ${o.k === 'a1' ? p.a1 : p.a2}38 0%, transparent 65%)`}} />
      ))}
      <div style={{position: 'absolute', left: '-50%', right: '-50%', bottom: '-10%', height: '65%',
        transform: 'perspective(700px) rotateX(68deg)', transformOrigin: 'bottom', opacity: 0.22,
        backgroundImage: `linear-gradient(${p.a2}66 2px, transparent 2px), linear-gradient(90deg, ${p.a2}66 2px, transparent 2px)`,
        backgroundSize: '90px 90px', backgroundPosition: `0px ${(f * 1.2) % 90}px`,
        WebkitMaskImage: 'linear-gradient(to top, #000 10%, transparent 85%)', maskImage: 'linear-gradient(to top, #000 10%, transparent 85%)'}} />
      {DOTS.map((d, i) => {
        const y = ((d.y - (f * d.v) / 1400) % 1 + 1) % 1;
        return <div key={i} style={{position: 'absolute', left: `${d.x * 100}%`, top: `${y * 100}%`, width: d.s, height: d.s,
          borderRadius: '50%', background: i % 3 ? p.a2 : p.a1, opacity: 0.25 + 0.45 * (0.5 + 0.5 * Math.sin(f * 0.06 + d.ph)),
          boxShadow: `0 0 ${d.s * 3}px ${p.a1}`}} />;
      })}
      <div style={{position: 'absolute', inset: 0, opacity: 0.5,
        background: `linear-gradient(115deg, transparent ${sweep * 160 - 40}%, rgba(255,255,255,0.06) ${sweep * 160 - 25}%, transparent ${sweep * 160 - 10}%)`}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at 45% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)'}} />
    </AbsoluteFill>
  );
};
