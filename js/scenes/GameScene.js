class GameScene extends Phaser.Scene {
  constructor() {
    super('GameScene');
  }

  init(data) {
    this.difficulty = (data && data.difficulty) || 'hard';
  }

  create() {
    const preset = DIFFICULTY_PRESETS[this.difficulty];

    this.gold = preset.gold;
    this.lives = preset.lives;
    this.enemyHealthMult = preset.healthMult;
    this.scoreMult = preset.scoreMult;
    this.difficultyLabel = preset.label;
    this.wave = 0;
    this.kills = 0;
    this.totalWaves = 10;
    this.enemies = [];
    this.towers = [];
    this.projectiles = [];

    this.spawnQueue = [];
    this.spawnTimer = 0;
    this.spawnInterval = 700;
    this.waveActive = false;
    this.waveCooldown = 2000;

    this.selectedTowerType = 'basic';
    this.vignetteActive = false;
    this.tutorialDismissed = false;

    SFX.init(this);

    drawBackground(this);
    this.buildPath();
    this.drawPath();
    this.buildUI();
    this.showTutorialHint();
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
    graphics.lineStyle(42, THEME.roadEdge, 1);
    this.path.draw(graphics, 64);
    graphics.lineStyle(32, THEME.road, 1);
    this.path.draw(graphics, 64);
  }

  buildUI() {
    const topPanel = this.add.rectangle(0, 0, 260, 100, THEME.panel, 0.7).setOrigin(0, 0);
    topPanel.setStrokeStyle(1, THEME.panelBorder, 0.8);
    this.goldText = this.add.text(16, 12, '', { fontSize: '20px', color: '#ffd23f' });
    this.livesText = this.add.text(16, 40, '', { fontSize: '20px', color: '#ff6b6b' });
    this.waveText = this.add.text(16, 68, '', { fontSize: '16px', color: THEME.text });

    const bottomPanel = this.add.rectangle(0, 570, 960, 70, THEME.panel, 0.85).setOrigin(0, 0);
    bottomPanel.setStrokeStyle(1, THEME.panelBorder, 0.8);
    this.hintText = this.add.text(16, 578, '타워를 선택하고 배치할 위치를 클릭하세요', { fontSize: '14px', color: THEME.textDim });

    const { width, height } = this.scale;
    this.vignette = this.add.graphics();
    this.vignette.lineStyle(36, THEME.danger, 1);
    this.vignette.strokeRect(18, 18, width - 36, height - 36);
    this.vignette.setDepth(90);
    this.vignette.setAlpha(0);

    this.buildTowerButtons();
    this.updateUI();

    this.input.on('pointerdown', (pointer) => this.tryPlaceTower(pointer.x, pointer.y));

    this.scheduleNextWave();
  }

  buildTowerButtons() {
    this.towerButtons = {};
    const types = Object.keys(TOWER_TYPES);

    types.forEach((type, i) => {
      const def = TOWER_TYPES[type];
      const bx = 320 + i * 150;
      const by = 610;

      this.add.rectangle(bx + 3, by + 3, 130, 44, 0x000000, 0.3).setOrigin(0.5);

      const btnBg = this.add.rectangle(bx, by, 130, 44, def.color, 0.85).setOrigin(0.5);
      btnBg.setStrokeStyle(1, 0xffffff, 0.25);
      btnBg.setInteractive({ useHandCursor: true });
      this.add.text(bx, by, `${def.name}\n${def.cost}G`, {
        fontSize: '13px', color: '#ffffff', align: 'center',
      }).setOrigin(0.5);

      btnBg.on('pointerdown', (pointer, x, y, event) => {
        event.stopPropagation();
        this.selectedTowerType = type;
        this.highlightTowerButtons();
        this.tweens.add({ targets: btnBg, scale: 0.9, duration: 60, yoyo: true });
      });

      this.towerButtons[type] = btnBg;
    });

    this.highlightTowerButtons();
  }

  highlightTowerButtons() {
    for (const type in this.towerButtons) {
      const btn = this.towerButtons[type];
      if (type === this.selectedTowerType) {
        btn.setStrokeStyle(3, 0xffffff, 1);
      } else {
        btn.setStrokeStyle(1, 0xffffff, 0.25);
      }
    }
  }

  showTutorialHint() {
    const { width } = this.scale;
    const bg = this.add.rectangle(width / 2, 300, 520, 90, 0x000000, 0.65).setOrigin(0.5).setDepth(80);
    const text = this.add.text(width / 2, 300,
      '① 아래 타워를 선택하세요\n② 필드를 클릭해 설치하세요\n③ 적을 막아내세요!', {
        fontSize: '16px', color: THEME.text, align: 'center', lineSpacing: 6,
      }).setOrigin(0.5).setDepth(81);

    bg.setInteractive({ useHandCursor: true });
    bg.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      this.dismissTutorial();
    });

    this.tutorialElements = [bg, text];
    this.time.delayedCall(4000, () => this.dismissTutorial());
  }

  dismissTutorial() {
    if (this.tutorialDismissed) return;
    this.tutorialDismissed = true;
    this.tweens.add({
      targets: this.tutorialElements,
      alpha: 0,
      duration: 300,
      onComplete: () => this.tutorialElements.forEach((el) => el.destroy()),
    });
  }

  updateUI() {
    this.goldText.setText(`Gold: ${this.gold}`);
    this.livesText.setText(`Lives: ${this.lives}`);
    this.waveText.setText(`Wave: ${this.wave} / ${this.totalWaves}  (${this.difficultyLabel})`);
  }

  scheduleNextWave() {
    this.time.delayedCall(this.waveCooldown, () => this.startWave());
  }

  startWave() {
    this.wave += 1;
    this.spawnQueue = this.buildWaveQueue(this.wave);
    this.waveActive = true;
    this.spawnTimer = 0;
    this.updateUI();
  }

  showWaveClearBanner(wave) {
    const { width, height } = this.scale;
    const bonus = wave * 5;
    this.gold += bonus;
    this.updateUI();
    SFX.play(this, 'sfx_wave_clear');

    const banner = this.add.text(width / 2, height / 2 - 100, `WAVE ${wave} CLEAR!  +${bonus}G`, {
      fontSize: '28px', color: '#ffd23f', fontStyle: 'bold',
    }).setOrigin(0.5).setDepth(70).setScale(0);

    this.tweens.add({ targets: banner, scale: 1, duration: 250, ease: 'Back.Out' });
    this.time.delayedCall(1200, () => {
      this.tweens.add({
        targets: banner, alpha: 0, duration: 300, onComplete: () => banner.destroy(),
      });
    });
  }

  buildWaveQueue(wave) {
    const queue = [];

    if (wave >= this.totalWaves) {
      for (let i = 0; i < 3; i++) queue.push('tank');
      queue.push('boss');
      return queue;
    }

    const basicCount = 4 + wave;
    for (let i = 0; i < basicCount; i++) queue.push('basic');

    if (wave >= 3) {
      const swarmCount = 3 + (wave - 3) * 2;
      for (let i = 0; i < swarmCount; i++) queue.push('swarm');
    }

    if (wave >= 5) {
      const tankCount = 2 + (wave - 5);
      for (let i = 0; i < tankCount; i++) queue.push('tank');
    }

    return this.shuffle(queue);
  }

  shuffle(arr) {
    const a = [...arr];
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  spawnEnemy(type) {
    const def = ENEMY_TYPES[type];
    const bonusHealth = (this.wave - 1) * def.healthPerWave;
    const health = Math.round((def.healthBase + bonusHealth) * this.enemyHealthMult);
    const enemy = new Enemy(this, this.path, {
      speed: def.speed,
      health,
      reward: def.reward,
      color: def.color,
      radius: def.radius,
    });
    enemy.isBoss = type === 'boss';
    this.enemies.push(enemy);
  }

  tryPlaceTower(x, y) {
    if (y > 570) return; // 하단 UI 영역

    const def = TOWER_TYPES[this.selectedTowerType];
    if (this.gold < def.cost) return;

    for (const tower of this.towers) {
      if (Phaser.Math.Distance.Between(tower.x, tower.y, x, y) < 32) return;
    }

    this.gold -= def.cost;
    const tower = new Tower(this, x, y, def);
    this.towers.push(tower);
    this.updateUI();

    SFX.play(this, 'sfx_place');
    this.dismissTutorial();
  }

  onEnemyKilled(enemy) {
    this.gold += enemy.reward;
    this.kills += 1;
    this.enemies.splice(this.enemies.indexOf(enemy), 1);
    this.updateUI();
  }

  onEnemyReachedEnd(enemy) {
    this.lives -= 1;
    this.enemies.splice(this.enemies.indexOf(enemy), 1);
    this.updateUI();

    if (this.lives === 1 && !this.vignetteActive) {
      this.vignetteActive = true;
      this.tweens.add({
        targets: this.vignette, alpha: { from: 0, to: 0.5 }, duration: 500, yoyo: true, repeat: -1,
      });
    }

    if (this.lives <= 0) {
      SFX.play(this, 'sfx_gameover');
      this.scene.start('GameOverScene', this.buildResultData(false));
    }
  }

  buildResultData(won) {
    const rawScore = this.wave * 100 + this.kills * 5 + this.gold;
    const score = Math.round(rawScore * this.scoreMult);
    return {
      won, wave: this.wave, kills: this.kills, gold: this.gold, score,
      difficulty: this.difficulty, difficultyLabel: this.difficultyLabel,
    };
  }

  update(time, delta) {
    if (this.lives <= 0) return;

    if (this.waveActive) {
      this.spawnTimer -= delta;
      if (this.spawnTimer <= 0 && this.spawnQueue.length > 0) {
        const type = this.spawnQueue.shift();
        this.spawnEnemy(type);
        this.spawnTimer = type === 'swarm' ? 350 : this.spawnInterval;
      }

      if (this.spawnQueue.length === 0 && this.enemies.length === 0) {
        this.waveActive = false;

        if (this.wave >= this.totalWaves) {
          SFX.play(this, 'sfx_victory');
          this.scene.start('GameOverScene', this.buildResultData(true));
          return;
        }
        this.showWaveClearBanner(this.wave);
        this.scheduleNextWave();
      }
    }

    for (const enemy of this.enemies) enemy.update(delta);
    for (const tower of this.towers) tower.update(delta, this.enemies);
    for (const projectile of [...this.projectiles]) projectile.update(delta);
  }
}
