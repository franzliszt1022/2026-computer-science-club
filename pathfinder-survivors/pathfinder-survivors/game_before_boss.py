"""
game.py — "PATHFINDER SURVIVORS"
================================
파이썬 + pygame 으로 만든 뱀서라이크(vampire-survivors-like) 디펜스 게임.

핵심 설계
---------
· 맵에 벽과 바위가 있어서 적이 '직선으로 오면 막힌다'.
  → 그래서 A* 최단경로 탐색이 게임 규칙상 반드시 필요하다. (억지 삽입 X)
· 가시선이 뚫려 있으면 A*를 아예 돌리지 않고 바로 직진한다.
  → 필요할 때만 계산하는 게 실제 게임 AI의 표준 구조.
· 한 프레임에 돌릴 수 있는 A* 횟수를 제한(예산)하고,
  예산이 바닥나면 다익스트라 flow field로 대체한다.
· F1: 적들의 탐색 경로를 실시간으로 그려서 보여준다 (발표 시연용).

조작
----
WASD / 방향키 : 이동      (공격은 자동)
1 2 3          : 레벨업 강화 선택
F1             : 경로 디버그 보기
ESC / P        : 일시정지
R              : 재시작
"""

import math
import os
import random
import sys

import pygame

import gen_assets
from pathfinding import Grid, FlowField, astar, smooth_path

# ----------------------------------------------------------------- 설정
SW, SH = 1024, 640  # 화면 크기
TILE = 32
MAP_W, MAP_H = 64, 48  # 타일 개수 → 월드 2048 x 1536
WORLD_W, WORLD_H = MAP_W * TILE, MAP_H * TILE
FPS = 60

PATH_BUDGET_PER_FRAME = 8  # 프레임당 A* 호출 상한
FLOW_REBUILD_INTERVAL = 0.5  # flow field 갱신 주기(초)

# ------------------------------------------------------------- [ChatGPT 수정] 웨이브 난이도 튜닝
# 한 웨이브의 적을 전부 처치해야 다음 웨이브가 시작된다.
# 후반 웨이브는 적 수/체력/정예 비율/종류가 계속 증가하므로 사실상 무한 진행.
ENEMY_CAP = 70  # 동시에 존재 가능한 최대 적 수(큰 웨이브는 여러 묶음으로 등장)
WAVE_INTRO_TIME = 2.0  # "웨이브 N" 표시 후 전투 시작까지 대기
WAVE_CLEAR_TIME = 1.4  # 웨이브 클리어 후 다음 웨이브까지 대기
WAVE_SPAWN_INTERVAL = 0.16  # 같은 웨이브 안에서 적이 등장하는 간격
WAVE_BASE_ENEMIES = 6  # 1웨이브 기본 몬스터 수
WAVE_ENEMY_GROWTH = 3  # 웨이브마다 추가되는 몬스터 수
WAVE_HP_GROWTH = 0.10  # 웨이브마다 적 체력 배율 +10%
BOSS_EVERY = 5  # 5, 10, 15... 웨이브마다 보스 등장
ELITE_UNLOCK_WAVE = 7  # 정예 몬스터 해금 웨이브
ELITE_CHANCE_BASE = 0.04  # 정예 기본 확률
ELITE_CHANCE_GROWTH = 0.008  # 웨이브가 오를수록 정예 확률 증가
SEPARATION_NEIGHBORS = 8  # 밀어내기 계산에 쓸 최대 이웃 수

# [ChatGPT 수정] 난이도별 플레이어 체력 / 요구 경험치 / 몬스터 체력·속도·공격력 배율
DIFFICULTIES = {
    "easy": {
        "hp": 130.0,
        "xp_mul": 0.85,
        "enemy_hp_mul": 1.10,
        "enemy_speed_mul": 1.00,
        "enemy_damage_mul": 0.90,
    },
    "normal": {
        "hp": 100.0,
        "xp_mul": 1.00,
        "enemy_hp_mul": 1.20,
        "enemy_speed_mul": 1.12,
        "enemy_damage_mul": 1.00,
    },
    "hard": {
        "hp": 75.0,
        "xp_mul": 1.25,
        "enemy_hp_mul": 1.40,
        "enemy_speed_mul": 1.28,
        "enemy_damage_mul": 1.30,
    },
    "very_hard": {
        "hp": 55.0,
        "xp_mul": 1.50,
        "enemy_hp_mul": 1.70,
        "enemy_speed_mul": 1.45,
        "enemy_damage_mul": 1.60,
    },
}

C_BG = (18, 20, 28)
C_UI = (232, 238, 250)
C_DIM = (140, 150, 172)
C_HP = (226, 76, 92)
C_XP = (110, 232, 236)
C_GOLD = (255, 214, 92)
C_PANEL = (28, 32, 44)

# ----------------------------------------------------------------- 폰트
# assets/ 안에 이 파일이 있으면 시스템 폰트보다 우선해서 쓴다.
# 게임을 통째로 옮겨도 글꼴이 따라가므로 어느 컴퓨터에서든 똑같이 보인다.
FONT_FILE = "ramche.ttf"
FONT_ANTIALIAS = True  # 픽셀(비트맵) 글꼴이면 False가 더 또렷하다
FONT_SIZES = (16, 20, 32, 52)  # 작은 / 보통 / 큰 / 매우 큰

KOREAN_FONTS = [
    "malgungothic",
    "malgun gothic",
    "applesdgothicneo",
    "apple sd gothic neo",
    "applegothic",
    "nanumgothic",
    "nanumbarungothic",
    "notosanscjkkr",
    "noto sans cjk kr",
    "notosanskr",
    "spoqahansansneo",
    "d2coding",
    "gulim",
    "dotum",
    "batang",
    "unbatang",
    "nanumgothiccoding",
]


def usable_font(path):
    """실제로 열리고 '한글이' 그려지는 글꼴인지 확인한다.

    파일이 깨졌거나 한글 글자가 없는 글꼴이면 화면이 전부 두부(□)가 되는데,
    그러고 나서야 알아채면 늦다. 여기서 미리 걸러 영어 UI로 넘긴다.

    판별 방법: 어떤 글꼴에도 없는 문자(사용자 정의 영역 U+E000)를 같이 그려서
    '가'와 픽셀이 똑같으면 둘 다 대체 글리프(두부)라는 뜻이므로 탈락시킨다.
    글자 폭만 재면 두부도 폭이 있어서 통과해 버린다.
    """
    if not path:
        return False
    try:
        f = pygame.font.Font(path, 20)
        ko = f.render("가", True, (255, 255, 255))
        missing = f.render("\ue000", True, (255, 255, 255))
        if ko.get_width() <= 0:
            return False
        if ko.get_size() == missing.get_size():
            if pygame.image.tostring(ko, "RGBA") == pygame.image.tostring(
                missing, "RGBA"
            ):
                return False
        return True
    except Exception:
        return False


def find_korean_font():
    bundled = os.path.join(gen_assets.ASSET_DIR, FONT_FILE)
    if os.path.exists(bundled):
        if usable_font(bundled):
            return bundled
        print(f"[경고] {FONT_FILE} 을 읽을 수 없어 시스템 글꼴로 대체합니다.")
    for name in KOREAN_FONTS:
        path = pygame.font.match_font(name)
        if usable_font(path):
            return path
    return None


# 한글 폰트가 없는 환경에서는 자동으로 영어 UI로 넘어간다.
TEXT = {
    "ko": {
        "title": "PATHFINDER SURVIVORS",
        "sub": "A* 길찾기로 몰려오는 적을 버텨내라",
        "start": "SPACE 를 눌러 시작",
        "difficulty": "난이도를 선택하세요",
        "difficulty_hint": "1 쉬움   ·   2 보통   ·   3 어려움   ·   4 매우 어려움",
        "easy": "쉬움",
        "normal": "보통",
        "hard": "어려움",
        "very_hard": "매우 어려움",
        "ctrl": "WASD/방향키 이동   ·   공격은 자동   ·   F1 경로 보기   ·   F11 전체화면   ·   ESC 일시정지",
        "lv": "레벨",
        "time": "생존",
        "kill": "처치",
        "wave": "웨이브",
        "remaining": "남은 적",
        "wave_clear": "웨이브 클리어!",
        "levelup": "레벨 업!",
        "choose": "1 / 2 / 3 키로 강화를 선택하세요",
        "pause": "일시정지",
        "resume": "ESC 로 계속하기",
        "over": "G A M E   O V E R",
        "survived": "생존 시간",
        "restart": "R 을 눌러 다시 시작",
        "home": "H 를 눌러 홈으로",
        "paths": "A* 경로 표시",
        "boss": "보스 등장!",
        "maxed": "(최대)",
    },
    "en": {
        "title": "PATHFINDER SURVIVORS",
        "sub": "Survive the A*-driven swarm",
        "start": "PRESS SPACE TO START",
        "difficulty": "SELECT DIFFICULTY",
        "difficulty_hint": "1 EASY   ·   2 NORMAL   ·   3 HARD   ·   4 VERY HARD",
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "very_hard": "VERY HARD",
        "ctrl": "WASD/Arrows move  ·  Auto attack  ·  F1 paths  ·  F11 fullscreen  ·  ESC pause",
        "lv": "LV",
        "time": "TIME",
        "kill": "KILLS",
        "wave": "WAVE",
        "remaining": "LEFT",
        "wave_clear": "WAVE CLEAR!",
        "levelup": "LEVEL UP!",
        "choose": "Press 1 / 2 / 3 to pick an upgrade",
        "pause": "PAUSED",
        "resume": "Press ESC to resume",
        "over": "G A M E   O V E R",
        "survived": "SURVIVED",
        "restart": "PRESS R TO RESTART",
        "home": "PRESS H TO RETURN HOME",
        "paths": "A* PATHS",
        "boss": "BOSS INCOMING!",
        "maxed": "(MAX)",
    },
}

# ------------------------------------------------------- 강화(업그레이드)
# name/desc는 (한국어, 영어) 튜플
UPGRADES = [
    {
        "key": "dmg",
        "max": 8,
        "name": ("화력 강화", "Firepower"),
        "desc": ("총알 데미지 +25%", "Bullet damage +25%"),
    },
    {
        "key": "rate",
        "max": 8,
        "name": ("속사", "Rapid Fire"),
        "desc": ("발사 간격 -16%", "Fire interval -16%"),
    },
    {
        "key": "multi",
        "max": 4,
        "name": ("분열탄", "Split Shot"),
        "desc": ("총알 발사 수 +1", "+1 bullet per shot"),
    },
    {
        "key": "pierce",
        "max": 4,
        "name": ("관통탄", "Piercing"),
        "desc": ("총알 관통 +1", "+1 pierce"),
    },
    {
        "key": "orb",
        "max": 5,
        "name": ("궤도 오브", "Orbit Orb"),
        "desc": ("주위를 도는 오브 +1", "+1 orbiting orb"),
    },
    {
        "key": "aura",
        "max": 5,
        "name": ("전격 장판", "Shock Aura"),
        "desc": ("주변 지속 피해 강화", "Stronger damage aura"),
    },
    {
        "key": "speed",
        "max": 5,
        "name": ("경량화", "Light Boots"),
        "desc": ("이동 속도 +10%", "Move speed +10%"),
    },
    {
        "key": "hp",
        "max": 6,
        "name": ("체력 증강", "Vitality"),
        "desc": ("최대 체력 +20, 즉시 회복", "+20 max HP, heal now"),
    },
    {
        "key": "regen",
        "max": 5,
        "name": ("재생", "Regeneration"),
        "desc": ("초당 체력 +0.6", "+0.6 HP per second"),
    },
    {
        "key": "magnet",
        "max": 4,
        "name": ("자력 코일", "Magnet Coil"),
        "desc": ("경험치 흡수 범위 +45%", "Pickup range +45%"),
    },
    {
        "key": "xp",
        "max": 4,
        "name": ("학습 가속", "Fast Learner"),
        "desc": ("경험치 획득 +20%", "XP gain +20%"),
    },
]

# 적 종류: (이미지, 체력, 속도, 접촉피해, 경험치, 반지름)
ENEMY_TYPES = {
    "grunt": dict(img="enemy_grunt", hp=14, speed=80, dmg=8, xp=1, r=11),
    "runner": dict(img="enemy_runner", hp=7, speed=160, dmg=6, xp=2, r=10),
    "tank": dict(img="enemy_tank", hp=70, speed=53, dmg=16, xp=5, r=17),
    "boss": dict(img="enemy_boss", hp=900, speed=60, dmg=26, xp=60, r=28),
}


# ----------------------------------------------------------------- 유틸
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def norm(dx, dy):
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return 0.0, 0.0, 0.0
    return dx / d, dy / d, d


def move_and_collide(grid, ent, dx, dy):
    """원형 개체를 축별로 이동시키며 벽에 밀어낸다."""
    r, t = ent.r, grid.tile
    # X축
    ent.x += dx
    if dx:
        ty0, ty1 = int((ent.y - r) // t), int((ent.y + r) // t)
        tx = int((ent.x + (r if dx > 0 else -r)) // t)
        for ty in range(ty0, ty1 + 1):
            if grid.is_solid(tx, ty):
                ent.x = tx * t - r - 0.01 if dx > 0 else (tx + 1) * t + r + 0.01
                ent.vx = 0.0
                break
    # Y축
    ent.y += dy
    if dy:
        tx0, tx1 = int((ent.x - r) // t), int((ent.x + r) // t)
        ty = int((ent.y + (r if dy > 0 else -r)) // t)
        for tx in range(tx0, tx1 + 1):
            if grid.is_solid(tx, ty):
                ent.y = ty * t - r - 0.01 if dy > 0 else (ty + 1) * t + r + 0.01
                ent.vy = 0.0
                break
    ent.x = clamp(ent.x, r, WORLD_W - r)
    ent.y = clamp(ent.y, r, WORLD_H - r)


class SpatialHash:
    """균등 격자 공간 해시.
    모든 쌍을 검사하면 O(n²)이지만, 적을 셀에 나눠 담으면
    셀당 평균 개체 수가 상수라는 가정 아래 기대 O(n)으로 줄어든다.
    (적 200마리 = 2만 쌍 → 수백 쌍)
    """

    CELL = 48

    def __init__(self):
        self.cells = {}

    def clear(self):
        self.cells.clear()

    def add(self, e):
        k = (int(e.x) // self.CELL, int(e.y) // self.CELL)
        self.cells.setdefault(k, []).append(e)

    def query(self, x, y, radius):
        c = self.CELL
        x0, x1 = int((x - radius) // c), int((x + radius) // c)
        y0, y1 = int((y - radius) // c), int((y + radius) // c)
        out = []
        for cy in range(y0, y1 + 1):
            for cx in range(x0, x1 + 1):
                lst = self.cells.get((cx, cy))
                if lst:
                    out.extend(lst)
        return out


# ----------------------------------------------------------------- 개체
class Player:
    def __init__(self, x, y, max_hp=100.0, xp_need_mul=1.0):
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.r = 12
        # [ChatGPT 수정] 선택한 난이도에 따라 시작 체력과 레벨업 요구 경험치를 적용한다.
        self.max_hp = float(max_hp)
        self.hp = self.max_hp
        self.xp_need_mul = float(xp_need_mul)
        self.speed = 190.0
        self.facing = 1
        self.level = 1
        self.xp = 0.0
        self.xp_need = 8.0 * self.xp_need_mul
        self.iframe = 0.0
        # 무기 스탯
        self.gun_dmg = 10.0
        self.gun_cd = 0.55
        self.gun_timer = 0.0
        self.gun_count = 1
        self.gun_pierce = 1
        self.gun_range = 460.0
        self.orbs = 0
        self.orb_angle = 0.0
        self.orb_dmg = 14.0
        self.aura_lv = 0
        self.aura_timer = 0.0
        self.regen = 0.0
        self.magnet = 90.0
        self.xp_mul = 1.0
        self.taken = {}  # 강화 key -> 레벨

    def apply_upgrade(self, up):
        k = up["key"]
        self.taken[k] = self.taken.get(k, 0) + 1
        if k == "dmg":
            self.gun_dmg *= 1.25
            self.orb_dmg *= 1.2
        elif k == "rate":
            self.gun_cd *= 0.84
        elif k == "multi":
            self.gun_count += 1
        elif k == "pierce":
            self.gun_pierce += 1
        elif k == "orb":
            self.orbs += 1
        elif k == "aura":
            self.aura_lv += 1
        elif k == "speed":
            self.speed *= 1.10
        elif k == "hp":
            self.max_hp += 20
            self.hp = min(self.max_hp, self.hp + 20)
        elif k == "regen":
            self.regen += 0.6
        elif k == "magnet":
            self.magnet *= 1.45
        elif k == "xp":
            self.xp_mul *= 1.2

    @property
    def aura_radius(self):
        return 0 if self.aura_lv == 0 else 68 + 16 * self.aura_lv

    @property
    def aura_dps(self):
        return 9.0 * self.aura_lv


class Enemy:
    __slots__ = (
        "x",
        "y",
        "vx",
        "vy",
        "r",
        "hp",
        "max_hp",
        "speed",
        "dmg",
        "xp",
        "kind",
        "img",
        "path",
        "path_i",
        "repath_t",
        "flash",
        "facing",
        "hit_cd",
        "elite",
        "los",
        "los_t",
        "lx",
        "ly",
        "chk_t",
        "force_t",
    )

    def __init__(
        self,
        kind,
        x,
        y,
        scale,
        elite=False,
        hp_mul=1.0,
        speed_mul=1.0,
        damage_mul=1.0,
    ):
        s = ENEMY_TYPES[kind]
        self.kind = kind
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.r = s["r"]
        # [ChatGPT 수정] 쉬움부터 몬스터 체력이 더 높고 난이도가 오를수록 추가 증가한다.
        self.max_hp = s["hp"] * scale * (2.2 if elite else 1.0) * hp_mul
        self.hp = self.max_hp
        # [ChatGPT 수정] 난이도가 높을수록 모든 몬스터의 이동 속도를 높인다.
        self.speed = s["speed"] * (0.9 if elite else 1.0) * speed_mul
        # [ChatGPT 수정] 난이도가 높을수록 몬스터의 접촉 공격력도 함께 증가한다.
        self.dmg = s["dmg"] * (1.0 + 0.35 * (scale - 1)) * damage_mul
        self.xp = s["xp"] * (3 if elite else 1)
        self.img = s["img"]
        self.path = None
        self.path_i = 0
        self.repath_t = random.uniform(0.0, 0.5)
        self.flash = 0.0
        self.facing = 1
        self.hit_cd = 0.0
        self.elite = elite
        self.los = False  # 마지막으로 계산한 가시선 결과(캐시)
        self.los_t = random.uniform(0.0, 0.15)  # 가시선 재계산 타이머
        self.lx, self.ly = x, y  # 끼임 감지용 이전 위치
        self.chk_t = random.uniform(0.0, 0.4)
        self.force_t = 0.0  # >0이면 가시선을 무시하고 A*를 강제


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "pierce", "life", "hit")

    def __init__(self, x, y, vx, vy, dmg, pierce):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.r = 5
        self.dmg = dmg
        self.pierce = pierce
        self.life = 1.6
        self.hit = set()


class Gem:
    __slots__ = ("x", "y", "vx", "vy", "value", "t", "heart")

    def __init__(self, x, y, value, heart=False):
        self.x, self.y = x, y
        self.vx = random.uniform(-40, 40)
        self.vy = random.uniform(-40, 40)
        self.value = value
        self.t = 0.0
        self.heart = heart


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color, size=3, speed=140):
        a = random.uniform(0, math.tau)
        s = random.uniform(0.3, 1.0) * speed
        self.x, self.y = x, y
        self.vx, self.vy = math.cos(a) * s, math.sin(a) * s
        self.life = self.max_life = random.uniform(0.25, 0.55)
        self.color = color
        self.size = size


class FloatText:
    __slots__ = ("x", "y", "text", "life", "color")

    def __init__(self, x, y, text, color=C_UI):
        self.x, self.y = x, y
        self.text = text
        self.life = 0.6
        self.color = color


# ----------------------------------------------------------------- 게임
class Game:
    def __init__(self, headless=False):
        pygame.init()
        pygame.display.set_caption("Pathfinder Survivors")
        self.headless = headless

        # [ChatGPT 수정] 게임 내부 해상도는 1024x640으로 유지하고,
        # 실제 모니터에는 비율을 유지해 확대해서 전체화면에서도 UI/맵이 깨지지 않게 한다.
        self.fullscreen = False
        self.display = pygame.display.set_mode((SW, SH))
        self.screen = pygame.Surface((SW, SH))
        self.clock = pygame.time.Clock()

        gen_assets.build()
        self.img = self.load_images()
        self.flash_img = {k: self.make_flash(v) for k, v in self.img.items()}

        kpath = find_korean_font()
        self.lang = "ko" if kpath else "en"
        self.T = TEXT[self.lang]
        s1, s2, s3, s4 = FONT_SIZES
        self.f_small = pygame.font.Font(kpath, s1)
        self.f_mid = pygame.font.Font(kpath, s2)
        self.f_big = pygame.font.Font(kpath, s3)
        self.f_huge = pygame.font.Font(kpath, s4)

        self.aura_cache = {}
        # [ChatGPT 수정] 기본값은 보통이며, 시작 화면 뒤에서 1/2/3으로 난이도를 고른다.
        self.difficulty_key = "normal"
        self.state = "title"
        self.show_paths = False
        self.reset()

    # ------------------------------------------------------ [ChatGPT 수정] 전체화면
    def toggle_fullscreen(self):
        """F11(또는 Alt+Enter)로 창모드/전체화면을 전환한다."""
        if self.headless:
            return
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.display = pygame.display.set_mode((SW, SH))

    def present_frame(self):
        """고정된 게임 화면을 실제 모니터 크기에 맞춰 비율 유지 확대한다."""
        dw, dh = self.display.get_size()
        if (dw, dh) == (SW, SH):
            self.display.blit(self.screen, (0, 0))
        else:
            scale = min(dw / SW, dh / SH)
            out_w = max(1, int(SW * scale))
            out_h = max(1, int(SH * scale))
            frame = pygame.transform.smoothscale(self.screen, (out_w, out_h))
            self.display.fill(C_BG)
            self.display.blit(frame, ((dw - out_w) // 2, (dh - out_h) // 2))
        pygame.display.flip()

    # ------------------------------------------------------ 리소스
    def load_images(self):
        d = gen_assets.ASSET_DIR
        out = {}
        for f in os.listdir(d):
            if f.endswith(".png"):
                out[f[:-4]] = pygame.image.load(os.path.join(d, f)).convert_alpha()
        return out

    @staticmethod
    def make_flash(surf):
        s = surf.copy()
        s.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
        return s

    # ------------------------------------------------------ 맵 생성
    def build_map(self):
        """바깥 테두리 + 랜덤 바위 군집. 생성 후 고립 지역은 벽으로 메운다."""
        grid = Grid(MAP_W, MAP_H, TILE)
        rng = random.Random()
        for x in range(MAP_W):
            grid.set_solid(x, 0)
            grid.set_solid(x, MAP_H - 1)
        for y in range(MAP_H):
            grid.set_solid(0, y)
            grid.set_solid(MAP_W - 1, y)

        cx, cy = MAP_W // 2, MAP_H // 2
        rock = set()
        for _ in range(46):  # 랜덤 워크로 덩어리 생성
            x = rng.randrange(3, MAP_W - 3)
            y = rng.randrange(3, MAP_H - 3)
            for _ in range(rng.randint(4, 16)):
                if abs(x - cx) > 5 or abs(y - cy) > 5:  # 시작 지점 주변은 비움
                    rock.add((x, y))
                x = clamp(x + rng.choice((-1, 0, 1)), 2, MAP_W - 3)
                y = clamp(y + rng.choice((-1, 0, 1)), 2, MAP_H - 3)
        # 긴 벽 몇 개 (여기서 우회 경로가 필요해진다)
        walls = set()
        for _ in range(9):
            x = rng.randrange(6, MAP_W - 10)
            y = rng.randrange(5, MAP_H - 6)
            ln = rng.randint(7, 16)
            if rng.random() < 0.5:
                seg = [(x + i, y) for i in range(ln)]
            else:
                seg = [(x, y + i) for i in range(min(ln, MAP_H - 6 - y))]
            if not seg:
                continue
            gap = rng.randrange(len(seg))  # 통로 한 칸은 반드시 뚫어 둔다
            for i, (tx, ty) in enumerate(seg):
                if abs(i - gap) <= 0:
                    continue
                if abs(tx - cx) > 5 or abs(ty - cy) > 5:
                    walls.add((tx, ty))
        for t in rock | walls:
            grid.set_solid(*t)

        # 연결성 보정: 중앙에서 못 가는 빈 칸은 아예 벽으로 만든다
        reach = grid.flood_reachable((cx, cy))
        for y in range(MAP_H):
            for x in range(MAP_W):
                if grid.walkable(x, y) and (x, y) not in reach:
                    grid.set_solid(x, y)
        self.rock_tiles = {t for t in rock if t not in walls}
        return grid

    def render_background(self):
        """월드 전체를 큰 Surface에 한 번만 그려 두고 매 프레임 잘라 쓴다."""
        bg = pygame.Surface((WORLD_W, WORLD_H)).convert()
        f0, f1 = self.img["floor0"], self.img["floor1"]
        wall, rockimg = self.img["wall"], self.img["rock"]
        rng = random.Random(7)
        for ty in range(MAP_H):
            for tx in range(MAP_W):
                px, py = tx * TILE, ty * TILE
                bg.blit(f0 if rng.random() < 0.85 else f1, (px, py))
                if self.grid.is_solid(tx, ty):
                    if (tx, ty) in self.rock_tiles:
                        bg.blit(rockimg, (px, py))
                    else:
                        bg.blit(wall, (px, py))
        return bg

    def render_minimap(self):
        s = pygame.Surface((MAP_W * 2, MAP_H * 2)).convert_alpha()
        s.fill((10, 12, 18, 190))
        for ty in range(MAP_H):
            for tx in range(MAP_W):
                if self.grid.is_solid(tx, ty):
                    s.fill((78, 84, 100, 230), (tx * 2, ty * 2, 2, 2))
        return s

    # ------------------------------------------------------ 초기화
    def reset(self):
        self.grid = self.build_map()
        self.bg = self.render_background()
        self.minimap_bg = self.render_minimap()
        self.flow = FlowField(self.grid)
        self.flow_timer = 0.0

        sx, sy = self.grid.tile_center(MAP_W // 2, MAP_H // 2)
        # [ChatGPT 수정] 재시작해도 현재 선택한 난이도를 그대로 유지한다.
        diff = DIFFICULTIES[self.difficulty_key]
        # [ChatGPT 수정] 선택한 난이도의 몬스터 체력·속도·공격력 배율을 스폰에 적용한다.
        self.enemy_hp_mul = diff["enemy_hp_mul"]
        self.enemy_speed_mul = diff["enemy_speed_mul"]
        self.enemy_damage_mul = diff["enemy_damage_mul"]
        self.player = Player(sx, sy, diff["hp"], diff["xp_mul"])
        self.enemies = []
        self.bullets = []
        self.gems = []
        self.particles = []
        self.texts = []
        self.hash = SpatialHash()

        self.time = 0.0
        self.kills = 0
        self.wave = 1
        self.wave_phase = "intro"
        self.wave_timer = WAVE_INTRO_TIME
        self.wave_spawn_timer = 0.0
        self.wave_queue = self.build_wave_queue(self.wave)
        self.wave_total = len(self.wave_queue)
        self.wave_spawned = 0
        self.wave_banner = (f"{self.T['wave']} {self.wave}", WAVE_INTRO_TIME)
        self.shake = 0.0
        self.banner = ("", 0.0)
        self.choices = []
        self.path_calls = 0
        self.path_calls_shown = 0
        self.path_timer = 0.0
        self.cam = [0.0, 0.0]
        self.flow.rebuild(self.grid.world_to_tile(sx, sy))

    # ------------------------------------------------------ [ChatGPT 수정] 웨이브 / 스폰
    def wave_enemy_count(self, wave):
        """웨이브가 올라갈수록 적 수가 선형으로 증가한다."""
        return WAVE_BASE_ENEMIES + (wave - 1) * WAVE_ENEMY_GROWTH

    def wave_kind_weights(self, wave):
        """웨이브별 몬스터 구성비.

        1~2: 그런트만
        3~4: 러너 추가
        5+: 탱커 추가
        후반으로 갈수록 러너/탱커 비중이 커진다.
        """
        grunt = max(24.0, 100.0 - wave * 3.5)
        runner = 0.0 if wave < 3 else min(48.0, 16.0 + (wave - 3) * 2.2)
        tank = 0.0 if wave < 5 else min(38.0, 7.0 + (wave - 5) * 1.5)
        return [("grunt", grunt), ("runner", runner), ("tank", tank)]

    def pick_wave_kind(self, wave):
        cand = [(kind, w) for kind, w in self.wave_kind_weights(wave) if w > 0]
        total = sum(w for _, w in cand)
        r = random.uniform(0.0, total)
        for kind, weight in cand:
            r -= weight
            if r <= 0:
                return kind
        return cand[-1][0]

    def build_wave_queue(self, wave):
        """이번 웨이브에서 등장할 적 목록을 미리 만든다.

        적 수가 ENEMY_CAP보다 커져도 큐에 남겨 두었다가 자리가 생기는 대로
        이어서 스폰하므로 웨이브 수에는 상한이 없다.
        """
        queue = []
        count = self.wave_enemy_count(wave)
        elite_chance = 0.0
        if wave >= ELITE_UNLOCK_WAVE:
            elite_chance = min(0.30, ELITE_CHANCE_BASE + (wave - ELITE_UNLOCK_WAVE) * ELITE_CHANCE_GROWTH)

        for _ in range(count):
            kind = self.pick_wave_kind(wave)
            elite = elite_chance > 0 and random.random() < elite_chance
            queue.append((kind, elite))

        # 5웨이브마다 보스. 15웨이브부터는 보스 수도 조금씩 늘어난다.
        if wave % BOSS_EVERY == 0:
            boss_count = 1 + wave // 15
            for _ in range(boss_count):
                queue.append(("boss", False))

        random.shuffle(queue)
        return queue

    def begin_wave(self, wave):
        self.wave = wave
        self.wave_phase = "intro"
        self.wave_timer = WAVE_INTRO_TIME
        self.wave_spawn_timer = 0.0
        self.wave_queue = self.build_wave_queue(wave)
        self.wave_total = len(self.wave_queue)
        self.wave_spawned = 0
        self.wave_banner = (f"{self.T['wave']} {wave}", WAVE_INTRO_TIME)

    def update_wave(self, dt):
        """시간제 무한 스폰 대신 '전멸 → 다음 웨이브' 방식으로 진행한다."""
        if self.wave_phase == "intro":
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.wave_phase = "spawning"
                self.wave_spawn_timer = 0.0
            return

        if self.wave_phase == "clear":
            self.wave_timer -= dt
            if self.wave_timer <= 0:
                self.begin_wave(self.wave + 1)
            return

        # 현재 웨이브의 적을 빠르게 순차 등장시킨다.
        if self.wave_phase == "spawning":
            self.wave_spawn_timer -= dt
            while (
                self.wave_spawn_timer <= 0
                and self.wave_queue
                and len(self.enemies) < ENEMY_CAP
            ):
                kind, elite = self.wave_queue.pop()
                self.spawn(kind, elite)
                self.wave_spawned += 1
                self.wave_spawn_timer += WAVE_SPAWN_INTERVAL
                if kind == "boss":
                    self.banner = (self.T["boss"], 2.5)
                    self.shake = max(self.shake, 10.0)

            if not self.wave_queue:
                self.wave_phase = "combat"

        # 큐도 비었고 살아 있는 적도 없으면 그 웨이브 클리어.
        if self.wave_phase in ("spawning", "combat") and not self.wave_queue and not self.enemies:
            self.wave_phase = "clear"
            self.wave_timer = WAVE_CLEAR_TIME
            self.wave_banner = (
                f"{self.T['wave']} {self.wave}  {self.T['wave_clear']}",
                WAVE_CLEAR_TIME,
            )

    def wave_remaining(self):
        """아직 스폰되지 않은 적 + 현재 살아 있는 적."""
        return len(self.wave_queue) + len(self.enemies)

    def spawn(self, kind, elite=False):
        """화면 밖 원주 위에서 균등한 각도로 등장.
        θ ~ U[0, 2π), r = 상수 → 플레이어를 중심으로 한 원 위의 균등분포."""
        p = self.player
        # 플레이 시간이 아니라 웨이브를 기준으로 강해져서, 천천히 플레이해도 난이도가 튀지 않는다.
        scale = 1.0 + (self.wave - 1) * WAVE_HP_GROWTH
        for _ in range(12):
            a = random.uniform(0, math.tau)
            rad = random.uniform(620, 760)
            x = clamp(p.x + math.cos(a) * rad, TILE, WORLD_W - TILE)
            y = clamp(p.y + math.sin(a) * rad, TILE, WORLD_H - TILE)
            tx, ty = self.grid.world_to_tile(x, y)
            spot = self.grid.nearest_walkable(tx, ty, 4)
            if spot:
                wx, wy = self.grid.tile_center(*spot)
                self.enemies.append(
                    Enemy(
                        kind,
                        wx,
                        wy,
                        scale,
                        elite,
                        self.enemy_hp_mul,
                        self.enemy_speed_mul,
                        self.enemy_damage_mul,
                    )
                )
                return

    # ------------------------------------------------------ 업데이트
    def update(self, dt, keys):
        p = self.player
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 26)

        # --- 입력/이동
        mx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        my = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (
            keys[pygame.K_w] or keys[pygame.K_UP]
        )
        # [ChatGPT 수정] 대각선(W+A, W+D 등)에서도 X/Y축 속도를 깎지 않는다.
        # 기존 정규화는 대각선에서 각 축을 약 70.7%로 줄였기 때문에 체감상 느리게 느껴질 수 있었다.
        if mx:
            p.facing = 1 if mx > 0 else -1
        move_and_collide(self.grid, p, mx * p.speed * dt, my * p.speed * dt)

        p.iframe = max(0.0, p.iframe - dt)
        if p.regen:
            p.hp = min(p.max_hp, p.hp + p.regen * dt)

        # --- 공간 해시 재구성
        self.hash.clear()
        for e in self.enemies:
            self.hash.add(e)

        # --- flow field 갱신 (A* 예산 초과 시의 대체 경로)
        self.flow_timer -= dt
        if self.flow_timer <= 0:
            self.flow_timer = FLOW_REBUILD_INTERVAL
            self.flow.rebuild(self.grid.world_to_tile(p.x, p.y))

        self.update_enemies(dt)
        self.update_weapons(dt)
        self.update_bullets(dt)
        self.update_pickups(dt)

        for lst, attr in ((self.particles, "life"), (self.texts, "life")):
            for o in lst:
                o.life -= dt
        for o in self.particles:
            o.x += o.vx * dt
            o.y += o.vy * dt
            o.vx *= 0.92
            o.vy *= 0.92
        for o in self.texts:
            o.y -= 34 * dt
        self.particles = [o for o in self.particles if o.life > 0]
        self.texts = [o for o in self.texts if o.life > 0]

        self.update_wave(dt)

        # 초당 A* 호출 수 집계 (디버그 표시용)
        self.path_timer += dt
        if self.path_timer >= 1.0:
            self.path_timer -= 1.0
            self.path_calls_shown = self.path_calls
            self.path_calls = 0

        if self.banner[1] > 0:
            self.banner = (self.banner[0], self.banner[1] - dt)
        if self.wave_banner[1] > 0:
            self.wave_banner = (self.wave_banner[0], self.wave_banner[1] - dt)
        if p.hp <= 0:
            self.state = "over"

    # ---------------- 적 AI (여기가 A* 파트) ----------------
    def update_enemies(self, dt):
        p = self.player
        grid = self.grid
        budget = PATH_BUDGET_PER_FRAME
        ptile = grid.world_to_tile(p.x, p.y)

        for e in self.enemies:
            e.flash = max(0.0, e.flash - dt)
            e.hit_cd = max(0.0, e.hit_cd - dt)
            e.repath_t -= dt

            dx, dy = p.x - e.x, p.y - e.y
            dist = math.hypot(dx, dy)

            # 끼임 감지: 일정 시간 동안 거의 못 움직였다면 벽 모서리에 걸린 것.
            # 이때는 가시선이 뚫려 보여도 강제로 A*를 돌려 우회시킨다.
            e.chk_t -= dt
            e.force_t = max(0.0, e.force_t - dt)
            if e.chk_t <= 0:
                e.chk_t = 0.35
                if dist > e.r + p.r + 6 and math.hypot(e.x - e.lx, e.y - e.ly) < 10:
                    e.force_t = 1.2
                    e.repath_t = 0.0
                e.lx, e.ly = e.x, e.y

            # 가시선 판정은 비싸므로 매 프레임이 아니라 0.1초 간격으로만 갱신한다.
            e.los_t -= dt
            if e.los_t <= 0:
                e.los_t = random.uniform(0.09, 0.17)
                e.los = dist < 800 and grid.line_clear(e.x, e.y, p.x, p.y, e.r * 0.85)

            # 1) 가시선이 뚫려 있으면 길찾기 자체가 불필요 → 그냥 직진
            if e.los and e.force_t <= 0:
                e.path = None
                desired = (dx / max(dist, 1e-6), dy / max(dist, 1e-6))
            else:
                # 2) 막혀 있으면 A*. 단 프레임당 호출 수를 제한한다.
                need_new = (e.path is None) or (e.repath_t <= 0)
                if need_new and budget > 0:
                    budget -= 1
                    self.path_calls += 1
                    e.repath_t = random.uniform(0.35, 0.75)
                    raw = astar(grid, grid.world_to_tile(e.x, e.y), ptile, 1500)
                    if raw:
                        # 3) string pulling으로 계단 모양 경로를 직선화
                        e.path = smooth_path(grid, raw, e.r)
                        e.path_i = 1 if len(e.path) > 1 else 0
                    else:
                        e.path = None

                if e.path and e.path_i < len(e.path):
                    wx, wy = e.path[e.path_i]
                    if math.hypot(wx - e.x, wy - e.y) < 14:
                        e.path_i += 1
                        if e.path_i >= len(e.path):
                            e.path = None
                if e.path and e.path_i < len(e.path):
                    wx, wy = e.path[e.path_i]
                    ndx, ndy, _ = norm(wx - e.x, wy - e.y)
                    desired = (ndx, ndy)
                else:
                    # 4) 예산 초과 등으로 경로가 없으면 flow field 방향 사용
                    fd = self.flow.direction(*grid.world_to_tile(e.x, e.y))
                    desired = fd if fd else (dx / max(dist, 1e-6), dy / max(dist, 1e-6))

            # 5) 분리(separation) 조향: 서로 겹쳐 한 점에 뭉치는 걸 막는다
            # 겹친 이웃 전부를 계산하면 적이 뭉쳤을 때 비용이 제곱으로 튄다.
            # 밀어내는 방향만 알면 되므로 가까운 몇 마리에서 끊어도 결과는 같다.
            sx = sy = 0.0
            near = 0
            for o in self.hash.query(e.x, e.y, 34):
                if o is e:
                    continue
                ox, oy = e.x - o.x, e.y - o.y
                d2 = ox * ox + oy * oy
                lim = (e.r + o.r) * 1.05
                if 1e-6 < d2 < lim * lim:
                    inv = 1.0 / math.sqrt(d2)
                    sx += ox * inv
                    sy += oy * inv
                    near += 1
                    if near >= SEPARATION_NEIGHBORS:
                        break
            if sx or sy:
                nx, ny, _ = norm(sx, sy)
                desired = (desired[0] + nx * 0.9, desired[1] + ny * 0.9)

            ddx, ddy, _ = norm(desired[0], desired[1])
            tvx, tvy = ddx * e.speed, ddy * e.speed
            k = min(1.0, 9.0 * dt)  # 속도 보간 → 방향 전환이 부드럽다
            e.vx += (tvx - e.vx) * k
            e.vy += (tvy - e.vy) * k
            if e.vx:
                e.facing = 1 if e.vx > 0 else -1
            move_and_collide(self.grid, e, e.vx * dt, e.vy * dt)

            # 6) 플레이어 접촉 피해
            if dist < e.r + p.r and p.iframe <= 0:
                p.hp -= e.dmg
                p.iframe = 0.55
                self.shake = max(self.shake, 7.0)
                for _ in range(8):
                    self.particles.append(Particle(p.x, p.y, C_HP))

    # ---------------- 무기 ----------------
    def nearest_enemy(self, x, y, rng):
        best, bd = None, rng * rng
        for e in self.hash.query(x, y, rng):
            d2 = (e.x - x) ** 2 + (e.y - y) ** 2
            if d2 < bd:
                best, bd = e, d2
        return best

    def update_weapons(self, dt):
        p = self.player
        # 자동 조준 사격
        p.gun_timer -= dt
        if p.gun_timer <= 0:
            tgt = self.nearest_enemy(p.x, p.y, p.gun_range)
            if tgt:
                p.gun_timer = p.gun_cd
                base = math.atan2(tgt.y - p.y, tgt.x - p.x)
                spread = 0.16
                for i in range(p.gun_count):
                    a = base + (i - (p.gun_count - 1) / 2) * spread
                    self.bullets.append(
                        Bullet(
                            p.x,
                            p.y,
                            math.cos(a) * 800,
                            math.sin(a) * 800,
                            p.gun_dmg,
                            p.gun_pierce,
                        )
                    )
        # 궤도 오브
        if p.orbs:
            p.orb_angle += dt * 2.6
            for i in range(p.orbs):
                a = p.orb_angle + math.tau * i / p.orbs
                ox, oy = p.x + math.cos(a) * 76, p.y + math.sin(a) * 76
                for e in self.hash.query(ox, oy, 22):
                    if (
                        e.hit_cd <= 0
                        and (e.x - ox) ** 2 + (e.y - oy) ** 2 < (e.r + 12) ** 2
                    ):
                        e.hit_cd = 0.35
                        self.damage(e, p.orb_dmg)
        # 전격 장판
        if p.aura_lv:
            p.aura_timer -= dt
            if p.aura_timer <= 0:
                p.aura_timer = 0.4
                rad = p.aura_radius
                for e in self.hash.query(p.x, p.y, rad):
                    if (e.x - p.x) ** 2 + (e.y - p.y) ** 2 < rad * rad:
                        self.damage(e, p.aura_dps * 0.4, silent=True)

    def update_bullets(self, dt):
        alive = []
        for b in self.bullets:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt
            if b.life <= 0:
                continue
            tx, ty = self.grid.world_to_tile(b.x, b.y)
            if self.grid.is_solid(tx, ty):
                for _ in range(4):
                    self.particles.append(Particle(b.x, b.y, (200, 200, 210), 2, 90))
                continue
            dead = False
            for e in self.hash.query(b.x, b.y, 26):
                if id(e) in b.hit:
                    continue
                if (e.x - b.x) ** 2 + (e.y - b.y) ** 2 < (e.r + b.r) ** 2:
                    b.hit.add(id(e))
                    self.damage(e, b.dmg)
                    b.pierce -= 1
                    if b.pierce <= 0:
                        dead = True
                        break
            if not dead:
                alive.append(b)
        self.bullets = alive

    def damage(self, e, amount, silent=False):
        e.hp -= amount
        e.flash = 0.09
        if not silent:
            self.texts.append(
                FloatText(
                    e.x, e.y - e.r, str(int(amount)), C_GOLD if amount > 20 else C_UI
                )
            )
        if e.hp <= 0 and e in self.enemies:
            self.enemies.remove(e)
            self.kills += 1
            col = (150, 220, 160) if e.kind == "grunt" else (240, 150, 90)
            for _ in range(10 if e.kind != "boss" else 40):
                self.particles.append(Particle(e.x, e.y, col, 3, 200))
            self.gems.append(Gem(e.x, e.y, e.xp))
            if e.kind == "boss":
                self.shake = 14.0
                for _ in range(6):
                    self.gems.append(Gem(e.x, e.y, 10))
            if random.random() < (0.02 if e.kind != "boss" else 1.0):
                self.gems.append(Gem(e.x, e.y, 0, heart=True))

    def update_pickups(self, dt):
        p = self.player
        keep = []
        for g in self.gems:
            g.t += dt
            dx, dy = p.x - g.x, p.y - g.y
            d = math.hypot(dx, dy)
            if d < p.magnet:
                s = 460 if d < p.magnet * 0.5 else 240
                g.x += dx / max(d, 1e-6) * s * dt
                g.y += dy / max(d, 1e-6) * s * dt
            else:
                g.x += g.vx * dt
                g.y += g.vy * dt
                g.vx *= 0.9
                g.vy *= 0.9
            if d < 18:
                if g.heart:
                    p.hp = min(p.max_hp, p.hp + 25)
                    self.texts.append(FloatText(p.x, p.y - 20, "+25", C_HP))
                else:
                    p.xp += g.value * p.xp_mul
                continue
            keep.append(g)
        self.gems = keep

        while p.xp >= p.xp_need:
            p.xp -= p.xp_need
            p.level += 1
            # [ChatGPT 수정] 난이도가 높을수록 다음 능력 선택까지 더 많은 경험치가 필요하다.
            p.xp_need = (6 + 5 * p.level) * p.xp_need_mul
            self.open_levelup()

    def open_levelup(self):
        pool = [u for u in UPGRADES if self.player.taken.get(u["key"], 0) < u["max"]]
        random.shuffle(pool)
        self.choices = pool[:3]
        if self.choices:
            self.state = "levelup"

    # ------------------------------------------------------ 그리기
    def camera(self):
        p = self.player
        cx = clamp(p.x - SW / 2, 0, WORLD_W - SW)
        cy = clamp(p.y - SH / 2, 0, WORLD_H - SH)
        if self.shake > 0.2:
            cx += random.uniform(-self.shake, self.shake)
            cy += random.uniform(-self.shake, self.shake)
        return clamp(cx, 0, WORLD_W - SW), clamp(cy, 0, WORLD_H - SH)

    def blit_center(self, img, x, y, cam, flip=False, flash=False):
        s = self.flash_img[img] if flash else self.img[img]
        if flip:
            s = pygame.transform.flip(s, True, False)
        self.screen.blit(
            s, (x - cam[0] - s.get_width() // 2, y - cam[1] - s.get_height() // 2)
        )

    def aura_surface(self, r):
        if r not in self.aura_cache:
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (110, 232, 236, 34), (r, r), r)
            pygame.draw.circle(s, (150, 245, 250, 90), (r, r), r, 2)
            self.aura_cache[r] = s
        return self.aura_cache[r]

    def draw_world(self):
        cam = self.camera()
        self.screen.blit(self.bg, (0, 0), pygame.Rect(cam[0], cam[1], SW, SH))
        p = self.player

        # 디버그: A* 경로
        if self.show_paths:
            for e in self.enemies:
                if not (-40 < e.x - cam[0] < SW + 40 and -40 < e.y - cam[1] < SH + 40):
                    continue  # 화면 밖 적의 경로까지 그리면 알아볼 수 없다
                if e.path and e.path_i < len(e.path):
                    pts = [(e.x - cam[0], e.y - cam[1])] + [
                        (wx - cam[0], wy - cam[1]) for wx, wy in e.path[e.path_i :]
                    ]
                    if len(pts) > 1:
                        pygame.draw.lines(self.screen, (255, 120, 190), False, pts, 2)
                    for q in pts[1:]:
                        pygame.draw.circle(
                            self.screen, (255, 200, 120), (int(q[0]), int(q[1])), 3
                        )

        # 오라
        if p.aura_lv:
            r = p.aura_radius
            self.screen.blit(self.aura_surface(r), (p.x - cam[0] - r, p.y - cam[1] - r))

        # 젬 / 하트
        for g in self.gems:
            bob = math.sin(g.t * 6) * 2
            self.blit_center("heart" if g.heart else "gem", g.x, g.y + bob, cam)

        # 적
        for e in self.enemies:
            if -60 < e.x - cam[0] < SW + 60 and -60 < e.y - cam[1] < SH + 60:
                if e.elite:
                    pygame.draw.circle(
                        self.screen,
                        (255, 200, 90),
                        (int(e.x - cam[0]), int(e.y - cam[1])),
                        e.r + 4,
                        2,
                    )
                self.blit_center(e.img, e.x, e.y, cam, e.facing < 0, e.flash > 0)
                if e.hp < e.max_hp:
                    w = e.r * 2
                    x0, y0 = e.x - cam[0] - e.r, e.y - cam[1] - e.r - 8
                    pygame.draw.rect(self.screen, (30, 12, 16), (x0, y0, w, 3))
                    pygame.draw.rect(
                        self.screen, C_HP, (x0, y0, w * (e.hp / e.max_hp), 3)
                    )

        # 궤도 오브
        for i in range(p.orbs):
            a = p.orb_angle + math.tau * i / p.orbs
            self.blit_center("orb", p.x + math.cos(a) * 76, p.y + math.sin(a) * 76, cam)

        # 플레이어 (무적 시간 동안 깜빡임)
        if not (p.iframe > 0 and int(p.iframe * 20) % 2 == 0):
            self.blit_center("player", p.x, p.y, cam, p.facing < 0)

        # 총알
        for b in self.bullets:
            img = pygame.transform.rotate(
                self.img["bullet"], -math.degrees(math.atan2(b.vy, b.vx))
            )
            self.screen.blit(
                img,
                (
                    b.x - cam[0] - img.get_width() / 2,
                    b.y - cam[1] - img.get_height() / 2,
                ),
            )

        # 파티클 / 데미지 숫자
        for o in self.particles:
            a = o.life / o.max_life
            pygame.draw.rect(
                self.screen,
                o.color,
                (o.x - cam[0], o.y - cam[1], o.size * a + 1, o.size * a + 1),
            )
        for o in self.texts:
            surf = self.f_small.render(o.text, FONT_ANTIALIAS, o.color)
            surf.set_alpha(int(255 * min(1, o.life / 0.6)))
            self.screen.blit(surf, (o.x - cam[0] - surf.get_width() / 2, o.y - cam[1]))

        return cam

    def draw_hud(self, cam):
        p = self.player
        T = self.T
        # 체력바
        pygame.draw.rect(self.screen, (0, 0, 0, 120), (16, 14, 264, 22))
        pygame.draw.rect(self.screen, (48, 20, 26), (18, 16, 260, 18))
        pygame.draw.rect(self.screen, C_HP, (18, 16, 260 * max(0, p.hp) / p.max_hp, 18))
        hp_s = self.f_small.render(
            f"{int(max(0, p.hp))} / {int(p.max_hp)}", FONT_ANTIALIAS, C_UI
        )
        self.screen.blit(hp_s, (148 - hp_s.get_width() // 2, 17))
        # 경험치바
        pygame.draw.rect(self.screen, (18, 42, 48), (18, 40, 260, 10))
        pygame.draw.rect(
            self.screen, C_XP, (18, 40, 260 * clamp(p.xp / p.xp_need, 0, 1), 10)
        )
        self.screen.blit(
            self.f_mid.render(f"{T['lv']} {p.level}", FONT_ANTIALIAS, C_GOLD), (288, 20)
        )

        # [ChatGPT 수정] HP/레벨 UI와 웨이브 정보가 겹치지 않도록 중앙 정보를 두 줄로 분리한다.
        m, s = divmod(int(self.time), 60)
        remaining = self.wave_remaining()
        status_info = f"{T['time']} {m:02d}:{s:02d}   {T['kill']} {self.kills}"
        wave_info = f"{T['wave']} {self.wave}   {T['remaining']} {remaining}"
        status_surf = self.f_mid.render(status_info, FONT_ANTIALIAS, C_UI)
        wave_surf = self.f_small.render(wave_info, FONT_ANTIALIAS, C_GOLD)
        hud_center_x = 590
        self.screen.blit(
            status_surf, (hud_center_x - status_surf.get_width() // 2, 12)
        )
        self.screen.blit(
            wave_surf, (hud_center_x - wave_surf.get_width() // 2, 37)
        )

        # 미니맵
        mm = self.minimap_bg.copy()
        for e in self.enemies:
            mm.fill((236, 92, 92), (int(e.x / TILE * 2), int(e.y / TILE * 2), 2, 2))
        mm.fill(
            (120, 220, 255), (int(p.x / TILE * 2) - 1, int(p.y / TILE * 2) - 1, 4, 4)
        )
        self.screen.blit(mm, (SW - mm.get_width() - 14, 14))

        if self.show_paths:
            dbg = self.f_small.render(
                f"{T['paths']}: ON   A*/s {self.path_calls_shown}   enemies {len(self.enemies)}",
                FONT_ANTIALIAS,
                (255, 160, 200),
            )
            self.screen.blit(dbg, (16, SH - 26))

        if self.wave_banner[1] > 0:
            w = self.f_huge.render(self.wave_banner[0], FONT_ANTIALIAS, C_GOLD)
            w.set_alpha(int(255 * clamp(self.wave_banner[1] / 0.8, 0, 1)))
            self.screen.blit(w, (SW // 2 - w.get_width() // 2, 86))

        if self.banner[1] > 0:
            b = self.f_big.render(self.banner[0], FONT_ANTIALIAS, (255, 120, 120))
            b.set_alpha(int(255 * clamp(self.banner[1] / 1.0, 0, 1)))
            self.screen.blit(b, (SW // 2 - b.get_width() // 2, 146))

    def draw_levelup(self):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((8, 10, 16, 190))
        self.screen.blit(ov, (0, 0))
        t = self.f_huge.render(self.T["levelup"], FONT_ANTIALIAS, C_GOLD)
        self.screen.blit(t, (SW // 2 - t.get_width() // 2, 70))
        sub = self.f_small.render(self.T["choose"], FONT_ANTIALIAS, C_DIM)
        self.screen.blit(sub, (SW // 2 - sub.get_width() // 2, 138))

        li = 0 if self.lang == "ko" else 1
        cw, ch = 280, 190
        for i, up in enumerate(self.choices):
            x = SW // 2 + (i - 1) * (cw + 24) - cw // 2
            y = 200
            pygame.draw.rect(self.screen, C_PANEL, (x, y, cw, ch), border_radius=10)
            pygame.draw.rect(self.screen, C_XP, (x, y, cw, ch), 2, border_radius=10)
            num = self.f_huge.render(str(i + 1), FONT_ANTIALIAS, (60, 70, 92))
            self.screen.blit(
                num, (x + cw - num.get_width() - 14, y + ch - num.get_height() - 6)
            )
            name = self.f_big.render(up["name"][li], FONT_ANTIALIAS, C_UI)
            self.screen.blit(name, (x + 20, y + 26))
            desc = self.f_small.render(up["desc"][li], FONT_ANTIALIAS, C_DIM)
            self.screen.blit(desc, (x + 20, y + 78))
            cur = self.player.taken.get(up["key"], 0)
            for k in range(up["max"]):
                col = C_GOLD if k < cur else (58, 64, 82)
                pygame.draw.rect(self.screen, col, (x + 20 + k * 16, y + 118, 12, 8))

    def draw_center_text(self, lines):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((8, 10, 16, 205))
        self.screen.blit(ov, (0, 0))
        y = SH // 2 - 110
        for text, font, col in lines:
            s = font.render(text, FONT_ANTIALIAS, col)
            self.screen.blit(s, (SW // 2 - s.get_width() // 2, y))
            y += s.get_height() + 16

    # ------------------------------------------------------ 루프
    def run(self, max_frames=None):
        frames = 0
        running = True
        while running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    running = self.on_key(ev.key)
            keys = pygame.key.get_pressed()

            if self.state == "play":
                self.update(dt, keys)

            if self.state == "title":
                self.screen.fill(C_BG)
                self.draw_center_text(
                    [
                        (self.T["title"], self.f_huge, C_XP),
                        (self.T["sub"], self.f_mid, C_UI),
                        (self.T["start"], self.f_big, C_GOLD),
                        (self.T["ctrl"], self.f_small, C_DIM),
                    ]
                )
            elif self.state == "difficulty":
                # [ChatGPT 수정] 게임 시작 전에 쉬움 / 보통 / 어려움 / 매우 어려움 선택 화면을 표시한다.
                self.screen.fill(C_BG)
                self.draw_center_text(
                    [
                        (self.T["difficulty"], self.f_huge, C_XP),
                        (self.T["difficulty_hint"], self.f_big, C_GOLD),
                        (
                            f"{self.T['easy']}  HP 130  ·  XP 85%  ·  ENEMY HP 110%  ·  SPEED 100%  ·  DMG 90%",
                            self.f_small,
                            C_UI,
                        ),
                        (
                            f"{self.T['normal']}  HP 100  ·  XP 100%  ·  ENEMY HP 120%  ·  SPEED 112%  ·  DMG 100%",
                            self.f_small,
                            C_UI,
                        ),
                        (
                            f"{self.T['hard']}  HP 75  ·  XP 125%  ·  ENEMY HP 140%  ·  SPEED 128%  ·  DMG 130%",
                            self.f_small,
                            C_HP,
                        ),
                        (
                            f"{self.T['very_hard']}  HP 55  ·  XP 150%  ·  ENEMY HP 170%  ·  SPEED 145%  ·  DMG 160%",
                            self.f_small,
                            C_HP,
                        ),
                    ]
                )
            else:
                cam = self.draw_world()
                self.draw_hud(cam)
                if self.state == "levelup":
                    self.draw_levelup()
                elif self.state == "pause":
                    self.draw_center_text(
                        [
                            (self.T["pause"], self.f_huge, C_UI),
                            (self.T["resume"], self.f_mid, C_DIM),
                        ]
                    )
                elif self.state == "over":
                    m, s = divmod(int(self.time), 60)
                    self.draw_center_text(
                        [
                            (self.T["over"], self.f_huge, C_HP),
                            (
                                f"{self.T['survived']}  {m:02d}:{s:02d}",
                                self.f_big,
                                C_UI,
                            ),
                            (
                                f"{self.T['lv']} {self.player.level}   {self.T['kill']} {self.kills}",
                                self.f_mid,
                                C_DIM,
                            ),
                            (self.T["restart"], self.f_mid, C_GOLD),
                            # [ChatGPT 수정] 게임 오버 화면에서 H 키로 홈(타이틀)으로 돌아갈 수 있게 안내한다.
                            (self.T["home"], self.f_mid, C_UI),
                        ]
                    )

            # [ChatGPT 수정] 창모드/전체화면 모두 같은 1024x640 게임 화면을 비율 유지 출력한다.
            self.present_frame()

            frames += 1
            if self.headless:
                self.auto_play(frames)
            if max_frames and frames >= max_frames:
                running = False
        pygame.quit()

    def on_key(self, key):
        # [ChatGPT 수정] F11 또는 Alt+Enter로 언제든 전체화면 전환.
        if key == pygame.K_F11 or (
            key == pygame.K_RETURN and pygame.key.get_mods() & pygame.KMOD_ALT
        ):
            self.toggle_fullscreen()
        elif key == pygame.K_F1:
            self.show_paths = not self.show_paths
        elif self.state == "title" and key in (pygame.K_SPACE, pygame.K_RETURN):
            self.state = "difficulty"
        elif self.state == "difficulty" and key in (
            pygame.K_1,
            pygame.K_2,
            pygame.K_3,
            pygame.K_4,
        ):
            # [ChatGPT 수정] 1=쉬움, 2=보통, 3=어려움, 4=매우 어려움 선택.
            self.difficulty_key = {
                pygame.K_1: "easy",
                pygame.K_2: "normal",
                pygame.K_3: "hard",
                pygame.K_4: "very_hard",
            }[key]
            self.reset()
            self.state = "play"
        elif self.state == "levelup" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            i = key - pygame.K_1
            if i < len(self.choices):
                self.player.apply_upgrade(self.choices[i])
                self.state = "play"
        elif self.state == "play" and key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "pause"
        elif self.state == "pause" and key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "play"
        elif key == pygame.K_r and self.state in ("over", "pause", "play"):
            self.reset()
            self.state = "play"
        # [ChatGPT 수정] 게임 오버 상태에서 H를 누르면 처음 타이틀 화면으로 돌아간다.
        elif key == pygame.K_h and self.state == "over":
            self.state = "title"
        elif key == pygame.K_q:
            return False
        return True

    # 자동 플레이(테스트용)
    def auto_play(self, frames):
        if self.state == "title":
            self.state = "difficulty"
        elif self.state == "difficulty":
            self.difficulty_key = "normal"
            self.reset()
            self.state = "play"
        elif self.state == "levelup":
            self.player.apply_upgrade(self.choices[0])
            self.state = "play"
        elif self.state == "over":
            self.reset()
            self.state = "play"
        if frames % 24 == 0:
            self._auto_dir = random.choice(
                [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d]
            )
        k = getattr(self, "_auto_dir", pygame.K_d)
        p = self.player
        v = p.speed / FPS * 1.0
        move_and_collide(
            self.grid,
            p,
            v * (1 if k == pygame.K_d else -1 if k == pygame.K_a else 0),
            v * (1 if k == pygame.K_s else -1 if k == pygame.K_w else 0),
        )


def main():
    if "--selftest" in sys.argv:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        g = Game(headless=True)
        g.state = "play"
        g.time = 0.0
        g.run(max_frames=1800)
        print("selftest OK")
        return
    Game().run()


if __name__ == "__main__":
    main()
