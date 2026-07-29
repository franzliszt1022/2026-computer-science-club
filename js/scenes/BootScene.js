class BootScene extends Phaser.Scene {
  constructor() {
    super('BootScene');
  }

  preload() {
    this.load.audio('sfx_hit', 'assets/audio/hit.ogg');
    this.load.audio('sfx_kill', 'assets/audio/kill.ogg');
    this.load.audio('sfx_gold', 'assets/audio/gold.ogg');
    this.load.audio('sfx_place', 'assets/audio/tower_place.ogg');
    this.load.audio('sfx_wave_clear', 'assets/audio/wave_clear.ogg');
    this.load.audio('sfx_victory', 'assets/audio/victory.ogg');
    this.load.audio('sfx_gameover', 'assets/audio/gameover.ogg');
  }

  create() {
    this.scene.start('MenuScene');
  }
}
