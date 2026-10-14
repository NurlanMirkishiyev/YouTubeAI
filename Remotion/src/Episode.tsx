import React from 'react';
import {AbsoluteFill, Sequence, interpolate, useCurrentFrame} from 'remotion';
import {AnimScene} from './AnimScene';
import {ThemeCtx} from './anim/kit';
import {IntroScene, OutroScene} from './Bookend';
import {Captions} from './Captions';
import {OwlLayer} from './OwlLayer';
import {PhotoScene} from './PhotoScene';
import {SectionTitle} from './SectionTitle';
import {COLORS, ENTER, W, palette} from './theme';
import {Props, Scene} from './types';

const Enter: React.FC<{i: number; children: React.ReactNode}> = ({i, children}) => {
  const f = useCurrentFrame();
  const t = interpolate(f, [0, ENTER], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const mode = i === 0 ? 'none' : ['fade', 'slide', 'wipe'][i % 3];
  const style: React.CSSProperties = mode === 'fade' ? {opacity: t}
    : mode === 'slide' ? {transform: `translateX(${(1 - t) * W}px)`}
    : mode === 'wipe' ? {clipPath: `inset(0 ${(1 - t) * 100}% 0 0)`} : {};
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
};

const SceneView: React.FC<{s: Scene; title: string}> = ({s, title}) => {
  if (s.type === 'intro' && s.img) return <IntroScene src={s.img} title={title} />;
  if (s.type === 'outro' && s.img) return <OutroScene src={s.img} />;
  if (s.type === 'photo' && s.img) return <PhotoScene src={s.img} n={s.n} />;
  if (s.anim) return <AnimScene anim={s.anim} n={s.n} />;
  return <AbsoluteFill style={{background: `radial-gradient(circle at 30% 40%, ${COLORS.bg2}, ${COLORS.bg1})`}} />;
};

// theme: videonun mövzusuna uyğun palitra (plan.with_theme) - animasiya fonu, kartlar, parıltı.
export const Episode: React.FC<Props> = ({title, theme, scenes, captions}) => (
  <ThemeCtx.Provider value={palette(theme)}>
    <AbsoluteFill style={{background: '#000'}}>
      {scenes.map((s, i) => (
        <Sequence key={s.n} from={s.from} durationInFrames={s.frames + (i < scenes.length - 1 ? ENTER : 0)}>
          <Enter i={i}><SceneView s={s} title={title} /></Enter>
        </Sequence>
      ))}
      {scenes.filter((s) => s.sectionStart && s.section).map((s) => (
        <Sequence key={`t${s.n}`} from={s.from} durationInFrames={Math.min(95, s.frames)}>
          <SectionTitle text={s.section} />
        </Sequence>
      ))}
      <OwlLayer scenes={scenes} />
      <Captions captions={captions} />
    </AbsoluteFill>
  </ThemeCtx.Provider>
);
