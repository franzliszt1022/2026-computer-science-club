const ENEMY_TYPES = {
  basic: {
    name: '기본', speed: 90, healthBase: 10, healthPerWave: 4, reward: 5, radius: 12, color: 0xe74c3c,
    desc: '속도와 체력이 무난한 표준 몬스터',
  },
  swarm: {
    name: '스웜', speed: 160, healthBase: 6, healthPerWave: 2, reward: 3, radius: 8, color: 0xf1c40f,
    desc: '체력은 약하지만 아주 빠르게 움직이는 잡몹',
  },
  tank: {
    name: '탱커', speed: 55, healthBase: 40, healthPerWave: 8, reward: 12, radius: 18, color: 0x8e44ad,
    desc: '이동은 느리지만 체력이 매우 높음',
  },
  armored: {
    name: '중장갑', speed: 70, healthBase: 22, healthPerWave: 5, reward: 9, radius: 14, color: 0x7f8c8d, armor: 3,
    desc: '방어력이 있어 타워 공격력을 일부 무시함 (최소 1 데미지는 항상 들어감)',
  },
  boss: {
    name: '보스', speed: 40, healthBase: 300, healthPerWave: 0, reward: 100, radius: 30, color: 0x2c3e50,
    desc: '웨이브 최종 등장, 압도적인 체력의 보스',
  },
};

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
    this.armor = config.armor || 0;

    this.t = 0; // 0~1 경로 진행률
    this.alive = true;
    this.isBoss = false;
    this.slowFactor = 1;
    this.slowTimer = 0;

    const start = this.path.getPoint(0);
    this.sprite = scene.add.circle(start.x, start.y, this.radius, this.color);
    this.sprite.setStrokeStyle(2, 0x000000, 0.35);

    this.healthBarBg = scene.add.rectangle(start.x, start.y - this.radius - 10, 24, 4, 0x1a1a1a);
    this.healthBar = scene.add.rectangle(start.x, start.y - this.radius - 10, 24, 4, 0x2ecc71);
  }

  get x() { return this.sprite.x; }
  get y() { return this.sprite.y; }

  update(delta) {
    if (!this.alive) return;

    if (this.slowTimer > 0) {
      this.slowTimer -= delta;
      if (this.slowTimer <= 0) {
        this.slowFactor = 1;
        this.sprite.setFillStyle(this.color);
      }
    }

    const effectiveSpeed = this.speed * this.slowFactor;
    this.t += (effectiveSpeed * delta / 1000) / this.path.getLength();

    if (this.t >= 1) {
      this.reachEnd();
      return;
    }

    const point = this.path.getPoint(this.t);
    this.sprite.setPosition(point.x, point.y);
    this.healthBarBg.setPosition(point.x, point.y - this.radius - 10);
    this.healthBar.setPosition(point.x, point.y - this.radius - 10);
  }

  applySlow(factor, duration) {
    this.slowFactor = Math.min(this.slowFactor, factor);
    this.slowTimer = Math.max(this.slowTimer, duration);
    this.sprite.setFillStyle(0x66e0e8);
  }

  takeDamage(amount) {
    const dmg = Math.max(amount - this.armor, 1);
    this.health -= dmg;
    const pct = Math.max(this.health / this.maxHealth, 0);
    this.healthBar.width = 24 * pct;

    if (this.health <= 0) {
      this.die();
    }
  }

  die() {
    if (!this.alive) return;
    this.alive = false;

    FX.killBurst(this.scene, this.x, this.y, this.color, { big: this.isBoss });
    if (this.isBoss) FX.shake(this.scene, { intensity: 0.01, duration: 400, force: true });
    SFX.play(this.scene, 'sfx_kill');

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
