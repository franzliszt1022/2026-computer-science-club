class Projectile {
  constructor(scene, x, y, target, damage, splashRadius = 0, slowFactor = null, slowDuration = 0) {
    this.scene = scene;
    this.target = target;
    this.damage = damage;
    this.splashRadius = splashRadius;
    this.slowFactor = slowFactor;
    this.slowDuration = slowDuration;
    this.speed = 500;

    this.sprite = scene.add.circle(x, y, 4, 0xffe66d);
    scene.projectiles.push(this);
  }

  update(delta) {
    if (!this.target || !this.target.alive) {
      this.destroy();
      return;
    }

    const dist = Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, this.target.x, this.target.y);
    if (dist <= 8) {
      this.hit();
      this.destroy();
      return;
    }

    const angle = Phaser.Math.Angle.Between(this.sprite.x, this.sprite.y, this.target.x, this.target.y);
    const moveDist = this.speed * delta / 1000;
    this.sprite.x += Math.cos(angle) * moveDist;
    this.sprite.y += Math.sin(angle) * moveDist;
  }

  hit() {
    const isCrit = Math.random() < 0.12;
    const dmg = isCrit ? Math.round(this.damage * 1.8) : this.damage;

    const targets = this.splashRadius > 0
      ? this.scene.enemies.filter((e) => e.alive
        && Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, e.x, e.y) <= this.splashRadius)
      : [this.target];

    for (const enemy of targets) {
      enemy.takeDamage(dmg);
      if (this.slowFactor && enemy.alive) enemy.applySlow(this.slowFactor, this.slowDuration);
      FX.hitBurst(this.scene, enemy.x, enemy.y, enemy.color);
      DamageNumber.show(this.scene, enemy.x, enemy.y, dmg, { crit: isCrit });
    }

    SFX.play(this.scene, 'sfx_hit');

    if (isCrit || targets.length >= 2) {
      FX.shake(this.scene, { intensity: isCrit ? 0.006 : 0.004 });
    }
  }

  destroy() {
    this.sprite.destroy();
    const idx = this.scene.projectiles.indexOf(this);
    if (idx !== -1) this.scene.projectiles.splice(idx, 1);
  }
}
