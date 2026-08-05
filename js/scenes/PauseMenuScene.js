class PauseMenuScene extends Phaser.Scene {
  constructor() {
    super('PauseMenuScene');
  }

  create() {
    const { width, height } = this.scale;

    this.add.rectangle(0, 0, width, height, 0x000000, 0.6).setOrigin(0, 0);

    this.add.text(width / 2, height / 2 - 220, '일시정지', {
      fontSize: '56px', color: THEME.text, fontStyle: 'bold',
    }).setOrigin(0.5).setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.mainMenuElements = [
      ...this.buildMenuButton(width / 2, height / 2 - 80, '계속하기', () => this.resumeGame()),
      ...this.buildMenuButton(width / 2, height / 2 + 10, '도감', () => this.openSub('CodexScene')),
      ...this.buildMenuButton(width / 2, height / 2 + 100, '설정', () => this.openSub('SettingsScene')),
      ...this.buildMenuButton(width / 2, height / 2 + 190, '메인 메뉴로', () => this.confirmExit()),
    ];
  }

  buildMenuButton(cx, y, label, onClick) {
    const btn = this.add.rectangle(cx, y, 360, 72, THEME.panel, 0.95).setOrigin(0.5);
    btn.setStrokeStyle(2, THEME.accent, 0.8);
    btn.setInteractive({ useHandCursor: true });
    const text = this.add.text(cx, y, label, { fontSize: '28px', color: '#ffffff', fontStyle: 'bold' }).setOrigin(0.5);

    btn.on('pointerdown', (pointer, x, y2, event) => {
      event.stopPropagation();
      onClick();
    });

    return [btn, text];
  }

  resumeGame() {
    this.scene.stop();
    this.scene.resume('GameScene');
  }

  openSub(sceneKey) {
    this.scene.start(sceneKey, { returnTo: 'PauseMenuScene' });
  }

  confirmExit() {
    const { width, height } = this.scale;
    const elements = [];
    this.mainMenuElements.forEach((el) => el.setVisible(false));

    const bg = this.add.rectangle(width / 2, height / 2, 560, 220, 0x000000, 0.95).setOrigin(0.5).setDepth(50);
    bg.setStrokeStyle(2, THEME.danger, 0.9);
    elements.push(bg);

    elements.push(this.add.text(width / 2, height / 2 - 40, '진행 중인 게임을 포기하고\n메인 메뉴로 나가시겠어요?', {
      fontSize: '22px', color: THEME.text, align: 'center', lineSpacing: 8,
    }).setOrigin(0.5).setDepth(51));

    const yesBtn = this.add.rectangle(width / 2 - 100, height / 2 + 60, 160, 56, THEME.danger, 0.9).setOrigin(0.5).setDepth(51);
    yesBtn.setInteractive({ useHandCursor: true });
    elements.push(yesBtn);
    elements.push(this.add.text(width / 2 - 100, height / 2 + 60, '나가기', {
      fontSize: '22px', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5).setDepth(52));

    const noBtn = this.add.rectangle(width / 2 + 100, height / 2 + 60, 160, 56, THEME.panel, 0.9).setOrigin(0.5).setDepth(51);
    noBtn.setStrokeStyle(1, 0xffffff, 0.3);
    noBtn.setInteractive({ useHandCursor: true });
    elements.push(noBtn);
    elements.push(this.add.text(width / 2 + 100, height / 2 + 60, '취소', {
      fontSize: '22px', color: '#ffffff',
    }).setOrigin(0.5).setDepth(52));

    yesBtn.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      this.scene.stop('GameScene');
      this.scene.stop();
      this.scene.start('MenuScene');
    });

    noBtn.on('pointerdown', (pointer, x, y, event) => {
      event.stopPropagation();
      elements.forEach((el) => el.destroy());
      this.mainMenuElements.forEach((el) => el.setVisible(true));
    });
  }
}
