import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Overlay} from '../types';
import {FONT} from '../fonts';
import {DUR, EASE, ease} from '../motion';
import {C, Count, useIn} from './common';

/** Faza 2.7 (istifadeci 2026-10-07; reference: counter_events): foto sehnesinde danisilan pul/faiz reqemi
 *  oz sozunde count-up kart kimi gorunur (<= 2.5 s, sehnede <= 1), bayqus ve altyazi zonasindan kenarda. */
export const NumberOverlay: React.FC<{o: Overlay}> = ({o}) => {
  const frame = useCurrentFrame();
  const p = useIn(o.from, 'snappy');
  const out = 1 - ease(frame, o.from + o.frames - DUR.out, DUR.out, EASE.in);
  if (frame < o.from || frame > o.from + o.frames) return null;
  const [x, y, w, h] = o.box;
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div style={{position: 'absolute', left: x, top: y, width: w, height: h, display: 'flex',
        alignItems: 'center', opacity: p * out, transform: `scale(${0.86 + 0.14 * p})`, transformOrigin: 'left center'}}>
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 150, color: C.accent, lineHeight: 1,
          padding: '18px 34px', borderRadius: 24, background: 'rgba(10,15,30,0.72)',
          boxShadow: `0 0 50px ${C.accent}44`}}>
          <Count value={o.value} unit={o.unit} delay={o.from} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
