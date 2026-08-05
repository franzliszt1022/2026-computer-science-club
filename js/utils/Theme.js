const THEME = {
  bgTop: 0x25344a,
  bgBottom: 0x0e1420,
  panel: 0x111827,
  panelBorder: 0x3a4a63,
  accent: 0xffd23f,
  accentSoft: 0xffe9a8,
  danger: 0xff6b6b,
  success: 0x2ecc71,
  road: 0x40485a,
  roadEdge: 0x2a3040,
  text: '#f5f6fa',
  textDim: '#9aa5b5',
};

const DIFFICULTY_PRESETS = {
  easy: { label: '쉬움', lives: 7, gold: 130, healthMult: 0.85, speedMult: 1.0, scoreMult: 0.7, color: 0x2ecc71 },
  normal: { label: '보통', lives: 4, gold: 100, healthMult: 1.0, speedMult: 1.0, scoreMult: 1.0, color: 0xffd23f },
  hard: { label: '어려움', lives: 2, gold: 80, healthMult: 1.2, speedMult: 1.1, scoreMult: 1.5, color: 0xe74c3c },
};

function drawBackground(scene) {
  const { width, height } = scene.scale;
  const g = scene.add.graphics();
  g.fillGradientStyle(THEME.bgTop, THEME.bgTop, THEME.bgBottom, THEME.bgBottom, 1);
  g.fillRect(0, 0, width, height);
  return g;
}
