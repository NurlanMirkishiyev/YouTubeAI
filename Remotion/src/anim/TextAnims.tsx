import React from 'react';
import {interpolate, useCurrentFrame} from 'remotion';
import {Anim} from '../types';
import {Badge, Burst, clamp, glass, gradText, iconAt, ramp, Shine, txt, usePal} from './kit';

// Metn animasiyalari: flow (axin), list, versus, timeline. Yazilar danisiqdan deqiq fragmentdir (a-dan).
type P = {a: Anim};
const STEP = 16;                                   // novbeti elementin girisine qeder kadr

// flow: SAFE_RIGHT-dan sola sigsin (1920 - 470 - 80 = 1370 px)
const FLOW: Record<number, {w: number; font: number; gap: number}> = {2: {w: 470, font: 46, gap: 120},
  3: {w: 340, font: 40, gap: 80}, 4: {w: 270, font: 33, gap: 60}};

const Connector: React.FC<{k: number; gap: number}> = ({k, gap}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const d = 10 + k * STEP;
  const grow = ramp(f, d, d + 14);
  const run = ((f - d - 14) % 40) / 40;
  return (
    <div style={{position: 'relative', width: gap, height: 8, alignSelf: 'center', marginTop: -40}}>
      <div style={{position: 'absolute', inset: 0, borderRadius: 4, background: `linear-gradient(90deg, ${p.a2}, ${p.a1})`,
        transform: `scaleX(${grow})`, transformOrigin: 'left', boxShadow: `0 0 16px ${p.glow}`}} />
      {f > d + 14 ? <div style={{position: 'absolute', top: -7, left: run * (gap - 22), width: 22, height: 22, borderRadius: 11,
        background: '#fff', boxShadow: `0 0 18px ${p.a1}, 0 0 36px ${p.a1}`}} /> : null}
      <div style={{position: 'absolute', right: -6, top: -11, width: 0, height: 0, opacity: grow,
        borderTop: '15px solid transparent', borderBottom: '15px solid transparent', borderLeft: `20px solid ${p.a1}`}} />
    </div>
  );
};

export const Flow: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const steps: string[] = a.steps ?? [];
  const fl = FLOW[Math.min(4, Math.max(2, steps.length))];
  return (
    <div style={{display: 'flex', alignItems: 'stretch'}}>
      {steps.map((s, k) => {
        const d = k * STEP;
        const t = ramp(f, d, d + 18);
        const pose = a.variant ? `perspective(900px) rotateX(${(1 - t) * 70}deg) translateY(${(1 - t) * 60}px)`
          : `scale(${0.7 + 0.3 * t})`;
        return (
          <React.Fragment key={k}>
            {k > 0 ? <Connector k={k - 1} gap={fl.gap} /> : null}
            <div style={{...glass(p), width: fl.w, padding: '30px 24px 34px', boxSizing: 'border-box', opacity: t,
              transform: `${pose} translateY(${Math.sin((f + k * 20) / 22) * 5}px)`,
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 18, textAlign: 'center'}}>
              <div style={{...txt(26, p.a1), letterSpacing: 3}}>{String(k + 1).padStart(2, '0')}</div>
              <Badge icon={iconAt(a, k)} size={fl.w > 300 ? 110 : 92} delay={d + 4} />
              <div style={{...txt(fl.font), overflowWrap: 'break-word', minWidth: 0}}>{s}</div>
              <Shine every={120} delay={d + 20 + k * 7} />
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

export const List: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const items: string[] = a.items ?? [];
  const n = items.length;
  const all = (n - 1) * STEP + 24;
  const active = f > all ? Math.floor((f - all) / 36) % n : -1;
  return (
    <div style={{display: 'flex', flexDirection: 'column', gap: 26, width: 1180}}>
      {items.map((s, k) => {
        const d = k * STEP;
        const t = ramp(f, d, d + 20);
        const on = active === k ? 1 : 0;
        return (
          <div key={k} style={{...glass(p, on), display: 'flex', alignItems: 'center', gap: 34, padding: '24px 36px',
            opacity: t, transform: `translateX(${(1 - t) * -140}px) scale(${1 + on * 0.025})`}}>
            {a.variant
              ? <div style={{...txt(78), ...gradText(p), width: 120}}>{String(k + 1).padStart(2, '0')}</div>
              : <Badge icon={a.icons?.[k] ?? 'check'} size={92} delay={d + 4} />}
            <div style={{...txt(n > 3 ? 46 : 52), flex: 1}}>{s}</div>
            <Shine every={140} delay={d + 22 + k * 9} />
          </div>
        );
      })}
    </div>
  );
};

export const Versus: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const side = (k: number) => {
    const t = ramp(f, k * 8, k * 8 + 22);
    const move = a.variant ? `translateY(${(1 - t) * 120}px)`
      : `perspective(1000px) rotateY(${(1 - t) * (k ? -60 : 60)}deg) translateX(${(1 - t) * (k ? 160 : -160)}px)`;
    return (
      <div style={{...glass(p), width: 500, height: 440, padding: 36, boxSizing: 'border-box', opacity: t,
        transform: `${move} translateY(${Math.sin((f + k * 40) / 26) * 6}px)`,
        background: `linear-gradient(160deg, ${k ? p.a1 : p.a2}33, rgba(255,255,255,0.03))`,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 30, textAlign: 'center'}}>
        <Badge icon={iconAt(a, k)} size={150} delay={k * 8 + 6} />
        <div style={txt(56)}>{k ? a.right : a.left}</div>
        <Shine every={130} delay={30 + k * 25} />
      </div>
    );
  };
  const vs = a.variant ? interpolate(f, [20, 30, 36], [3, 0.9, 1], clamp) : interpolate(f, [18, 28, 34], [0, 1.2, 1], clamp);
  return (
    <div style={{display: 'flex', alignItems: 'center', gap: 50, position: 'relative'}}>
      <div style={{position: 'absolute', left: '50%', top: -40, bottom: -40, width: 4, marginLeft: -2,
        background: `linear-gradient(transparent, ${p.a1}, transparent)`, opacity: ramp(f, 14, 30)}} />
      {side(0)}
      <div style={{position: 'relative', width: 150, height: 150, flexShrink: 0}}>
        <Burst size={460} delay={20} rays={12} />
        <div style={{position: 'absolute', inset: 0, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: `radial-gradient(circle at 30% 25%, ${p.a2}, ${p.a1})`, boxShadow: `0 0 50px ${p.glow}`,
          transform: `scale(${vs}) rotate(${Math.sin(f / 15) * 4}deg)`, opacity: f >= 18 ? 1 : 0, ...txt(64, '#0b0f1e')}}>VS</div>
      </div>
      {side(1)}
    </div>
  );
};

export const Timeline: React.FC<P> = ({a}) => {
  const p = usePal();
  const f = useCurrentFrame();
  const events: string[] = a.events ?? [];
  const n = events.length;
  const W = 1250;
  const span = 10 + n * 11;
  const line = ramp(f, 0, span);
  return (
    <div style={{position: 'relative', width: W, height: 520}}>
      <div style={{position: 'absolute', top: 256, left: 0, height: 8, width: W, borderRadius: 4, background: 'rgba(255,255,255,0.1)'}} />
      <div style={{position: 'absolute', top: 256, left: 0, height: 8, width: line * W, borderRadius: 4,
        background: `linear-gradient(90deg, ${p.a2}, ${p.a1})`, boxShadow: `0 0 22px ${p.glow}`}} />
      <div style={{position: 'absolute', top: 247, left: line * W - 13, width: 26, height: 26, borderRadius: 13, background: '#fff',
        boxShadow: `0 0 20px ${p.a1}, 0 0 44px ${p.a1}`, opacity: line < 1 ? 1 : 0.5 + 0.5 * Math.sin(f / 8)}} />
      {events.map((e, k) => {
        const x = n < 2 ? W / 2 : 80 + (k / (n - 1)) * (W - 160);
        const d = (x / W) * span;
        const t = ramp(f, d, d + 16);
        const up = a.variant ? k % 2 === 0 : false;
        return (
          <div key={k} style={{position: 'absolute', left: x, top: 0, height: 520, width: 0}}>
            <div style={{position: 'absolute', top: 205, left: -55}}><Badge icon={iconAt(a, k)} size={110} delay={d} rings={k === n - 1} /></div>
            <div style={{...glass(p), position: 'absolute', left: -150, width: 300, padding: '18px 20px', boxSizing: 'border-box',
              top: up ? 30 : 350, opacity: t, transform: `translateY(${(1 - t) * (up ? -30 : 30)}px)`,
              textAlign: 'center', ...txt(n > 3 ? 32 : 36)}}>{e}</div>
          </div>
        );
      })}
    </div>
  );
};
