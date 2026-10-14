import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {ANIMS} from './anim/Anims';
import {Backdrop} from './anim/Backdrop';
import {SAFE_RIGHT} from './theme';
import {Anim} from './types';

// Canli fon + yavas "kamera" yaxinlasmasi ve yellenme: animasiya girisden sonra da hec vaxt donmur.
export const AnimScene: React.FC<{anim: Anim; n: number}> = ({anim, n}) => {
  const f = useCurrentFrame();
  const C = ANIMS[anim.kind] ?? ANIMS.quote;
  const push = interpolate(f, [0, 600], [1, 1.05], {extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill>
      <Backdrop seed={n} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', paddingRight: SAFE_RIGHT, paddingLeft: 80,
        paddingTop: 90, paddingBottom: 190}}>
        <div style={{transform: `scale(${push}) translateY(${Math.sin(f / 40) * 6}px) rotate(${Math.sin(f / 70) * 0.4}deg)`}}>
          <C a={anim} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
