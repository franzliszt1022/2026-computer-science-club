const config = {
  type: Phaser.AUTO,
  width: 960,
  height: 640,
  parent: 'game-container',
  backgroundColor: '#2d3436',
  fps: { forceSetTimeOut: true },
  dom: { createContainer: true },
  scene: [BootScene, MenuScene, GameScene, GameOverScene],
};

window.game = new Phaser.Game(config);
