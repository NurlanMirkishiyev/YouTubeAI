export type Side = 'left' | 'right';
export type Motion = 'zoom_in' | 'zoom_out' | 'pan_lr' | 'pan_rl';

export type Scene = {
  frames: number;          // gorunme muddeti (kecid ortusmesi daxil deyil)
  bg: string | null;       // public-dir-e nisbi yol; analitik sehnede null
  visual?: Visual | null;
  reveal?: number[];       // visual elementlerinin acilma kadrlari
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
  introOwl: string;        // poses acari: movzu bayqusu 'intro' ve ya sprite 'front'
  outroOwl: string;        // 'outro' ve ya 'three_q'
  introBg: string | null;   // #46: null -> dizayn fonu (sehne fotosu tekrar olunmur)
  outroBg: string | null;
  transitionFrames: number;
  scenes: Scene[];
  words: Word[];
  poses: Record<string, OwlPose>;       // poz -> olculer + ekran hundurluyu payi
};

export type OwlPose = {name: string; w: number; h: number; height: number; flippable: boolean};

// #45: analitik animasiya spec-i (Projects/visuals.py yoxlayir); reveal = elementlerin acilma kadri (sehne basindan)
export type Unit = '$' | '%' | '';
export type Item = {label: string; value: number | null; unit?: Unit};   // unit: danisiqdan ($4, 40%)
export type Visual =
  | {kind: 'bars'; title: string; unit: Unit; items: Item[]}
  | {kind: 'line'; title: string; unit: Unit; points: Item[]}
  | {kind: 'compare'; title: string; unit: Unit; left: Item & {note: string}; right: Item & {note: string}}
  | {kind: 'ring'; title: string; value: number; label: string}
  | {kind: 'equation'; title: string; unit: Unit; op: '+' | '-' | '×' | '÷'; terms: Item[]; result: Item}
  | {kind: 'flow'; title: string; steps: string[]}
  | {kind: 'timeline'; title: string; events: {label: string; when: string}[]}
  | {kind: 'counter'; title: string; value: number; unit: Unit; label: string}
  | {kind: 'keypoints'; title: string; points: string[]};
