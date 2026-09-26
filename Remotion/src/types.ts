export type Side = 'left' | 'right';
export type Motion = 'zoom_in' | 'zoom_out' | 'pan_lr' | 'pan_rl';

export type Scene = {
  frames: number;          // gorunme muddeti (kecid ortusmesi daxil deyil)
  bg: string;              // public-dir-e nisbi yol
  pose: string;            // owl/<pose>.png
  side: Side;
  flip?: boolean;          // fonu guzgule: bos yer solda qurulub, bayqus ise hemise sagdadir
  motion: Motion;
  title: string | null;    // bolmenin ilk sehnesi -> lower-third
};

export type Word = {w: string; s: number; e: number};  // saniye, qlobal zaman xetti

export type EpisodeProps = {
  fps: number;
  topic: string;
  brand: string;
  audio: string;
  introFrames: number;
  outroFrames: number;
  introBg: string;
  outroBg: string;
  transitionFrames: number;
  scenes: Scene[];
  words: Word[];
  poses: Record<string, OwlPose>;       // poz -> olculer + ekran hundurluyu payi
};

export type OwlPose = {name: string; w: number; h: number; height: number; flippable: boolean};
