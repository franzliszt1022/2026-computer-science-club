"""
gen_sounds.py
-------------
효과음을 '코드로 합성'해서 assets/sfx/ 에 WAV로 저장한다.
gen_assets.py가 이미지를 그리는 것과 같은 방식. 외부 음원 파일이 없으니
저작권 문제가 없고, 아래 숫자만 바꾸면 음색을 통째로 바꿀 수 있다.

python gen_sounds.py 로 단독 실행하거나, game.py가 자동으로 호출한다.

합성 원리 요약
--------------
· 소리 = 시간에 대한 진폭 배열. 22050Hz면 1초에 22050개의 숫자.
· 사인파 sin(2πft)는 맑은 소리, 사각파는 거칠고 8비트 같은 소리,
  화이트 노이즈(난수)는 타격음·폭발음의 재료가 된다.
· 그대로 재생하면 '삐-' 하고 끊기므로 포락선(envelope)을 곱해
  시작과 끝을 부드럽게 만든다. 이게 없으면 딱딱한 클릭음이 섞인다.
· 주파수를 시간에 따라 바꾸면(스윕) 발사음·낙하음 느낌이 난다.
"""

import os
import wave

# numpy가 없어도 게임 자체는 켜져야 한다.
# 음원 파일이 이미 있으면(배포본에 포함) numpy 없이도 소리가 정상 재생되고,
# 파일이 없고 numpy도 없을 때만 조용히 무음으로 넘어간다.
try:
    import numpy as np
except ImportError:
    np = None

SR = 22050  # 샘플레이트
SFX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sfx")


# ----------------------------------------------------------------- 재료
def t_axis(dur):
    return np.linspace(0.0, dur, int(SR * dur), endpoint=False)


def sine(freq, dur, phase=0.0):
    return np.sin(2 * np.pi * freq * t_axis(dur) + phase)


def square(freq, dur, duty=0.5):
    ph = (t_axis(dur) * freq) % 1.0
    return np.where(ph < duty, 1.0, -1.0)


def saw(freq, dur):
    return 2.0 * ((t_axis(dur) * freq) % 1.0) - 1.0


def noise(dur, seed=0):
    rng = np.random.default_rng(seed)
    return rng.uniform(-1.0, 1.0, int(SR * dur))


def sweep(f0, f1, dur, kind="sine"):
    """주파수가 f0에서 f1로 변하는 파형. 위상 = 주파수의 적분이다."""
    t = t_axis(dur)
    f = np.linspace(f0, f1, len(t))
    phase = 2 * np.pi * np.cumsum(f) / SR
    if kind == "square":
        return np.where((phase / (2 * np.pi)) % 1.0 < 0.5, 1.0, -1.0)
    if kind == "saw":
        return 2.0 * ((phase / (2 * np.pi)) % 1.0) - 1.0
    return np.sin(phase)


# ----------------------------------------------------------------- 가공
def env(sig, attack=0.005, release=0.05, curve=2.0):
    """포락선: 앞은 짧게 올리고 뒤는 곡선으로 줄인다."""
    n = len(sig)
    e = np.ones(n)
    a = max(1, int(SR * attack))
    r = max(1, int(SR * release))
    a, r = min(a, n), min(r, n)
    e[:a] = np.linspace(0.0, 1.0, a)
    e[n - r:] *= np.linspace(1.0, 0.0, r) ** curve
    return sig * e


def decay(sig, power=4.0):
    """전체를 지수적으로 감쇠 — 타격음/폭발음에 쓴다."""
    return sig * np.exp(-power * np.linspace(0.0, 1.0, len(sig)))


def lowpass(sig, alpha=0.25):
    """아주 단순한 1차 저역통과. 노이즈의 날카로움을 깎는다."""
    out = np.empty_like(sig)
    acc = 0.0
    for i, v in enumerate(sig):
        acc += alpha * (v - acc)
        out[i] = acc
    return out


def highpass(sig, alpha=0.25):
    """원신호에서 저역을 빼면 고역만 남는다. 총성의 '탁' 하는 파열음용."""
    return sig - lowpass(sig, alpha)


def mix(*parts):
    n = max(len(p) for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[: len(p)] += p
    return out


def pad(sig, dur):
    n = int(SR * dur)
    out = np.zeros(n)
    out[: min(n, len(sig))] = sig[: min(n, len(sig))]
    return out


def place(buf, start_sec, tone):
    """buf의 start_sec 위치에 tone을 더한다. 버퍼를 넘으면 잘라서 넣는다.
    (길이 계산을 매번 손으로 맞추면 실수하기 쉬워서 헬퍼로 뺐다)"""
    s = int(SR * start_sec)
    if s >= len(buf):
        return buf
    n = min(len(tone), len(buf) - s)
    buf[s: s + n] += tone[:n]
    return buf


def save(sig, name, gain=0.85):
    peak = np.max(np.abs(sig))
    if peak > 1e-9:
        sig = sig / peak * gain
    data = (np.clip(sig, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(os.path.join(SFX_DIR, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ----------------------------------------------------------------- 효과음
def make_all():
    # 발사: 총성은 '음정'이 없다. 주파수를 스윕하면 레이저처럼 들리므로
    # 노이즈 세 겹으로 만든다.
    #   1) crack : 고역 노이즈를 극단적으로 짧게 → 탁! 하는 파열음
    #   2) body  : 중역 노이즈, 조금 길게 → 총열에서 나오는 몸통 소리
    #   3) thump : 90Hz 저음 → 반동의 '퍽' 하는 무게감
    crack = decay(highpass(noise(0.05, 11), 0.55) * 1.2, 60.0)
    body = decay(lowpass(noise(0.09, 12), 0.35), 26.0)
    thump = decay(sine(90, 0.09) * 0.9, 22.0)
    tail = decay(lowpass(noise(0.16, 13), 0.10) * 0.35, 9.0)
    save(env(mix(crack, body, thump, tail), 0.0004, 0.02, 1.5), "shoot", 0.5)

    # 명중: 노이즈 한 방 + 낮은 톤. 짧을수록 경쾌하다
    save(decay(mix(lowpass(noise(0.05, 1), 0.5) * 0.8, sine(200, 0.05) * 0.5), 9.0),
         "hit", 0.5)

    # 처치: 조금 더 길고 부드러운 노이즈 폭발
    save(decay(mix(lowpass(noise(0.18, 2), 0.28), sweep(320, 80, 0.18) * 0.5), 5.0),
         "kill", 0.6)

    # 보스 처치: 저음 폭발 + 긴 여운
    save(decay(mix(lowpass(noise(0.9, 3), 0.10) * 1.2,
                   sweep(180, 35, 0.9) * 0.9,
                   sine(55, 0.9) * 0.5), 2.2), "boss_die", 0.95)

    # 경험치 획득: 맑고 아주 짧은 상승음
    save(env(sweep(880, 1320, 0.06), 0.002, 0.03), "pickup", 0.3)

    # 회복: 두 음 상승
    save(env(mix(pad(sine(660, 0.09), 0.09), pad(np.zeros(int(SR * 0.07)), 0.07),
                 np.concatenate([np.zeros(int(SR * 0.07)), sine(990, 0.12)])),
             0.005, 0.08), "heal", 0.5)

    # 레벨업: 도-미-솔-도 아르페지오
    notes, seg = [523, 659, 784, 1047], 0.085
    lv = np.zeros(int(SR * (seg * len(notes) + 0.12)))
    for i, f in enumerate(notes):
        place(lv, seg * i, env(mix(sine(f, seg + 0.1), square(f, seg + 0.1) * 0.18),
                               0.004, 0.06))
    save(lv, "levelup", 0.6)

    # 피격: 낮고 거친 하강음
    save(decay(env(mix(sweep(420, 90, 0.28, "square") * 0.8,
                       lowpass(noise(0.28, 4), 0.2) * 0.6), 0.002, 0.1), 3.0),
         "hurt", 0.75)

    # 보스 탄환: 발사음보다 낮고 둔하게
    save(decay(env(mix(sweep(420, 150, 0.13, "saw"), sine(90, 0.13) * 0.5),
                   0.002, 0.04), 4.0), "boss_shot", 0.55)

    # 예비동작 경고: 서서히 올라가는 긴장음
    save(env(mix(sweep(300, 780, 0.42) * 0.7, sweep(302, 786, 0.42) * 0.5),
             0.03, 0.12), "telegraph", 0.45)

    # 돌진: 바람 가르는 노이즈 스윕
    sw = lowpass(noise(0.38, 5), 0.06) * np.linspace(0.2, 1.0, int(SR * 0.38))
    save(decay(mix(sw, sweep(200, 620, 0.38) * 0.35), 1.4), "dash", 0.7)

    # 보스 등장: 저음 경적 두 번
    horn = np.zeros(int(SR * 1.1))
    for i, st in enumerate((0.0, 0.42)):
        place(horn, st,
              env(mix(saw(88 - i * 8, 0.34), saw(44 - i * 4, 0.34) * 0.7), 0.02, 0.14))
    save(mix(horn, lowpass(noise(1.1, 6), 0.04) * 0.35), "boss_spawn", 1.0)

    # 지형 붕괴: 낮은 굉음
    rb = lowpass(noise(0.85, 7), 0.05)
    save(decay(mix(rb * 1.3, sweep(140, 40, 0.85) * 0.6), 1.8), "collapse", 0.9)

    # 지형 복원: 반대로 차오르는 소리
    rb2 = lowpass(noise(0.6, 8), 0.06) * np.linspace(0.1, 1.0, int(SR * 0.6))
    save(mix(rb2, sweep(60, 190, 0.6) * 0.7), "restore", 0.8)

    # 웨이브 클리어: 짧은 3음 상승
    wc = np.zeros(int(SR * 0.62))
    for i, f in enumerate((659, 880, 1175)):
        place(wc, 0.12 * i, env(mix(sine(f, 0.28), sine(f * 2, 0.28) * 0.25), 0.005, 0.16))
    save(wc, "wave_clear", 0.55)

    # 게임 오버: 하강하는 단조
    go = np.zeros(int(SR * 1.5))
    for i, f in enumerate((523, 440, 349, 262)):
        place(go, 0.28 * i, env(mix(sine(f, 0.5), square(f, 0.5) * 0.15), 0.01, 0.32))
    save(go, "gameover", 0.7)

    # 승리: 팡파르
    win = np.zeros(int(SR * 1.8))
    for i, (f, st, ln) in enumerate([(523, 0.0, 0.18), (659, 0.16, 0.18),
                                     (784, 0.32, 0.18), (1047, 0.48, 0.5),
                                     (784, 0.98, 0.16), (1047, 1.12, 0.62)]):
        place(win, st,
              env(mix(sine(f, ln), square(f, ln) * 0.2, sine(f * 2, ln) * 0.15),
                  0.006, min(0.25, ln * 0.6)))
    save(win, "win", 0.75)

    # UI 선택
    save(env(sweep(620, 980, 0.05), 0.002, 0.025), "select", 0.4)


def build(force=False):
    os.makedirs(SFX_DIR, exist_ok=True)
    if not force and os.path.exists(os.path.join(SFX_DIR, "shoot.wav")):
        return SFX_DIR
    if np is None:
        print("[알림] numpy가 없어 음원을 생성할 수 없습니다. (pip install numpy)")
        return SFX_DIR
    make_all()
    return SFX_DIR


if __name__ == "__main__":
    print("생성 완료:", build(force=True))
