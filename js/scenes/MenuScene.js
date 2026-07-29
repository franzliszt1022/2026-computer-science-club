class MenuScene extends Phaser.Scene {
  constructor() {
    super('MenuScene');
  }

  create() {
    const { width, height } = this.scale;

    this.add.text(width / 2, height / 2 - 80, 'DEFENSE GAME', {
      fontSize: '48px',
      color: '#ffffff',
      fontStyle: 'bold',
    }).setOrigin(0.5);

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
