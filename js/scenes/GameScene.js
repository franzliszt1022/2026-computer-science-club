class GameScene extends Phaser.Scene {
  constructor() {
    super('GameScene');
  }

  create() {
    this.gold = 100;
    this.lives = 20;
    this.wave = 0;
    this.enemies = [];
    this.towers = [];
    this.projectiles = [];

    this.enemiesToSpawn = 0;
    this.spawnTimer = 0;
    this.spawnInterval = 700;
    this.waveActive = false;
    this.waveCooldown = 2000;

    this.towerCost = 20;

    this.buildPath();
    this.drawPath();
    this.buildUI();
  }

  buildPath() {
    this.path = new Phaser.Curves.Path(40, 160);
    this.path.lineTo(200, 160);
    this.path.lineTo(200, 320);
    this.path.lineTo(500, 320);
    this.path.lineTo(500, 120);
    this.path.lineTo(760, 120);
    this.path.lineTo(760, 480);
    this.path.lineTo(920, 480);
  }

  drawPath() {
    const graphics = this.add.graphics();
    graphics.lineStyle(36, 0x555b6e, 1);
    this.path.draw(graphics, 64);
  }

  buildUI() {
    this.add.rectangle(0, 0, 260, 100, 0x000000, 0.4).setOrigin(0, 0);
    this.goldText = this.add.text(16, 12, '', { fontSize: '20px', color: '#ffd23f' });
    this.livesText = this.add.text(16, 40, '', { fontSize: '20px', color: '#ff6b6b' });
    this.waveText = this.add.text(16, 68, '', { fontSize: '20px', color: '#ffffff' });
    this.hintText = this.add.text(16, 600, '빈 곳을 클릭하면 타워 설치 (20 골드)', { fontSize: '16px', color: '#aaaaaa' });
    this.updateUI();

    this.input.on('pointerdown', (pointer) => this.tryPlaceTower(pointer.x, pointer.y));

    this.time.delayedCall(this.waveCooldown, () => this.startWave());
  }

  updateUI() {
    this.goldText.setText(`Gold: ${this.gold}`);
    this.livesText.setText(`Lives: ${this.lives}`);
    this.waveText.setText(`Wave: ${this.wave}`);
  }

  startWave() {
    this.wave += 1;
    this.enemiesToSpawn = 5 + (this.wave - 1) * 2;
    this.waveActive = true;
    this.spawnTimer = 0;
    this.updateUI();
  }

  spawnEnemy() {
    const bonusHealth = (this.wave - 1) * 4;
    const enemy = new Enemy(this, this.path, {
      speed: 90,
      health: 10 + bonusHealth,
      reward: 5,
      color: 0xe74c3c,
      radius: 12,
    });
    this.enemies.push(enemy);
  }

  tryPlaceTower(x, y) {
    if (this.gold < this.towerCost) return;

    for (const tower of this.towers) {
      if (Phaser.Math.Distance.Between(tower.x, tower.y, x, y) < 32) return;
    }

    this.gold -= this.towerCost;
    const tower = new Tower(this, x, y, {
      range: 130,
      fireRate: 1.2,
      damage: 5,
      color: 0x3498db,
    });
    this.towers.push(tower);
    this.updateUI();
  }

  onEnemyKilled(enemy) {
    this.gold += enemy.reward;
    this.enemies.splice(this.enemies.indexOf(enemy), 1);
    this.updateUI();
  }

  onEnemyReachedEnd(enemy) {
    this.lives -= 1;
    this.enemies.splice(this.enemies.indexOf(enemy), 1);
    this.updateUI();

    if (this.lives <= 0) {
      this.scene.start('GameOverScene', { won: false, wave: this.wave });
    }
  }

  update(time, delta) {
    if (this.lives <= 0) return;

    if (this.waveActive) {
      this.spawnTimer -= delta;
      if (this.spawnTimer <= 0 && this.enemiesToSpawn > 0) {
        this.spawnEnemy();
        this.enemiesToSpawn -= 1;
        this.spawnTimer = this.spawnInterval;
      }

      if (this.enemiesToSpawn <= 0 && this.enemies.length === 0) {
        this.waveActive = false;

        if (this.wave >= 8) {
          this.scene.start('GameOverScene', { won: true, wave: this.wave });
          return;
        }
        this.time.delayedCall(this.waveCooldown, () => this.startWave());
      }
    }

    for (const enemy of this.enemies) enemy.update(delta);
    for (const tower of this.towers) tower.update(delta, this.enemies);
    for (const projectile of [...this.projectiles]) projectile.update(delta);
  }
}
