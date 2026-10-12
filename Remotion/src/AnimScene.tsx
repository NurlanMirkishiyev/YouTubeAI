import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ANIMS} from './anim/Anims';
import {COLORS, SAFE_RIGHT} from './theme';
import {Anim} from './types';

export const AnimScene: React.FC<{anim: Anim}> = ({anim}) => {
  const C = ANIMS[anim.kind] ?? ANIMS.quote;
  return (
    <AbsoluteFill style={{background: `radial-gradient(circle at 30% 40%, ${COLORS.bg2}, ${COLORS.bg1})`,
      justifyContent: 'center', alignItems: 'center', paddingRight: SAFE_RIGHT, paddingLeft: 80}}>
      <C a={anim} />
    </AbsoluteFill>
  );
};
