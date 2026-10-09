import React from 'react';
import {AbsoluteFill} from 'remotion';
import {Visual} from './types';
import {AnalyticsScene} from './visuals/AnalyticsScene';

/** #134 QA: tek analitik sehne (pipeline-dan kenar) - yeni/canli animasiya novlerinin renderStill yoxlamasi ucun. */
export type ProbeProps = {visual: Visual; reveal: number[]};

export const VisualProbe: React.FC<ProbeProps> = ({visual, reveal}) => (
  <AbsoluteFill style={{background: '#0B1222'}}>
    <AnalyticsScene visual={visual} reveal={reveal} kicker="Probe" />
  </AbsoluteFill>
);
