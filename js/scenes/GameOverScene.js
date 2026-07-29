class GameOverScene extends Phaser.Scene {
  constructor() {
    super('GameOverScene');
  }

  init(data) {
    this.won = data.won || false;
    this.wave = data.wave || 0;
    this.kills = data.kills || 0;
    this.gold = data.gold || 0;
    this.score = data.score || 0;
  }

  create() {
    const { width, height } = this.scale;

    drawBackground(this);

    const accent = this.won ? THEME.success : THEME.danger;
    const glow = this.add.circle(width / 2, 150, 160, accent, 0.1);
    this.tweens.add({
      targets: glow,
      scale: 1.15,
      alpha: 0.18,
      duration: 1200,
      yoyo: true,
      repeat: -1,
      ease: 'Sine.easeInOut',
    });

    const title = this.add.text(width / 2, 100, this.won ? 'VICTORY!' : 'GAME OVER', {
      fontSize: '44px',
      color: this.won ? '#2ecc71' : '#e74c3c',
      fontStyle: 'bold',
    }).setOrigin(0.5);
    title.setShadow(0, 4, 'rgba(0,0,0,0.5)', 8, false, true);

    this.add.text(width / 2, 150, `도달 웨이브: ${this.wave}   점수: ${this.score}`, {
      fontSize: '20px',
      color: THEME.text,
    }).setOrigin(0.5);

    this.isNewHighScore = Leaderboard.isHighScore(this.score);

    if (this.isNewHighScore) {
      this.buildScoreForm(width / 2, 200);
    } else {
      this.buildLeaderboardView(230);
      this.buildRetryButton(width / 2, 590);
    }
  }

  buildScoreForm(x, y) {
    const badge = this.add.text(x, y - 25, '신기록! 이니셜을 입력하세요', {
      fontSize: '18px',
      color: '#ffd23f',
      fontStyle: 'bold',
    }).setOrigin(0.5);
    this.tweens.add({ targets: badge, alpha: 0.4, duration: 500, yoyo: true, repeat: -1 });

    const formHtml = `
      <div style="display:flex; gap:10px; align-items:center;">
        <input id="initials-input" type="text" maxlength="${Leaderboard.MAX_INITIALS_LENGTH}"
          style="width:200px; font-size:20px; text-align:center; letter-spacing:2px; text-transform:uppercase; padding:6px; border-radius:4px; border:none;" />
        <button id="submit-btn" style="font-size:16px; padding:8px 16px; cursor:pointer; border-radius:4px; border:none; background:#ffd23f; font-weight:bold;">등록</button>
      </div>
    `;
    this.form = this.add.dom(x, y + 15).createFromHTML(formHtml);

    const inputEl = this.form.getChildByID('initials-input');
    const btnEl = this.form.getChildByID('submit-btn');
    inputEl.focus();

    const submit = () => {
      const initials = (inputEl.value || 'YOU').trim() || 'YOU';
      Leaderboard.addScore(initials, this.score, this.wave);
      this.form.destroy();
      badge.destroy();
      this.buildLeaderboardView(230);
      this.buildRetryButton(this.scale.width / 2, 590);
    };

    btnEl.addEventListener('click', submit);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submit();
    });
  }

  buildLeaderboardView(startY) {
    const { width } = this.scale;

    this.add.text(width / 2, startY, 'TOP 10', {
      fontSize: '20px',
      color: THEME.accent,
      fontStyle: 'bold',
    }).setOrigin(0.5);

    const scores = Leaderboard.getScores();
    const lines = scores.length > 0
      ? scores.map((s, i) => `${String(i + 1).padStart(2, ' ')}.  ${s.initials.padEnd(Leaderboard.MAX_INITIALS_LENGTH, ' ')}   ${s.score}점  (Wave ${s.wave})`).join('\n')
      : '아직 기록이 없습니다';

    this.add.text(width / 2, startY + 35, lines, {
      fontSize: '16px',
      color: THEME.text,
      align: 'left',
      lineSpacing: 8,
    }).setOrigin(0.5, 0);
  }

  buildRetryButton(x, y) {
    const retryText = this.add.text(x, y, '클릭해서 다시 시작', {
      fontSize: '24px',
      color: '#ffd23f',
    }).setOrigin(0.5);
    retryText.setInteractive({ useHandCursor: true });

    this.tweens.add({
      targets: retryText,
      alpha: 0.3,
      duration: 700,
      yoyo: true,
      repeat: -1,
    });

    retryText.on('pointerdown', () => {
      this.scene.start('GameScene');
    });
  }
}
