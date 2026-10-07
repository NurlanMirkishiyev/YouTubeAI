import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {KenBurns} from './Background';
import {FONT} from './fonts';
import {DUR, EASE, ease, springIn} from './motion';
import {TypeText} from './Text';
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
        const sp = springIn(frame, fps, delay + i * stagger);
        return <span key={i} style={{display: 'inline-block', marginRight: size * 0.28, opacity: sp,
          transform: `translateY(${interpolate(sp, [0, 1], [40, 0])}px)`}}>{w}</span>;
      })}
    </div>
  );
};

const Bar: React.FC<{delay: number}> = ({delay}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const sp = springIn(frame, fps, delay);
  return <div style={{width: 14, height: 190 * sp, background: ACCENT, borderRadius: 7, marginRight: 36}} />;
};

/** Faza 3.2: cold open (hook) variantlari - typewriter (default, Faza 5 qapisi teleb edir), word_rise, mask_reveal.
 *  Typewriter kartin ustunde, seslendirme ile eyni vaxtda yazilir - kart muddeti deyismir. */
const Hook: React.FC<{text: string; variant: string}> = ({text, variant}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const p = springIn(frame, fps, DUR.staggerLoose);
  const style: React.CSSProperties = {fontFamily: FONT, fontWeight: 700, fontSize: 46, color: '#fff', marginTop: 26,
    maxWidth: 1080, lineHeight: 1.2, borderLeft: `6px solid ${ACCENT}`, paddingLeft: 22};
  if (variant === 'typewriter') {
    return <div style={style}><TypeText text={text} start={DUR.stagger} /></div>;
  }
  if (variant === 'mask_reveal') {
    return <div style={{...style, clipPath: `inset(0 ${(1 - p) * 100}% 0 0)`}}>{text}</div>;
  }
  return <div style={{...style, opacity: p, transform: `translateY(${interpolate(p, [0, 1], [24, 0])}px)`}}>{text}</div>;
};

export const IntroCard: React.FC<{title: string; brand: string; bg: string | null; owl?: OwlPose;
  hook?: string | null; hookVariant?: string; backdrop?: string}> = (
  {title, brand, bg, owl, hook, hookVariant = 'typewriter', backdrop}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const brandIn = springIn(frame, fps, DUR.inSlow);
  return (
    <AbsoluteFill>
      {bg ? <KenBurns src={bg} motion="zoom_in" blur={12} dim={0.45} /> : <StudioBackdrop variant={backdrop} />}
      <AbsoluteFill style={{flexDirection: 'row', alignItems: 'center', paddingLeft: 170}}>
        <Bar delay={DUR.staggerTight} />
        <div>
          <Words text={title} size={96} delay={DUR.staggerTight * 2} stagger={DUR.staggerTight * 1.5} />
          {hook ? <Hook text={hook} variant={hookVariant} /> : null /* #56: seslenen hook ekranda da */}
          <div style={{fontFamily: FONT, fontWeight: 600, fontSize: 42, color: ACCENT, marginTop: 18,
            opacity: brandIn}}>{brand}</div>
        </div>
      </AbsoluteFill>
      <CardOwl pose={owl} height={0.58} />
    </AbsoluteFill>
  );
};

export const OutroCard: React.FC<{brand: string; bg: string | null; owl?: OwlPose; backdrop?: string}> = (
  {brand, bg, owl, backdrop}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const btn = springIn(frame, fps, DUR.inSlow + DUR.stagger, 'bouncy');
  const pulse = 1 + 0.035 * Math.sin((2 * Math.PI * frame) / fps / 1.1);
  return (
    <AbsoluteFill>
      {bg ? <KenBurns src={bg} motion="zoom_out" blur={12} dim={0.5} /> : <StudioBackdrop variant={backdrop} />}
      <AbsoluteFill style={{flexDirection: 'row', alignItems: 'center', paddingLeft: 170}}>
        <Bar delay={DUR.staggerTight} />
        <div>
          <Words text="Thanks for watching!" size={88} delay={DUR.staggerTight * 2} stagger={DUR.staggerTight * 2} />
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

/** Bolme basligi (foto sehnesi). Faza 3.2 variantlari: slide_in, wipe, typewriter. */
export const LowerThird: React.FC<{text: string; variant?: string | null}> = ({text, variant}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const inn = springIn(frame, fps, DUR.staggerTight, 'snappy');
  const out = ease(frame, durationInFrames - DUR.outSlow, DUR.out, EASE.in);
  const v = variant ?? 'slide_in';
  const shown = inn * (1 - out);
  const motion: React.CSSProperties = v === 'wipe' ? {clipPath: `inset(0 ${(1 - shown) * 100}% 0 0)`}
    : v === 'typewriter' ? {opacity: 1 - out}
      : {transform: `translateX(${interpolate(shown, [0, 1], [-900, 0])}px)`};
  return (
    <div style={{position: 'absolute', top: 60, left: 70, display: 'flex', alignItems: 'stretch', borderRadius: 16,
      overflow: 'hidden', boxShadow: '0 10px 30px rgba(0,0,0,0.35)', ...motion}}>
      <div style={{width: 12, background: ACCENT}} />
      <div style={{background: 'rgba(15,18,28,0.85)', padding: '16px 34px', color: '#fff',
        fontFamily: FONT, fontWeight: 800, fontSize: 46}}>
        {v === 'typewriter' ? <TypeText text={text} start={DUR.staggerTight} /> : text}
      </div>
    </div>
  );
};
