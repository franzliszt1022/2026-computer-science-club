class BootScene extends Phaser.Scene {
  constructor() {
    super('BootScene');
  }

  preload() {
    // 아직 이미지/사운드 없음 - 도형으로만 진행 중
  }

  create() {
    this.scene.start('MenuScene');
  }
}
