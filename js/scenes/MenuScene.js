class MenuScene extends Phaser.Scene {
  constructor() {
    super('MenuScene');
  }

  create() {
    const { width, height } = this.scale;

    drawBackground(this);

    const glow = this.add.circle(width / 2, height / 2 - 130, 220, THEME.accent, 0.08);
    this.tweens.add({
      targets: glow,
      scale: 1.15,
      alpha: 0.14,
      duration: 1400,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    const title = this.add.text(width / 2, height / 2 - 130, 'DEFENSE GAME', {
      fontSize: '72px',
      color: THEME.text,
      fontStyle: 'bold',
    }).setOrigin(0.5);
    title.setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.add.rectangle(width / 2, height / 2 - 60, 240, 4, THEME.accent, 0.8);

    const promptText = this.add.text(width / 2, height / 2 + 20, '난이도를 선택하세요', {
      fontSize: '28px',
      color: '#ffd23f',
    }).setOrigin(0.5);

    this.tweens.add({
      targets: promptText,
      alpha: 0.3,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    this.buildDifficultyButtons(width / 2, height / 2 + 130);
    this.buildFullscreenButton(width, height);
  }

  buildDifficultyButtons(centerX, y) {
    const difficulties = ['easy', 'normal', 'hard'];

    difficulties.forEach((key, i) => {
      const preset = DIFFICULTY_PRESETS[key];
      const bx = centerX + (i - 1) * 240;

      this.add.rectangle(bx + 4, y + 4, 220, 80, 0x000000, 0.3).setOrigin(0.5);

      const btn = this.add.rectangle(bx, y, 220, 80, preset.color, 0.85).setOrigin(0.5);
      btn.setStrokeStyle(1, 0xffffff, 0.3);
      btn.setInteractive({ useHandCursor: true });

      this.add.text(bx, y, preset.label, {
        fontSize: '30px', color: '#ffffff', fontStyle: 'bold',
      }).setOrigin(0.5);

      btn.on('pointerdown', () => {
        this.scene.start('GameScene', { difficulty: key });
      });
    });
  }

  buildFullscreenButton(width, height) {
    if (!this.sys.game.device.fullscreen.available) return;

    const bx = width - 110;
    const by = 50;
    const btn = this.add.rectangle(bx, by, 180, 56, THEME.panel, 0.85).setOrigin(0.5);
    btn.setStrokeStyle(1, 0xffffff, 0.3);
    btn.setInteractive({ useHandCursor: true });

    const label = this.add.text(bx, by, this.scale.isFullscreen ? '창 모드' : '전체화면', {
      fontSize: '20px', color: '#ffffff',
    }).setOrigin(0.5);

    btn.on('pointerdown', () => {
      this.scale.toggleFullscreen();
    });

    // 전체화면 전환 시점에 텍스트 갱신을 바로 시도하면 렌더 컨텍스트가 아직
    // 전환 중이라 Phaser 내부에서 간헐적으로 예외가 나서(brower fullscreen
    // transition race) 한 틱 미뤄서 갱신
    const onEnter = () => this.time.delayedCall(0, () => label.active && label.setText('창 모드'));
    const onLeave = () => this.time.delayedCall(0, () => label.active && label.setText('전체화면'));
    this.scale.on('enterfullscreen', onEnter);
    this.scale.on('leavefullscreen', onLeave);
    this.events.once('shutdown', () => {
      this.scale.off('enterfullscreen', onEnter);
      this.scale.off('leavefullscreen', onLeave);
    });
  }
}
