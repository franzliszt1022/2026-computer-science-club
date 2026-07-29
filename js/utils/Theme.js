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

function drawBackground(scene) {
  const { width, height } = scene.scale;
  const g = scene.add.graphics();
  g.fillGradientStyle(THEME.bgTop, THEME.bgTop, THEME.bgBottom, THEME.bgBottom, 1);
  g.fillRect(0, 0, width, height);
  return g;
}
