import {CalculateMetadataFunction, Composition} from 'remotion';
import {Episode} from './Episode';
import {EpisodeProps} from './types';
import {ProbeProps, VisualProbe} from './VisualProbe';

const calculateMetadata: CalculateMetadataFunction<EpisodeProps> = ({props}) => ({
  durationInFrames: props.introFrames + props.scenes.reduce((a, s) => a + s.frames, 0) + props.outroFrames,
  fps: props.fps,
});

const empty: EpisodeProps = {
  fps: 30, topic: 'Preview', brand: 'ELI5 Business', audio: '', introFrames: 90, outroFrames: 90, introOwl: 'front', outroOwl: 'three_q',
  introBg: null, outroBg: null, transitionFrames: 15, scenes: [], words: [], poses: {},
};

const probe: ProbeProps = {visual: {kind: 'counter', title: 'Probe', value: 42, unit: '', label: 'Probe'}, reveal: [10]};

export const RemotionRoot = () => (
  <>
    <Composition id="Episode" component={Episode} width={1920} height={1080} fps={30}
      durationInFrames={180} defaultProps={empty} calculateMetadata={calculateMetadata} />
    <Composition id="VisualProbe" component={VisualProbe} width={1920} height={1080} fps={30}
      durationInFrames={240} defaultProps={probe} />
  </>
);
