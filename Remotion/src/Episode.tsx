import {Audio} from '@remotion/media';
import {linearTiming, TransitionSeries} from '@remotion/transitions';
import {fade} from '@remotion/transitions/fade';
import {slide} from '@remotion/transitions/slide';
import React, {useMemo} from 'react';
import {AbsoluteFill, Sequence, staticFile} from 'remotion';
import {KenBurns} from './Background';
import {Captions} from './Captions';
import {IntroCard, LowerThird, OutroCard} from './Cards';
import './fonts';
import {OwlLayer} from './Owl';
import {AnalyticsScene} from './visuals/AnalyticsScene';
import {EpisodeProps, Side} from './types';

const LOWER_THIRD_S = 4;

/** Sehneler ardicil, narration ile eyni saatda: sehne k = intro + onceki sehnelerin cemi.
 *  Kecid ortusmesi ucun her klip (sonuncudan basqa) T kadr uzadilir - montage.py ile eyni qayda. */
export const Episode: React.FC<EpisodeProps> = (p) => {
  const T = p.transitionFrames;
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
    {key: 'intro', frames: p.introFrames, section: '__intro__',
      node: <IntroCard title={p.topic} brand={p.brand} bg={p.introBg} owl={p.poses[p.introOwl]} />},
    ...p.scenes.map((s, i) => ({key: `sc${i}`, frames: s.frames, section: s.side + (s.title ?? i),
      node: s.visual ? <AnalyticsScene visual={s.visual} reveal={s.reveal ?? []} />
        : <KenBurns src={s.bg as string} motion={s.motion} flip={s.flip} />})),
    {key: 'outro', frames: p.outroFrames, section: '__outro__',
      node: <OutroCard brand={p.brand} bg={p.outroBg} owl={p.poses[p.outroOwl]} />},
  ];
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
          const next = p.scenes[i];       // clips[i + 1] sehnesi (intro-dan sonra indeks surusur)
          const sectionChange = i === 0 || i === clips.length - 2 || Boolean(next?.title);
          return [seq, <TransitionSeries.Transition key={`t${i}`} timing={linearTiming({durationInFrames: T})}
            presentation={sectionChange ? slide({direction: 'from-right'}) : fade()} />];
        })}
      </TransitionSeries>
      <OwlLayer scenes={placed} poses={p.poses} endFrame={scenesEnd} />
      {placed.filter((s) => s.title).map((s) => (
        <Sequence key={s.start} from={s.start} durationInFrames={Math.min(s.frames, LOWER_THIRD_S * p.fps)}
          layout="none">
          <LowerThird text={s.title as string} />
        </Sequence>))}
      <Captions words={p.words} from={p.introFrames} to={scenesEnd} sideAt={sideAt} />
      <Audio src={staticFile(p.audio)} />
    </AbsoluteFill>
  );
};
