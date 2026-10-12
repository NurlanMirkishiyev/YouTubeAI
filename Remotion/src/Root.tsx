import React from 'react';
import {Composition} from 'remotion';
import {Episode} from './Episode';
import {Props} from './types';
import {H, W} from './theme';

const empty: Props = {fps: 30, total: 60, title: '', scenes: [], captions: []};
export const Root: React.FC = () => (
  <Composition id="Episode" component={Episode} width={W} height={H} fps={30} durationInFrames={60}
    defaultProps={empty}
    calculateMetadata={({props}) => ({durationInFrames: Math.max(1, props.total), fps: props.fps})} />
);
