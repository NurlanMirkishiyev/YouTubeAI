import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {FONT} from './fonts';
import {ACCENT} from './theme';
import {Side, Word} from './types';

const MAX_CHARS = 44;
const MAX_GAP = 0.7;
const HOLD = 0.35;          // son sozden sonra setir bir az qalir
const SHIFT = 170;          // setir bayqusun eks terefine surusur
const SLIDE = 10;           // teref deyisende setrin surusme muddeti (kadr)

type Page = {words: Word[]; start: number; end: number};

export const toPages = (words: Word[]): Page[] => {
  const pages: Page[] = [];
  let cur: Word[] = [];
  const flush = () => {
    if (cur.length) pages.push({words: cur, start: cur[0].s, end: cur[cur.length - 1].e});
    cur = [];
  };
  for (const w of words) {
    const text = [...cur, w].map((x) => x.w.trim()).join(' ');
    const gap = cur.length ? w.s - cur[cur.length - 1].e : 0;
    if (cur.length && (text.length > MAX_CHARS || gap > MAX_GAP)) flush();
    cur.push(w);
    if (/[.!?]$/.test(w.w.trim())) flush();
  }
  flush();
  return pages.map((p, i) => ({...p, end: Math.min(p.end + HOLD, pages[i + 1]?.start ?? Infinity)}));
};

const offsetFor = (side: Side) => (side === 'left' ? SHIFT : -SHIFT);

export const Captions: React.FC<{words: Word[]; from: number; to: number;
  sideAt: (f: number) => {side: Side; prev: Side; since: number}}> = ({words, from, to, sideAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pages = useMemo(() => toPages(words), [words]);
  if (frame < from || frame >= to) return null;
  const t = frame / fps;
  const page = pages.find((p) => t >= p.start && t < p.end);
  if (!page) return null;
  const pop = interpolate(t, [page.start, page.start + 0.12], [0.96, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const {side, prev, since} = sideAt(frame);
  const x = interpolate(frame - since, [0, SLIDE], [offsetFor(prev), offsetFor(side)],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 64}}>
      <div style={{transform: `translateX(${x}px) scale(${pop})`, maxWidth: 1080, textAlign: 'center',
        background: 'rgba(12,14,22,0.72)', borderRadius: 18, padding: '14px 30px',
        fontFamily: FONT, fontWeight: 600, fontSize: 46, lineHeight: 1.25, color: '#fff'}}>
        {page.words.map((w, i) => {
          const active = t >= w.s && t < (page.words[i + 1]?.s ?? page.end);
          // Faza 3.9: reqem sozleri (Python `num`) aktiv olmasa da accent renginde qalir
          return <span key={i} style={{color: active || w.num ? ACCENT : '#fff'}}>{(i ? ' ' : '') + w.w.trim()}</span>;
        })}
      </div>
    </AbsoluteFill>
  );
};
