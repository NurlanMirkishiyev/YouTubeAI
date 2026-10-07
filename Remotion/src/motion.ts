import {Easing, interpolate, spring, SpringConfig} from 'remotion';

/** Faza 3.1 (istifadeci 2026-10-07): motion tokenleri - chart, kart ve overlay-de muddet/easing yalniz buradan.
 *  Xetti animasiya yoxdur (Ken Burns istisnadir: Background.tsx sabit suret). Muddetler kadrla (30 fps). */
export const FPS_REF = 30;
const ms = (v: number) => Math.round((v / 1000) * FPS_REF);

export const DUR = {
  inFast: ms(300), in: ms(450), inSlow: ms(600),          // giris 300-600 ms
  outFast: ms(200), out: ms(300), outSlow: ms(400),       // cixis 200-400 ms
  staggerTight: ms(60), stagger: ms(90), staggerLoose: ms(120),   // stagger 60-120 ms
  count: ms(600),                                         // reqem sayilmasi (giris pencereisi)
  draw: ms(600),                                          // xett/egri cekilmesi
  pulse: ms(400),                                         // vurgu <= 400 ms
  typeChar: 1,                                            // typewriter: kadr / simvol
  hold: ms(2500),                                         // overlay <= 2.5 s
  lead: ms(130),                                          // element sozden bir az evvel
};

export const SPRING: Record<'soft' | 'snappy' | 'bouncy', Partial<SpringConfig>> = {
  soft: {damping: 200},
  snappy: {damping: 20, stiffness: 200},
  bouncy: {damping: 9, stiffness: 160},
};

export const EASE = {
  out: Easing.bezier(0.16, 1, 0.3, 1),        // expo-out
  inOut: Easing.bezier(0.65, 0, 0.35, 1),
  in: Easing.bezier(0.55, 0, 1, 0.45),
  back: Easing.bezier(0.34, 1.56, 0.64, 1),
};

/** 0..1 easing ile (xetti deyil). */
export const ease = (frame: number, from: number, dur: number, curve: (t: number) => number = EASE.out) =>
  interpolate(frame, [from, from + Math.max(1, dur)], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: curve});

export const springIn = (frame: number, fps: number, delay: number, kind: keyof typeof SPRING = 'soft') =>
  spring({frame, fps, delay, config: SPRING[kind], durationInFrames: kind === 'soft' ? DUR.in : undefined});
