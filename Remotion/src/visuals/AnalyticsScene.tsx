import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Visual} from '../types';
import {Bars, Counter, Line, Ring} from './Charts';
import {AREA, Title} from './common';
import {Compare, Equation, Flow, Keypoints, Timeline} from './Diagrams';
import {StudioBackdrop} from './Studio';

const Chart: React.FC<{v: Visual; reveal: number[]}> = ({v, reveal}) => {
  switch (v.kind) {
    case 'bars': return <Bars items={v.items} unit={v.unit} reveal={reveal} />;
    case 'line': return <Line points={v.points} unit={v.unit} reveal={reveal} />;
    case 'ring': return <Ring value={v.value} label={v.label} reveal={reveal} />;
    case 'counter': return <Counter value={v.value} unit={v.unit} label={v.label} reveal={reveal} />;
    case 'compare': return <Compare left={v.left} right={v.right} unit={v.unit} reveal={reveal} />;
    case 'equation': return <Equation terms={v.terms} result={v.result} op={v.op} unit={v.unit} reveal={reveal} />;
    case 'flow': return <Flow steps={v.steps} reveal={reveal} />;
    case 'timeline': return <Timeline events={v.events} reveal={reveal} />;
    case 'keypoints': return <Keypoints points={v.points} reveal={reveal} />;
  }
};

/** #45: foto evezine analitik sehne - dizayn fonu + chart sol sahede (bayqus sagda, altyazi asagida). */
export const AnalyticsScene: React.FC<{visual: Visual; reveal: number[]}> = ({visual, reveal}) => (
  <AbsoluteFill>
    <StudioBackdrop />
    <div style={{position: 'absolute', left: AREA.left, top: AREA.top, width: AREA.width, height: AREA.height}}>
      <Title text={visual.title} />
      <Chart v={visual} reveal={reveal} />
    </div>
  </AbsoluteFill>
);
