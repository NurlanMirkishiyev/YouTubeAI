import React from 'react';
import {useCurrentFrame} from 'remotion';
import {DUR} from './motion';

/** Faza 3.2 (istifadeci 2026-10-07; reference: hook typewriter): metn herf-herf yazilir. Qara ekran ve sukut
 *  ELAVE ETMIR - sehnenin/kartin ustunde, danisiqla eyni vaxtda islenir; muddet deyismir. Yazilmamis hisse seffaf
 *  qalir (setir yerlesmesi tullanmir). */
export const TypeText: React.FC<{text: string; start: number; framesPerChar?: number}> = (
  {text, start, framesPerChar = DUR.typeChar}) => {
  const frame = useCurrentFrame();
  const n = Math.max(0, Math.min(text.length, Math.floor((frame - start) / framesPerChar)));
  const typing = n < text.length;
  return (
    <span>
      {text.slice(0, n)}
      {typing ? <span style={{display: 'inline-block', width: 0, overflow: 'visible', opacity: 0.85}}>▍</span> : null}
      <span style={{opacity: 0}}>{text.slice(n)}</span>
    </span>
  );
};
