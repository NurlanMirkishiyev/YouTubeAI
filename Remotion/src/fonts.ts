import {loadFont} from '@remotion/fonts';
import {staticFile} from 'remotion';

export const FONT = 'Montserrat';

// loadFont ozu delayRender edir - sekil sriftsiz cekilmir
loadFont({family: FONT, url: staticFile('fonts/Montserrat-SemiBold.ttf'), weight: '600'});
loadFont({family: FONT, url: staticFile('fonts/Montserrat-ExtraBold.ttf'), weight: '800'});
