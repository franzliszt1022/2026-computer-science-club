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

    const startText = this.add.text(width / 2, height / 2 + 20, '클릭해서 시작', {
      fontSize: '28px',
      color: '#ffd23f',
    }).setOrigin(0.5);

    this.tweens.add({
      targets: startText,
      alpha: 0.3,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    this.input.once('pointerdown', () => {
      this.scene.start('GameScene');
    });
  }
}
