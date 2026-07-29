const FX = {
  _lastShake: 0,

  burst(scene, x, y, color, count, speedRange, life) {
    for (let i = 0; i < count; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = Phaser.Math.Between(speedRange[0], speedRange[1]);
      const dx = Math.cos(angle) * speed;
      const dy = Math.sin(angle) * speed;
      const dot = scene.add.circle(x, y, Phaser.Math.Between(2, 4), color);

      scene.tweens.add({
        targets: dot,
        x: x + dx,
        y: y + dy,
        alpha: 0,
        scale: 0,
        duration: life,
        ease: 'Cubic.easeOut',
        onComplete: () => dot.destroy(),
      });
    }
  },

  hitBurst(scene, x, y, color) {
    this.burst(scene, x, y, color, 6, [40, 90], 300);
  },

  killBurst(scene, x, y, color, opts = {}) {
    const big = opts.big;
    this.burst(scene, x, y, color, big ? 40 : 14, big ? [80, 220] : [50, 140], big ? 500 : 350);
  },

  shake(scene, opts = {}) {
    const now = scene.time.now;
    if (!opts.force && now - this._lastShake < 100) return;
    this._lastShake = now;
    scene.cameras.main.shake(opts.duration || 120, opts.intensity || 0.004);
  },
};
