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
    this.enemySpeedMult = preset.speedMult || 1;
    this.scoreMult = preset.scoreMult;
    this.difficultyLabel = preset.label;
    this.wave = 0;
    this.kills = 0;
    this.totalWaves = 20;
    this.enemies = [];
    this.towers = [];
    this.projectiles = [];

    this.spawnQueue = [];
    this.spawnTimer = 0;
    this.spawnInterval = 700;
    this.waveActive = false;

    this.selectedTowerType = 'basic';
    this.vignetteActive = false;
    this.tutorialDismissed = false;
    this.gameSpeed = 1; // 0.5 / 1 / 2 — 핵심 시뮬레이션(적 이동, 타워 쿨다운, 투사체, 스폰 타이밍)에만 적용, 트윈/딜레이콜/사운드는 실시간 유지

    // UI 패널/경로 모두 이 타일 단위를 기준으로 배치 — 그리드와 시각적으로 정확히 맞물리게
    this.tileSize = 60;
    this.panelCols = 8;
    this.panelRows = 3;
    this.bottomRows = 3;

    SFX.init(this);

    drawBackground(this);
    this.buildPath();
    this.drawPath();
    this.buildUI();
    this.showTutorialHint();
  }

  buildPath() {
    const t = this.tileSize;
    const toPixel = ([col, row]) => [col * t + t / 2, row * t + t / 2];

    // 타일 좌표 기준 경유지 — 코너를 늘려 초크포인트/긴 직선 구간을 섞음
    this.pathWaypoints = [
      [1, 4], [8, 4], [8, 8], [14, 8], [14, 3],
      [20, 3], [20, 11], [26, 11], [26, 5], [30, 5],
    ];

    const [sx, sy] = toPixel(this.pathWaypoints[0]);
    this.path = new Phaser.Curves.Path(sx, sy);
    for (let i = 1; i < this.pathWaypoints.length; i++) {
      const [px, py] = toPixel(this.pathWaypoints[i]);
      this.path.lineTo(px, py);
    }

    // 경로가 실제로 지나가는 타일 목록 (그리드 차단에 그대로 사용 — 별도 샘플링 불필요)
    this.pathTiles = new Set();
    for (let i = 0; i < this.pathWaypoints.length - 1; i++) {
      let [c, r] = this.pathWaypoints[i];
      const [c2, r2] = this.pathWaypoints[i + 1];
      const dc = Math.sign(c2 - c);
      const dr = Math.sign(r2 - r);
      this.pathTiles.add(`${c},${r}`);
      while (c !== c2 || r !== r2) {
        c += dc;
        r += dr;
        this.pathTiles.add(`${c},${r}`);
      }
    }
  }

  drawPath() {
    const t = this.tileSize;
    const graphics = this.add.graphics();
    graphics.lineStyle(t, THEME.roadEdge, 1);
    this.path.draw(graphics, 64);
    graphics.lineStyle(t - 10, THEME.road, 1);
    this.path.draw(graphics, 64);
  }

  buildUI() {
    const panelW = this.panelCols * this.tileSize;
    const panelH = this.panelRows * this.tileSize;
    const topPanel = this.add.rectangle(0, 0, panelW, panelH, THEME.panel, 0.7).setOrigin(0, 0);
    topPanel.setStrokeStyle(1, THEME.panelBorder, 0.8);
    this.goldText = this.add.text(28, 20, '', { fontSize: '32px', color: '#ffd23f' });
    this.livesText = this.add.text(28, 68, '', { fontSize: '32px', color: '#ff6b6b' });
    this.waveText = this.add.text(28, 116, '', { fontSize: '24px', color: THEME.text });

    const { width, height } = this.scale;
    this.fieldBottomY = height - this.bottomRows * this.tileSize;

    const bottomPanel = this.add.rectangle(0, this.fieldBottomY, width, this.bottomRows * this.tileSize, THEME.panel, 0.85).setOrigin(0, 0);
    bottomPanel.setStrokeStyle(1, THEME.panelBorder, 0.8);
    this.hintText = this.add.text(28, this.fieldBottomY + 14, '타워를 선택하고 배치할 위치를 클릭하세요', { fontSize: '20px', color: THEME.textDim });

    this.vignette = this.add.graphics();
    this.vignette.lineStyle(60, THEME.danger, 1);
    this.vignette.strokeRect(30, 30, width - 60, height - 60);
    this.vignette.setDepth(90);
    this.vignette.setAlpha(0);

    this.buildGrid();
    this.buildTowerButtons();
    this.buildSpeedButtons();
    this.buildPlacementPreview();
    this.updateUI();

    this.input.on('pointerdown', (pointer) => this.onFieldClick(pointer.x, pointer.y));
    this.input.on('pointermove', (pointer) => this.updatePlacementPreview(pointer.x, pointer.y));

    this.enterPrepPhase();
  }

  buildGrid() {
    this.blockedTiles = new Set();
    this.towersByTile = new Map();

    const { width, height } = this.scale;
    const cols = Math.ceil(width / this.tileSize);
    const rows = Math.ceil(height / this.tileSize);

    // 좌상단 정보 패널 영역 (buildUI의 panelCols/panelRows와 동일한 값)
    for (let c = 0; c < this.panelCols; c++) {
      for (let r = 0; r < this.panelRows; r++) this.blockedTiles.add(`${c},${r}`);
    }

    // 하단 UI 바 영역
    const bottomRowStart = rows - this.bottomRows;
    for (let r = bottomRowStart; r < rows; r++) {
      for (let c = 0; c < cols; c++) this.blockedTiles.add(`${c},${r}`);
    }

    // 경로 타일 — buildPath()에서 이미 정확히 계산해둔 목록을 그대로 사용
    for (const key of this.pathTiles) this.blockedTiles.add(key);
  }

  buildPlacementPreview() {
    this.previewRange = this.add.circle(0, 0, 10, 0xffffff, 0.08).setVisible(false).setDepth(40);
    this.previewTower = this.add.circle(0, 0, 16, 0xffffff, 0.45).setVisible(false).setDepth(41);
    this.previewTile = this.add.rectangle(0, 0, this.tileSize, this.tileSize, 0xffffff, 0)
      .setStrokeStyle(3, THEME.success, 0.9).setVisible(false).setDepth(42);
  }

  updatePlacementPreview(x, y) {
    this.lastPointerX = x;
    this.lastPointerY = y;

    const col = Math.floor(x / this.tileSize);
    const row = Math.floor(y / this.tileSize);
    const key = `${col},${row}`;
    const cx = col * this.tileSize + this.tileSize / 2;
    const cy = row * this.tileSize + this.tileSize / 2;

    const def = TOWER_TYPES[this.selectedTowerType];
    const valid = !this.blockedTiles.has(key) && !this.towersByTile.has(key) && this.gold >= def.cost;

    this.previewRange.setPosition(cx, cy).setRadius(def.range).setFillStyle(def.color, 0.08).setVisible(true);
    this.previewTower.setPosition(cx, cy).setFillStyle(def.color, 0.45).setVisible(true);
    this.previewTile.setPosition(cx, cy)
      .setStrokeStyle(3, valid ? THEME.success : THEME.danger, 0.9).setVisible(true);
  }

  hidePlacementPreview() {
    if (this.previewRange) this.previewRange.setVisible(false);
    if (this.previewTower) this.previewTower.setVisible(false);
    if (this.previewTile) this.previewTile.setVisible(false);
  }

  selectTower(tower) {
    this.hideTowerInfo();

    const { width } = this.scale;
    const panelW = 280;
    const panelH = 220;
    const px = Phaser.Math.Clamp(tower.x + 40, 10, width - panelW - 10);
    const py = Phaser.Math.Clamp(tower.y - panelH / 2, this.panelRows * this.tileSize + 10, this.fieldBottomY - panelH - 10);

    const def = tower.def;
    const bg = this.add.rectangle(px, py, panelW, panelH, THEME.panel, 0.95).setOrigin(0, 0).setDepth(60);
    bg.setStrokeStyle(2, THEME.accent, 0.9);

    const lines = [
      def.name,
      `공격력: ${def.damage}${def.splashRadius ? ' (범위)' : ''}`,
      `사거리: ${def.range}`,
      `공속: 초당 ${def.fireRate}발`,
      `비용: ${def.cost}G`,
      `HP: ${tower.hp}/${tower.maxHp}`,
    ];
    const text = this.add.text(px + 20, py + 18, lines.join('\n'), {
      fontSize: '19px', color: THEME.text, lineSpacing: 10,
    }).setDepth(61);

    const closeBtn = this.add.text(px + panelW - 34, py + 12, '✕', {
      fontSize: '22px', color: THEME.textDim,
    }).setInteractive({ useHandCursor: true }).setDepth(61);
    closeBtn.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      this.hideTowerInfo();
    });

    this.towerInfoElements = [bg, text, closeBtn];
  }

  hideTowerInfo() {
    if (this.towerInfoElements) {
      this.towerInfoElements.forEach((el) => el.destroy());
      this.towerInfoElements = null;
    }
  }

  buildTowerButtons() {
    this.towerButtons = {};
    const types = Object.keys(TOWER_TYPES);
    const by = this.fieldBottomY + 65;

    types.forEach((type, i) => {
      const def = TOWER_TYPES[type];
      const bx = 640 + i * 280;

      this.add.rectangle(bx + 4, by + 4, 220, 75, 0x000000, 0.3).setOrigin(0.5);

      const btnBg = this.add.rectangle(bx, by, 220, 75, def.color, 0.85).setOrigin(0.5);
      btnBg.setStrokeStyle(1, 0xffffff, 0.25);
      btnBg.setInteractive({ useHandCursor: true });
      this.add.text(bx, by, `${def.name}\n${def.cost}G`, {
        fontSize: '22px', color: '#ffffff', align: 'center',
      }).setOrigin(0.5);

      btnBg.on('pointerdown', (pointer, x, y, event) => {
        event.stopPropagation();
        this.selectedTowerType = type;
        this.highlightTowerButtons();
        this.tweens.add({ targets: btnBg, scale: 0.9, duration: 60, yoyo: true });
        if (this.lastPointerX != null) this.updatePlacementPreview(this.lastPointerX, this.lastPointerY);
      });

      this.towerButtons[type] = btnBg;
    });

    this.highlightTowerButtons();
  }

  buildSpeedButtons() {
    this.speedButtons = {};
    const speeds = [0.5, 1, 2];
    const { width } = this.scale;

    speeds.forEach((speed, i) => {
      const bx = width - 190 + i * 62;
      const by = 36;

      const btnBg = this.add.rectangle(bx, by, 56, 44, THEME.panel, 0.85).setOrigin(0.5);
      btnBg.setStrokeStyle(1, 0xffffff, 0.25);
      btnBg.setInteractive({ useHandCursor: true });
      this.add.text(bx, by, `${speed}x`, {
        fontSize: '20px', color: '#ffffff',
      }).setOrigin(0.5);

      btnBg.on('pointerdown', (pointer, x, y, event) => {
        event.stopPropagation();
        this.gameSpeed = speed;
        this.highlightSpeedButtons();
      });

      this.speedButtons[speed] = btnBg;
    });

    this.highlightSpeedButtons();
  }

  highlightSpeedButtons() {
    for (const speed in this.speedButtons) {
      const btn = this.speedButtons[speed];
      if (Number(speed) === this.gameSpeed) {
        btn.setStrokeStyle(2, THEME.accent, 1);
        btn.setFillStyle(THEME.panel, 1);
      } else {
        btn.setStrokeStyle(1, 0xffffff, 0.25);
        btn.setFillStyle(THEME.panel, 0.85);
      }
    }
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
    const { width, height } = this.scale;
    const cy = height / 2 - 60;
    const bg = this.add.rectangle(width / 2, cy, 940, 260, 0x000000, 0.75).setOrigin(0.5).setDepth(80);
    bg.setStrokeStyle(3, THEME.accent, 0.6);
    const text = this.add.text(width / 2, cy - 30,
      '① 아래에서 타워를 선택하세요\n② 필드를 클릭해 설치하세요\n③ 적을 막아내세요!', {
        fontSize: '36px', color: THEME.text, align: 'center', lineSpacing: 20, fontStyle: 'bold',
      }).setOrigin(0.5).setDepth(81);
    const hint = this.add.text(width / 2, cy + 90, '(클릭하면 닫혀요)', {
      fontSize: '20px', color: THEME.textDim,
    }).setOrigin(0.5).setDepth(81);

    bg.setInteractive({ useHandCursor: true });
    bg.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      this.dismissTutorial();
    });

    this.tutorialElements = [bg, text, hint];
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

  enterPrepPhase() {
    this.prepActive = true;
    const { width } = this.scale;
    const by = 750;
    const label = this.wave === 0 ? '게임 시작' : `웨이브 ${this.wave + 1} 시작`;

    const btnBg = this.add.rectangle(width / 2, by, 360, 96, THEME.accent, 0.92).setOrigin(0.5).setDepth(70);
    btnBg.setStrokeStyle(2, 0xffffff, 0.4);
    btnBg.setInteractive({ useHandCursor: true });
    const btnText = this.add.text(width / 2, by, label, {
      fontSize: '34px', color: '#1a1a1a', fontStyle: 'bold',
    }).setOrigin(0.5).setDepth(71);

    this.tweens.add({
      targets: [btnBg, btnText], scale: 1.06, duration: 600, yoyo: true, repeat: -1, ease: 'Sine.easeInOut',
    });

    btnBg.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      this.exitPrepPhase();
      this.startWave();
    });

    this.prepElements = [btnBg, btnText];
  }

  exitPrepPhase() {
    this.prepActive = false;
    if (this.prepElements) {
      this.prepElements.forEach((el) => el.destroy());
      this.prepElements = null;
    }
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
      for (let i = 0; i < 4; i++) queue.push('tank');
      queue.push('boss');
      return queue;
    }

    // 적 "개수" 증가는 wave 10에서 상한을 둠 (그 이후는 체력 스케일링으로만 어려워짐 — 웨이브가 몰려서 정신없어지는 것 방지)
    const rampWave = Math.min(wave, 10);

    const basicCount = 4 + rampWave;
    for (let i = 0; i < basicCount; i++) queue.push('basic');

    if (wave >= 3) {
      const swarmCount = 3 + (rampWave - 3) * 2;
      for (let i = 0; i < swarmCount; i++) queue.push('swarm');
    }

    if (wave >= 5) {
      const tankCount = 2 + (rampWave - 5);
      for (let i = 0; i < tankCount; i++) queue.push('tank');
    }

    if (wave === 10) queue.push('boss'); // 중간 체크포인트 보스

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
      speed: def.speed * this.enemySpeedMult,
      health,
      reward: def.reward,
      color: def.color,
      radius: def.radius,
    });
    enemy.isBoss = type === 'boss';
    this.enemies.push(enemy);
  }

  onFieldClick(x, y) {
    this.hideTowerInfo();

    const col = Math.floor(x / this.tileSize);
    const row = Math.floor(y / this.tileSize);
    const key = `${col},${row}`;

    if (this.towersByTile.has(key)) {
      this.selectTower(this.towersByTile.get(key));
      return;
    }
    if (this.blockedTiles.has(key)) return;

    const def = TOWER_TYPES[this.selectedTowerType];
    if (this.gold < def.cost) return;

    const cx = col * this.tileSize + this.tileSize / 2;
    const cy = row * this.tileSize + this.tileSize / 2;

    this.gold -= def.cost;
    const tower = new Tower(this, cx, cy, def);
    this.towers.push(tower);
    this.towersByTile.set(key, tower);
    this.updateUI();
    this.updatePlacementPreview(x, y);

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

    const simDelta = delta * this.gameSpeed;

    if (this.waveActive) {
      this.spawnTimer -= simDelta;
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
        this.enterPrepPhase();
      }
    }

    for (const enemy of this.enemies) enemy.update(simDelta);
    for (const tower of this.towers) tower.update(simDelta, this.enemies);
    for (const projectile of [...this.projectiles]) projectile.update(simDelta);
  }
}
