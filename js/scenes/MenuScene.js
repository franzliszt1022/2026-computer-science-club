class MenuScene extends Phaser.Scene {
  constructor() {
    super('MenuScene');
  }

  create() {
    const { width, height } = this.scale;

    drawBackground(this);

    const glow = this.add.circle(width / 2, height / 2 - 80, 140, THEME.accent, 0.08);
    this.tweens.add({
      targets: glow,
      scale: 1.15,
      alpha: 0.14,
      duration: 1400,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    const title = this.add.text(width / 2, height / 2 - 80, 'DEFENSE GAME', {
      fontSize: '48px',
      color: THEME.text,
      fontStyle: 'bold',
    }).setOrigin(0.5);
    title.setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.add.rectangle(width / 2, height / 2 - 40, 160, 3, THEME.accent, 0.8);

    const promptText = this.add.text(width / 2, height / 2 + 20, '난이도를 선택하세요', {
      fontSize: '20px',
      color: '#ffd23f',
    }).setOrigin(0.5);

    this.tweens.add({
      targets: promptText,
      alpha: 0.3,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    this.buildDifficultyButtons(width / 2, height / 2 + 90);
  }

  buildDifficultyButtons(centerX, y) {
    const difficulties = ['easy', 'normal', 'hard'];

    difficulties.forEach((key, i) => {
      const preset = DIFFICULTY_PRESETS[key];
      const bx = centerX + (i - 1) * 160;

      this.add.rectangle(bx + 3, y + 3, 140, 50, 0x000000, 0.3).setOrigin(0.5);

      const btn = this.add.rectangle(bx, y, 140, 50, preset.color, 0.85).setOrigin(0.5);
      btn.setStrokeStyle(1, 0xffffff, 0.3);
      btn.setInteractive({ useHandCursor: true });

      this.add.text(bx, y, preset.label, {
        fontSize: '20px', color: '#ffffff', fontStyle: 'bold',
      }).setOrigin(0.5);

      btn.on('pointerdown', () => {
        this.scene.start('GameScene', { difficulty: key });
      });
    });
  }
}
