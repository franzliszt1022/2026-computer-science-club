class Enemy {
  constructor(scene, path, config) {
    this.scene = scene;
    this.path = path;
    this.speed = config.speed;
    this.maxHealth = config.health;
    this.health = config.health;
    this.reward = config.reward;
    this.radius = config.radius || 12;
    this.color = config.color || 0xe74c3c;

    this.t = 0; // 0~1 경로 진행률
    this.alive = true;

    const start = this.path.getPoint(0);
    this.sprite = scene.add.circle(start.x, start.y, this.radius, this.color);

    this.healthBarBg = scene.add.rectangle(start.x, start.y - this.radius - 10, 24, 4, 0x333333);
    this.healthBar = scene.add.rectangle(start.x, start.y - this.radius - 10, 24, 4, 0x2ecc71);
  }

  get x() { return this.sprite.x; }
  get y() { return this.sprite.y; }

  update(delta) {
    if (!this.alive) return;

    this.t += (this.speed * delta / 1000) / this.path.getLength();

    if (this.t >= 1) {
      this.reachEnd();
      return;
    }

    const point = this.path.getPoint(this.t);
    this.sprite.setPosition(point.x, point.y);
    this.healthBarBg.setPosition(point.x, point.y - this.radius - 10);
    this.healthBar.setPosition(point.x, point.y - this.radius - 10);
  }

  takeDamage(amount) {
    this.health -= amount;
    const pct = Math.max(this.health / this.maxHealth, 0);
    this.healthBar.width = 24 * pct;

    if (this.health <= 0) {
      this.die();
    }
  }

  die() {
    if (!this.alive) return;
    this.alive = false;
    this.scene.onEnemyKilled(this);
    this.destroy();
  }

  reachEnd() {
    if (!this.alive) return;
    this.alive = false;
    this.scene.onEnemyReachedEnd(this);
    this.destroy();
  }

  destroy() {
    this.sprite.destroy();
    this.healthBarBg.destroy();
    this.healthBar.destroy();
  }
}
