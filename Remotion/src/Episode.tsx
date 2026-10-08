import {Audio} from '@remotion/media';
import {springTiming, TransitionPresentation, TransitionSeries} from '@remotion/transitions';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {fade} from '@remotion/transitions/fade';
import {flip} from '@remotion/transitions/flip';
import {iris} from '@remotion/transitions/iris';
import {pushCut} from '@remotion/transitions/push-cut';
import {slide} from '@remotion/transitions/slide';
import {wipe} from '@remotion/transitions/wipe';
import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {KenBurns} from './Background';
import {Captions} from './Captions';
import {IntroCard, LowerThird, OutroCard} from './Cards';
import {EmphasisLayer, FilmLook} from './Effects';
import './fonts';
import {SPRING} from './motion';
import {OwlLayer} from './Owl';
import {H, W} from './theme';
import {AnalyticsScene} from './visuals/AnalyticsScene';
import {TitleVariantCtx, VariantCtx} from './visuals/common';
import {NumberOverlay} from './visuals/NumberOverlay';
import {EpisodeProps, Side} from './types';

const LOWER_THIRD_S = 4;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Presentation = TransitionPresentation<any>;

/** Faza 3.3 (istifadeci 2026-10-07): motion.py-in kecid adlari -> @remotion/transitions 4.0.529-un QURASDIRILMIS
 *  DOM presentation-lari. Bolme kecidi: slide_right..clock_wipe; adi kecid: fade..slide_left. */
const TRANSITION_PRESETS: Record<string, () => Presentation> = {
  fade: () => fade(),
  wipe_left: () => wipe({direction: 'from-left'}),
  wipe_right: () => wipe({direction: 'from-right'}),
  wipe_top_left: () => wipe({direction: 'from-top-left'}),
  slide_left: () => slide({direction: 'from-left'}),
  slide_right: () => slide({direction: 'from-right'}),
  slide_bottom: () => slide({direction: 'from-bottom'}),
  push_cut: () => pushCut(),
  iris: () => iris({width: W, height: H}),
  flip: () => flip({direction: 'from-right'}),
  clock_wipe: () => clockWipe({width: W, height: H}),
};

/** Plansiz (kohne) props: bolme kecidi slide, adi kecid fade. Cixis kartina kecid evvelkini tekrar etmir. */
const pickTransition = (name: string | undefined, section: boolean, prev: string | undefined): string => {
  if (name && TRANSITION_PRESETS[name]) return name;
  const base = section ? 'slide_right' : 'fade';
  return base === prev ? (section ? 'push_cut' : 'wipe_left') : base;
};

/** Sehneler ardicil, narration ile eyni saatda: sehne k = intro + onceki sehnelerin cemi.
 *  Kecid ortusmesi ucun her klip (sonuncudan basqa) T kadr uzadilir - montage.py ile eyni qayda.
 *  Faza 3: hereket plani (props.motion + sehne transition/variant/titleVariant) Python motion.py-dan gelir. */
export const Episode: React.FC<EpisodeProps> = (p) => {
  const T = p.transitionFrames;
  const plan = p.motion;
  const placed = useMemo(() => {
    let t = p.introFrames;
    return p.scenes.map((s) => {
      const out = {...s, start: t};
      t += s.frames;
      return out;
    });
  }, [p.scenes, p.introFrames]);
  const scenesEnd = p.introFrames + p.scenes.reduce((a, s) => a + s.frames, 0);
  const sideAt = (f: number): {side: Side; prev: Side; since: number} => {
    let k = placed.findIndex((s) => f >= s.start && f < s.start + s.frames);
    if (k < 0) k = f < p.introFrames ? 0 : placed.length - 1;
    let j = k;
    while (j > 0 && placed[j - 1].side === placed[k].side) j--;
    return {side: placed[k].side, prev: j > 0 ? placed[j - 1].side : placed[k].side, since: placed[j].start};
  };
  const clips = [
    {key: 'intro', frames: p.introFrames,
      node: <IntroCard title={p.topic} hook={p.hook} brand={p.brand} bg={p.introBg} owl={p.poses[p.introOwl]}
        hookVariant={plan?.cold_open} backdrop={plan?.backdrop} />},
    ...p.scenes.map((s, i) => ({key: `sc${i}`, frames: s.frames,
      node: s.visual
        ? (
          <VariantCtx.Provider value={s.variant ?? null}>
            <TitleVariantCtx.Provider value={plan?.chart_title ?? 'slide_up'}>
              <AnalyticsScene visual={s.visual} reveal={s.reveal ?? []} kicker={s.kicker ?? null}
                kickerVariant={s.titleVariant} backdrop={plan?.backdrop} />
            </TitleVariantCtx.Provider>
          </VariantCtx.Provider>)
        : <KenBurns src={s.bg as string} motion={s.motion} flip={s.flip} />})),
    {key: 'outro', frames: p.outroFrames,
      node: <OutroCard brand={p.brand} bg={p.outroBg} owl={p.poses[p.outroOwl]} backdrop={plan?.backdrop} />},
  ];
  // kecid i: clips[i] -> clips[i + 1]; sehne kecidi plan-dan (sehnenin oz transition-u), cixis karti bolme kecidi
  const transitions = useMemo(() => {
    const out: string[] = [];
    for (let i = 0; i < clips.length - 1; i++) {
      const next = p.scenes[i];
      const section = i === 0 || i === clips.length - 2 || Boolean(next?.title);
      out.push(pickTransition(next?.transition, section, out[i - 1]));
    }
    return out;
  }, [p.scenes, clips.length]);
  return (
    <AbsoluteFill style={{backgroundColor: '#000'}}>
      <TransitionSeries>
        {clips.flatMap((c, i) => {
          const last = i === clips.length - 1;
          const seq = (
            <TransitionSeries.Sequence key={c.key} durationInFrames={c.frames + (last ? 0 : T)}>
              {c.node}
            </TransitionSeries.Sequence>);
          if (last) return [seq];
          return [seq, <TransitionSeries.Transition key={`t${i}`}
            timing={springTiming({config: SPRING.soft, durationInFrames: T})}
            presentation={TRANSITION_PRESETS[transitions[i]]()} />];
        })}
      </TransitionSeries>
      {plan?.theme === 'editorial' ? <FilmLook /> : null}
      <EmphasisLayer items={p.emphasis ?? []} />
      <OwlLayer scenes={placed} poses={p.poses} endFrame={scenesEnd} />
      {placed.filter((s) => s.title && s.lowerThird !== false).map((s) => (
        <Sequence key={s.start} from={s.start} durationInFrames={Math.min(s.frames, LOWER_THIRD_S * p.fps)}
          layout="none">
          <LowerThird text={s.title as string} variant={s.titleVariant} />
        </Sequence>))}
      {placed.filter((s) => s.overlay).map((s) => (
        <Sequence key={`ov${s.start}`} from={s.start} durationInFrames={s.frames} layout="none">
          <NumberOverlay o={s.overlay!} />
        </Sequence>))}
      <Captions words={p.words} from={p.introFrames} to={scenesEnd} sideAt={sideAt} />
      <Audio src={staticFile(p.audio)} />
    </AbsoluteFill>
  );
};
