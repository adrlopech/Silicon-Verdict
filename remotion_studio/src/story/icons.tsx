import React from 'react';

/** Stroke-only line icons on a 100x100 grid. Unknown names fall back to a star. */
export const ICON_NAMES = [
  'bulb', 'mirror', 'clock', 'building', 'phone', 'wifi', 'chip', 'battery', 'cable', 'eye',
  'smile', 'lock', 'bolt', 'cloud', 'magnifier', 'gear', 'heart', 'arrow', 'question', 'star',
  'box', 'plane', 'wave', 'thermometer', 'drop', 'hand', 'fire', 'sun',
];

export const Icon: React.FC<{ name?: string; size?: number; ink: string }> = ({ name = 'star', size = 200, ink }) => {
  const p = { fill: 'none', stroke: ink, strokeWidth: 3.5, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  let g: React.ReactNode;
  switch ((name || '').toLowerCase()) {
    case 'bulb':
      g = (<><path d="M50 14 a24 24 0 0 1 14 44 v10 h-28 v-10 a24 24 0 0 1 14-44z" {...p} /><path d="M40 78h20M43 86h14" {...p} /><path d="M50 2v6M16 20l5 4M84 20l-5 4M6 48h7M87 48h7" {...p} /></>);
      break;
    case 'mirror':
      g = (<><rect x="24" y="8" width="52" height="84" rx="8" {...p} /><path d="M36 70l26-44M44 78l22-38" {...p} opacity={0.7} /></>);
      break;
    case 'clock':
      g = (<><circle cx="50" cy="50" r="38" {...p} /><path d="M50 26v26l16 10" {...p} /></>);
      break;
    case 'building':
      g = (<><rect x="26" y="8" width="48" height="84" {...p} /><path d="M38 24h8M54 24h8M38 40h8M54 40h8M38 56h8M54 56h8M44 92V76h12v16" {...p} /></>);
      break;
    case 'phone':
      g = (<><rect x="28" y="6" width="44" height="88" rx="8" {...p} /><path d="M44 14h12M46 84h8" {...p} /></>);
      break;
    case 'wifi':
      g = (<><path d="M12 38a54 54 0 0 1 76 0M25 52a36 36 0 0 1 50 0M38 66a18 18 0 0 1 24 0" {...p} /><circle cx="50" cy="80" r="4" fill={ink} /></>);
      break;
    case 'chip':
      g = (<><rect x="28" y="28" width="44" height="44" rx="5" {...p} /><rect x="40" y="40" width="20" height="20" {...p} /><path d="M38 28V14M50 28V14M62 28V14M38 72v14M50 72v14M62 72v14M28 38H14M28 50H14M28 62H14M72 38h14M72 50h14M72 62h14" {...p} /></>);
      break;
    case 'battery':
      g = (<><rect x="10" y="30" width="72" height="40" rx="6" {...p} /><path d="M88 42v16M20 40v20M32 40v20M44 40v20" {...p} /></>);
      break;
    case 'cable':
      g = (<><path d="M8 60c20 0 20-30 40-30s20 30 40 30" {...p} /><rect x="84" y="52" width="10" height="16" {...p} /><rect x="6" y="52" width="10" height="16" {...p} /></>);
      break;
    case 'eye':
      g = (<><path d="M6 50c16-26 72-26 88 0-16 26-72 26-88 0z" {...p} /><circle cx="50" cy="50" r="12" {...p} /></>);
      break;
    case 'smile':
      g = (<><circle cx="50" cy="50" r="38" {...p} /><circle cx="38" cy="42" r="3" fill={ink} /><circle cx="62" cy="42" r="3" fill={ink} /><path d="M32 58q18 20 36 0" {...p} /></>);
      break;
    case 'lock':
      g = (<><rect x="22" y="44" width="56" height="42" rx="7" {...p} /><path d="M32 44V32a18 18 0 0 1 36 0v12M50 58v12" {...p} /></>);
      break;
    case 'bolt':
      g = <path d="M56 4L22 54h24l-6 42 38-54H54z" {...p} />;
      break;
    case 'cloud':
      g = <path d="M26 74a18 18 0 0 1 2-36 24 24 0 0 1 46 4 16 16 0 0 1-2 32z" {...p} />;
      break;
    case 'magnifier':
      g = (<><circle cx="42" cy="42" r="28" {...p} /><path d="M62 62l28 28" {...p} /></>);
      break;
    case 'gear':
      g = (<><circle cx="50" cy="50" r="14" {...p} /><circle cx="50" cy="50" r="30" {...p} /><path d="M50 8v12M50 80v12M8 50h12M80 50h12M20 20l9 9M71 71l9 9M80 20l-9 9M29 71l-9 9" {...p} /></>);
      break;
    case 'heart':
      g = <path d="M50 88C10 58 14 22 36 20c10 0 14 6 14 10 0-4 4-10 14-10 22 2 26 38-14 68z" {...p} />;
      break;
    case 'arrow':
      g = <path d="M10 50h76M62 26l24 24-24 24" {...p} />;
      break;
    case 'question':
      g = <text x="50" y="78" textAnchor="middle" fontSize="86" fontWeight="900" fill="none" stroke={ink} strokeWidth="3" fontFamily="Arial, sans-serif">?</text>;
      break;
    case 'box':
      g = (<><path d="M50 8l36 18v40L50 90 14 66V26z" {...p} /><path d="M14 26l36 18 36-18M50 44v46" {...p} /></>);
      break;
    case 'plane':
      g = <path d="M8 56l84-34-22 56-20-18-12 14-4-20z" {...p} />;
      break;
    case 'wave':
      g = <path d="M4 50q11-34 22 0t22 0 22 0 22 0" {...p} />;
      break;
    case 'thermometer':
      g = (<><path d="M42 14a8 8 0 0 1 16 0v46a18 18 0 1 1-16 0z" {...p} /><circle cx="50" cy="74" r="8" fill={ink} /><path d="M50 28v36" {...p} /></>);
      break;
    case 'drop':
      g = <path d="M50 8C50 8 22 44 22 62a28 28 0 0 0 56 0C78 44 50 8 50 8z" {...p} />;
      break;
    case 'hand':
      g = <path d="M30 88V50a6 6 0 0 1 12 0V30a6 6 0 0 1 12 0v-4a6 6 0 0 1 12 0v8a6 6 0 0 1 12 0v36c0 14-10 24-24 24H46C36 94 30 90 30 88z" {...p} />;
      break;
    case 'fire':
      g = <path d="M50 6C58 28 78 38 78 62a28 28 0 0 1-56 0c0-12 6-18 12-26 2 8 6 12 10 12 0-14 0-28 6-42z" {...p} />;
      break;
    case 'sun':
      g = (<><circle cx="50" cy="50" r="18" {...p} /><path d="M50 8v12M50 80v12M8 50h12M80 50h12M20 20l8 8M72 72l8 8M80 20l-8 8M28 72l-8 8" {...p} /></>);
      break;
    default:
      g = <path d="M50 8l12 28 30 3-23 20 7 30-26-16-26 16 7-30L8 39l30-3z" {...p} />;
  }
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ overflow: 'visible' }}>
      {g}
    </svg>
  );
};
