import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const W = 1920, H = 1080, ENTER = 12;
export const COLORS = {bg1: '#0b1324', bg2: '#16233f', text: '#ffffff', accent: '#ffc83d', soft: '#9fb3d9', bar: '#4f8cff'};
export const FONT = 'Montserrat';
loadFont({family: FONT, url: staticFile('fonts/Montserrat-ExtraBold.ttf'), weight: '800'});
loadFont({family: FONT, url: staticFile('fonts/Montserrat-SemiBold.ttf'), weight: '600'});
export const OWL_H = 560, OWL_H_BIG = 820, OWL_RIGHT = 40, OWL_BOTTOM = 0;
export const SAFE_RIGHT = 470;   // altyazi/animasiya bayqusun ustune dusmur
