class GameOverScene extends Phaser.Scene {
  constructor() {
    super('GameOverScene');
  }

  init(data) {
    this.won = data.won || false;
    this.wave = data.wave || 0;
  }

  create() {
    const { width, height } = this.scale;

    drawBackground(this);

    const accent = this.won ? THEME.success : THEME.danger;
    const glow = this.add.circle(width / 2, height / 2 - 60, 160, accent, 0.1);
    this.tweens.add({
      targets: glow,
      scale: 1.2,
      alpha: 0.18,
      duration: 1200,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    const title = this.add.text(width / 2, height / 2 - 60, this.won ? 'VICTORY!' : 'GAME OVER', {
      fontSize: '44px',
      color: this.won ? '#2ecc71' : '#e74c3c',
      fontStyle: 'bold',
    }).setOrigin(0.5);
    title.setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.add.text(width / 2, height / 2, `도달 웨이브: ${this.wave}`, {
      fontSize: '24px',
      color: THEME.text,
    }).setOrigin(0.5);

    const retryText = this.add.text(width / 2, height / 2 + 80, '클릭해서 다시 시작', {
      fontSize: '24px',
      color: '#ffd23f',
    }).setOrigin(0.5);

    this.tweens.add({
      targets: retryText,
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
