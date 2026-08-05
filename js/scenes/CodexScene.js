class CodexScene extends Phaser.Scene {
  constructor() {
    super('CodexScene');
  }

  init(data) {
    this.returnTo = (data && data.returnTo) || 'MenuScene';
  }

  create() {
    const { width } = this.scale;
    drawBackground(this);

    this.add.text(width / 2, 90, '도감', {
      fontSize: '56px', color: THEME.text, fontStyle: 'bold',
    }).setOrigin(0.5).setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.activeTab = 'monster';
    this.contentGroup = this.add.group();

    this.buildTabs(width / 2, 190);
    this.renderTab();
    this.buildBackButton(width / 2, 990);
  }

  buildTabs(cx, y) {
    this.tabButtons = {};
    const tabs = [['monster', '몬스터'], ['tower', '타워']];

    tabs.forEach(([key, label], i) => {
      const bx = cx + (i - 0.5) * 220;
      const bg = this.add.rectangle(bx, y, 200, 60, THEME.panel, 0.9).setOrigin(0.5);
      bg.setStrokeStyle(1, 0xffffff, 0.3);
      bg.setInteractive({ useHandCursor: true });
      this.add.text(bx, y, label, { fontSize: '24px', color: '#ffffff', fontStyle: 'bold' }).setOrigin(0.5);

      bg.on('pointerdown', () => {
        this.activeTab = key;
        this.highlightTabs();
        this.renderTab();
      });

      this.tabButtons[key] = bg;
    });

    this.highlightTabs();
  }

  highlightTabs() {
    for (const key in this.tabButtons) {
      const btn = this.tabButtons[key];
      if (key === this.activeTab) btn.setStrokeStyle(3, THEME.accent, 1);
      else btn.setStrokeStyle(1, 0xffffff, 0.3);
    }
  }

  renderTab() {
    this.contentGroup.clear(true, true);

    const data = this.activeTab === 'monster' ? ENEMY_TYPES : TOWER_TYPES;
    const entries = Object.values(data);
    const cols = 3;
    const cardW = 560;
    const cardH = 220;
    const startX = this.scale.width / 2 - (cols * cardW) / 2 + cardW / 2;
    const startY = 340;

    entries.forEach((def, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      const cx = startX + col * cardW;
      const cy = startY + row * (cardH + 30);
      this.buildCard(cx, cy, cardW - 30, cardH, def);
    });
  }

  buildCard(cx, cy, w, h, def) {
    const bg = this.add.rectangle(cx, cy, w, h, THEME.panel, 0.8).setOrigin(0.5);
    bg.setStrokeStyle(1, THEME.panelBorder, 0.9);
    this.contentGroup.add(bg);

    const icon = this.add.circle(cx - w / 2 + 50, cy, 24, def.color);
    this.contentGroup.add(icon);

    const name = this.add.text(cx - w / 2 + 90, cy - h / 2 + 20, def.name, {
      fontSize: '26px', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0, 0);
    this.contentGroup.add(name);

    const stats = this.add.text(cx - w / 2 + 90, cy - h / 2 + 58, this.buildStatLine(def), {
      fontSize: '16px', color: THEME.accent,
    }).setOrigin(0, 0);
    this.contentGroup.add(stats);

    const desc = this.add.text(cx - w / 2 + 20, cy + h / 2 - 65, def.desc || '', {
      fontSize: '16px', color: THEME.textDim, wordWrap: { width: w - 40 },
    }).setOrigin(0, 0);
    this.contentGroup.add(desc);
  }

  buildStatLine(def) {
    if (this.activeTab === 'monster') {
      const armorPart = def.armor ? ` · 방어 ${def.armor}` : '';
      return `속도 ${def.speed} · 체력 ${def.healthBase} · 보상 ${def.reward}G${armorPart}`;
    }
    return `비용 ${def.cost}G · 공격력 ${def.damage} · 사거리 ${def.range}`;
  }

  buildBackButton(x, y) {
    const text = this.add.text(x, y, '← 뒤로가기', {
      fontSize: '28px', color: '#ffd23f',
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });

    this.tweens.add({ targets: text, alpha: 0.4, duration: 700, yoyo: true, repeat: -1 });

    text.on('pointerdown', () => {
      this.scene.start(this.returnTo);
    });
  }
}
