const DamageNumber = {
  show(scene, x, y, amount, opts = {}) {
    if (!Settings.get().showDamageNumbers) return;

    const crit = opts.crit || false;
    const text = scene.add.text(x, y, crit ? `${amount}!` : `${amount}`, {
      fontSize: crit ? '22px' : '14px',
      color: crit ? '#ffd23f' : '#ffffff',
      fontStyle: crit ? 'bold' : 'normal',
    }).setOrigin(0.5);

    scene.tweens.add({
      targets: text,
      y: y - 30,
      alpha: 0,
      duration: 500,
      ease: 'Cubic.easeOut',
      onComplete: () => text.destroy(),
    });
  },
};
