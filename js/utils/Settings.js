const Settings = {
  KEY: 'defenseGameSettings',
  DEFAULTS: {
    muted: false,
    volume: 1,
    showDamageNumbers: true,
    showEffects: true,
  },

  get() {
    try {
      const raw = localStorage.getItem(this.KEY);
      const saved = raw ? JSON.parse(raw) : {};
      return { ...this.DEFAULTS, ...saved };
    } catch (e) {
      return { ...this.DEFAULTS };
    }
  },

  set(partial) {
    const merged = { ...this.get(), ...partial };
    localStorage.setItem(this.KEY, JSON.stringify(merged));
    return merged;
  },
};
