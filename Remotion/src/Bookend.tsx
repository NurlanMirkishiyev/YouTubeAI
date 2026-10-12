import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, FONT, SAFE_RIGHT} from './theme';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const RED = '#ff0033';
const SHADOW = '0 6px 24px rgba(0,0,0,0.55)';

// Intro / outro fonu: movzu fotosu, bulanıq ve qaraldilmis, yavas zoom
const Backdrop: React.FC<{src: string}> = ({src}) => {
  const f = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const z = interpolate(f, [0, Math.max(1, durationInFrames)], [1.08, 1.16], clamp);
  return (
    <AbsoluteFill style={{overflow: 'hidden', background: COLORS.bg1}}>
      <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${z})`,
        filter: 'blur(6px) brightness(0.55) saturate(1.1)'}} />
      <AbsoluteFill style={{background: `linear-gradient(90deg, ${COLORS.bg1}ee 0%, ${COLORS.bg1}99 55%, transparent 100%)`}} />
    </AbsoluteFill>
  );
};

const useSpring = (delay: number) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  return spring({frame: f - delay, fps, config: {damping: 14, stiffness: 110}});
};

const Content: React.FC<{children: React.ReactNode}> = ({children}) => (
  <AbsoluteFill style={{justifyContent: 'center', paddingLeft: 110, paddingRight: SAFE_RIGHT + 250}}>{children}</AbsoluteFill>
);

const Channel: React.FC = () => {
  const t = useSpring(0);
  return (
    <div style={{alignSelf: 'flex-start', fontFamily: FONT, fontWeight: 800, fontSize: 34, letterSpacing: 4,
      color: COLORS.bg1, background: COLORS.accent, padding: '10px 22px', borderRadius: 10, marginBottom: 34,
      opacity: t, transform: `translateX(${(1 - t) * -60}px)`}}>ELI5 BUSINESS</div>
  );
};

export const IntroScene: React.FC<{src: string; title: string}> = ({src, title}) => {
  const f = useCurrentFrame();
  const words = title.split(/\s+/).filter(Boolean);
  const size = words.length > 8 ? 76 : 92;
  const lineStart = 8 + words.length * 4;
  const line = interpolate(f, [lineStart, lineStart + 18], [0, 460], clamp);
  return (
    <AbsoluteFill>
      <Backdrop src={src} />
      <Content>
        <Channel />
        <div style={{display: 'flex', flexWrap: 'wrap', columnGap: 22, fontFamily: FONT, fontWeight: 800, fontSize: size,
          lineHeight: 1.06, color: COLORS.text, textShadow: SHADOW}}>
          {words.map((w, k) => <Word key={k} text={w} delay={6 + k * 4} />)}
        </div>
        <div style={{height: 12, width: line, background: COLORS.accent, borderRadius: 6, marginTop: 30}} />
      </Content>
    </AbsoluteFill>
  );
};

const Word: React.FC<{text: string; delay: number}> = ({text, delay}) => {
  const t = useSpring(delay);
  return <span style={{display: 'inline-block', opacity: t, transform: `translateY(${(1 - t) * 50}px)`}}>{text}</span>;
};

const Bell: React.FC<{swing: number}> = ({swing}) => (
  <svg width="86" height="86" viewBox="0 0 24 24" style={{transform: `rotate(${swing}deg)`, transformOrigin: '50% 10%'}}>
    <path fill="#fff" d="M12 22a2.5 2.5 0 0 0 2.45-2h-4.9A2.5 2.5 0 0 0 12 22zm7-6V11a7 7 0 0 0-5.5-6.84V3.5a1.5 1.5 0 0 0-3 0v.66A7 7 0 0 0 5 11v5l-2 2v1h18v-1l-2-2z" />
  </svg>
);

export const OutroScene: React.FC<{src: string}> = ({src}) => {
  const f = useCurrentFrame();
  const thanks = useSpring(0);
  const pop = useSpring(10);
  const CLICK = 42;
  const press = interpolate(f, [CLICK - 6, CLICK, CLICK + 6], [1, 0.9, 1], clamp);
  const done = f >= CLICK;
  const swing = done ? Math.sin((f - CLICK) / 3) * 18 * Math.max(0, 1 - (f - CLICK) / 60) : 0;
  return (
    <AbsoluteFill>
      <Backdrop src={src} />
      <Content>
        <Channel />
        <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 88, color: COLORS.text, textShadow: SHADOW,
          opacity: thanks, transform: `translateY(${(1 - thanks) * 40}px)`, marginBottom: 46}}>Thanks for watching!</div>
        <div style={{display: 'flex', alignItems: 'center', gap: 30, transform: `scale(${pop * press})`,
          transformOrigin: 'left center'}}>
          <div style={{fontFamily: FONT, fontWeight: 800, fontSize: 64, letterSpacing: 2, color: '#fff',
            background: done ? '#4a4a4a' : RED, padding: '22px 56px', borderRadius: 60, boxShadow: SHADOW}}>
            {done ? 'SUBSCRIBED ✓' : 'SUBSCRIBE'}
          </div>
          <Bell swing={swing} />
        </div>
      </Content>
    </AbsoluteFill>
  );
};
