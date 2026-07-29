const SFX = {
  minGap: 80,
  _lastPlay: {},

  init(scene) {
    scene.sfxReady = true;
  },

  play(scene, key, opts = {}) {
    if (!scene.sound || scene.sound.locked) return;
    if (!scene.cache.audio.exists(key)) return;

    const now = scene.time.now;
    const last = this._lastPlay[key] || 0;
    const minGap = opts.minGap ?? this.minGap;
    if (now - last < minGap) return;
    this._lastPlay[key] = now;

    scene.sound.play(key, {
      volume: opts.volume ?? 1,
      detune: Phaser.Math.Between(-60, 60),
    });
  },
};
