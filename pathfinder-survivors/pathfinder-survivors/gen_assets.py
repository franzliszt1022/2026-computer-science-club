"""
gen_assets.py
--------------
Pillow(PIL)로 게임에 쓰이는 모든 이미지를 '코드로' 그려서 assets/ 폴더에 저장한다.
외부 이미지 파일을 하나도 쓰지 않기 때문에 저작권 걱정이 없고,
색·크기를 상수만 바꿔서 통째로 리터칭할 수 있다.

python gen_assets.py  로 단독 실행하거나, game.py가 자동으로 호출한다.
"""

import os
import math
import random
from PIL import Image, ImageDraw

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# ---------------------------------------------------------------- 팔레트
OUT = (14, 16, 26, 255)          # 공통 외곽선(어두운 남색)
WHITE = (245, 248, 255, 255)
BLACK = (18, 18, 24, 255)

P_BODY = (58, 118, 220, 255)     # 1P 파랑
P_BODY_D = (34, 74, 156, 255)
P_HELM = (36, 78, 158, 255)
# 2P(협동)는 같은 모양에 색만 빨강으로 — 부원 스타일대로 외부 이미지 없이 코드로 구분한다.
P2_BODY = (214, 66, 66, 255)
P2_BODY_D = (150, 36, 36, 255)
P2_HELM = (158, 40, 40, 255)
P_SKIN = (240, 200, 160, 255)
P_EYE = (140, 226, 255, 255)
GUN = (96, 104, 122, 255)

E1 = (86, 190, 96, 255)          # 그런트 초록
E1_D = (48, 130, 62, 255)
E2 = (236, 122, 60, 255)         # 러너 주황
E2_D = (176, 74, 32, 255)
E3 = (150, 106, 216, 255)        # 탱커 보라
E3_D = (96, 62, 154, 255)
E4 = (198, 54, 66, 255)          # 보스 진홍
E4_D = (128, 26, 40, 255)

GOLD = (255, 214, 92, 255)
CYAN = (110, 232, 236, 255)
CYAN_D = (40, 150, 168, 255)


def _new(w, h=None):
    return Image.new("RGBA", (w, h or w), (0, 0, 0, 0))


def _save(img, name):
    img.save(os.path.join(ASSET_DIR, name))


# ---------------------------------------------------------------- 캐릭터
def make_player(body=P_BODY, body_d=P_BODY_D, helm=P_HELM, name="player1.png"):
    """32x32 병사. 머리(투구+바이저) + 몸통 + 팔 + 총.
    body/body_d/helm을 바꿔서 1P/2P를 같은 모양·다른 색으로 찍어낸다(협동 배치 K)."""
    img = _new(32)
    d = ImageDraw.Draw(img)
    # 다리
    d.rectangle((11, 22, 15, 29), fill=body_d, outline=OUT)
    d.rectangle((17, 22, 21, 29), fill=body_d, outline=OUT)
    # 몸통
    d.ellipse((6, 13, 26, 27), fill=body, outline=OUT)
    # 팔
    d.ellipse((2, 15, 10, 23), fill=body, outline=OUT)
    d.ellipse((22, 15, 30, 23), fill=body, outline=OUT)
    # 총(오른손)
    d.rectangle((24, 17, 31, 20), fill=GUN, outline=OUT)
    d.rectangle((26, 20, 28, 23), fill=GUN, outline=OUT)
    # 머리
    d.ellipse((9, 3, 23, 17), fill=P_SKIN, outline=OUT)
    # 투구
    d.pieslice((8, 1, 24, 17), 180, 360, fill=helm, outline=OUT)
    d.rectangle((7, 8, 25, 10), fill=helm, outline=OUT)
    # 바이저 눈
    d.rectangle((12, 12, 14, 14), fill=P_EYE)
    d.rectangle((18, 12, 20, 14), fill=P_EYE)
    _save(img, name)


def make_grunt():
    """28x28 초록 슬라임형 근접 몹."""
    img = _new(28)
    d = ImageDraw.Draw(img)
    d.ellipse((2, 7, 26, 27), fill=E1, outline=OUT)
    d.ellipse((5, 4, 23, 18), fill=E1, outline=OUT)
    d.chord((6, 6, 22, 16), 180, 360, fill=(120, 216, 128, 255))
    # 눈
    d.ellipse((8, 11, 13, 17), fill=WHITE, outline=OUT)
    d.ellipse((15, 11, 20, 17), fill=WHITE, outline=OUT)
    d.ellipse((10, 13, 12, 16), fill=BLACK)
    d.ellipse((17, 13, 19, 16), fill=BLACK)
    # 이빨
    d.polygon([(11, 20), (14, 24), (17, 20)], fill=E1_D, outline=OUT)
    _save(img, "enemy_grunt.png")


def make_runner():
    """26x26 주황색 돌진형. 뾰족하고 날렵한 실루엣."""
    img = _new(26)
    d = ImageDraw.Draw(img)
    d.polygon([(13, 1), (24, 14), (19, 24), (7, 24), (2, 14)], fill=E2, outline=OUT)
    d.polygon([(13, 4), (20, 14), (13, 12), (6, 14)], fill=(252, 168, 96, 255))
    # 외눈
    d.ellipse((8, 12, 18, 19), fill=WHITE, outline=OUT)
    d.ellipse((11, 13, 15, 18), fill=E2_D, outline=OUT)
    # 다리
    d.line((8, 24, 5, 25), fill=OUT, width=2)
    d.line((18, 24, 21, 25), fill=OUT, width=2)
    _save(img, "enemy_runner.png")


def make_tank():
    """40x40 보라색 장갑형. 느리지만 체력 높음."""
    img = _new(40)
    d = ImageDraw.Draw(img)
    d.ellipse((3, 8, 37, 38), fill=E3, outline=OUT)
    # 어깨 스파이크
    d.polygon([(3, 16), (0, 6), (11, 11)], fill=E3_D, outline=OUT)
    d.polygon([(37, 16), (40, 6), (29, 11)], fill=E3_D, outline=OUT)
    # 장갑판
    d.rectangle((10, 20, 30, 30), fill=E3_D, outline=OUT)
    d.line((14, 20, 14, 30), fill=OUT)
    d.line((20, 20, 20, 30), fill=OUT)
    d.line((26, 20, 26, 30), fill=OUT)
    # 머리
    d.ellipse((11, 4, 29, 20), fill=E3, outline=OUT)
    d.polygon([(14, 11), (20, 13), (14, 15)], fill=GOLD)
    d.polygon([(26, 11), (20, 13), (26, 15)], fill=GOLD)
    _save(img, "enemy_tank.png")


def make_boss():
    """64x64 보스. 뿔 + 발광하는 눈."""
    img = _new(64)
    d = ImageDraw.Draw(img)
    d.ellipse((6, 16, 58, 62), fill=E4, outline=OUT, width=2)
    d.polygon([(6, 26), (1, 4), (20, 18)], fill=E4_D, outline=OUT)
    d.polygon([(58, 26), (63, 4), (44, 18)], fill=E4_D, outline=OUT)
    d.ellipse((16, 6, 48, 36), fill=E4, outline=OUT, width=2)
    # 눈
    d.ellipse((21, 15, 30, 24), fill=GOLD, outline=OUT)
    d.ellipse((34, 15, 43, 24), fill=GOLD, outline=OUT)
    d.ellipse((24, 18, 27, 22), fill=BLACK)
    d.ellipse((37, 18, 40, 22), fill=BLACK)
    # 입
    d.rectangle((22, 28, 42, 34), fill=BLACK, outline=OUT)
    for x in range(23, 42, 5):
        d.polygon([(x, 28), (x + 2, 33), (x + 4, 28)], fill=WHITE)
    # 가슴 장갑
    d.polygon([(20, 42), (44, 42), (38, 58), (26, 58)], fill=E4_D, outline=OUT)
    # 64px로 그린 뒤 48px로 축소한다. 통로 폭(32px)에 비해 몸집이 너무 커서
    # 길찾기로도 해결이 안 되는 문제가 있어 스프라이트 자체를 줄였다.
    img = img.resize((48, 48), Image.NEAREST)
    _save(img, "enemy_boss.png")


# ---------------------------------------------------------------- 오브젝트
def make_bullet():
    img = _new(12)
    d = ImageDraw.Draw(img)
    d.ellipse((0, 2, 11, 9), fill=GOLD, outline=OUT)
    d.ellipse((3, 4, 7, 7), fill=WHITE)
    _save(img, "bullet.png")


def make_orb():
    img = _new(22)
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, 21, 21), fill=CYAN_D, outline=OUT)
    d.ellipse((2, 2, 17, 17), fill=CYAN)
    d.ellipse((5, 4, 10, 9), fill=WHITE)
    _save(img, "orb.png")


def make_gem():
    img = _new(16)
    d = ImageDraw.Draw(img)
    d.polygon([(8, 0), (15, 7), (8, 15), (1, 7)], fill=CYAN, outline=OUT)
    d.polygon([(8, 0), (11, 7), (8, 15)], fill=(190, 250, 252, 255))
    _save(img, "gem.png")


def make_heart():
    img = _new(16)
    d = ImageDraw.Draw(img)
    d.polygon([(1, 6), (14, 6), (8, 15)], fill=E4, outline=OUT)
    d.ellipse((1, 2, 8, 9), fill=E4, outline=OUT)
    d.ellipse((7, 2, 14, 9), fill=E4, outline=OUT)
    d.polygon([(1, 6), (14, 6), (8, 12)], fill=E4)
    d.polygon([(3, 4), (6, 4), (4, 7)], fill=(250, 140, 150, 255))
    _save(img, "heart.png")


def make_gear():
    """36x36 톱니바퀴 아이콘. 인게임 설정 버튼에 쓴다(버튼이 42x42라 여유를 조금 둠)."""
    size = 36
    img = _new(size)
    d = ImageDraw.Draw(img)
    cx = cy = size / 2
    r_outer = 9.75
    tooth_len, tooth_w, n = 4.8, 5.1, 8
    col = (200, 206, 222, 255)
    for i in range(n):
        a = math.tau * i / n
        ox, oy = math.cos(a), math.sin(a)  # 중심→바깥 방향
        px, py = -math.sin(a), math.cos(a)  # 그 방향에 수직(이빨 폭 방향)
        base, tip = r_outer, r_outer + tooth_len
        d.polygon(
            [
                (cx + ox * base + px * tooth_w / 2, cy + oy * base + py * tooth_w / 2),
                (cx + ox * base - px * tooth_w / 2, cy + oy * base - py * tooth_w / 2),
                (cx + ox * tip - px * tooth_w / 2, cy + oy * tip - py * tooth_w / 2),
                (cx + ox * tip + px * tooth_w / 2, cy + oy * tip + py * tooth_w / 2),
            ],
            fill=col,
        )
    d.ellipse((cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer), fill=col, outline=OUT)
    d.ellipse((cx - 3.9, cy - 3.9, cx + 3.9, cy + 3.9), fill=(18, 20, 28, 255))
    _save(img, "gear.png")


# ---------------------------------------------------------------- 타일
def make_floor(seed, name):
    """32x32 바닥 타일. 가장자리에 특징을 넣지 않아 이어붙여도 티가 안 난다."""
    rng = random.Random(seed)
    img = Image.new("RGBA", (32, 32), (38, 42, 54, 255))
    d = ImageDraw.Draw(img)
    for _ in range(46):
        x, y = rng.randrange(32), rng.randrange(32)
        c = rng.choice([(44, 48, 62, 255), (33, 36, 48, 255), (50, 55, 70, 255)])
        d.rectangle((x, y, x + 1, y + 1), fill=c)
    if seed % 2 == 1:  # 변형 타일에는 균열 한 줄
        d.line((7, 9, 22, 20), fill=(30, 33, 44, 255))
        d.line((22, 20, 26, 17), fill=(30, 33, 44, 255))
    _save(img, name)


def make_wall():
    """32x32 벽돌 벽. 위/아래 두 줄이 반칸씩 어긋나 타일링이 자연스럽다."""
    img = Image.new("RGBA", (32, 32), (26, 28, 38, 255))
    d = ImageDraw.Draw(img)
    base = (78, 84, 100, 255)
    lite = (98, 105, 124, 255)
    # 윗줄: x = 0..15, 16..31
    for x0 in (0, 16):
        d.rectangle((x0 + 1, 1, x0 + 14, 14), fill=base)
        d.line((x0 + 1, 1, x0 + 14, 1), fill=lite)
    # 아랫줄: 8칸 어긋남 (경계 -8, 8, 24, 40)
    for x0 in (-8, 8, 24):
        d.rectangle((x0 + 1, 17, x0 + 14, 30), fill=base)
        d.line((max(x0 + 1, 0), 17, min(x0 + 14, 31), 17), fill=lite)
    _save(img, "wall.png")


def make_rock():
    """32x32 바위 장애물. 바닥 위에 겹쳐 그린다."""
    img = _new(32)
    d = ImageDraw.Draw(img)
    d.polygon([(3, 28), (6, 12), (14, 4), (24, 7), (29, 18), (27, 28)],
              fill=(92, 96, 112, 255), outline=OUT)
    d.polygon([(9, 14), (15, 8), (21, 11), (16, 17)], fill=(118, 124, 142, 255))
    d.line((12, 22, 22, 24), fill=(62, 66, 80, 255), width=2)
    _save(img, "rock.png")


def build(force=False):
    os.makedirs(ASSET_DIR, exist_ok=True)
    boss = os.path.join(ASSET_DIR, "enemy_boss.png")
    if not force and os.path.exists(os.path.join(ASSET_DIR, "player1.png")):
        # 예전에 만든 64px 보스가 남아 있으면 크기가 안 맞으므로 다시 그린다.
        try:
            if Image.open(boss).size == (48, 48):
                return ASSET_DIR
        except Exception:
            pass
    make_player(P_BODY, P_BODY_D, P_HELM, "player1.png")
    make_player(P2_BODY, P2_BODY_D, P2_HELM, "player2.png")
    make_grunt()
    make_runner()
    make_tank()
    make_boss()
    make_bullet()
    make_orb()
    make_gem()
    make_heart()
    make_gear()
    make_floor(1, "floor0.png")
    make_floor(3, "floor1.png")
    make_wall()
    make_rock()
    return ASSET_DIR


if __name__ == "__main__":
    print("생성 완료:", build(force=True))
