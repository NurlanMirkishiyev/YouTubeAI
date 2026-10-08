import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {DUR, ease, EASE} from './motion';
import {Emphasis} from './types';

/** Faza 3.7 (istifadeci 2026-10-07): nitqle sinxron vurgu - acar reqem seslenende ekran kenarinda qisa accent
 *  parlamasi (<= 400 ms). Siyahi Python-da (motion.emphasis) limitlenir: saniyede <= 3, 20 s-de <= 1 "boyuk".
 *  Kenar parlamasi bayqusu ve altyaziyi ortmur (merkez seffaf qalir). */
const Pulse: React.FC<{frames: number; big: boolean}> = ({frames, big}) => {
  const frame = useCurrentFrame();
  const half = Math.max(1, Math.floor(frames / 2));
  const a = ease(frame, 0, half, EASE.out) - ease(frame, half, frames - half, EASE.inOut);
  const glow = big ? 0.42 : 0.22;
  const spread = big ? 190 : 110;
  return (
    <AbsoluteFill style={{pointerEvents: 'none',
      boxShadow: `inset 0 0 ${spread}px rgba(255,196,0,${(glow * a).toFixed(3)})`}} />
  );
};

export const EmphasisLayer: React.FC<{items: Emphasis[]}> = ({items}) => (
  <>
    {items.map((e) => (
      <Sequence key={`em${e.at}`} from={e.at} durationInFrames={Math.min(e.frames, DUR.pulse)} layout="none">
        <Pulse frames={Math.min(e.frames, DUR.pulse)} big={e.big} />
      </Sequence>))}
  </>
);

/** Faza 3.6: "editorial" theme-de yungul film gorunusu (reference: rəng tənzimləməsi, vinyet, incə dənə).
 *  Dene her 2 kadrda seed deyisir (deterministik - eyni kadr eyni gorunus). Bayqusun ALTINDA qoyulur. */
const GRAIN_EVERY = 2;
export const FilmLook: React.FC = () => {
  const frame = useCurrentFrame();
  const seed = Math.floor(frame / GRAIN_EVERY) % 97;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <AbsoluteFill style={{background: 'rgba(255,170,90,0.06)', mixBlendMode: 'soft-light'}} />
      <AbsoluteFill style={{background:
        'radial-gradient(ellipse at center, rgba(0,0,0,0) 58%, rgba(10,6,0,0.32) 100%)'}} />
      <svg width="100%" height="100%" style={{position: 'absolute', opacity: 0.07, mixBlendMode: 'overlay'}}>
        <filter id={`grain${seed}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves={2} seed={seed} stitchTiles="stitch" />
          <feColorMatrix type="saturate" values="0" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain${seed})`} />
      </svg>
    </AbsoluteFill>
  );
};
