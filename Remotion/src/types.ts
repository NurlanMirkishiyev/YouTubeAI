export type Anim = {kind: 'counter'|'bars'|'percent'|'flow'|'list'|'versus'|'timeline'|'quote'; variant: number; [k: string]: any};
export type Scene = {n: number; type: 'photo'|'anim'|'intro'|'outro'; img: string | null; owl: string; anim: Anim | null;
                     section: string; sectionStart: boolean; from: number; frames: number};
export type Word = {from: number; to: number; text: string};
export type Caption = {from: number; to: number; text: string; words: Word[]};
export type Props = {fps: number; total: number; title: string; scenes: Scene[]; captions: Caption[]};
