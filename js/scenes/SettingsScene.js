class SettingsScene extends Phaser.Scene {
  constructor() {
    super('SettingsScene');
  }

  init(data) {
    this.returnTo = (data && data.returnTo) || 'MenuScene';
  }

  create() {
    const { width } = this.scale;
    drawBackground(this);

    this.settings = Settings.get();

    this.add.text(width / 2, 110, '설정', {
      fontSize: '56px', color: THEME.text, fontStyle: 'bold',
    }).setOrigin(0.5).setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.buildMuteRow(width / 2, 280);
    this.buildVolumeRow(width / 2, 400);
    this.buildToggleRow(width / 2, 520, '데미지 숫자 표시', 'showDamageNumbers');
    this.buildToggleRow(width / 2, 620, '이펙트 표시', 'showEffects');

    this.buildBackButton(width / 2, 800);
  }

  buildMuteRow(cx, y) {
    this.add.text(cx - 300, y, '사운드', { fontSize: '28px', color: THEME.text }).setOrigin(0, 0.5);

    const bg = this.add.rectangle(cx + 200, y, 160, 56, THEME.panel, 0.9).setOrigin(0.5);
    bg.setStrokeStyle(2, THEME.accent, 0.8);
    bg.setInteractive({ useHandCursor: true });
    const label = this.add.text(cx + 200, y, this.settings.muted ? '음소거' : '켜짐', {
      fontSize: '22px', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5);

    bg.on('pointerdown', () => {
      this.settings.muted = !this.settings.muted;
      Settings.set({ muted: this.settings.muted });
      this.sound.mute = this.settings.muted;
      label.setText(this.settings.muted ? '음소거' : '켜짐');
    });
  }

  buildVolumeRow(cx, y) {
    this.add.text(cx - 300, y, '음량', { fontSize: '28px', color: THEME.text }).setOrigin(0, 0.5);

    const steps = [0, 0.25, 0.5, 0.75, 1];
    const buttons = {};

    const highlight = () => {
      steps.forEach((v) => {
        const btn = buttons[v];
        if (v === this.settings.volume) btn.setStrokeStyle(3, THEME.accent, 1);
        else btn.setStrokeStyle(1, 0xffffff, 0.3);
      });
    };

    steps.forEach((v, i) => {
      const bx = cx + 40 + i * 60;
      const bg = this.add.rectangle(bx, y, 50, 44, THEME.panel, 0.9).setOrigin(0.5);
      bg.setStrokeStyle(1, 0xffffff, 0.3);
      bg.setInteractive({ useHandCursor: true });
      this.add.text(bx, y, `${Math.round(v * 100)}`, { fontSize: '16px', color: '#ffffff' }).setOrigin(0.5);

      bg.on('pointerdown', () => {
        this.settings.volume = v;
        Settings.set({ volume: v });
        this.sound.volume = v;
        highlight();
      });

      buttons[v] = bg;
    });

    highlight();
  }

  buildToggleRow(cx, y, labelText, key) {
    this.add.text(cx - 300, y, labelText, { fontSize: '28px', color: THEME.text }).setOrigin(0, 0.5);

    const bg = this.add.rectangle(cx + 200, y, 160, 56, THEME.panel, 0.9).setOrigin(0.5);
    bg.setStrokeStyle(2, THEME.accent, 0.8);
    bg.setInteractive({ useHandCursor: true });
    const label = this.add.text(cx + 200, y, this.settings[key] ? '켜짐' : '꺼짐', {
      fontSize: '22px', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5);

    bg.on('pointerdown', () => {
      this.settings[key] = !this.settings[key];
      Settings.set({ [key]: this.settings[key] });
      label.setText(this.settings[key] ? '켜짐' : '꺼짐');
    });
  }

  buildBackButton(x, y) {
    const text = this.add.text(x, y, '← 뒤로가기', {
      fontSize: '28px', color: '#ffd23f',
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });

    this.tweens.add({ targets: text, alpha: 0.4, duration: 700, yoyo: true, repeat: -1 });

    text.on('pointerdown', () => {
      this.scene.start(this.returnTo);
    });
  }
}
