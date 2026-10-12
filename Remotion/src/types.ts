export type Anim = {kind: 'counter'|'bars'|'percent'|'flow'|'list'|'versus'|'timeline'|'quote'; variant: number; [k: string]: any};
export type Scene = {n: number; type: 'photo'|'anim'; img: string | null; owl: string; anim: Anim | null;
                     section: string; sectionStart: boolean; from: number; frames: number};
export type Caption = {from: number; to: number; text: string};
export type Props = {fps: number; total: number; scenes: Scene[]; captions: Caption[]};
