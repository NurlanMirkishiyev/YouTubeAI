export type Side = 'left' | 'right';
// Faza 3.4: Ken Burns hereket novleri (motion.py KEN_BURNS ile eyni)
export type Motion = 'zoom_in' | 'zoom_out' | 'pan_lr' | 'pan_rl' | 'diag_tl_br' | 'diag_br_tl' | 'push_in'
  | 'tilt_up' | 'tilt_down';

export type Scene = {
  frames: number;          // gorunme muddeti (kecid ortusmesi daxil deyil)
  bg: string | null;       // public-dir-e nisbi yol; analitik sehnede null
  visual?: Visual | null;
  reveal?: number[];       // visual elementlerinin acilma kadrlari
  pose: string;            // owl/<pose>.png
  side: Side;
  flip?: boolean;          // fonu guzgule: bos yer solda qurulub, bayqus ise hemise sagdadir
  motion: Motion;
  title: string | null;    // bolmenin ilk sehnesi (bolme kecidi)
  lowerThird?: boolean;    // #55: lower-third yalniz foto sehnesinde
  kicker?: string | null;  // #55: chart sehnesinde bolme adi chart basliginin ustunde
  skeleton?: boolean;      // Faza 2.5: chart 0-ci kadrdan skelet (kontur, '—')
  overlay?: Overlay | null; // Faza 2.7
  // Faza 3 (motion.py plani): sehneye giris kecidi, chart giris varianti, bolme basligi varianti
  transition?: string;
  variant?: string | null;
  titleVariant?: string | null;
};

export type Word = {w: string; s: number; e: number; num?: boolean};  // saniye, qlobal; num: reqem sozu (3.9)

export type EpisodeProps = {
  fps: number;
  topic: string;
  hook?: string | null;    // #56: giris kartinda seslenen hook cumlesi (reqem/paradoks)
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
  motion?: MotionPlan;                  // Faza 3: epizodun hereket plani (yoxdursa kohne default)
  emphasis?: Emphasis[];                // Faza 3.7: nitqle sinxron vurgu
};

export type MotionPlan = {theme: 'clean' | 'dynamic' | 'editorial'; backdrop: string; cold_open: string;
  chart_title: string};
export type Emphasis = {at: number; frames: number; big: boolean};   // at: qlobal kadr

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
  | {kind: 'keypoints'; title: string; points: string[]}
  | {kind: 'stats'; title: string; cards: {value: number; unit: Unit; label: string}[]}   // #57 data kartlari
  // Faza 2 (2026-10-07): qerar vizuallari (model_result-dan), zaman seriyasi, ABS xeritesi
  | {kind: 'table'; title: string; columns: string[];
      rows: {label: string; before: number; after: number; delta: number | null; unit: Unit}[]}
  | {kind: 'threshold'; title: string; threshold: {value: number; unit: Unit; label: string};
      current: {value: number; label: string} | null;
      curve: {var: string; result: string; cross: number; points: [number, number][]; x_label: string;
        y_label: string; baseline: {value: number; label: string; unit: Unit} | null} | null}
  | {kind: 'timeseries'; title: string; unit: Unit; illustrative: boolean;
      points: {label: string; value: number; shown: boolean}[]; events: {index: number; label: string}[];
      segments: {from: number; to: number; down: boolean}[]}
  | {kind: 'usmap'; title: string; unit_label: string; keys: {value: number; label: string}[];
      outline: [number, number][]; dots: [number, number][]; per_dot: number; counter: [number, number, number, number]};

// Faza 2.7: foto sehnesinde danisilan reqemin count-up overlay-i
export type Overlay = {value: number; unit: Unit; from: number; frames: number; box: [number, number, number, number]};
