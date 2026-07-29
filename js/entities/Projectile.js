class Projectile {
  constructor(scene, x, y, target, damage) {
    this.scene = scene;
    this.target = target;
    this.damage = damage;
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
      this.target.takeDamage(this.damage);
      this.destroy();
      return;
    }

    const angle = Phaser.Math.Angle.Between(this.sprite.x, this.sprite.y, this.target.x, this.target.y);
    const moveDist = this.speed * delta / 1000;
    this.sprite.x += Math.cos(angle) * moveDist;
    this.sprite.y += Math.sin(angle) * moveDist;
  }

  destroy() {
    this.sprite.destroy();
    const idx = this.scene.projectiles.indexOf(this);
    if (idx !== -1) this.scene.projectiles.splice(idx, 1);
  }
}
