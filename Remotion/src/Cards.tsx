import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {KenBurns} from './Background';
import {FONT} from './fonts';
import {ACCENT, H} from './theme';
import {OwlPose} from './types';
import {StudioBackdrop} from './visuals/Studio';

const FADE_IN = 8;
const MAX_OWL_W = 470;     // basliq (sol 170 + maxWidth 1080) ~1300 px-e qeder gedir; 1920-150-470 = 1300

/** Istifadeci 2026-09-30: kart bayqusu da sabit dayanir - sinus "bob" ve yayli giris silindi,
 *  yalniz yerinde yumsaq gorunur. Sekil movzuya uygun giris/cixis bayqusudur (owl/intro, owl/outro),
 *  yoxdursa kohne sprite (front/three_q) guzgulenmis gosterilir. */
const CardOwl: React.FC<{pose?: OwlPose; height: number}> = ({pose, height}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, FADE_IN], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  if (!pose) return null;
  const aspect = pose.w / pose.h;
  const w = Math.min(height * H * aspect, MAX_OWL_W);
  return (
    <div style={{position: 'absolute', right: 150, bottom: 50, width: w, height: w / aspect, opacity}}>
      <Img src={staticFile(`owl/${pose.name}.png`)}
        style={{width: '100%', height: '100%', transform: `scaleX(${pose.flippable ? -1 : 1})`}} />
    </div>
  );
};

const Words: React.FC<{text: string; size: number; delay: number; stagger: number}> = (
  {text, size, delay, stagger}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <div style={{fontFamily: FONT, fontWeight: 800, fontSize: size, color: '#fff', lineHeight: 1.12,
      maxWidth: 1080, textShadow: '0 6px 24px rgba(0,0,0,0.45)'}}>
      {text.split(' ').map((w, i) => {
        const sp = spring({frame, fps, delay: delay + i * stagger, config: {damping: 200}});
        return <span key={i} style={{display: 'inline-block', marginRight: size * 0.28, opacity: sp,
          transform: `translateY(${interpolate(sp, [0, 1], [40, 0])}px)`}}>{w}</span>;
      })}
    </div>
  );
};

const Bar: React.FC<{delay: number}> = ({delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sp = spring({frame, fps, delay, config: {damping: 200}});
  return <div style={{width: 14, height: 190 * sp, background: ACCENT, borderRadius: 7, marginRight: 36}} />;
};

export const IntroCard: React.FC<{title: string; brand: string; bg: string | null; owl?: OwlPose;
  hook?: string | null}> = ({title, brand, bg, owl, hook}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const brandIn = spring({frame, fps, delay: 18, config: {damping: 200}});
  const hookIn = spring({frame, fps, delay: 10, config: {damping: 200}});
  return (
    <AbsoluteFill>
      {bg ? <KenBurns src={bg} motion="zoom_in" blur={12} dim={0.45} /> : <StudioBackdrop />}
      <AbsoluteFill style={{flexDirection: 'row', alignItems: 'center', paddingLeft: 170}}>
        <Bar delay={2} />
        <div>
          <Words text={title} size={96} delay={4} stagger={3} />
          {hook ? (
            /* #56: ilk saniyelerde seslenen hook (konkret reqem/paradoks) ekranda da */
            <div style={{fontFamily: FONT, fontWeight: 700, fontSize: 46, color: '#fff', marginTop: 26,
              maxWidth: 1080, lineHeight: 1.2, opacity: hookIn, borderLeft: `6px solid ${ACCENT}`, paddingLeft: 22,
              transform: `translateY(${interpolate(hookIn, [0, 1], [24, 0])}px)`}}>{hook}</div>
          ) : null}
          <div style={{fontFamily: FONT, fontWeight: 600, fontSize: 42, color: ACCENT, marginTop: 18,
            opacity: brandIn}}>{brand}</div>
        </div>
      </AbsoluteFill>
      <CardOwl pose={owl} height={0.58} />
    </AbsoluteFill>
  );
};

export const OutroCard: React.FC<{brand: string; bg: string | null; owl?: OwlPose}> = ({brand, bg, owl}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const btn = spring({frame, fps, delay: 22, config: {damping: 11}});
  const pulse = 1 + 0.035 * Math.sin((2 * Math.PI * frame) / fps / 1.1);
  return (
    <AbsoluteFill>
      {bg ? <KenBurns src={bg} motion="zoom_out" blur={12} dim={0.5} /> : <StudioBackdrop />}
      <AbsoluteFill style={{flexDirection: 'row', alignItems: 'center', paddingLeft: 170}}>
        <Bar delay={2} />
        <div>
          <Words text="Thanks for watching!" size={88} delay={4} stagger={4} />
          <div style={{display: 'inline-block', marginTop: 34, padding: '18px 44px', borderRadius: 16,
            background: '#E62117', color: '#fff', fontFamily: FONT, fontWeight: 800, fontSize: 44,
            transform: `scale(${btn * pulse})`, transformOrigin: '0% 50%'}}>
            Subscribe for more {brand}
          </div>
        </div>
      </AbsoluteFill>
      <CardOwl pose={owl} height={0.56} />
    </AbsoluteFill>
  );
};

export const LowerThird: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const inn = spring({frame, fps, delay: 6, config: {damping: 18, stiffness: 140}});
  const out = spring({frame, fps, delay: durationInFrames - 14, config: {damping: 200}});
  const x = interpolate(inn - out, [0, 1], [-900, 0]);
  return (
    <div style={{position: 'absolute', top: 60, left: 70, transform: `translateX(${x}px)`,
      display: 'flex', alignItems: 'stretch', borderRadius: 16, overflow: 'hidden',
      boxShadow: '0 10px 30px rgba(0,0,0,0.35)'}}>
      <div style={{width: 12, background: ACCENT}} />
      <div style={{background: 'rgba(15,18,28,0.85)', padding: '16px 34px', color: '#fff',
        fontFamily: FONT, fontWeight: 800, fontSize: 46}}>{text}</div>
    </div>
  );
};
