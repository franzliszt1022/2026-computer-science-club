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
    const applySettings = () => {
      const settings = Settings.get();
      this.sound.mute = settings.muted;
      this.sound.volume = settings.volume;
    };
    applySettings();
    // 페이지 로드 시점엔 오디오 컨텍스트가 아직 잠겨있어(사용자 제스처 전) mute/volume 설정이
    // 바로 반영되지 않을 수 있음 — 실제로 잠금 해제되는 시점에 한 번 더 적용해서 확실히 반영
    this.sound.once('unlocked', applySettings);

    this.scene.start('MenuScene');
  }
}
