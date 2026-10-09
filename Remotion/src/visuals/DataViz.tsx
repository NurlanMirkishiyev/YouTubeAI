import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Unit, Visual} from '../types';
import {FONT} from '../fonts';
import {DUR, EASE, ease} from '../motion';
import {AREA, Body, C, Count, fmt, GHOST, LiveHead, useEnter, TITLE_H, useIn} from './common';

/** Faza 2 (istifadeci 2026-10-07): qerar vizuallari (table, threshold), zaman seriyasi, ABS xeritesi.
 *  Hamisi skeletle (GHOST + "—") 0-ci kadrdan gorunur; reqem oz sozunde acilir (reveal). */
const BODY_H = AREA.height - TITLE_H - 24;
const at = (reveal: number[], i: number) => reveal[i] ?? reveal[reveal.length - 1] ?? 0;
const GREEN = '#46D77D';
const RED = C.coral;

type TableV = Extract<Visual, {kind: 'table'}>;
type ThresholdV = Extract<Visual, {kind: 'threshold'}>;
type SeriesV = Extract<Visual, {kind: 'timeseries'}>;
type MapV = Extract<Visual, {kind: 'usmap'}>;

/** Evvel / sonra / ferq: setirler bir-bir acilir, ferq yasil (artim) ve ya qirmizi (azalma). */
export const Table: React.FC<{v: TableV; reveal: number[]}> = ({v, reveal}) => {
  const colW = [420, 250, 250, 250];
  const rowH = Math.min(120, (BODY_H - 90) / Math.max(1, v.rows.length));
  return (
    <Body style={{display: 'flex', flexDirection: 'column', justifyContent: 'center', paddingLeft: 30}}>
      <div style={{display: 'flex', fontSize: 30, fontWeight: 700, color: C.muted, letterSpacing: 2,
        textTransform: 'uppercase', borderBottom: `2px solid ${C.line}`, paddingBottom: 14}}>
        <div style={{width: colW[0]}} />
        {v.columns.map((c, i) => <div key={c} style={{width: colW[i + 1], textAlign: 'right'}}>{c}</div>)}
      </div>
      {v.rows.map((r, i) => <TableRow key={r.label} row={r} delay={at(reveal, i)} colW={colW} h={rowH} />)}
    </Body>
  );
};

const TableRow: React.FC<{row: TableV['rows'][number]; delay: number; colW: number[]; h: number}> = (
  {row, delay, colW, h}) => {
  const enter = useEnter();
  const p = useIn(delay);
  const up = (row.delta ?? row.after - row.before) >= 0;
  const color = up ? GREEN : RED;
  return (
    <div style={{display: 'flex', alignItems: 'center', height: h, borderBottom: `1px solid ${C.line}`,
      fontSize: 52, fontWeight: 800, ...enter(p, 16)}}>
      <div style={{width: colW[0], fontSize: 40, fontWeight: 700}}>{row.label}</div>
      <div style={{width: colW[1], textAlign: 'right', color: C.muted}}><Count value={row.before} unit={row.unit} delay={delay} /></div>
      <div style={{width: colW[2], textAlign: 'right'}}><Count value={row.after} unit={row.unit} delay={delay + DUR.stagger} /></div>
      <div style={{width: colW[3], textAlign: 'right', color}}>
        {row.delta !== null ? <>{up ? '+' : '−'}<Count value={Math.abs(row.delta)} unit={row.unit} delay={delay + DUR.stagger * 2} /></> : ''}
      </div>
    </div>
  );
};

/** Break-even: egri (deyisen -> netice) evvelki seviyye xettini threshold-da kesir; egri yoxdursa sayqac xetti
 *  uzerinde esik ve bugunku deyer. */
export const Threshold: React.FC<{v: ThresholdV; reveal: number[]}> = ({v, reveal}) =>
  v.curve ? <ThresholdCurve v={v} reveal={reveal} /> : <ThresholdGauge v={v} reveal={reveal} />;

const ThresholdGauge: React.FC<{v: ThresholdV; reveal: number[]}> = ({v, reveal}) => {
  const cur = v.current;
  const hi = Math.max(v.threshold.value, cur?.value ?? 0) * 1.35 || 1;
  const x0 = 60;
  const span = AREA.width - 160;
  const xs = (val: number) => x0 + (val / hi) * span;
  const tIdx = cur ? 1 : 0;
  const pT = useIn(at(reveal, tIdx));
  const pC = useIn(cur ? at(reveal, 0) : 0);
  const y = 250;
  const ok = cur ? cur.value >= v.threshold.value : true;
  return (
    <Body>
      <div style={{position: 'absolute', left: x0, top: y - 10, width: span, height: 20, borderRadius: 10,
        background: C.line}} />
      <div style={{position: 'absolute', left: xs(v.threshold.value), top: y - 10,
        width: span - (xs(v.threshold.value) - x0), height: 20, borderRadius: 10,
        background: `linear-gradient(90deg, ${GREEN}55, ${GREEN}22)`, opacity: GHOST + (1 - GHOST) * pT}} />
      <Marker x={xs(v.threshold.value)} y={y} p={pT} color={C.accent} above
        label={v.threshold.label} value={<Count value={v.threshold.value} unit={v.threshold.unit} delay={at(reveal, tIdx)} />} />
      {cur ? <Marker x={xs(cur.value)} y={y} p={pC} color={ok ? GREEN : RED} above={false}
        label={cur.label} value={<Count value={cur.value} unit="" delay={at(reveal, 0)} />} /> : null}
    </Body>
  );
};

const Marker: React.FC<{x: number; y: number; p: number; color: string; above: boolean; label: string;
  value: React.ReactNode}> = ({x, y, p, color, above, label, value}) => {
  const enter = useEnter();
  return (
  <>
    <div style={{position: 'absolute', left: x - 4, top: above ? y - 120 : y, width: 8, height: 120,
      background: color, opacity: GHOST + (1 - GHOST) * p}} />
    <div style={{position: 'absolute', left: x - 200, width: 400, top: above ? y - 255 : y + 130, textAlign: 'center',
      ...enter(p, 14)}}>
      <div style={{fontSize: 76, fontWeight: 800, color}}>{value}</div>
      <div style={{fontSize: 32, fontWeight: 700, color: C.text}}>{label}</div>
    </div>
  </>
  );
};

const ThresholdCurve: React.FC<{v: ThresholdV; reveal: number[]}> = ({v, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const c = v.curve!;
  const xsV = c.points.map((q) => q[0]);
  const ysV = c.points.map((q) => q[1]);
  const base = c.baseline?.value ?? ysV[0];
  const lo = Math.min(...ysV, base);
  const hi = Math.max(...ysV, base);
  const pad = 90;
  const W2 = AREA.width - pad * 2;
  const H2 = BODY_H - 140;
  const px = (x: number) => pad + ((x - xsV[0]) / (xsV[xsV.length - 1] - xsV[0] || 1)) * W2;
  const py = (y: number) => 40 + (hi === lo ? H2 / 2 : (1 - (y - lo) / (hi - lo)) * H2);
  const d0 = at(reveal, 0);
  const draw = ease(frame, d0 - DUR.draw, DUR.draw, EASE.inOut);
  const n = Math.max(2, Math.round(draw * c.points.length));
  const path = c.points.slice(0, n).map((q, i) => `${i ? 'L' : 'M'} ${px(q[0])} ${py(q[1])}`).join(' ');
  const enter = useEnter();
  const pT = useIn(d0);
  const unit: Unit = c.baseline?.unit ?? '';
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        <line x1={pad} x2={pad} y1={30} y2={40 + H2} stroke={C.line} strokeWidth={3} />
        <line x1={pad} x2={pad + W2} y1={40 + H2} y2={40 + H2} stroke={C.line} strokeWidth={3} />
        <line x1={pad} x2={pad + W2} y1={py(base)} y2={py(base)} stroke={C.muted} strokeWidth={3} strokeDasharray="14 12" />
        <path d={path} fill="none" stroke={C.accent} strokeWidth={8} strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={px(c.cross)} cy={py(base)} r={18 * pT} fill={C.accent} stroke="#0A0F1E" strokeWidth={5} />
      </svg>
      <div style={{position: 'absolute', left: px(c.cross) - 200, width: 400, top: py(base) - 150, textAlign: 'center',
        ...enter(pT, 14)}}>
        <div style={{fontSize: 72, fontWeight: 800, color: C.accent}}>
          <Count value={v.threshold.value} unit={v.threshold.unit} delay={d0} /></div>
        <div style={{fontSize: 30, fontWeight: 700}}>{v.threshold.label}</div>
      </div>
      {c.baseline ? <div style={{position: 'absolute', right: 40, top: py(base) + 14, fontSize: 30, fontWeight: 700,
        color: C.muted}}>{c.baseline.label}: {fmt(c.baseline.value, unit)}</div> : null}
      <div style={{position: 'absolute', left: pad, top: 40 + H2 + 18, width: W2, textAlign: 'center', fontSize: 30,
        fontWeight: 600, color: C.muted}}>{c.x_label} →</div>
      <div style={{position: 'absolute', left: 0, top: 0, fontSize: 30, fontWeight: 600, color: C.muted}}>{c.y_label}</div>
    </Body>
  );
};

/** Zaman seriyasi (reference: sehm qrafiki): xett noqteden noqteye cekilir, enis qirmizi, hadise etiketi oz
 *  noqtesinde acilir; interpolasiya varsa "illustrative". */
export const Timeseries: React.FC<{v: SeriesV; reveal: number[]}> = ({v, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const vals = v.points.map((q) => q.value);
  const lo = Math.min(...vals);
  const hi = Math.max(...vals);
  const pad = 90;
  const W2 = AREA.width - pad * 2;
  const H2 = BODY_H - 170;
  const xy = vals.map((val, i) => [pad + (i / Math.max(1, vals.length - 1)) * W2,
    70 + (hi === lo ? H2 / 2 : (1 - (val - lo) / (hi - lo)) * H2)] as const);
  return (
    <Body>
      <svg width={AREA.width} height={BODY_H} style={{position: 'absolute', overflow: 'visible'}}>
        {[0, 0.5, 1].map((g) => <line key={g} x1={pad} x2={pad + W2} y1={70 + g * H2} y2={70 + g * H2} stroke={C.line} />)}
        {v.segments.map((s) => {
          const t = ease(frame, at(reveal, s.to) - DUR.draw, DUR.draw, EASE.inOut);
          const [x0, y0] = xy[s.from];
          const [x1, y1] = xy[s.to];
          return <line key={s.from} x1={x0} y1={y0} x2={x0 + (x1 - x0) * t} y2={y0 + (y1 - y0) * t}
            stroke={s.down ? RED : GREEN} strokeWidth={8} strokeLinecap="round" />;
        })}
      </svg>
      {v.points.map((q, i) => q.shown ? <SeriesPoint key={i} q={q} unit={v.unit} x={xy[i][0]} y={xy[i][1]}
        labelY={70 + H2 + 26} delay={at(reveal, i)} down={i > 0 && q.value < v.points[i - 1].value} /> : null)}
      {v.events.map((e) => <SeriesEvent key={e.index} label={e.label} x={xy[e.index][0]} y={xy[e.index][1]}
        labelY={70 + H2 + 70} delay={at(reveal, e.index)} />)}
      <LiveHead xy={xy} vals={vals} unit={v.unit} width={AREA.width}
        progress={vals.slice(1).map((_, i) => ease(frame, at(reveal, i + 1) - DUR.draw, DUR.draw, EASE.inOut))}
        colorOf={(i) => (v.points[i + 1].value < v.points[i].value ? RED : GREEN)} />
      {v.illustrative ? <div style={{position: 'absolute', right: 0, top: -6, fontSize: 26, fontWeight: 600,
        color: C.muted, letterSpacing: 2, textTransform: 'uppercase'}}>illustrative</div> : null}
    </Body>
  );
};

const SeriesPoint: React.FC<{q: {label: string; value: number}; unit: Unit; x: number; y: number; labelY: number;
  delay: number; down: boolean}> = ({q, unit, x, y, labelY, delay, down}) => {
  const enter = useEnter();
  const p = useIn(delay, 'snappy');
  const color = down ? RED : GREEN;
  return (
    <>
      <div style={{position: 'absolute', left: x - 13, top: y - 13, width: 26, height: 26, borderRadius: 13,
        background: color, border: '5px solid #111A30', opacity: GHOST + (1 - GHOST) * p}} />
      <div style={{position: 'absolute', left: x - 130, width: 260, top: y - 76, textAlign: 'center', fontSize: 40,
        fontWeight: 800, color, ...enter(p, 14)}}><Count value={q.value} unit={unit} delay={delay} /></div>
      <div style={{position: 'absolute', left: x - 120, width: 240, top: labelY, textAlign: 'center', fontSize: 30,
        fontWeight: 600, color: C.muted}}>{q.label}</div>
    </>
  );
};

const SeriesEvent: React.FC<{label: string; x: number; y: number; labelY: number; delay: number}> = (
  {label, x, labelY, delay}) => {
  const enter = useEnter();
  const p = useIn(delay + DUR.staggerTight);
  return (
    <div style={{position: 'absolute', left: x - 150, width: 300, top: labelY, textAlign: 'center', fontSize: 28,
      fontWeight: 800, color: C.accent, opacity: p, transform: `translateY(${interpolate(p, [0, 1], [12, 0])}px)`}}>
      ▲ {label}
    </div>
  );
};

/** ABS xeritesi (reference): kontur + noqteler (seed = slug); say acar deyerler arasinda deyisir, artim qizili,
 *  azalan noqteler qirmizi sonur. Sayqac bayqus/altyazi zonasindan kenarda (layout.MAP_COUNTER). */
export const USMap: React.FC<{v: MapV; reveal: number[]}> = ({v, reveal}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  let count = 0;
  let prev = 0;
  let label = '';
  v.keys.forEach((k, i) => {
    const t = ease(frame, at(reveal, i), DUR.draw * 2, EASE.inOut);
    if (frame >= at(reveal, i)) {
      prev = count;
      count = count + (k.value - count) * t;
      label = k.label;
    }
  });
  const started = frame >= at(reveal, 0);
  const lit = Math.round(count / v.per_dot);
  const gone = Math.max(0, Math.round(prev / v.per_dot) - lit);
  const [cx, cy, cw, ch] = v.counter;
  const toLocal = (x: number, y: number) => [x - AREA.left, y - AREA.top] as const;
  const outline = v.outline.map(([x, y]) => toLocal(x, y).join(',')).join(' ');
  return (
    <div style={{position: 'absolute', inset: 0, fontFamily: FONT, color: C.text}}>
      <svg width={AREA.width} height={AREA.height} style={{position: 'absolute', overflow: 'visible'}}>
        <polygon points={outline} fill="rgba(255,255,255,0.05)" stroke="rgba(160,175,200,0.55)" strokeWidth={3} />
        {v.dots.map(([x, y], i) => {
          const [lx, ly] = toLocal(x, y);
          const on = i < lit;
          const fading = !on && i < lit + gone;
          return <circle key={i} cx={lx} cy={ly} r={on ? 7 : 4}
            fill={on ? C.accent : fading ? RED : 'rgba(255,255,255,0.10)'} />;
        })}
      </svg>
      <div style={{position: 'absolute', left: cx - AREA.left, top: cy - AREA.top, width: cw, height: ch,
        textAlign: 'right'}}>
        <div style={{fontSize: 110, fontWeight: 800, color: C.accent, lineHeight: 1}}>
          {started ? Math.round(count).toLocaleString('en-US') : '—'}</div>
        <div style={{fontSize: 30, fontWeight: 700, color: C.muted, letterSpacing: 2, textTransform: 'uppercase'}}>
          {v.unit_label}</div>
        <div style={{fontSize: 30, fontWeight: 700, color: C.text, marginTop: 8}}>{label}</div>
      </div>
    </div>
  );
};
