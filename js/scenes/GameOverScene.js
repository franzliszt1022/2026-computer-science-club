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

    this.add.text(width / 2, height / 2 - 60, this.won ? 'VICTORY!' : 'GAME OVER', {
      fontSize: '44px',
      color: this.won ? '#2ecc71' : '#e74c3c',
      fontStyle: 'bold',
    }).setOrigin(0.5);

    this.add.text(width / 2, height / 2, `도달 웨이브: ${this.wave}`, {
      fontSize: '24px',
      color: '#ffffff',
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
