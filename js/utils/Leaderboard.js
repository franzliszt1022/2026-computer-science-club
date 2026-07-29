const Leaderboard = {
  KEY: 'defenseGameLeaderboard',
  MAX_ENTRIES: 10,

  getScores() {
    try {
      const raw = localStorage.getItem(this.KEY);
      const scores = raw ? JSON.parse(raw) : [];
      return Array.isArray(scores) ? scores : [];
    } catch (e) {
      return [];
    }
  },

  isHighScore(score) {
    const scores = this.getScores();
    if (scores.length < this.MAX_ENTRIES) return true;
    return score > scores[scores.length - 1].score;
  },

  addScore(initials, score, wave) {
    const scores = this.getScores();
    scores.push({
      initials: (initials || '???').toUpperCase().slice(0, 3),
      score,
      wave,
    });
    scores.sort((a, b) => b.score - a.score);
    const trimmed = scores.slice(0, this.MAX_ENTRIES);
    localStorage.setItem(this.KEY, JSON.stringify(trimmed));
    return trimmed;
  },
};
