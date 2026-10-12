import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {COLORS, FONT} from './theme';

export const SectionTitle: React.FC<{text: string}> = ({text}) => {
  const f = useCurrentFrame();
  const o = interpolate(f, [0, 10, 80, 95], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <div style={{position: 'absolute', top: 50, left: 60, opacity: o, fontFamily: FONT, fontWeight: 800, fontSize: 40,
      color: COLORS.text, background: 'rgba(11,19,36,0.78)', borderLeft: `8px solid ${COLORS.accent}`,
      padding: '12px 24px', borderRadius: 8}}>{text}</div>
  );
};
