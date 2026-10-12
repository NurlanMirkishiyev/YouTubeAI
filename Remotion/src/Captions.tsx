import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {FONT, SAFE_RIGHT} from './theme';
import {Caption} from './types';

export const Captions: React.FC<{captions: Caption[]}> = ({captions}) => {
  const f = useCurrentFrame();
  const c = captions.find((x) => f >= x.from && f < x.to);
  if (!c) return null;
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 70, paddingRight: SAFE_RIGHT}}>
      <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 52, color: '#fff', background: 'rgba(0,0,0,0.62)',
        padding: '12px 26px', borderRadius: 14, maxWidth: 1250, textAlign: 'center', lineHeight: 1.2}}>{c.text}</div>
    </AbsoluteFill>
  );
};
