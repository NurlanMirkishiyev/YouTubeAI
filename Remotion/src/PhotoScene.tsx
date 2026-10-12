import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export const PhotoScene: React.FC<{src: string; n: number}> = ({src, n}) => {
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const t = interpolate(f, [0, Math.max(1, durationInFrames)], [0, 1], {extrapolateRight: 'clamp'});
  const dir = [[1, 0], [-1, 0], [0, 1], [0, -1]][n % 4];
  const scale = n % 2 ? 1.06 + 0.06 * t : 1.12 - 0.06 * t;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover',
        transform: `scale(${scale}) translate(${dir[0] * 20 * t}px, ${dir[1] * 12 * t}px)`}} />
    </AbsoluteFill>
  );
};
