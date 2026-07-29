class Projectile {
  constructor(scene, x, y, target, damage, splashRadius = 0) {
    this.scene = scene;
    this.target = target;
    this.damage = damage;
    this.splashRadius = splashRadius;
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
    if (this.splashRadius > 0) {
      for (const enemy of this.scene.enemies) {
        if (!enemy.alive) continue;
        const dist = Phaser.Math.Distance.Between(this.sprite.x, this.sprite.y, enemy.x, enemy.y);
        if (dist <= this.splashRadius) enemy.takeDamage(this.damage);
      }
    } else {
      this.target.takeDamage(this.damage);
    }
  }

  destroy() {
    this.sprite.destroy();
    const idx = this.scene.projectiles.indexOf(this);
    if (idx !== -1) this.scene.projectiles.splice(idx, 1);
  }
}
