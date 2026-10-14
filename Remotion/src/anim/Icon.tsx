import React from 'react';

// Projects/grounding.py ICONS ile eyni adlar. 24x24 xett ikonlari; t (0..1) xettin cizilme hissesidir.
type Shape = ['p', string] | ['c', number, number, number] | ['r', number, number, number, number, number];
const ICONS: Record<string, Shape[]> = {
  money: [['r', 2, 6, 20, 12, 2], ['c', 12, 12, 3], ['p', 'M6 10v4M18 10v4']],
  coin: [['c', 12, 12, 9], ['p', 'M14.5 9.5c-.6-.9-1.6-1.3-2.5-1.3-1.5 0-2.7.8-2.7 2s1.2 1.6 2.7 1.9 2.7.8 2.7 2-1.2 2-2.7 2c-1 0-2-.4-2.6-1.3M12 6.5v1.7M12 15.8v1.7']],
  'chart-up': [['p', 'M3 3v18h18'], ['p', 'M7 15l4-4 3 3 6-7'], ['p', 'M15 7h5v5']],
  'chart-down': [['p', 'M3 3v18h18'], ['p', 'M7 8l4 4 3-3 6 7'], ['p', 'M20 11v5h-5']],
  users: [['c', 9, 8, 3.5], ['p', 'M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6'], ['c', 17, 9, 2.5], ['p', 'M17 14c2.5 0 4.5 1.8 4.5 4.5']],
  user: [['c', 12, 8, 4], ['p', 'M4 21c0-4.4 3.6-7.5 8-7.5s8 3.1 8 7.5']],
  phone: [['r', 6, 2, 12, 20, 2.5], ['p', 'M10.5 18h3']],
  cart: [['p', 'M2 3h3l2.5 12h11l2-8H6.2'], ['c', 9, 19.5, 1.5], ['c', 17, 19.5, 1.5]],
  bag: [['p', 'M5 8h14l-1.2 13H6.2z'], ['p', 'M9 8V6a3 3 0 0 1 6 0v2']],
  tag: [['p', 'M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z'], ['c', 7.5, 7.5, 1.5]],
  crown: [['p', 'M3 19h18M4 16L3 7l5 4 4-7 4 7 5-4-1 9z']],
  diamond: [['p', 'M6 3h12l4 6-10 12L2 9z'], ['p', 'M2 9h20M9 3l3 18M15 3l-3 18']],
  star: [['p', 'M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9z']],
  clock: [['c', 12, 12, 9], ['p', 'M12 7v5l3.5 2']],
  calendar: [['r', 3, 5, 18, 16, 2], ['p', 'M3 10h18M8 3v4M16 3v4']],
  globe: [['c', 12, 12, 9], ['p', 'M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3']],
  building: [['r', 4, 3, 16, 18, 1], ['p', 'M9 7h1M14 7h1M9 11h1M14 11h1M9 15h1M14 15h1M10 21v-3h4v3']],
  factory: [['p', 'M2 21V10l6 4V10l6 4V6h3l1 15zM2 21h20']],
  bulb: [['p', 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2V16h5v-.1c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z']],
  target: [['c', 12, 12, 9], ['c', 12, 12, 5], ['c', 12, 12, 1.5]],
  shield: [['p', 'M12 2.5l8 3v6c0 5-3.4 8.6-8 10-4.6-1.4-8-5-8-10v-6z'], ['p', 'M8.5 12l2.5 2.5 4.5-5']],
  heart: [['p', 'M12 20.5S3 15 3 8.8A4.8 4.8 0 0 1 12 6.3a4.8 4.8 0 0 1 9 2.5c0 6.2-9 11.7-9 11.7z']],
  lock: [['r', 4, 10, 16, 11, 2], ['p', 'M8 10V7a4 4 0 0 1 8 0v3M12 14.5v3']],
  gift: [['r', 3, 8, 18, 5, 1], ['p', 'M5 13v8h14v-8M12 8v13M12 8S10.5 3 8 3.8 8.8 8 12 8zM12 8s1.5-5 4-4.2S15.2 8 12 8z']],
  rocket: [['p', 'M12 2.5c3.5 2 5 5.5 5 9.5l-2.5 3.5h-5L7 12c0-4 1.5-7.5 5-9.5z'], ['c', 12, 9, 1.8], ['p', 'M9.5 15.5L7 20l3.2-1.2M14.5 15.5L17 20l-3.2-1.2']],
  megaphone: [['p', 'M3 10v4h3l9 5V5L6 10zM18.5 9a4 4 0 0 1 0 6M7 14l1.5 6h2.5L10 15']],
  check: [['c', 12, 12, 9], ['p', 'M7.5 12.5l3 3 6-6.5']],
  warning: [['p', 'M12 3l10 18H2z'], ['p', 'M12 10v5M12 18v.5']],
  scale: [['p', 'M12 3v18M7 21h10M4 7h16M4 7l-2.5 6a2.5 2.5 0 0 0 5 0zM20 7l-2.5 6a2.5 2.5 0 0 0 5 0z']],
  gear: [['c', 12, 12, 3.2], ['c', 12, 12, 7], ['p', 'M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1']],
  truck: [['p', 'M2 6h12v10H2zM14 10h4l3 3v3h-7'], ['c', 6, 18, 2], ['c', 17, 18, 2]],
  store: [['p', 'M3 9l1.5-5h15L21 9M3 9h18v2a3 3 0 0 1-6 0 3 3 0 0 1-6 0 3 3 0 0 1-6 0zM5 13v8h14v-8M10 21v-5h4v5']],
  brain: [['p', 'M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V5a2 2 0 0 0-3-1zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1']],
  eye: [['p', 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z'], ['c', 12, 12, 3]],
  handshake: [['p', 'M2 11l4-4 4 2 3-2 4 1 5 3M2 11l3 3M22 11l-4 4-4 3-4-3-3-2M10 12l2 2M12 10l3 3']],
  spark: [['p', 'M12 2l2.2 7.8L22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2z']],
};

export const hasIcon = (name?: string): boolean => !!name && name in ICONS;

export const Icon: React.FC<{name?: string; size: number; color: string; t?: number; stroke?: number}> = (
  {name, size, color, t = 1, stroke = 1.9}) => {
  const shapes = ICONS[name ?? ''] ?? ICONS.spark;
  const line = {fill: 'none', stroke: color, strokeWidth: stroke, strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const, pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - t};
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{overflow: 'visible'}}>
      {shapes.map((s, k) => s[0] === 'p' ? <path key={k} d={s[1]} {...line} />
        : s[0] === 'c' ? <circle key={k} cx={s[1]} cy={s[2]} r={s[3]} {...line} />
        : <rect key={k} x={s[1]} y={s[2]} width={s[3]} height={s[4]} rx={s[5]} {...line} />)}
    </svg>
  );
};
