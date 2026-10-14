import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const W = 1920, H = 1080, ENTER = 12;
export const COLORS = {bg1: '#0b1324', bg2: '#16233f', text: '#ffffff', accent: '#ffc83d', soft: '#9fb3d9', bar: '#4f8cff'};
export const FONT = 'Montserrat';
loadFont({family: FONT, url: staticFile('fonts/Montserrat-ExtraBold.ttf'), weight: '800'});
loadFont({family: FONT, url: staticFile('fonts/Montserrat-SemiBold.ttf'), weight: '600'});
export const OWL_H = 560, OWL_H_BIG = 820, OWL_RIGHT = 40, OWL_BOTTOM = 0;
export const SAFE_RIGHT = 470;   // altyazi/animasiya bayqusun ustune dusmur

// Videonun reng temasi (Projects/plan.py THEMES ile eyni adlar) - animasiya fonu, kartlar, parilti.
export type Palette = {bg1: string; bg2: string; a1: string; a2: string; glow: string; tint: string};
export const PALETTES: Record<string, Palette> = {
  royal: {bg1: '#070b1d', bg2: '#1b2463', a1: '#ffc83d', a2: '#7aa2ff', glow: 'rgba(122,162,255,0.35)', tint: '#2c3a8f'},
  gold: {bg1: '#0b0804', bg2: '#33230a', a1: '#f5c451', a2: '#fff0c2', glow: 'rgba(245,196,81,0.35)', tint: '#6b4a12'},
  emerald: {bg1: '#03120d', bg2: '#0b3d2d', a1: '#34e89e', a2: '#c4ffe6', glow: 'rgba(52,232,158,0.32)', tint: '#0f5c43'},
  electric: {bg1: '#040a1c', bg2: '#0e2a63', a1: '#3fb6ff', a2: '#b18cff', glow: 'rgba(63,182,255,0.38)', tint: '#1d3f8c'},
  sunset: {bg1: '#16060f', bg2: '#4a1430', a1: '#ff8a5c', a2: '#ffd36e', glow: 'rgba(255,138,92,0.35)', tint: '#7a2443'},
  crimson: {bg1: '#120509', bg2: '#410c1a', a1: '#ff4d6d', a2: '#ffc2cd', glow: 'rgba(255,77,109,0.35)', tint: '#6e1428'},
};
export const palette = (name?: string): Palette => PALETTES[name ?? ''] ?? PALETTES.royal;
