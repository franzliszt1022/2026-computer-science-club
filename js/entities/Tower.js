const TOWER_TYPES = {
  basic: { name: '기본', cost: 20, range: 130, fireRate: 1.2, damage: 5, color: 0x3498db },
  splash: { name: '스플래시', cost: 35, range: 110, fireRate: 0.8, damage: 4, splashRadius: 50, color: 0xe67e22 },
  rapid: { name: '속사', cost: 30, range: 100, fireRate: 3, damage: 2, color: 0x2ecc71 },
};

class Tower {
  constructor(scene, x, y, config) {
    this.scene = scene;
    this.range = config.range;
    this.fireRate = config.fireRate; // 초당 발사 횟수
    this.damage = config.damage;
    this.splashRadius = config.splashRadius || 0;
    this.color = config.color || 0x3498db;

    this.cooldown = 0;

    this.rangeCircle = scene.add.circle(x, y, this.range, this.color, 0.08);

    this.shadow = scene.add.circle(x + 2, y + 3, 16, 0x000000, 0.35);
    this.shadow.setScale(0);

    this.sprite = scene.add.circle(x, y, 16, this.color);
    this.sprite.setStrokeStyle(2, 0xffffff, 0.5);
    this.sprite.setScale(0);
    scene.tweens.add({
      targets: [this.sprite, this.shadow],
      scale: 1,
      duration: 200,
      ease: 'Back.Out',
    });
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
    new Projectile(this.scene, this.x, this.y, target, this.damage, this.splashRadius);
  }
}
