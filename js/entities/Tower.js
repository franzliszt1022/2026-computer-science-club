class Tower {
  constructor(scene, x, y, config) {
    this.scene = scene;
    this.range = config.range;
    this.fireRate = config.fireRate; // 초당 발사 횟수
    this.damage = config.damage;
    this.color = config.color || 0x3498db;

    this.cooldown = 0;

    this.sprite = scene.add.circle(x, y, 16, this.color);
    this.sprite.setScale(0);
    scene.tweens.add({
      targets: this.sprite,
      scale: 1,
      duration: 200,
      ease: 'Back.Out',
    });

    this.rangeCircle = scene.add.circle(x, y, this.range, this.color, 0.08);
  }

  get x() { return this.sprite.x; }
  get y() { return this.sprite.y; }

  update(delta, enemies) {
    this.cooldown -= delta;
    if (this.cooldown > 0) return;

    const target = this.findTarget(enemies);
    if (target) {
      this.shoot(target);
      this.cooldown = 1000 / this.fireRate;
    }
  }

  findTarget(enemies) {
    let nearest = null;
    let nearestDist = this.range;

    for (const enemy of enemies) {
      if (!enemy.alive) continue;
      const dist = Phaser.Math.Distance.Between(this.x, this.y, enemy.x, enemy.y);
      if (dist <= nearestDist) {
        nearest = enemy;
        nearestDist = dist;
      }
    }
    return nearest;
  }

  shoot(target) {
    new Projectile(this.scene, this.x, this.y, target, this.damage);
  }
}
