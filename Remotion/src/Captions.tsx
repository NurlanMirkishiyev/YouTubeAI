import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT, SAFE_RIGHT} from './theme';
import {Caption, Word} from './types';

// Oxunan soz rengle izlenir: deyilmis sozler ag, indiki soz sari + "pop", hele deyilmeyenler solgun.
const SPOKEN = '#ffffff', UPCOMING = 'rgba(255,255,255,0.55)';
const STROKE = '0 3px 0 #000, 0 0 12px rgba(0,0,0,0.85), 2px 2px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000';

const WordView: React.FC<{w: Word; f: number}> = ({w, f}) => {
  const {fps} = useVideoConfig();
  const active = f >= w.from && f < w.to;
  const pop = spring({frame: f - w.from, fps, config: {damping: 12, stiffness: 220, mass: 0.5}});
  const scale = active ? interpolate(pop, [0, 1], [1, 1.1]) : 1;
  return (
    <span style={{display: 'inline-block', margin: '0 13px', transform: `scale(${scale}) translateY(${active ? -3 : 0}px)`,
      color: active ? COLORS.accent : f >= w.to ? SPOKEN : UPCOMING, textShadow: STROKE}}>{w.text}</span>
  );
};

export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = captions.find((x) => f >= x.from && f < x.to);
  if (!c) return null;
  const enter = spring({frame: f - c.from, fps, config: {damping: 16, stiffness: 180}});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 64, paddingRight: SAFE_RIGHT}}>
      <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 58, lineHeight: 1.25, maxWidth: 1300, textAlign: 'center',
        padding: '14px 22px', borderRadius: 18, background: 'rgba(6,10,22,0.5)',
        opacity: enter, transform: `translateY(${(1 - enter) * 22}px) scale(${0.94 + 0.06 * enter})`}}>
        {c.words?.length ? c.words.map((w, i) => <WordView key={i} w={w} f={f} />)
          : <span style={{color: SPOKEN, textShadow: STROKE}}>{c.text}</span>}
      </div>
    </AbsoluteFill>
  );
};
