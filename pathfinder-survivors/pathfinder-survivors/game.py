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
import gen_sounds
import ui
from pathfinding import Grid, FlowField, astar, smooth_path

# ----------------------------------------------------------------- 설정
SW, SH = 1200, 800  # 화면 크기
TILE = 32
MAP_W, MAP_H = 64, 48  # 타일 개수 → 월드 2048 x 1536
WORLD_W, WORLD_H = MAP_W * TILE, MAP_H * TILE
FPS = 60
GAME_SPEEDS = (1.0, 1.5, 2.0)  # 인게임 배속 위젯 화살표로 순환하는 단계

PATH_BUDGET_PER_FRAME = 8  # 프레임당 A* 호출 상한
FLOW_REBUILD_INTERVAL = 0.5  # flow field 갱신 주기(초)

# ----------------------------------------------------------------- 협동(2P) 카메라
COOP_ZOOM_MIN = 0.62  # 최대로 줄어드는 배율(약 1.6배 줌아웃까지만 — 너무 멀어지면 잘 안 보임)
COOP_ZOOM_MARGIN = 220.0  # 두 플레이어의 바운딩 박스 바깥으로 남겨두는 여유(월드 픽셀)
COOP_ZOOM_LERP = 6.0  # 줌이 바뀌는 속도(클수록 빨리 따라붙음, dt 곱해서 씀)

# ----------------------------------------------------------------- 협동(2P) 난이도 배율
# 둘이 같이 하면 화력(총/오브/오라가 각자 따로 나감)이 대략 2배가 되지만,
# 체력 풀도 2배고 서로 흩어져서 적을 나눠 맞기 때문에 순수 2배보다는 낮게 잡는다.
# 플레이해보고 너무 쉽거나 어려우면 이 숫자만 바꾸면 된다.
COOP_ENEMY_COUNT_MUL = 1.6   # 웨이브당 적 수 배율
COOP_ENEMY_HP_MUL = 1.25     # 일반 몹 체력 추가 배율(난이도별 배율 위에 곱해짐)
COOP_ENEMY_CAP_MUL = 1.3     # 동시 생존 가능 적 상한 배율
COOP_BOSS_HP_MUL = 1.5       # 보스는 둘을 동시에 상대해야 하니 체력을 더 올린다
COOP_BOSS_DMG_MUL = 1.15     # 공격력은 적게만 — 텔레그래프를 두 명이 나눠 피하기 쉬워서

# ------------------------------------------------------------- [ChatGPT 수정] 웨이브 난이도 튜닝
# 한 웨이브의 적을 전부 처치해야 다음 웨이브가 시작된다.
# 후반 웨이브는 적 수/체력/정예 비율/종류가 계속 증가하므로 사실상 무한 진행.
ENEMY_CAP = 70  # 동시에 존재 가능한 최대 적 수(큰 웨이브는 여러 묶음으로 등장)
WAVE_INTRO_TIME = 2.0  # "웨이브 N" 표시 후 전투 시작까지 대기
WAVE_CLEAR_TIME = 1.4  # 웨이브 클리어 후 다음 웨이브까지 대기
WAVE_SPAWN_INTERVAL = 0.16  # 같은 웨이브 안에서 적이 등장하는 간격
WAVE_BASE_ENEMIES = 6  # 1웨이브 기본 몬스터 수
WAVE_ENEMY_GROWTH = 3  # 웨이브마다 추가되는 몬스터 수
WAVE_HP_GROWTH = 0.065  # 웨이브마다 적 체력 ×1.065 (복리)
WAVE_DMG_GROWTH = 0.045  # 웨이브마다 적 공격력 +4.5% (이쪽은 선형: 즉사 방지)
# 체력을 '선형(1 + 0.10×웨이브)'으로 두면 후반이 오히려 쉬워진다.
# 강화가 곱연산이라 플레이어 화력은 복리로 커지는데(웨이브 5→30에 약 95배),
# 선형 증가는 8배 남짓이라 격차가 계속 벌어지기 때문. 그래서 체력도 복리로 맞춘다.
#   웨이브  5 → x1.3   15 → x2.8   30 → x7.6   50 → x27
# 상한선의 근거: 강화 풀을 전부 소진하면(약 58레벨) 플레이어 화력이 더는 안 오른다.
# 그 천장에 맞춰 50웨이브가 '빡세지만 클리어 가능'한 선으로 맞춰 둔 값.
BOSS_EVERY = 5  # 5, 10, 15... 웨이브마다 보스 등장
WIN_WAVE = 30  # 이 웨이브까지 클리어하면 승리 (보스전 10회)
BOSS_XP_PENALTY = 0.75  # 보스가 살아 있는 동안 경험치 획득 배율
ELITE_UNLOCK_WAVE = 7  # 정예 몬스터 해금 웨이브
ELITE_CHANCE_BASE = 0.04  # 정예 기본 확률
ELITE_CHANCE_GROWTH = 0.008  # 웨이브가 오를수록 정예 확률 증가
SEPARATION_NEIGHBORS = 8  # 밀어내기 계산에 쓸 최대 이웃 수

# ----------------------------------------------------------------- 사운드
SFX_VOLUME = 0.55            # 효과음 전체 음량 기본값 (0.0~1.0, 설정 화면에서 0~100%로 조절 가능)
SFX_CHANNELS = 24            # 동시에 날 수 있는 소리 개수
# [ChatGPT 수정] 효과음과 별개로 관리되는 게임 배경음악.
BGM_VOLUME = 0.30            # BGM 음량 기본값(설정 화면에서 0~100%로 조절 가능)
BGM_FILE = os.path.join(gen_assets.ASSET_DIR, "bgm_underclocked.mp3")
# 소리별 (개별 음량, 최소 재생 간격 초).
# 총알처럼 초당 수십 번 나는 소리는 간격을 두지 않으면 귀가 아프고
# 채널도 금방 동난다. 같은 소리를 그 간격 안에 또 요청하면 무시한다.
SFX_TABLE = {
    "shoot":      (0.30, 0.055),
    "hit":        (0.35, 0.040),
    "kill":       (0.45, 0.050),
    "boss_die":   (1.00, 0.00),
    "pickup":     (0.25, 0.045),
    "heal":       (0.70, 0.00),
    "levelup":    (0.85, 0.00),
    "hurt":       (0.80, 0.15),
    "boss_shot":  (0.45, 0.05),
    "telegraph":  (0.50, 0.10),
    "dash":       (0.70, 0.10),
    "boss_spawn": (0.95, 0.00),
    "collapse":   (0.85, 0.00),
    "restore":    (0.70, 0.00),
    "wave_clear": (0.75, 0.00),
    "gameover":   (0.85, 0.00),
    "win":        (0.90, 0.00),
    "select":     (0.50, 0.03),
}

# --------------------------------------------------------------- 보스 튜닝
# 보스는 등장할 때마다 '단계(tier)'가 1씩 오른다. 5웨이브=1단계, 10웨이브=2단계...
BOSS_HP_GROWTH = 0.35        # 단계마다 체력 증가 계수
BOSS_HP_EXP = 1.25           # 체력 배율 = 1 + 계수 × (단계-1)^지수
                             # 지수를 1보다 크게 둬서 후반 보스가 일반 몹보다 더 가파르게 강해진다
BOSS_DMG_GROWTH = 0.14       # 단계마다 공격력 +14%
BOSS_SPEED_GROWTH = 0.06     # 단계마다 이동속도 +5% (최대 1.35배)
BOSS_CD_DECAY = 0.90         # 단계마다 공격 쿨타임 ×0.90 (최소 1.1초)
BOSS_KEEP_RANGE = 260.0      # 보스가 유지하려는 거리
BOSS_KEEP_BAND = 70.0        # 이 폭 안이면 접근/후퇴 대신 선회
BOSS_KEEP_SHRINK = 28.0      # 단계마다 유지 거리를 좁혀 점점 공격적으로
BOSS_BULLET_SPEED = 300.0
TERRAIN_FADE = 0.75          # 보스전 지형이 사라지고 돌아오는 데 걸리는 시간(초)
# 보스는 패턴과 별개로 러너를 계속 흘려보낸다. 1:1로 맞붙기만 하면 지루해지므로.
BOSS_TRICKLE_INTERVAL = 2.8  # 기본 소환 간격(초)
BOSS_TRICKLE_MIN = 1.3       # 단계가 올라도 이보다 자주는 안 나온다
BOSS_TRICKLE_TIER = 0.28     # 단계마다 간격 감소

# 공격 패턴: (해금 단계, 이름, 뽑기 가중치, 예비동작 시간)
BOSS_PATTERNS = [
    (1, "aimed", 30.0, 0.35),   # 이동을 예측한 조준탄
    (1, "spread", 22.0, 0.45),  # 부채꼴 산탄
    (2, "radial", 20.0, 0.70),  # 전방위 탄막
    (3, "dash", 22.0, 0.55),    # 돌진
    (4, "summon", 14.0, 0.80),  # 졸개 소환
]

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
        "title": "A-star SURVIVORS",
        "sub": "몰려오는 적을 버텨내라",
        "menu_single": "싱글 플레이",
        "menu_multi": "협동 플레이",
        "menu_settings": "설정",
        "menu_leaderboard": "리더보드",
        "coming_soon": "준비 중",
        "coop_hint": "P1: WASD 이동   ·   P2: 방향키 이동",
        "difficulty": "난이도를 선택하세요",
        "difficulty_hint": "1 쉬움   ·   2 보통   ·   3 어려움   ·   4 매우 어려움",
        "easy": "쉬움",
        "normal": "보통",
        "hard": "어려움",
        "very_hard": "매우 어려움",
        "ctrl": "WASD/방향키 이동   ·   공격은 자동   ·   M 효과음 음소거   ·   F1 경로 보기   ·   F11 전체화면   ·   ESC 일시정지",
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
        "pause_home": "H 로 메인 메뉴",
        "over": "G A M E   O V E R",
        "win": "C L E A R !",
        "win_sub": "모든 웨이브 클리어어",
        "muted": "효과음 끔",
        "unmuted": "효과음 켬",
        # [ChatGPT 수정] 배속/BGM 버튼에 쓰는 별도 표시.
        "speed_label": "배속",
        "bgm_on": "BGM 켬",
        "bgm_off": "BGM 끔",
        # [ChatGPT 수정] BGM 전용 음량 조절 표시.
        "bgm_volume": "BGM 음량",
        "sfx_volume": "효과음 음량",
        "damage_numbers": "데미지 표시",
        "enemy_hp_bars": "몬스터 체력바",
        "settings": "설정",
        "close": "닫기",
        "on": "켬",
        "off": "끔",
        "survived": "생존 시간",
        "restart": "R 을 눌러 다시 시작",
        "home": "H 를 눌러 홈으로",
        "paths": "이동동 경로 표시",
        "boss": "보스 등장!",
        "maxed": "(최대)",
    },
    "en": {
        "title": "A-star SURVIVORS",
        "sub": "Survive the A*-driven swarm",
        "menu_single": "SINGLE PLAYER",
        "menu_multi": "CO-OP",
        "menu_settings": "SETTINGS",
        "menu_leaderboard": "LEADERBOARD",
        "coming_soon": "COMING SOON",
        "coop_hint": "P1: WASD move  ·  P2: Arrow keys move",
        "difficulty": "SELECT DIFFICULTY",
        "difficulty_hint": "1 EASY   ·   2 NORMAL   ·   3 HARD   ·   4 VERY HARD",
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "very_hard": "VERY HARD",
        "ctrl": "WASD/Arrows move  ·  Auto attack  ·  M SFX mute  ·  F1 paths  ·  F11 fullscreen  ·  ESC pause",
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
        "pause_home": "Press H for main menu",
        "over": "G A M E   O V E R",
        "win": "C L E A R !",
        "win_sub": "50 WAVES COMPLETE",
        "muted": "SFX OFF",
        "unmuted": "SFX ON",
        # [ChatGPT 수정] Separate speed/BGM labels.
        "speed_label": "SPEED",
        "bgm_on": "BGM ON",
        "bgm_off": "BGM OFF",
        # [ChatGPT 수정] BGM-only volume control label.
        "bgm_volume": "BGM VOLUME",
        "sfx_volume": "SFX VOLUME",
        "damage_numbers": "DAMAGE NUMBERS",
        "enemy_hp_bars": "ENEMY HP BARS",
        "settings": "SETTINGS",
        "close": "CLOSE",
        "on": "ON",
        "off": "OFF",
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
        "max": 5,
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
        "max": 5,
        "name": ("체력 증강", "Vitality"),
        "desc": ("최대 체력 +20, 즉시 회복", "+20 max HP, heal now"),
    },
    {
        "key": "regen",
        "max": 4,
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
    "tank": dict(img="enemy_tank", hp=70, speed=53, dmg=16, xp=5, r=14),
    "boss": dict(img="enemy_boss", hp=320, speed=60, dmg=26, xp=60, r=15),
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


def predict_intercept(bx, by, speed, px, py, pvx, pvy, max_t=2.0):
    """등속으로 움직이는 목표를 향한 '요격점'을 구한다.

    쫓아가는 쪽이 t초 뒤 도달할 수 있는 거리는 speed·t,
    목표가 t초 뒤 있을 위치는 P + v·t 이므로 만나는 조건은

        |P + v t - B| = speed · t

    양변을 제곱해 정리하면 t에 대한 이차방정식이 된다.

        (v·v - speed²) t² + 2 v·(P-B) t + |P-B|² = 0

    양수 해 중 가장 작은 것이 가장 빨리 만나는 시각이다.
    해가 없으면(목표가 더 빨라 따라잡을 수 없는 경우) 현재 위치를 겨냥한다.

    보스가 플레이어의 '현재 위치'가 아니라 '갈 위치'를 노리게 만드는 부분.
    이것만으로도 그냥 따라오는 것과 체감이 크게 달라진다.
    """
    rx, ry = px - bx, py - by
    a = pvx * pvx + pvy * pvy - speed * speed
    b = 2.0 * (pvx * rx + pvy * ry)
    c = rx * rx + ry * ry
    t = None
    if abs(a) < 1e-6:                       # 속도가 같으면 일차방정식
        if abs(b) > 1e-6:
            cand = -c / b
            if cand > 0:
                t = cand
    else:
        disc = b * b - 4 * a * c
        if disc >= 0:
            sq = math.sqrt(disc)
            for cand in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)):
                if cand > 0 and (t is None or cand < t):
                    t = cand
    if t is None:
        return px, py
    t = min(t, max_t)                       # 너무 먼 미래는 예측이 무의미
    return px + pvx * t, py + pvy * t


class Audio:
    """효과음 재생기.

    · 오디오 장치가 없는 환경(원격 접속, 사운드카드 없음, --selftest)에서도
      게임이 죽으면 안 되므로 초기화 실패를 조용히 넘기고 무음으로 동작한다.
    · 같은 소리가 짧은 간격에 몰리면 무시한다(SFX_TABLE의 최소 간격).
    """

    def __init__(self):
        self.ok = False
        self.muted = False
        # [ChatGPT 수정] BGM 음소거는 기존 효과음(M 키)과 완전히 분리한다.
        self.bgm_muted = False
        # [ChatGPT 수정] BGM 음량은 효과음과 별도로 기억한다.
        self.bgm_volume = BGM_VOLUME
        self.bgm_loaded = False
        # 설정 화면의 효과음 슬라이더(0.0~1.0)용. 각 소리의 개별 균형(SFX_TABLE의 vol)은
        # 그대로 두고 여기에만 곱해서 전체 크기를 조절한다.
        self.sfx_volume = SFX_VOLUME
        self.sound_base_vol = {}
        self.sounds = {}
        self.last = {}

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(22050, -16, 1, 512)
            pygame.mixer.set_num_channels(SFX_CHANNELS)
            path = gen_sounds.build()
            for name, (vol, _) in SFX_TABLE.items():
                f = os.path.join(path, name + ".wav")
                if os.path.exists(f):
                    snd = pygame.mixer.Sound(f)
                    snd.set_volume(vol * self.sfx_volume)
                    self.sound_base_vol[name] = vol
                    self.sounds[name] = snd
            self.ok = bool(self.sounds)
        except Exception as ex:                      # 오디오 장치 없음 등
            print(f"[알림] 소리를 켤 수 없어 무음으로 실행합니다. ({ex})")

    def play(self, name):
        if not self.ok or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        gap = SFX_TABLE.get(name, (1.0, 0.0))[1]
        now = pygame.time.get_ticks() / 1000.0
        if gap > 0 and now - self.last.get(name, -9.9) < gap:
            return
        self.last[name] = now
        try:
            snd.play()
        except Exception:
            pass

    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted and self.ok:
            pygame.mixer.stop()          # 재생 중인 효과음을 끊는다
        return self.muted

    # [ChatGPT 수정] 제공된 MP3는 pygame.mixer.music으로 반복 재생한다.
    # Sound 채널과 music 채널을 분리해 BGM 버튼이 효과음에는 영향을 주지 않는다.
    def start_bgm(self, path, restart=False):
        try:
            if pygame.mixer.get_init() is None or not os.path.exists(path):
                return False
            if restart or not self.bgm_loaded:
                pygame.mixer.music.load(path)
                self.bgm_loaded = True
            pygame.mixer.music.set_volume(0.0 if self.bgm_muted else self.bgm_volume)
            if restart or not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
            return True
        except Exception as ex:
            print(f"[알림] 배경음악을 재생할 수 없습니다. ({ex})")
            return False

    def stop_bgm(self):
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.stop()
        except Exception:
            pass

    def toggle_bgm_mute(self):
        self.bgm_muted = not self.bgm_muted
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.set_volume(0.0 if self.bgm_muted else self.bgm_volume)
        except Exception:
            pass
        return self.bgm_muted

    def set_bgm_volume(self, volume):
        """설정 화면 슬라이더에서 호출 — BGM 음량을 0.0~1.0 사이 임의 값으로 바로 지정한다."""
        self.bgm_volume = clamp(volume, 0.0, 1.0)
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.music.set_volume(0.0 if self.bgm_muted else self.bgm_volume)
        except Exception:
            pass
        return self.bgm_volume

    def set_sfx_volume(self, volume):
        """설정 화면 슬라이더에서 호출 — 효과음 전체 음량을 0.0~1.0 사이로 지정한다.
        소리별 개별 균형(sound_base_vol)은 유지한 채 여기에만 곱한다."""
        self.sfx_volume = clamp(volume, 0.0, 1.0)
        for name, snd in self.sounds.items():
            snd.set_volume(self.sound_base_vol.get(name, 1.0) * self.sfx_volume)
        return self.sfx_volume


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
        self.mvx = self.mvy = 0.0   # 최근 실제 이동 속도(보스 예측용)
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
        # [ChatGPT 수정] 보스 전용 원거리 공격 쿨타임.
        "boss_shot_t",
        "stuck_n",
        # 협동(배치 K)에서 이 개체가 쫓고 있는 self.players의 인덱스.
        "target_pi",
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
        self.dmg = s["dmg"] * damage_mul
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
        self.stuck_n = 0  # 연속으로 끼임이 감지된 횟수
        # [ChatGPT 수정] 보스는 등장 직후 즉발하지 않고 잠깐 뒤부터 총알을 발사한다.
        self.boss_shot_t = random.uniform(0.9, 1.4) if kind == "boss" else 9999.0
        self.target_pi = 0  # update_enemies()가 매 프레임 가장 가까운 살아있는 플레이어로 갱신


class Boss(Enemy):
    """보스. 일반 적과 달리 거리를 재고, 예비동작을 거쳐 패턴 공격을 한다.

    tier(단계)는 등장 회차. 단계가 오를수록 체력·공격력·속도가 오르고
    쓸 수 있는 패턴이 늘어나며 공격 간격이 짧아진다.
    """

    __slots__ = (
        "tier", "state", "state_t", "atk_cd", "pattern",
        "strafe_dir", "lock_x", "lock_y", "goal_t", "trickle_t",
    )

    def __init__(self, x, y, scale, tier, hp_mul=1.0, speed_mul=1.0, damage_mul=1.0):
        super().__init__("boss", x, y, scale, False, hp_mul, speed_mul, damage_mul)
        self.tier = tier
        # 단계별 강화
        self.max_hp *= 1.0 + BOSS_HP_GROWTH * (tier - 1) ** BOSS_HP_EXP
        self.hp = self.max_hp
        self.dmg *= 1.0 + BOSS_DMG_GROWTH * (tier - 1)
        self.speed *= min(1.35, 1.0 + BOSS_SPEED_GROWTH * (tier - 1))
        self.state = "move"          # move / windup / dash / recover
        self.state_t = 0.0
        self.atk_cd = random.uniform(1.2, 1.8)
        self.pattern = None
        self.strafe_dir = random.choice((-1, 1))
        self.lock_x = self.lock_y = 0.0   # 예비동작 시점에 고정한 조준 방향
        self.goal_t = 0.0
        self.trickle_t = 1.5

    @property
    def trickle_interval(self):
        return max(BOSS_TRICKLE_MIN,
                   BOSS_TRICKLE_INTERVAL - BOSS_TRICKLE_TIER * (self.tier - 1))

    @property
    def attack_cd(self):
        return max(1.1, 2.6 * (BOSS_CD_DECAY ** (self.tier - 1)))

    @property
    def keep_range(self):
        return max(120.0, BOSS_KEEP_RANGE - BOSS_KEEP_SHRINK * (self.tier - 1))

    def unlocked_patterns(self):
        return [(n, w, tel) for req, n, w, tel in BOSS_PATTERNS if self.tier >= req]


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


# [ChatGPT 수정] 보스가 플레이어를 향해 발사하는 적 전용 투사체.
class BossBullet:
    __slots__ = ("x", "y", "vx", "vy", "r", "dmg", "life")

    def __init__(self, x, y, vx, vy, dmg):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.r = 7
        self.dmg = dmg
        self.life = 4.0


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
        try:
            # 버퍼를 작게 잡아야 총 쏘는 소리가 늦게 들리지 않는다
            pygame.mixer.pre_init(22050, -16, 1, 512)
        except Exception:
            pass
        pygame.init()
        pygame.display.set_caption("A-star Survivors")
        self.headless = headless

        # [ChatGPT 수정] 게임 내부 해상도는 1024x640으로 유지하고,
        # 실제 모니터에는 비율을 유지해 확대해서 전체화면에서도 UI/맵이 깨지지 않게 한다.
        self.fullscreen = False
        self.display = pygame.display.set_mode((SW, SH))
        self.screen = pygame.Surface((SW, SH))
        self.clock = pygame.time.Clock()
        self.audio = Audio()

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
        self.levelup_buttons = []
        self.difficulty_buttons = []
        self.menu_buttons = []
        self.speed_widget_buttons = []
        self.game_speed = 1.0
        # 인게임 설정 화면(톱니바퀴 버튼) — ESC/일시정지와는 완전히 별개의 상태.
        self.gear_button = None
        self.settings_buttons = []
        self.settings_sliders = {}  # {"bgm": pygame.Rect, "sfx": pygame.Rect} — 클릭/드래그 판정용
        self.dragging_slider = None  # 마우스 왼쪽 버튼을 누른 채 끌고 있는 슬라이더 id
        self.show_damage_numbers = True  # 판이 바뀌어도 유지되는 설정이라 reset()이 아니라 여기서 초기화
        self.show_enemy_hp_bars = True  # 몬스터 머리 위 체력바 표시 여부(마찬가지로 세션 내내 유지)
        # 로컬 협동(배치 K) — 메인 메뉴에서 "협동"을 고르면 2로 바뀐다. reset()이 이 값을
        # 읽어서 self.players를 몇 명 만들지 정한다.
        self.num_players = 1
        # 2P가 멀리 떨어지면 줌아웃해서 그리는 데 쓰는 임시 캔버스. 필요한 크기가
        # 바뀔 때만 다시 만들면 되므로 게임판이 새로 시작해도(reset) 그대로 재사용한다.
        self.world_surf = None
        # --selftest 전용: "1p"(기본) 또는 "2p" — main()이 두 번째 헤드리스 실행에서
        # "2p"로 바꿔서 협동 메뉴 클릭 경로까지 자동으로 지나가게 한다.
        self.selftest_mode = "1p"
        self._auto_dirs = []  # auto_play()가 플레이어마다 따로 굴리는 무작위 이동 방향
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

        self.widen_corridors(grid)

        # 연결성 보정: 중앙에서 못 가는 빈 칸은 아예 벽으로 만든다
        reach = grid.flood_reachable((cx, cy))
        for y in range(MAP_H):
            for x in range(MAP_W):
                if grid.walkable(x, y) and (x, y) not in reach:
                    grid.set_solid(x, y)
        self.rock_tiles = {t for t in rock if t not in walls}
        # 보스전에 사라졌다 돌아올 '실내 장애물' 목록.
        # 바깥 테두리는 맵 밖으로 나가는 걸 막아야 하므로 제외한다.
        self.obstacle_tiles = {
            (x, y)
            for y in range(1, MAP_H - 1)
            for x in range(1, MAP_W - 1)
            if grid.is_solid(x, y)
        }
        grid.build_clearance()   # 몸집을 고려한 A*를 위해 여유 공간 미리 계산
        return grid

    @staticmethod
    def widen_corridors(grid, max_passes=8):
        """모든 통로의 폭이 최소 2칸(64px)이 되도록 벽을 깎는다.

        판정 기준: 빈 칸 하나하나가 '전부 빈칸인 2×2 블록'에 최소 하나는
        속해 있어야 한다. 어떤 2×2에도 못 들어가는 칸은 폭이 1칸이라는 뜻이다.
        그런 칸을 찾으면 그 칸을 포함하는 2×2 후보 4개 중 **벽을 가장 적게
        허물어도 되는 것**을 골라 뚫는다. 최소 개수만 건드리므로 맵 모양이
        크게 망가지지 않고, 벽을 없애는 방향이라 통로가 끊길 일도 없다.

        한 곳을 뚫으면 이웃 칸의 판정이 바뀔 수 있어 변화가 없을 때까지 반복한다.

        큰 적(지름 30px)이 32px 통로에서 좌우 여유 1px로 끼는 문제는
        길찾기로 못 푼다. 애초에 그런 통로를 만들지 않는 게 해법.
        """
        w, h = grid.w, grid.h
        for _ in range(max_passes):
            changed = False
            for y in range(1, h - 1):
                for x in range(1, w - 1):
                    if grid.is_solid(x, y):
                        continue
                    # (x,y)를 왼쪽위/오른쪽위/왼쪽아래/오른쪽아래로 갖는 2×2 블록들
                    blocks = (
                        ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)),
                        ((x - 1, y), (x, y), (x - 1, y + 1), (x, y + 1)),
                        ((x, y - 1), (x + 1, y - 1), (x, y), (x + 1, y)),
                        ((x - 1, y - 1), (x, y - 1), (x - 1, y), (x, y)),
                    )
                    # 바깥 테두리를 물고 있는 블록은 후보에서 뺀다(테두리는 못 뚫음)
                    valid = [
                        b for b in blocks
                        if all(1 <= bx <= w - 2 and 1 <= by <= h - 2 for bx, by in b)
                    ]
                    if not valid:
                        continue
                    if any(all(not grid.is_solid(*c) for c in b) for b in valid):
                        continue                      # 이미 2×2 여유가 있음
                    best = min(valid, key=lambda b: sum(grid.is_solid(*c) for c in b))
                    for cx, cy in best:
                        if grid.is_solid(cx, cy):
                            grid.set_solid(cx, cy, 0)
                            changed = True
            if not changed:
                break

    def render_background(self):
        """월드 전체를 큰 Surface에 한 번만 그려 두고 매 프레임 잘라 쓴다.

        보스전에 장애물만 사라지게 하려면 두 겹으로 나눠야 한다.
          bg   : 바닥 + 바깥 테두리 (절대 사라지지 않는 것)
          obst : 실내 장애물만, 나머지는 투명
        평소엔 두 장을 겹쳐 그리고, 보스전엔 obst의 알파만 낮춘다.
        """
        bg = pygame.Surface((WORLD_W, WORLD_H)).convert()
        obst = pygame.Surface((WORLD_W, WORLD_H), pygame.SRCALPHA)
        f0, f1 = self.img["floor0"], self.img["floor1"]
        wall, rockimg = self.img["wall"], self.img["rock"]
        rng = random.Random(7)
        for ty in range(MAP_H):
            for tx in range(MAP_W):
                px, py = tx * TILE, ty * TILE
                bg.blit(f0 if rng.random() < 0.85 else f1, (px, py))
                if not self.grid.is_solid(tx, ty):
                    continue
                border = tx == 0 or ty == 0 or tx == MAP_W - 1 or ty == MAP_H - 1
                img = rockimg if (tx, ty) in self.rock_tiles else wall
                (bg if border else obst).blit(img, (px, py))
        return bg, obst

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
        self.bg, self.bg_obst = self.render_background()
        self.minimap_bg = self.render_minimap()
        self.flow_timer = 0.0

        sx, sy = self.grid.tile_center(MAP_W // 2, MAP_H // 2)
        # [ChatGPT 수정] 재시작해도 현재 선택한 난이도를 그대로 유지한다.
        diff = DIFFICULTIES[self.difficulty_key]
        # [ChatGPT 수정] 선택한 난이도의 몬스터 체력·속도·공격력 배율을 스폰에 적용한다.
        self.enemy_hp_mul = diff["enemy_hp_mul"]
        self.enemy_speed_mul = diff["enemy_speed_mul"]
        self.enemy_damage_mul = diff["enemy_damage_mul"]
        self.players = [Player(sx, sy, diff["hp"], diff["xp_mul"])]
        if self.num_players > 1:
            # 지도 중앙(1P 자리) 바로 옆 타일에 2P를 놓되, 벽이면 nearest_walkable로
            # 근처 빈 칸을 찾는다 — 두 플레이어가 겹쳐서 시작하지 않게.
            spot = self.grid.nearest_walkable(MAP_W // 2 + 1, MAP_H // 2, 6, 12.0)  # Player.r과 맞춘 반지름
            sx2, sy2 = self.grid.tile_center(*spot) if spot else (sx, sy)
            self.players.append(Player(sx2, sy2, diff["hp"], diff["xp_mul"]))
        # 아직 self.players로 옮기지 못한 코드(적 AI 타겟팅, HUD, 게임오버 등, 배치 K2~K5에서
        # 순차적으로 정리)가 참조할 임시 별칭. players[0]과 항상 같은 객체를 가리키므로
        # 어느 쪽으로 값을 바꿔도 서로 어긋나지 않는다. K5가 끝나면 삭제한다.
        self.player = self.players[0]
        # 적 대체 경로(flow field)는 목표점이 하나뿐이라 플레이어 수만큼 따로 둔다 —
        # 안 그러면 한쪽 플레이어 근처의 적들이 대체 경로를 아예 못 받는다.
        self.flows = [FlowField(self.grid) for _ in self.players]
        self.levelup_queue = []  # 동시에 여러 명이 레벨업하면 순서대로 처리
        self.levelup_player = 0  # 지금 레벨업 화면이 누구 것인지
        self.cam_zoom = 1.0  # 협동 카메라 줌 배율(1인이면 항상 1.0으로 고정됨)
        # 동시 생존 적 상한도 인원수에 맞춰 늘린다(그래야 늘어난 스폰 수가 상한에 막히지 않는다).
        self.enemy_cap = round(ENEMY_CAP * (COOP_ENEMY_CAP_MUL if self.num_players > 1 else 1.0))
        self.enemies = []
        self.bullets = []
        # [ChatGPT 수정] 보스 탄환은 플레이어 총알과 별도 관리한다.
        self.boss_bullets = []
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
        # 협동 모드로 시작할 때만 조작 안내를 잠깐 띄운다 — 부스 방문객이 둘이 바로
        # 앉아서 헷갈리지 않게.
        self.banner = (self.T["coop_hint"], 2.5) if self.num_players > 1 else ("", 0.0)
        self.choices = []
        self.path_calls = 0
        self.path_calls_shown = 0
        self.path_timer = 0.0
        self.cam = [0.0, 0.0]
        # 보스전 지형 상태: solid → fading → gone → returning → solid
        self.terrain_state = "solid"
        self.terrain_t = 0.0
        self.terrain_alpha = 1.0
        self.boss_active = False
        for pl, flow in zip(self.players, self.flows):
            flow.rebuild(self.grid.world_to_tile(pl.x, pl.y))

    # ------------------------------------------------------ [ChatGPT 수정] 웨이브 / 스폰
    def wave_enemy_count(self, wave):
        """웨이브가 올라갈수록 적 수가 선형으로 증가한다. 협동이면 인원수만큼 더 늘린다."""
        n = WAVE_BASE_ENEMIES + (wave - 1) * WAVE_ENEMY_GROWTH
        if len(self.players) > 1:
            n = round(n * COOP_ENEMY_COUNT_MUL)
        return n

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
                and len(self.enemies) < self.enemy_cap
            ):
                kind, elite = self.wave_queue.pop()
                self.spawn(kind, elite)
                self.wave_spawned += 1
                self.wave_spawn_timer += WAVE_SPAWN_INTERVAL
                if kind == "boss":
                    self.audio.play("boss_spawn")
                    self.banner = (self.T["boss"], 2.5)
                    self.shake = max(self.shake, 10.0)

            if not self.wave_queue:
                self.wave_phase = "combat"

        # 큐도 비었고 살아 있는 적도 없으면 그 웨이브 클리어.
        if self.wave_phase in ("spawning", "combat") and not self.wave_queue and not self.enemies:
            if self.wave >= WIN_WAVE:
                self.audio.play("win")
                self.state = "win"      # 마지막 웨이브를 비우면 승리
                return
            self.audio.play("wave_clear")
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
        θ ~ U[0, 2π), r = 상수 → 플레이어(들)를 중심으로 한 원 위의 균등분포.
        협동이면 살아있는 플레이어들의 중점을 중심으로 삼는다 — 안 그러면(예전처럼
        P1만 중심) 적이 항상 P1 근처에서만 새로 생기고 P2 쪽은 계속 비게 된다."""
        ps = self.alive_players()
        mx = sum(pl.x for pl in ps) / len(ps)
        my = sum(pl.y for pl in ps) / len(ps)
        # 플레이 시간이 아니라 웨이브를 기준으로 강해져서, 천천히 플레이해도 난이도가 튀지 않는다.
        scale = (1.0 + WAVE_HP_GROWTH) ** (self.wave - 1)
        # 공격력은 웨이브에 선형으로만 올린다(복리면 후반에 한 방 컷이 된다)
        dmg_mul = self.enemy_damage_mul * (1.0 + WAVE_DMG_GROWTH * (self.wave - 1))
        coop = len(self.players) > 1
        for _ in range(12):
            a = random.uniform(0, math.tau)
            rad = random.uniform(620, 760)
            x = clamp(mx + math.cos(a) * rad, TILE, WORLD_W - TILE)
            y = clamp(my + math.sin(a) * rad, TILE, WORLD_H - TILE)
            tx, ty = self.grid.world_to_tile(x, y)
            spot = self.grid.nearest_walkable(tx, ty, 6, ENEMY_TYPES[kind]["r"])
            if spot:
                wx, wy = self.grid.tile_center(*spot)
                if kind == "boss":
                    # 등장 회차 = 단계. 5웨이브마다 나오므로 wave//BOSS_EVERY.
                    tier = max(1, self.wave // BOSS_EVERY)
                    hp_mul = self.enemy_hp_mul * (COOP_BOSS_HP_MUL if coop else 1.0)
                    boss_dmg_mul = dmg_mul * (COOP_BOSS_DMG_MUL if coop else 1.0)
                    self.enemies.append(
                        Boss(
                            wx,
                            wy,
                            scale,
                            tier,
                            hp_mul,
                            self.enemy_speed_mul,
                            boss_dmg_mul,
                        )
                    )
                else:
                    hp_mul = self.enemy_hp_mul * (COOP_ENEMY_HP_MUL if coop else 1.0)
                    self.enemies.append(
                        Enemy(
                            kind,
                            wx,
                            wy,
                            scale,
                            elite,
                            hp_mul,
                            self.enemy_speed_mul,
                            dmg_mul,
                        )
                    )
                return

    # ------------------------------------------------------ 업데이트
    def update(self, dt, keys):
        self.time += dt
        self.shake = max(0.0, self.shake - dt * 26)

        # --- 입력/이동
        # 혼자면(1P) 기존처럼 WASD와 방향키를 둘 다 그 한 명에게 준다 — 원래 조작감을
        # 그대로 유지해야 하므로. 협동(2P)일 때만 1P=WASD / 2P=방향키로 나눈다.
        coop = len(self.players) > 1
        for i, pl in enumerate(self.players):
            if pl.hp <= 0:
                continue  # 쓰러진 플레이어는 조작 불가 — 나머지 한 명은 계속 진행
            if coop and i == 1:
                mx = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
                my = keys[pygame.K_DOWN] - keys[pygame.K_UP]
            elif coop:
                mx = keys[pygame.K_d] - keys[pygame.K_a]
                my = keys[pygame.K_s] - keys[pygame.K_w]
            else:
                mx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
                my = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
            # [ChatGPT 수정] 대각선(W+A, W+D 등)에서도 X/Y축 속도를 깎지 않는다.
            # 기존 정규화는 대각선에서 각 축을 약 70.7%로 줄였기 때문에 체감상 느리게 느껴질 수 있었다.
            if mx:
                pl.facing = 1 if mx > 0 else -1
            prev_x, prev_y = pl.x, pl.y
            move_and_collide(self.grid, pl, mx * pl.speed * dt, my * pl.speed * dt)
            # 보스의 요격 예측에 쓸 '실제' 이동 속도.
            # 입력 방향이 아니라 벽에 막힌 결과까지 반영된 변위로 구하고,
            # 지수이동평균으로 흔들림을 눌러 준다(값이 튀면 예측이 춤춘다).
            if dt > 1e-6:
                ivx, ivy = (pl.x - prev_x) / dt, (pl.y - prev_y) / dt
                k = min(1.0, 8.0 * dt)
                pl.mvx += (ivx - pl.mvx) * k
                pl.mvy += (ivy - pl.mvy) * k

            pl.iframe = max(0.0, pl.iframe - dt)
            if pl.regen:
                pl.hp = min(pl.max_hp, pl.hp + pl.regen * dt)

        self.update_camera_zoom(dt)

        # --- 공간 해시 재구성
        self.hash.clear()
        for e in self.enemies:
            self.hash.add(e)

        # --- flow field 갱신 (A* 예산 초과 시의 대체 경로) — 플레이어마다 하나씩
        self.flow_timer -= dt
        if self.flow_timer <= 0:
            self.flow_timer = FLOW_REBUILD_INTERVAL
            for pl, flow in zip(self.players, self.flows):
                flow.rebuild(self.grid.world_to_tile(pl.x, pl.y))

        self.update_enemies(dt)
        # [ChatGPT 수정] 보스가 발사한 탄환의 이동/벽 충돌/플레이어 피격을 처리한다.
        self.update_boss_bullets(dt)
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

        self.update_terrain(dt)
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
        # 부활 없음 — 전원(1인이면 그 한 명)이 쓰러져야 게임오버. 한 명만 쓰러지면
        # 남은 한 명이 계속 진행한다(위 입력 루프가 쓰러진 쪽을 건너뛰어 처리).
        if all(pl.hp <= 0 for pl in self.players):
            if self.state != "over":
                self.audio.play("gameover")
            self.state = "over"

    def alive_players(self):
        """쓰러지지 않은 플레이어 목록. 전원 쓰러졌으면(그 프레임 게임오버 처리 직전)
        0으로 나누기 등을 피하려고 그냥 전체 목록을 돌려준다."""
        alive = [p for p in self.players if p.hp > 0]
        return alive if alive else self.players

    def nearest_player_index(self, x, y):
        """(x,y)에서 가장 가까운, 아직 살아있는 플레이어의 self.players 인덱스.
        전원 쓰러졌으면 None(그 프레임은 게임오버 처리로 넘어간다)."""
        best, bd = None, 1e18
        for i, pl in enumerate(self.players):
            if pl.hp <= 0:
                continue
            d2 = (pl.x - x) ** 2 + (pl.y - y) ** 2
            if d2 < bd:
                best, bd = i, d2
        return best

    # ---------------- 적 AI (여기가 A* 파트) ----------------
    def update_enemies(self, dt):
        grid = self.grid
        budget = PATH_BUDGET_PER_FRAME

        for e in self.enemies:
            e.flash = max(0.0, e.flash - dt)
            e.hit_cd = max(0.0, e.hit_cd - dt)
            e.repath_t -= dt

            # 협동(2P)이면 매 프레임 가장 가까운 살아있는 플레이어를 다시 고른다.
            # 혼자면 항상 인덱스 0이라 아래 로직은 지금까지와 완전히 동일하게 동작한다.
            pi = self.nearest_player_index(e.x, e.y)
            if pi is None:
                continue  # 전원 쓰러짐 — 이번 프레임은 게임오버 처리로 넘어간다
            e.target_pi = pi
            p = self.players[pi]
            ptile = grid.world_to_tile(p.x, p.y)

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
                    e.stuck_n += 1
                    # 벽 모서리에 쐐기처럼 박히면 재탐색해도 같은 경로가 나와
                    # 영원히 못 빠져나온다. 세 번(약 1초) 연속이면 최후 수단으로
                    # 타일 중앙(반드시 빈 곳)으로 밀어 넣어 쐐기를 푼다.
                    if e.stuck_n >= 3:
                        spot = grid.nearest_walkable(
                            *grid.world_to_tile(e.x, e.y), 3, e.r
                        )
                        if spot:
                            e.x, e.y = grid.tile_center(*spot)
                        e.vx = e.vy = 0.0
                        e.path = None
                        e.stuck_n = 0
                else:
                    e.stuck_n = 0
                e.lx, e.ly = e.x, e.y

            # 가시선 판정은 비싸므로 매 프레임이 아니라 0.1초 간격으로만 갱신한다.
            e.los_t -= dt
            if e.los_t <= 0:
                e.los_t = random.uniform(0.09, 0.17)
                e.los = dist < 800 and grid.line_clear(e.x, e.y, p.x, p.y, e.r * 0.85)

            # 0) 보스는 전용 두뇌가 움직임을 결정한다.
            #    None을 돌려주면 일반 적과 같은 추격 로직으로 넘어간다.
            spd_mul = 1.0
            boss_desired = None
            if e.kind == "boss":
                boss_desired, spd_mul = self.boss_brain(e, dt, dist, dx, dy)

            if boss_desired is not None:
                e.path = None
                desired = boss_desired
            elif e.los and e.force_t <= 0:
                e.path = None
                desired = (dx / max(dist, 1e-6), dy / max(dist, 1e-6))
            else:
                # 2) 막혀 있으면 A*. 단 프레임당 호출 수를 제한한다.
                need_new = (e.path is None) or (e.repath_t <= 0)
                if need_new and budget > 0:
                    budget -= 1
                    self.path_calls += 1
                    e.repath_t = random.uniform(0.35, 0.75)
                    raw = astar(grid, grid.world_to_tile(e.x, e.y), ptile, 1500, e.r)
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
                    # 4) 예산 초과 등으로 경로가 없으면 flow field 방향 사용(쫓는 대상의 필드)
                    fd = self.flows[pi].direction(*grid.world_to_tile(e.x, e.y))
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
            tvx, tvy = ddx * e.speed * spd_mul, ddy * e.speed * spd_mul
            k = min(1.0, 9.0 * dt)  # 속도 보간 → 방향 전환이 부드럽다
            e.vx += (tvx - e.vx) * k
            e.vy += (tvy - e.vy) * k
            if e.vx:
                e.facing = 1 if e.vx > 0 else -1
            move_and_collide(self.grid, e, e.vx * dt, e.vy * dt)

            # 6) 플레이어 접촉 피해 — 쫓는 대상뿐 아니라, 옆에 서 있던 다른 플레이어도
            # 부딪히면 맞아야 한다("최근접"이 아니라 "닿은 사람 전원" 검사).
            for op in self.players:
                if op.hp <= 0:
                    continue
                odx, ody = op.x - e.x, op.y - e.y
                odist = math.hypot(odx, ody)
                if odist < e.r + op.r and op.iframe <= 0:
                    self.audio.play("hurt")
                    op.hp -= e.dmg
                    op.iframe = 0.55
                    self.shake = max(self.shake, 7.0)
                    for _ in range(8):
                        self.particles.append(Particle(op.x, op.y, C_HP))


    # ---------------- 보스전 지형 ----------------
    def set_obstacles(self, on):
        """실내 장애물의 충돌을 통째로 켜고 끈다.

        지형이 바뀌면 여유 공간(clearance)과 flow field가 전부 무효가 되므로
        같이 다시 계산하고, 적들이 들고 있던 경로도 버리게 한다.
        """
        for tx, ty in self.obstacle_tiles:
            self.grid.set_solid(tx, ty, 1 if on else 0)
        self.grid.build_clearance()
        for pl, flow in zip(self.players, self.flows):
            flow.rebuild(self.grid.world_to_tile(pl.x, pl.y))
        for e in self.enemies:
            e.path = None
            e.repath_t = 0.0
        self.minimap_bg = self.render_minimap()

    def terrain_burst(self, color):
        """사라지거나 돌아오는 장애물 자리에 파편을 뿌린다.

        전부 뿌리면 파티클이 수백 개라 프레임이 튀므로,
        화면 근처 타일만 골라 최대 90개까지만 만든다.
        """
        ps = self.alive_players()
        mx = sum(pl.x for pl in ps) / len(ps)
        my = sum(pl.y for pl in ps) / len(ps)
        near = [
            t for t in self.obstacle_tiles
            if abs(t[0] * TILE - mx) < SW * 0.7 and abs(t[1] * TILE - my) < SH * 0.7
        ]
        random.shuffle(near)
        for tx, ty in near[:90]:
            self.particles.append(
                Particle(tx * TILE + 16, ty * TILE + 16, color, 4, 150)
            )

    def relocate_out_of_walls(self):
        """지형이 돌아왔을 때 벽 속에 갇힌 대상을 가장 가까운 빈칸으로 빼낸다."""
        for ent in list(self.players) + self.enemies:
            tx, ty = self.grid.world_to_tile(ent.x, ent.y)
            if not self.grid.is_solid(tx, ty):
                continue
            spot = self.grid.nearest_walkable(tx, ty, 8, ent.r)
            if spot:
                ent.x, ent.y = self.grid.tile_center(*spot)
                for _ in range(6):
                    self.particles.append(Particle(ent.x, ent.y, (200, 220, 255), 3, 120))

    def update_terrain(self, dt):
        """보스가 살아 있는 동안 장애물이 사라진다 → 열린 투기장이 된다.

        사라질 때는 충돌을 즉시 끄고 그림만 서서히 지운다(반응이 빨라야 하니까).
        돌아올 때는 반대로 그림이 먼저 차오르고 마지막에 충돌이 켜진다.
        미리 보이니까 피할 시간이 있다.
        """
        has_boss = any(e.kind == "boss" for e in self.enemies)
        self.boss_active = has_boss   # 경험치 감소 판정에 쓴다

        if has_boss and self.terrain_state in ("solid", "returning"):
            self.terrain_state = "fading"
            self.terrain_t = TERRAIN_FADE * self.terrain_alpha
            self.set_obstacles(False)
            self.terrain_burst((225, 180, 120))
            self.audio.play("collapse")
            self.shake = max(self.shake, 10.0)
        elif not has_boss and self.terrain_state in ("gone", "fading"):
            self.terrain_state = "returning"
            self.terrain_t = TERRAIN_FADE * (1.0 - self.terrain_alpha)

        if self.terrain_state == "fading":
            self.terrain_t -= dt
            self.terrain_alpha = clamp(self.terrain_t / TERRAIN_FADE, 0.0, 1.0)
            if self.terrain_t <= 0:
                self.terrain_state, self.terrain_alpha = "gone", 0.0
        elif self.terrain_state == "returning":
            self.terrain_t -= dt
            self.terrain_alpha = clamp(1.0 - self.terrain_t / TERRAIN_FADE, 0.0, 1.0)
            if self.terrain_t <= 0:
                self.terrain_state, self.terrain_alpha = "solid", 1.0
                self.set_obstacles(True)
                self.relocate_out_of_walls()
                self.terrain_burst((150, 160, 190))
                self.audio.play("restore")
                self.shake = max(self.shake, 7.0)

    # ---------------- 보스 전용 두뇌 ----------------
    def boss_brain(self, e, dt, dist, dx, dy):
        """보스의 이동/공격 결정. (이동방향, 속도배율)을 돌려준다.

        일반 적은 '플레이어를 향해 직진'뿐이지만 보스는 상태 기계로 움직인다.

            move ──(쿨타임 끝 + 가시선)──> windup ──> [공격] ──> recover ──> move
                                                   └─ dash면 ─> dash ─> recover

        이동은 세 가지를 거리에 따라 갈라 쓴다.
          · 멀면  : 요격점(예측 위치)으로 접근      → 플레이어의 도주 방향을 가로막음
          · 가까우면: 후퇴                          → 근접에서 두들겨 맞는 걸 피함
          · 중간이면: 선회(strafe)                  → 사거리를 유지하며 옆으로 돌기

        dist/dx/dy는 update_enemies()가 이미 e.target_pi 기준으로 계산해서 넘겨주므로,
        여기서도 반드시 같은 대상(self.players[e.target_pi])을 써야 한다 — 안 그러면
        "쫓는 사람과 조준하는 사람이 다른" 버그가 생긴다.
        """
        p = self.players[e.target_pi]
        grid = self.grid
        e.state_t -= dt
        e.atk_cd -= dt

        # 상시 러너 소환. 공격 패턴과 별개로 계속 돌아서 전장이 비지 않는다.
        e.trickle_t -= dt
        if e.trickle_t <= 0:
            e.trickle_t = e.trickle_interval * random.uniform(0.85, 1.15)
            self.boss_summon(e, 2 + e.tier // 2, "runner")

        # --- 예비동작: 제자리에서 살짝만 움직이며 조준을 고정한다.
        #     공격 직전에 멈칫하는 시간이 있어야 플레이어가 피할 수 있다.
        if e.state == "windup":
            if e.state_t <= 0:
                self.boss_attack(e)
                if e.pattern == "dash":
                    self.audio.play("dash")
                    e.state, e.state_t = "dash", 0.45
                else:
                    e.state, e.state_t = "recover", 0.45
            return (e.lock_x, e.lock_y), 0.15

        # --- 돌진: 예비동작에서 고정한 방향으로 빠르게 밀고 들어간다.
        if e.state == "dash":
            if e.state_t <= 0:
                e.state, e.state_t = "recover", 0.5
                return None, 1.0
            if random.random() < 0.6:
                self.particles.append(
                    Particle(e.x, e.y, (255, 150, 90), 3, 60)
                )
            return (e.lock_x, e.lock_y), 3.1

        # --- 경직: 공격 직후 잠깐 느려진다(반격 기회).
        if e.state == "recover":
            if e.state_t <= 0:
                e.state = "move"
            return None, 0.45

        # --- 이동 상태에서 공격 시작 판정
        los = dist < 780 and grid.line_clear(e.x, e.y, p.x, p.y, 6)
        if e.atk_cd <= 0 and los:
            pats = e.unlocked_patterns()
            total = sum(w for _, w, _ in pats)
            r = random.uniform(0, total)
            for name, w, tel in pats:
                r -= w
                if r <= 0:
                    e.pattern = name
                    break
            else:
                e.pattern = pats[-1][0]
            tele = dict((n, t) for n, _, t in pats)[e.pattern]
            # 조준 방향을 지금 고정한다. 돌진/조준탄은 예측 위치를 노린다.
            if e.pattern in ("aimed", "dash"):
                sp = BOSS_BULLET_SPEED if e.pattern == "aimed" else e.speed * 3.1
                ax, ay = predict_intercept(e.x, e.y, sp, p.x, p.y, p.mvx, p.mvy)
            else:
                ax, ay = p.x, p.y
            e.lock_x, e.lock_y, _ = norm(ax - e.x, ay - e.y)
            e.state, e.state_t = "windup", tele
            e.atk_cd = e.attack_cd
            self.audio.play("telegraph")
            return (e.lock_x, e.lock_y), 0.15

        # --- 거리 유지 기동
        keep = e.keep_range
        if dist > keep + BOSS_KEEP_BAND:
            if los:
                # 플레이어가 '갈' 자리로 접근한다(현재 위치가 아니라).
                ax, ay = predict_intercept(e.x, e.y, e.speed, p.x, p.y, p.mvx, p.mvy)
                ndx, ndy, _ = norm(ax - e.x, ay - e.y)
                return (ndx, ndy), 1.0
            return None, 1.0          # 벽 너머면 일반 A* 추격에 맡긴다
        if dist < keep - BOSS_KEEP_BAND:
            # 너무 붙었으면 물러선다. 뒤가 벽이면 물러설 곳이 없으니 선회로.
            bx, by = -dx / max(dist, 1e-6), -dy / max(dist, 1e-6)
            if grid.line_clear(e.x, e.y, e.x + bx * 90, e.y + by * 90, e.r):
                return (bx, by), 0.85

        # 선회: 플레이어를 향한 방향의 법선. 벽에 막히면 반대로 돈다.
        ux, uy = dx / max(dist, 1e-6), dy / max(dist, 1e-6)
        sx, sy = -uy * e.strafe_dir, ux * e.strafe_dir
        e.goal_t -= dt
        blocked = not grid.line_clear(e.x, e.y, e.x + sx * 80, e.y + sy * 80, e.r)
        if blocked or e.goal_t <= 0:
            if blocked:
                e.strafe_dir *= -1
                sx, sy = -sx, -sy
            e.goal_t = random.uniform(1.4, 2.6)
        # 사거리를 유지하도록 반경 방향 보정을 살짝 섞는다.
        pull = (dist - keep) / max(keep, 1.0)
        return (sx + ux * pull * 0.6, sy + uy * pull * 0.6), 0.9

    def boss_summon(self, e, n, kind="runner"):
        """보스 주변에 졸개를 불러낸다. 스폰 자리는 몸집이 들어가는 칸으로 고른다."""
        st = ENEMY_TYPES[kind]
        made = 0
        for _ in range(n):
            if len(self.enemies) >= self.enemy_cap + 12:
                break
            a = random.uniform(0, math.tau)
            d = random.uniform(55, 95)
            spot = self.grid.nearest_walkable(
                *self.grid.world_to_tile(e.x + math.cos(a) * d, e.y + math.sin(a) * d),
                4, st["r"])
            if not spot:
                continue
            wx, wy = self.grid.tile_center(*spot)
            self.enemies.append(
                Enemy(kind, wx, wy, (1.0 + WAVE_HP_GROWTH) ** (self.wave - 1),
                      False, self.enemy_hp_mul, self.enemy_speed_mul,
                      self.enemy_damage_mul * (1.0 + WAVE_DMG_GROWTH * (self.wave - 1))))
            made += 1
            for _ in range(6):
                self.particles.append(Particle(wx, wy, (200, 120, 255), 3, 120))
        return made

    def boss_attack(self, e):
        """예비동작이 끝난 순간 실제로 공격을 발사한다."""
        dmg = max(8.0, e.dmg * 0.45)
        lx, ly = e.lock_x, e.lock_y

        if e.pattern in ("aimed", "spread", "radial"):
            self.audio.play("boss_shot")

        def shoot(vx, vy, d=None):
            self.boss_bullets.append(
                BossBullet(
                    e.x + vx / BOSS_BULLET_SPEED * (e.r + 9),
                    e.y + vy / BOSS_BULLET_SPEED * (e.r + 9),
                    vx, vy, dmg if d is None else d,
                )
            )

        if e.pattern == "aimed":
            shoot(lx * BOSS_BULLET_SPEED, ly * BOSS_BULLET_SPEED)
        elif e.pattern == "spread":
            n = 3 + min(4, e.tier - 1)          # 단계마다 탄이 늘어난다
            base = math.atan2(ly, lx)
            for i in range(n):
                a = base + (i - (n - 1) / 2) * 0.20
                shoot(math.cos(a) * BOSS_BULLET_SPEED, math.sin(a) * BOSS_BULLET_SPEED)
        elif e.pattern == "radial":
            n = 10 + 2 * min(5, e.tier)
            off = random.uniform(0, math.tau)   # 매번 각도를 틀어 외우기 어렵게
            for i in range(n):
                a = off + math.tau * i / n
                sp = BOSS_BULLET_SPEED * 0.8
                shoot(math.cos(a) * sp, math.sin(a) * sp, dmg * 0.75)
        elif e.pattern == "summon":
            self.boss_summon(e, 2 + min(4, e.tier // 2))
        elif e.pattern == "dash":
            self.shake = max(self.shake, 6.0)

        for _ in range(8):
            self.particles.append(Particle(e.x, e.y, (215, 110, 245), 3, 130))

    # ---------------- 무기 ----------------
    def nearest_enemy(self, x, y, rng):
        best, bd = None, rng * rng
        for e in self.hash.query(x, y, rng):
            d2 = (e.x - x) ** 2 + (e.y - y) ** 2
            if d2 < bd:
                best, bd = e, d2
        return best

    def update_weapons(self, dt):
        # 협동이면 두 플레이어가 각자 자기 총/오브/오라를 독립적으로 굴린다.
        for p in self.players:
            if p.hp <= 0:
                continue  # 쓰러진 플레이어는 공격도 멈춘다
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
                        self.audio.play("shoot")
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

    # [ChatGPT 수정] 보스 탄환 처리. 플레이어의 무적 시간은 기존 접촉 피해와 공유한다.
    def update_boss_bullets(self, dt):
        alive = []
        for b in self.boss_bullets:
            b.x += b.vx * dt
            b.y += b.vy * dt
            b.life -= dt
            if b.life <= 0:
                continue

            tx, ty = self.grid.world_to_tile(b.x, b.y)
            if self.grid.is_solid(tx, ty):
                for _ in range(5):
                    self.particles.append(Particle(b.x, b.y, (190, 90, 235), 2, 90))
                continue

            # 원래 노리던 대상이 아니어도, 탄환 경로에 서 있던 다른 플레이어면 맞는다.
            hit = False
            for p in self.players:
                if p.hp <= 0:
                    continue
                if (p.x - b.x) ** 2 + (p.y - b.y) ** 2 < (p.r + b.r) ** 2:
                    hit = True
                    if p.iframe <= 0:
                        self.audio.play("hurt")
                        p.hp -= b.dmg
                        p.iframe = 0.55
                        self.shake = max(self.shake, 8.0)
                        if self.show_damage_numbers:
                            self.texts.append(FloatText(p.x, p.y - p.r - 8, f"-{int(b.dmg)}", C_HP))
                        for _ in range(10):
                            self.particles.append(Particle(p.x, p.y, C_HP))
                    break
            if hit:
                continue

            alive.append(b)
        self.boss_bullets = alive

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
            self.audio.play("hit")
        if not silent and self.show_damage_numbers:
            self.texts.append(
                FloatText(
                    e.x, e.y - e.r, str(int(amount)), C_GOLD if amount > 20 else C_UI
                )
            )
        if e.hp <= 0 and e in self.enemies:
            self.enemies.remove(e)
            self.kills += 1
            self.audio.play("boss_die" if e.kind == "boss" else "kill")
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
        keep = []
        for g in self.gems:
            g.t += dt
            # 젬 하나는 가장 가까운 살아있는 플레이어한테만 끌려가고 먹힌다 —
            # 둘 다에게 동시에 끌리면 어중간한 곳에서 진동한다.
            pi = self.nearest_player_index(g.x, g.y)
            p = self.players[pi] if pi is not None else None
            d = 1e18
            dx = dy = 0.0
            if p is not None:
                dx, dy = p.x - g.x, p.y - g.y
                d = math.hypot(dx, dy)
            if p is not None and d < p.magnet:
                s = 460 if d < p.magnet * 0.5 else 240
                g.x += dx / max(d, 1e-6) * s * dt
                g.y += dy / max(d, 1e-6) * s * dt
            else:
                g.x += g.vx * dt
                g.y += g.vy * dt
                g.vx *= 0.9
                g.vy *= 0.9
            if p is not None and d < 18:
                if g.heart:
                    self.audio.play("heal")
                    p.hp = min(p.max_hp, p.hp + 25)
                    self.texts.append(FloatText(p.x, p.y - 20, "+25", C_HP))
                else:
                    # 보스전에는 소환된 졸개가 많아 경험치가 과하게 들어온다.
                    # 보스가 살아 있는 동안만 획득량을 줄여 레벨업 속도를 맞춘다.
                    mul = BOSS_XP_PENALTY if self.boss_active else 1.0
                    p.xp += g.value * p.xp_mul * mul
                    self.audio.play("pickup")
                continue
            keep.append(g)
        self.gems = keep

        # 둘이 같은 프레임에 동시에 레벨업할 수도 있으니 큐에 쌓아두고 하나씩 보여준다.
        for pi, p in enumerate(self.players):
            while p.xp >= p.xp_need:
                p.xp -= p.xp_need
                p.level += 1
                # [ChatGPT 수정] 난이도가 높을수록 다음 능력 선택까지 더 많은 경험치가 필요하다.
                p.xp_need = (6 + 5 * p.level) * p.xp_need_mul
                self.levelup_queue.append(pi)
        if self.levelup_queue:
            self.open_levelup(self.levelup_queue.pop(0))

    def open_levelup(self, player_index):
        self.levelup_player = player_index
        pool = [
            u for u in UPGRADES
            if self.players[player_index].taken.get(u["key"], 0) < u["max"]
        ]
        random.shuffle(pool)
        self.choices = pool[:3]
        if self.choices:
            self.audio.play("levelup")
            self.state = "levelup"

    def level_summary_text(self):
        """승리/패배 화면에 쓰는 레벨 표시. 협동이면 P1/P2를 나란히 보여준다."""
        if len(self.players) > 1:
            return "   ".join(
                f"P{i + 1} {self.T['lv']} {p.level}" for i, p in enumerate(self.players)
            )
        return f"{self.T['lv']} {self.players[0].level}"

    # ------------------------------------------------------ 그리기
    def update_camera_zoom(self, dt):
        """혼자면 항상 1.0 그대로. 협동이면 살아있는 두 명을 다 담는 데 필요한
        배율을 목표로 잡고 COOP_ZOOM_LERP 속도로 부드럽게 따라간다(뚝뚝 끊기지 않게)."""
        ps = self.alive_players()
        if len(ps) <= 1:
            target = 1.0
        else:
            xs = [p.x for p in ps]
            ys = [p.y for p in ps]
            need_w = (max(xs) - min(xs)) + COOP_ZOOM_MARGIN * 2
            need_h = (max(ys) - min(ys)) + COOP_ZOOM_MARGIN * 2
            fit = min(1.0, SW / max(need_w, 1.0), SH / max(need_h, 1.0))
            target = max(COOP_ZOOM_MIN, fit)
        k = min(1.0, COOP_ZOOM_LERP * dt)
        self.cam_zoom += (target - self.cam_zoom) * k

    def camera(self):
        """카메라 중심(cx, cy)과 줌 배율을 돌려준다. 1인이면 zoom은 항상 1.0으로 고정되어
        있으므로(update_camera_zoom 참고) 아래 계산은 예전 단일 플레이어 카메라와 동일하다."""
        ps = self.alive_players()
        mx = sum(p.x for p in ps) / len(ps)
        my = sum(p.y for p in ps) / len(ps)
        zoom = self.cam_zoom
        vw, vh = SW / zoom, SH / zoom
        cx = clamp(mx - vw / 2, 0, max(0, WORLD_W - vw))
        cy = clamp(my - vh / 2, 0, max(0, WORLD_H - vh))
        if self.shake > 0.2:
            cx += random.uniform(-self.shake, self.shake)
            cy += random.uniform(-self.shake, self.shake)
        return (
            clamp(cx, 0, max(0, WORLD_W - vw)),
            clamp(cy, 0, max(0, WORLD_H - vh)),
            zoom,
        )

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
        cx, cy, zoom = self.camera()
        cam = (cx, cy)
        # 줌아웃 중(협동, 둘이 멀리 떨어짐)이면 필요한 만큼 더 넓은 임시 캔버스에
        # 평소와 똑같은 좌표로 그린 다음, 마지막에 화면 크기로 한 번에 축소해서 붙인다.
        # present_frame()의 레터박싱과 같은 요령이라 draw_world() 안의 그리기 코드
        # 자체는(화면 크기를 참조하는 몇 군데만 빼면) 손댈 필요가 없다.
        vw, vh = (SW, SH) if zoom >= 0.999 else (round(SW / zoom), round(SH / zoom))
        real_screen = self.screen
        if (vw, vh) != (SW, SH):
            if self.world_surf is None or self.world_surf.get_size() != (vw, vh):
                self.world_surf = pygame.Surface((vw, vh))
            self.screen = self.world_surf

        self.screen.blit(self.bg, (0, 0), pygame.Rect(cam[0], cam[1], vw, vh))
        # 장애물 레이어. 보스전에는 알파가 0까지 떨어져 사라진다.
        if self.terrain_alpha > 0.004:
            self.bg_obst.set_alpha(int(255 * self.terrain_alpha))
            self.screen.blit(self.bg_obst, (0, 0), pygame.Rect(cam[0], cam[1], vw, vh))

        # 디버그: A* 경로
        if self.show_paths:
            for e in self.enemies:
                if not (-40 < e.x - cam[0] < vw + 40 and -40 < e.y - cam[1] < vh + 40):
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

        # 오라 (플레이어별로 따로 표시, 쓰러진 플레이어는 무기 자체가 멈춰 있으니 안 그림)
        for pl in self.players:
            if pl.hp <= 0:
                continue
            if pl.aura_lv:
                r = pl.aura_radius
                self.screen.blit(self.aura_surface(r), (pl.x - cam[0] - r, pl.y - cam[1] - r))

        # 젬 / 하트
        for g in self.gems:
            bob = math.sin(g.t * 6) * 2
            self.blit_center("heart" if g.heart else "gem", g.x, g.y + bob, cam)

        # 보스 예비동작 표시. 무엇이 올지 미리 보여줘야 피할 수 있다.
        for e in self.enemies:
            if e.kind != "boss" or e.state != "windup":
                continue
            # 조준탄·산탄 같은 평타는 표시하지 않는다.
            # 전부 알려주면 긴장감이 없고, 특수공격 표시도 눈에 안 들어온다.
            if e.pattern in ("aimed", "spread"):
                continue
            ex, ey = int(e.x - cam[0]), int(e.y - cam[1])
            prog = 1.0 - clamp(e.state_t / 0.8, 0.0, 1.0)   # 0 → 1로 차오름
            if e.pattern == "radial":
                # 전방위: 링이 바깥으로 퍼진다
                pygame.draw.circle(self.screen, (255, 120, 190), (ex, ey),
                                   int(30 + 90 * prog), 2)
            elif e.pattern == "dash":
                # 돌진: 날아올 직선을 미리 긋는다
                pygame.draw.line(self.screen, (255, 170, 90), (ex, ey),
                                 (int(ex + e.lock_x * 260), int(ey + e.lock_y * 260)), 3)
            elif e.pattern == "summon":
                pygame.draw.circle(self.screen, (190, 130, 255), (ex, ey), 74, 2)
            pygame.draw.circle(self.screen, (255, 235, 140), (ex, ey),
                               int(e.r + 6 + 4 * math.sin(prog * 12)), 2)

        # 적
        for e in self.enemies:
            if -60 < e.x - cam[0] < vw + 60 and -60 < e.y - cam[1] < vh + 60:
                if e.elite:
                    pygame.draw.circle(
                        self.screen,
                        (255, 200, 90),
                        (int(e.x - cam[0]), int(e.y - cam[1])),
                        e.r + 4,
                        2,
                    )
                self.blit_center(e.img, e.x, e.y, cam, e.facing < 0, e.flash > 0)
                if self.show_enemy_hp_bars and e.hp < e.max_hp:
                    w = e.r * 2
                    x0, y0 = e.x - cam[0] - e.r, e.y - cam[1] - e.r - 8
                    pygame.draw.rect(self.screen, (30, 12, 16), (x0, y0, w, 3))
                    pygame.draw.rect(
                        self.screen, C_HP, (x0, y0, w * (e.hp / e.max_hp), 3)
                    )

        # 궤도 오브 (플레이어별로 따로 돈다)
        for pl in self.players:
            if pl.hp <= 0:
                continue
            for i in range(pl.orbs):
                a = pl.orb_angle + math.tau * i / pl.orbs
                self.blit_center("orb", pl.x + math.cos(a) * 76, pl.y + math.sin(a) * 76, cam)

        # [ChatGPT 수정] 보스 탄환은 플레이어 총알과 색/크기를 다르게 그려 쉽게 구분한다.
        for b in self.boss_bullets:
            bx, by = int(b.x - cam[0]), int(b.y - cam[1])
            pygame.draw.circle(self.screen, (95, 35, 120), (bx, by), b.r + 4)
            pygame.draw.circle(self.screen, (225, 120, 255), (bx, by), b.r)
            pygame.draw.circle(self.screen, (255, 225, 255), (bx, by), 2)

        # 플레이어 (무적 시간 동안 깜빡임). 1P/2P는 색만 다른 별도 스프라이트
        # ("player1"/"player2", gen_assets.make_player가 둘 다 만들어 둠)로 구분한다.
        for i, pl in enumerate(self.players):
            if pl.hp <= 0:
                # 쓰러짐: 무적 깜빡임보다 훨씬 듬성듬성 보여서 "빠졌다"는 걸 알 수 있게.
                if int(self.time * 4) % 3 == 0:
                    self.blit_center(f"player{i + 1}", pl.x, pl.y, cam, pl.facing < 0)
                continue
            if not (pl.iframe > 0 and int(pl.iframe * 20) % 2 == 0):
                self.blit_center(f"player{i + 1}", pl.x, pl.y, cam, pl.facing < 0)

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

        # 임시 캔버스에 그렸으면 실제 화면 크기로 축소해서 붙이고 되돌린다.
        # HUD(draw_hud)는 이 축소와 무관하게 항상 원래 해상도로 그 위에 그려서
        # 글자/숫자가 흐려지지 않는다.
        if self.screen is not real_screen:
            self.screen = real_screen
            self.screen.blit(pygame.transform.smoothscale(self.world_surf, (SW, SH)), (0, 0))

        return cam

    def draw_hud(self, cam):
        p = self.player
        T = self.T
        # 체력바
        pygame.draw.rect(self.screen, (0, 0, 0, 120), (16, 14, 264, 22))
        pygame.draw.rect(self.screen, (48, 20, 26), (18, 16, 260, 18))
        pygame.draw.rect(self.screen, C_HP, (18, 16, 260 * max(0, p.hp) / p.max_hp, 18))
        # 협동일 때만 "P1"을 붙인다 — 혼자면 P2 바 자체가 없으니 붙일 이유가 없다.
        hp_label = f"P1  {int(max(0, p.hp))} / {int(p.max_hp)}" if len(self.players) > 1 else f"{int(max(0, p.hp))} / {int(p.max_hp)}"
        hp_s = self.f_small.render(hp_label, FONT_ANTIALIAS, C_UI)
        self.screen.blit(hp_s, (148 - hp_s.get_width() // 2, 17))
        # 경험치바
        pygame.draw.rect(self.screen, (18, 42, 48), (18, 40, 260, 10))
        pygame.draw.rect(
            self.screen, C_XP, (18, 40, 260 * clamp(p.xp / p.xp_need, 0, 1), 10)
        )
        self.screen.blit(
            self.f_mid.render(f"{T['lv']} {p.level}", FONT_ANTIALIAS, C_GOLD), (288, 20)
        )

        # 협동이면 P1 바로 밑에 P2용 체력/경험치 바를 하나 더 그린다(1인이면 이 블록
        # 자체가 안 그려지니 지금까지의 레이아웃과 완전히 동일하다).
        if len(self.players) > 1:
            p2 = self.players[1]
            y0 = 54
            pygame.draw.rect(self.screen, (0, 0, 0, 120), (16, y0, 264, 22))
            pygame.draw.rect(self.screen, (48, 20, 26), (18, y0 + 2, 260, 18))
            pygame.draw.rect(
                self.screen, C_HP, (18, y0 + 2, 260 * max(0, p2.hp) / p2.max_hp, 18)
            )
            hp2_s = self.f_small.render(
                f"P2  {int(max(0, p2.hp))} / {int(p2.max_hp)}", FONT_ANTIALIAS, C_UI
            )
            self.screen.blit(hp2_s, (148 - hp2_s.get_width() // 2, y0 + 3))
            pygame.draw.rect(self.screen, (18, 42, 48), (18, y0 + 26, 260, 10))
            pygame.draw.rect(
                self.screen, C_XP, (18, y0 + 26, 260 * clamp(p2.xp / p2.xp_need, 0, 1), 10)
            )
            self.screen.blit(
                self.f_mid.render(f"{T['lv']} {p2.level}", FONT_ANTIALIAS, C_GOLD),
                (288, y0 + 6),
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

        # 보스 체력바. 여러 마리여도 바는 하나만 그리고 체력을 합산한다.
        # 줄이 늘어나면 화면만 어수선하고, 어차피 전부 잡아야 웨이브가 끝난다.
        bosses = [e for e in self.enemies if e.kind == "boss"]
        if bosses:
            cur = sum(max(0.0, e.hp) for e in bosses)
            top = sum(e.max_hp for e in bosses)
            tier = max(e.tier for e in bosses)
            bw, bh = 420, 18
            bx, by = SW // 2 - bw // 2, SH - 34
            pygame.draw.rect(self.screen, (12, 8, 14), (bx - 3, by - 3, bw + 6, bh + 6))
            pygame.draw.rect(self.screen, (52, 16, 24), (bx, by, bw, bh))
            pygame.draw.rect(self.screen, (214, 60, 78), (bx, by, bw * cur / top, bh))
            pygame.draw.rect(self.screen, (255, 190, 120), (bx - 3, by - 3, bw + 6, bh + 6), 1)
            name = f"BOSS Lv.{tier}" + (f"  x{len(bosses)}" if len(bosses) > 1 else "")
            lab = self.f_small.render(name, FONT_ANTIALIAS, (255, 220, 200))
            self.screen.blit(lab, (bx, by - lab.get_height() - 4))
            pct = self.f_small.render(f"{cur / top * 100:.0f}%", FONT_ANTIALIAS, (255, 220, 200))
            self.screen.blit(pct, (bx + bw - pct.get_width(), by - pct.get_height() - 4))

        # 미니맵
        mm = self.minimap_bg.copy()
        for e in self.enemies:
            mm.fill((236, 92, 92), (int(e.x / TILE * 2), int(e.y / TILE * 2), 2, 2))
        for e in self.enemies:
            if e.kind == "boss":
                mm.fill((255, 180, 90), (int(e.x / TILE * 2) - 2, int(e.y / TILE * 2) - 2, 5, 5))
        dot_colors = ((120, 220, 255), (255, 150, 150))
        for i, pl in enumerate(self.players):
            col = dot_colors[i % len(dot_colors)]
            mm.fill(col, (int(pl.x / TILE * 2) - 1, int(pl.y / TILE * 2) - 1, 4, 4))
        self.screen.blit(mm, (SW - mm.get_width() - 14, 14))

        # 배속 위젯. 일시정지로 안 들어가도 인게임에서 바로 화살표로 조절할 수 있게
        # 미니맵 밑에 작고 투명하게 둔다. 일시정지 중에는 draw_pause()가 같은 자리에
        # 암전 레이어 '위에' 한 번 더 그린다.
        if self.state in ("play", "pause"):
            self.draw_speed_widget(mm.get_width())
        # 설정(톱니바퀴) 버튼은 플레이 중에만 — 체력/경험치 바로 밑, 왼쪽 상단.
        if self.state == "play":
            self.draw_gear_button()

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

    def draw_speed_widget(self, width, foreground=False):
        """미니맵 아래의 기존 배속 위젯. pause에서는 같은 자리에 밝게 다시 그린다."""
        aw, wh = 26, 26
        x = SW - width - 14
        y = 14 + 96 + 8  # 미니맵(MAP_H*2=96 높이) 바로 아래
        panel = pygame.Surface((width, wh), pygame.SRCALPHA)
        # [ChatGPT 수정] 일시정지 중 foreground=True면 암전보다 앞쪽의 불투명 패널로 표시.
        panel.fill((10, 12, 18, 238 if foreground else 130))
        self.screen.blit(panel, (x, y))
        if foreground:
            pygame.draw.rect(
                self.screen, C_GOLD, (x - 2, y - 2, width + 4, wh + 4), 2, border_radius=5
            )

        label_s = self.f_small.render(
            f"{self.T['speed_label']} {self.game_speed:g}x", FONT_ANTIALIAS, C_UI
        )
        self.screen.blit(
            label_s,
            (x + width // 2 - label_s.get_width() // 2, y + wh // 2 - label_s.get_height() // 2),
        )

        i = GAME_SPEEDS.index(self.game_speed)
        mouse_pos = self.mouse_logical_pos()
        self.speed_widget_buttons = []
        for id_, ax, glyph, enabled in (
            ("dec", x, "<", i > 0),
            ("inc", x + width - aw, ">", i < len(GAME_SPEEDS) - 1),
        ):
            btn = ui.Button(ax, y, aw, wh, id_)
            btn.update_hover(mouse_pos if enabled else None)
            self.speed_widget_buttons.append(btn)
            col = C_GOLD if btn.hover else (C_UI if enabled else (70, 74, 86))
            glyph_s = self.f_mid.render(glyph, FONT_ANTIALIAS, col)
            self.screen.blit(
                glyph_s,
                (ax + aw // 2 - glyph_s.get_width() // 2, y + wh // 2 - glyph_s.get_height() // 2),
            )

    def gear_button_rect(self):
        """체력/경험치 바 바로 밑, 톱니바퀴 설정 버튼 자리. 협동이면 P2 바 밑으로 내려간다."""
        y = 54 if len(self.players) == 1 else 98
        return pygame.Rect(16, y, 42, 42)

    def draw_gear_button(self):
        """플레이 중에만 보이는 설정 버튼. ESC(일시정지)와는 별개로 이걸 눌러야 설정 화면이 뜬다."""
        rect = self.gear_button_rect()
        mouse_pos = self.mouse_logical_pos()
        btn = ui.Button(rect.x, rect.y, rect.w, rect.h, "gear")
        btn.update_hover(mouse_pos)
        self.gear_button = btn

        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        panel.fill((10, 12, 18, 170))
        self.screen.blit(panel, rect.topleft)
        border_col = C_GOLD if btn.hover else (90, 96, 112)
        pygame.draw.rect(self.screen, border_col, rect, 2, border_radius=6)
        gear = self.img["gear"]
        self.screen.blit(
            gear, (rect.centerx - gear.get_width() // 2, rect.centery - gear.get_height() // 2)
        )

    def draw_levelup(self):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((8, 10, 16, 190))
        self.screen.blit(ov, (0, 0))
        # 협동이면 지금 누구 차례인지 제목 앞에 표시 — 옆 사람은 화면이 멈춘 이유를 몰라 헷갈릴 수 있다.
        title_text = self.T["levelup"]
        if len(self.players) > 1:
            title_text = f"P{self.levelup_player + 1}  {title_text}"
        t = self.f_huge.render(title_text, FONT_ANTIALIAS, C_GOLD)
        self.screen.blit(t, (SW // 2 - t.get_width() // 2, 70))
        sub = self.f_small.render(self.T["choose"], FONT_ANTIALIAS, C_DIM)
        self.screen.blit(sub, (SW // 2 - sub.get_width() // 2, 138))

        li = 0 if self.lang == "ko" else 1
        cw, ch = 280, 190
        mouse_pos = self.mouse_logical_pos()
        self.levelup_buttons = []
        for i, up in enumerate(self.choices):
            x = SW // 2 + (i - 1) * (cw + 24) - cw // 2
            y = 200
            btn = ui.Button(x, y, cw, ch, i)
            btn.update_hover(mouse_pos)
            self.levelup_buttons.append(btn)
            pygame.draw.rect(self.screen, C_PANEL, (x, y, cw, ch), border_radius=10)
            border_col = C_GOLD if btn.hover else C_XP
            border_w = 3 if btn.hover else 2
            pygame.draw.rect(self.screen, border_col, (x, y, cw, ch), border_w, border_radius=10)
            num = self.f_huge.render(str(i + 1), FONT_ANTIALIAS, (60, 70, 92))
            self.screen.blit(
                num, (x + cw - num.get_width() - 14, y + ch - num.get_height() - 6)
            )
            name = self.f_big.render(up["name"][li], FONT_ANTIALIAS, C_UI)
            self.screen.blit(name, (x + 20, y + 26))
            desc = self.f_small.render(up["desc"][li], FONT_ANTIALIAS, C_DIM)
            self.screen.blit(desc, (x + 20, y + 78))
            cur = self.players[self.levelup_player].taken.get(up["key"], 0)
            for k in range(up["max"]):
                col = C_GOLD if k < cur else (58, 64, 82)
                pygame.draw.rect(self.screen, col, (x + 20 + k * 16, y + 118, 12, 8))

    def draw_pause(self):
        self.draw_center_text(
            [
                (self.T["pause"], self.f_huge, C_UI),
                (self.T["resume"], self.f_mid, C_DIM),
                (self.T["pause_home"], self.f_mid, C_DIM),
            ]
        )
        # [ChatGPT 수정] 암전 레이어가 그려진 뒤에 같은 배속 위젯을 다시 그려
        # '앞에 떠 있는 실제 클릭 가능한 설정'이라는 것이 눈에 확실히 보이게 한다.
        width = self.minimap_bg.get_width()
        self.draw_speed_widget(width, foreground=True)

    def draw_settings(self):
        """톱니바퀴 버튼으로 여는 설정 화면. ESC/P는 여기서 아무 동작도 안 하도록
        on_key에 이 상태에 대한 분기를 일부러 안 만들었다 — 오직 마우스로만 닫는다."""
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((8, 10, 16, 205))
        self.screen.blit(ov, (0, 0))

        T = self.T
        # 토글 버튼은 전부 같은 크기로 통일한다(원래 60x26이었는데 "효과음 켬" 글자가
        # 넘쳐서 20%씩 키운 걸, 나머지 버튼들도 크기를 맞춰달라는 피드백 반영).
        btn_w, btn_h = 72, 31
        panel_w, panel_h = 600, 400
        px, py = SW // 2 - panel_w // 2, SH // 2 - panel_h // 2
        pygame.draw.rect(self.screen, C_PANEL, (px, py, panel_w, panel_h), border_radius=12)
        pygame.draw.rect(self.screen, C_XP, (px, py, panel_w, panel_h), 2, border_radius=12)

        title_s = self.f_huge.render(T["settings"], FONT_ANTIALIAS, C_GOLD)
        self.screen.blit(title_s, (SW // 2 - title_s.get_width() // 2, py + 20))

        mouse_pos = self.mouse_logical_pos()
        self.settings_buttons = []
        self.settings_sliders = {}
        slider_x, slider_w = px + 210, 200
        label_x = px + 30
        row_y = py + 82
        row_gap = 58

        def toggle_button(label, active_col, x, y):
            btn = ui.Button(x, y, btn_w, btn_h, "")
            btn.update_hover(mouse_pos)
            pygame.draw.rect(
                self.screen, C_GOLD if btn.hover else (60, 66, 82), btn.rect, 2, border_radius=6
            )
            lab = self.f_small.render(label, FONT_ANTIALIAS, active_col)
            # 가운데 정렬: 버튼 중심에서 글자 폭/높이의 절반만큼 빼서 위치를 잡는다.
            self.screen.blit(
                lab, (btn.rect.centerx - lab.get_width() // 2, btn.rect.centery - lab.get_height() // 2)
            )
            return btn

        def volume_row(y, label, value, slider_id, mute_label, mute_id, muted):
            self.screen.blit(self.f_mid.render(label, FONT_ANTIALIAS, C_UI), (label_x, y))
            track = pygame.Rect(slider_x, y + 6, slider_w, 10)
            hit = pygame.Rect(slider_x, y - 4, slider_w, 26)
            self.settings_sliders[slider_id] = hit
            pygame.draw.rect(self.screen, (18, 20, 30), track, border_radius=5)
            fill_w = int(slider_w * clamp(value, 0.0, 1.0))
            if fill_w > 0:
                pygame.draw.rect(self.screen, C_XP, (track.x, track.y, fill_w, track.h), border_radius=5)
            thumb_hover = mouse_pos is not None and hit.collidepoint(mouse_pos)
            thumb_col = C_GOLD if (thumb_hover or self.dragging_slider == slider_id) else C_UI
            thumb_pos = (track.x + fill_w, track.centery)
            pygame.draw.circle(self.screen, thumb_col, thumb_pos, 8)
            pygame.draw.circle(self.screen, (14, 16, 24), thumb_pos, 8, 2)
            pct_s = self.f_small.render(f"{int(round(value * 100))}%", FONT_ANTIALIAS, C_UI)
            self.screen.blit(pct_s, (slider_x + slider_w + 14, y))
            mb = toggle_button(mute_label, C_HP if muted else C_XP, px + panel_w - 30 - btn_w, y - 4)
            mb.id = mute_id
            self.settings_buttons.append(mb)

        def bool_row(y, label, on, on_id):
            self.screen.blit(self.f_mid.render(label, FONT_ANTIALIAS, C_UI), (label_x, y))
            btn = toggle_button(
                T["on"] if on else T["off"], C_XP if on else C_HP, px + panel_w - 30 - btn_w, y - 4
            )
            btn.id = on_id
            self.settings_buttons.append(btn)

        volume_row(
            row_y, T["bgm_volume"], self.audio.bgm_volume, "bgm",
            T["bgm_off"] if self.audio.bgm_muted else T["bgm_on"], "bgm_mute", self.audio.bgm_muted,
        )
        row_y += row_gap
        volume_row(
            row_y, T["sfx_volume"], self.audio.sfx_volume, "sfx",
            T["muted"] if self.audio.muted else T["unmuted"], "sfx_mute", self.audio.muted,
        )
        row_y += row_gap
        bool_row(row_y, T["damage_numbers"], self.show_damage_numbers, "damage_toggle")
        row_y += row_gap
        bool_row(row_y, T["enemy_hp_bars"], self.show_enemy_hp_bars, "enemy_hp_toggle")
        row_y += row_gap

        close_w, close_h = 140, 40
        close_rect = pygame.Rect(SW // 2 - close_w // 2, row_y + 10, close_w, close_h)
        close_btn = ui.Button(close_rect.x, close_rect.y, close_w, close_h, "close")
        close_btn.update_hover(mouse_pos)
        self.settings_buttons.append(close_btn)
        pygame.draw.rect(self.screen, C_PANEL, close_rect, border_radius=8)
        pygame.draw.rect(
            self.screen, C_GOLD if close_btn.hover else C_XP, close_rect, 2, border_radius=8
        )
        close_s = self.f_mid.render(T["close"], FONT_ANTIALIAS, C_UI)
        self.screen.blit(
            close_s,
            (close_rect.centerx - close_s.get_width() // 2, close_rect.centery - close_s.get_height() // 2),
        )

        # 마우스 왼쪽 버튼을 누른 채 끌면 슬라이더가 계속 따라온다(헤드리스에서는 스킵).
        if not self.headless:
            if self.dragging_slider is not None and pygame.mouse.get_pressed()[0] and mouse_pos is not None:
                rect = self.settings_sliders.get(self.dragging_slider)
                if rect:
                    pct = clamp((mouse_pos[0] - rect.x) / rect.w, 0.0, 1.0)
                    if self.dragging_slider == "bgm":
                        self.audio.set_bgm_volume(pct)
                    elif self.dragging_slider == "sfx":
                        self.audio.set_sfx_volume(pct)
            elif self.dragging_slider is not None and not pygame.mouse.get_pressed()[0]:
                self.dragging_slider = None

    def draw_title(self):
        """타이틀 = 메인 메뉴 허브. 별도 "menu" 상태를 만들지 않고 title을 그대로 확장한다
        (스페이스/엔터로 바로 시작하는 기존 단축키와 동일한 목적지라 상태를 나눌 이유가 없다).
        멀티(협동)는 배치 K에서 연결됨. 설정/리더보드는 아직 화면 자체가 없어서(배치 I/F)
        눌러도 "준비 중" 배너만 뜬다.
        """
        self.screen.fill(C_BG)
        title_s = self.f_huge.render(self.T["title"], FONT_ANTIALIAS, C_XP)
        sub_s = self.f_mid.render(self.T["sub"], FONT_ANTIALIAS, C_UI)
        ctrl_s = self.f_small.render(self.T["ctrl"], FONT_ANTIALIAS, C_DIM)

        items = (
            ("single", self.T["menu_single"], True),
            ("multi", self.T["menu_multi"], True),
            ("settings", self.T["menu_settings"], False),
            ("leaderboard", self.T["menu_leaderboard"], False),
        )
        label_surfs = [
            self.f_mid.render(label, FONT_ANTIALIAS, C_UI if enabled else C_DIM)
            for _, label, enabled in items
        ]
        tag_s = self.f_small.render(self.T["coming_soon"], FONT_ANTIALIAS, C_DIM)

        gap = 24
        bw = max(max(s.get_width() for s in label_surfs) + 48, tag_s.get_width() + 32)
        bh = 78
        row_w = len(items) * bw + (len(items) - 1) * gap

        block_h = (
            title_s.get_height() + 18
            + sub_s.get_height() + 34
            + bh + 30
            + ctrl_s.get_height()
        )
        y = SH // 2 - block_h // 2

        self.screen.blit(title_s, (SW // 2 - title_s.get_width() // 2, y))
        y += title_s.get_height() + 18
        self.screen.blit(sub_s, (SW // 2 - sub_s.get_width() // 2, y))
        y += sub_s.get_height() + 34

        mouse_pos = self.mouse_logical_pos()
        self.menu_buttons = []
        x = SW // 2 - row_w // 2
        for (id_, label, enabled), label_s in zip(items, label_surfs):
            btn = ui.Button(x, y, bw, bh, id_)
            btn.update_hover(mouse_pos if enabled else None)
            self.menu_buttons.append(btn)
            pygame.draw.rect(
                self.screen, C_PANEL if enabled else (22, 24, 32), (x, y, bw, bh), border_radius=10
            )
            border_col = C_GOLD if btn.hover else (C_XP if enabled else (54, 58, 70))
            pygame.draw.rect(
                self.screen, border_col, (x, y, bw, bh), 3 if btn.hover else 2, border_radius=10
            )
            self.screen.blit(label_s, (x + bw // 2 - label_s.get_width() // 2, y + 14))
            if not enabled:
                self.screen.blit(
                    tag_s, (x + bw // 2 - tag_s.get_width() // 2, y + bh - tag_s.get_height() - 12)
                )
            x += bw + gap
        y += bh + 30

        self.screen.blit(ctrl_s, (SW // 2 - ctrl_s.get_width() // 2, y))

    def draw_difficulty(self):
        self.screen.fill(C_BG)
        title_s = self.f_huge.render(self.T["difficulty"], FONT_ANTIALIAS, C_XP)
        hint_s = self.f_big.render(self.T["difficulty_hint"], FONT_ANTIALIAS, C_GOLD)

        keys = ("easy", "normal", "hard", "very_hard")
        colors = {"easy": C_UI, "normal": C_UI, "hard": C_HP, "very_hard": C_HP}
        row_surfs = []
        for key in keys:
            d = DIFFICULTIES[key]
            text = (
                f"{self.T[key]}  HP {d['hp']:.0f}  ·  XP {d['xp_mul'] * 100:.0f}%  ·  "
                f"ENEMY HP {d['enemy_hp_mul'] * 100:.0f}%  ·  SPEED {d['enemy_speed_mul'] * 100:.0f}%  ·  "
                f"DMG {d['enemy_damage_mul'] * 100:.0f}%"
            )
            row_surfs.append(self.f_small.render(text, FONT_ANTIALIAS, colors[key]))

        gap = 14
        row_w = max(s.get_width() for s in row_surfs) + 48
        row_h = max(s.get_height() for s in row_surfs) + 22
        block_h = (
            title_s.get_height() + 16
            + hint_s.get_height() + 28
            + len(keys) * row_h + (len(keys) - 1) * gap
        )
        y = SH // 2 - block_h // 2

        self.screen.blit(title_s, (SW // 2 - title_s.get_width() // 2, y))
        y += title_s.get_height() + 16
        self.screen.blit(hint_s, (SW // 2 - hint_s.get_width() // 2, y))
        y += hint_s.get_height() + 28

        mouse_pos = self.mouse_logical_pos()
        self.difficulty_buttons = []
        x = SW // 2 - row_w // 2
        for key, surf in zip(keys, row_surfs):
            btn = ui.Button(x, y, row_w, row_h, key)
            btn.update_hover(mouse_pos)
            self.difficulty_buttons.append(btn)
            pygame.draw.rect(self.screen, C_PANEL, (x, y, row_w, row_h), border_radius=8)
            border_col = C_GOLD if btn.hover else C_XP
            border_w = 3 if btn.hover else 2
            pygame.draw.rect(self.screen, border_col, (x, y, row_w, row_h), border_w, border_radius=8)
            self.screen.blit(surf, (SW // 2 - surf.get_width() // 2, y + row_h // 2 - surf.get_height() // 2))
            y += row_h + gap

    def draw_center_text(self, lines):
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((8, 10, 16, 205))
        self.screen.blit(ov, (0, 0))
        # 줄 수가 화면마다 달라서(2~6줄) 고정 시작 높이를 쓰면 줄이 많은 화면일수록
        # 블록이 아래로 넘쳐 전체적으로 위쪽에 쏠려 보인다. 총 높이를 먼저 재서
        # 블록 자체를 화면 세로 중앙에 맞춘다.
        surfaces = [font.render(text, FONT_ANTIALIAS, col) for text, font, col in lines]
        total_h = sum(s.get_height() for s in surfaces) + 16 * (len(surfaces) - 1)
        y = SH // 2 - total_h // 2
        for s in surfaces:
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
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    running = self.on_click(
                        ui.screen_to_logical(ev.pos, self.display.get_size(), (SW, SH))
                    )
            keys = pygame.key.get_pressed()

            if self.state == "play":
                # 시뮬레이션 시간만 배속하고 실제 프레임 타이밍(dt 자체)은 안 건드린다 —
                # 그래야 렌더링/입력 반응성은 그대로고 게임 진행 속도만 빨라진다.
                self.update(dt * self.game_speed, keys)

            if self.state == "title":
                self.draw_title()
            elif self.state == "difficulty":
                self.draw_difficulty()
            else:
                cam = self.draw_world()
                self.draw_hud(cam)
                if self.state == "levelup":
                    self.draw_levelup()
                elif self.state == "pause":
                    self.draw_pause()
                elif self.state == "settings":
                    self.draw_settings()
                elif self.state == "win":
                    m, sec = divmod(int(self.time), 60)
                    self.draw_center_text(
                        [
                            (self.T["win"], self.f_huge, C_GOLD),
                            (self.T["win_sub"], self.f_big, C_XP),
                            (
                                f"{self.T['survived']}  {m:02d}:{sec:02d}",
                                self.f_mid,
                                C_UI,
                            ),
                            (
                                f"{self.level_summary_text()}   {self.T['kill']} {self.kills}",
                                self.f_mid,
                                C_DIM,
                            ),
                            (self.T["restart"], self.f_mid, C_GOLD),
                            (self.T["home"], self.f_mid, C_UI),
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
                                f"{self.level_summary_text()}   {self.T['kill']} {self.kills}",
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
        elif key == pygame.K_m:
            muted = self.audio.toggle_mute()
            self.banner = (self.T["muted"] if muted else self.T["unmuted"], 1.2)
        elif key == pygame.K_F1:
            self.show_paths = not self.show_paths
        elif self.state == "title" and key in (pygame.K_SPACE, pygame.K_RETURN):
            # 키보드 단축키는 항상 싱글로 시작한다 — 협동은 마우스로 "협동" 버튼을
            # 눌러야만 들어갈 수 있고, 이전 판이 협동이었어도 여기서 확실히 되돌린다.
            self.num_players = 1
            self.state = "difficulty"
        elif self.state == "difficulty" and key in (
            pygame.K_1,
            pygame.K_2,
            pygame.K_3,
            pygame.K_4,
        ):
            # [ChatGPT 수정] 1=쉬움, 2=보통, 3=어려움, 4=매우 어려움 선택.
            self.confirm_difficulty_choice(
                {
                    pygame.K_1: "easy",
                    pygame.K_2: "normal",
                    pygame.K_3: "hard",
                    pygame.K_4: "very_hard",
                }[key]
            )
        elif self.state == "levelup" and key in (pygame.K_1, pygame.K_2, pygame.K_3):
            i = key - pygame.K_1
            if i < len(self.choices):
                self.confirm_levelup_choice(i)
        elif self.state == "play" and key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "pause"
        elif self.state == "pause" and key in (pygame.K_ESCAPE, pygame.K_p):
            self.state = "play"
        elif key == pygame.K_r and self.state in ("over", "win", "pause", "play"):
            self.reset()
            self.state = "play"
            # [ChatGPT 수정] 새 판을 시작하면 BGM도 처음부터 다시 재생한다.
            self.audio.start_bgm(BGM_FILE, restart=True)
        # [ChatGPT 수정] 게임 오버 상태에서 H를 누르면 처음 타이틀 화면으로 돌아간다.
        elif key == pygame.K_h and self.state in ("over", "win", "pause"):
            self.audio.stop_bgm()
            self.state = "title"
        elif key == pygame.K_q:
            return False
        return True

    def on_click(self, pos):
        """마우스 왼쪽 클릭 라우팅 — on_key와 나란한 self.state별 분기."""
        if self.state == "title":
            for btn in self.menu_buttons:
                if btn.hit(pos):
                    if btn.id in ("single", "multi"):
                        self.num_players = 2 if btn.id == "multi" else 1
                        self.audio.play("select")
                        self.state = "difficulty"
                    else:
                        self.banner = (self.T["coming_soon"], 1.2)
                    break
        elif self.state == "levelup":
            for btn in self.levelup_buttons:
                if btn.hit(pos):
                    self.confirm_levelup_choice(btn.id)
                    break
        elif self.state == "difficulty":
            for btn in self.difficulty_buttons:
                if btn.hit(pos):
                    self.confirm_difficulty_choice(btn.id)
                    break
        # 일시정지 중에도 배속 위젯 좌우 버튼은 그대로 클릭할 수 있다.
        elif self.state in ("play", "pause"):
            # 설정(톱니바퀴)은 ESC/일시정지와 완전히 별개 — 플레이 중에만, 마우스로만 연다.
            if self.state == "play" and self.gear_button is not None and self.gear_button.hit(pos):
                self.state = "settings"
                self.audio.play("select")
                return True
            for btn in self.speed_widget_buttons:
                if btn.hit(pos):
                    self.step_game_speed(btn.id)
                    break
        elif self.state == "settings":
            for btn in self.settings_buttons:
                if btn.hit(pos):
                    if btn.id == "bgm_mute":
                        self.audio.toggle_bgm_mute()
                    elif btn.id == "sfx_mute":
                        self.audio.toggle_mute()
                    elif btn.id == "damage_toggle":
                        self.show_damage_numbers = not self.show_damage_numbers
                    elif btn.id == "enemy_hp_toggle":
                        self.show_enemy_hp_bars = not self.show_enemy_hp_bars
                    elif btn.id == "close":
                        self.state = "play"
                    self.audio.play("select")
                    return True
            for sid, rect in self.settings_sliders.items():
                if rect.collidepoint(pos):
                    pct = clamp((pos[0] - rect.x) / rect.w, 0.0, 1.0)
                    if sid == "bgm":
                        self.audio.set_bgm_volume(pct)
                    elif sid == "sfx":
                        self.audio.set_sfx_volume(pct)
                    self.dragging_slider = sid
                    break
        return True

    def mouse_logical_pos(self):
        """현재 마우스 위치를 논리 화면(SW x SH) 좌표로 변환. 헤드리스면 None."""
        if self.headless:
            return None
        return ui.screen_to_logical(pygame.mouse.get_pos(), self.display.get_size(), (SW, SH))

    def confirm_levelup_choice(self, i):
        self.audio.play("select")
        self.players[self.levelup_player].apply_upgrade(self.choices[i])
        # 같은 프레임에 둘 다 레벨업했으면 큐에 남은 다음 사람 화면을 이어서 보여준다.
        if self.levelup_queue:
            self.open_levelup(self.levelup_queue.pop(0))
        else:
            self.state = "play"

    def confirm_difficulty_choice(self, key):
        self.audio.play("select")
        self.difficulty_key = key
        self.reset()
        self.state = "play"
        # [ChatGPT 수정] 난이도 선택 후 실제 게임이 시작되는 순간 제공된 BGM을 반복 재생한다.
        self.audio.start_bgm(BGM_FILE, restart=True)

    def step_game_speed(self, direction):
        i = GAME_SPEEDS.index(self.game_speed)
        i = clamp(i + (1 if direction == "inc" else -1), 0, len(GAME_SPEEDS) - 1)
        self.audio.play("select")
        self.game_speed = GAME_SPEEDS[i]

    # 자동 플레이(테스트용)
    def auto_play(self, frames):
        if self.state == "title":
            # selftest_mode가 "2p"면 "협동" 버튼을, 아니면 지금까지처럼 "싱글" 버튼을
            # 실제로 on_click()으로 눌러서 마우스 클릭 라우팅까지 검증한다.
            want = "multi" if getattr(self, "selftest_mode", "1p") == "2p" else "single"
            for btn in self.menu_buttons:
                if btn.id == want:
                    self.on_click(btn.rect.center)
                    break
        elif self.state == "difficulty":
            # 마우스 클릭 라우팅(on_click)까지 실제로 지나가도록 "보통" 행을 "클릭"한다.
            for btn in self.difficulty_buttons:
                if btn.id == "normal":
                    self.on_click(btn.rect.center)
                    break
        elif self.state == "levelup":
            # 마우스 클릭 라우팅(on_click)까지 실제로 지나가도록 첫 카드를 "클릭"한다.
            self.on_click(self.levelup_buttons[0].rect.center)
        elif self.state in ("over", "win"):
            self.reset()
            self.state = "play"
        elif self.state == "play" and frames % 300 == 150 and self.speed_widget_buttons:
            # 인게임 배속 위젯의 클릭 라우팅도 selftest가 주기적으로 지나가게 한다.
            for btn in self.speed_widget_buttons:
                if btn.id == "inc":
                    self.on_click(btn.rect.center)
                    break
        elif self.state == "play" and frames % 300 == 210 and self.gear_button:
            # 설정(톱니바퀴) 진입 라우팅도 selftest가 주기적으로 지나가게 한다.
            self.on_click(self.gear_button.rect.center)
        elif self.state == "settings":
            # 슬라이더 클릭과 토글/닫기 버튼까지 실제 on_click 경로로 한 번씩 눌러본다.
            rect = self.settings_sliders.get("bgm")
            if rect:
                self.on_click((rect.x + rect.w // 2, rect.centery))
            for btn in self.settings_buttons:
                if btn.id == "close":
                    self.on_click(btn.rect.center)
                    break
        # 플레이어마다 따로 무작위 방향으로 걸어다니게 한다 — 둘이 서로 다른 방향으로
        # 흩어져야 K2의 개별 타겟팅과 K3의 줌아웃이 실제로 트리거되어 검증된다.
        if frames % 24 == 0 or len(self._auto_dirs) != len(self.players):
            self._auto_dirs = [
                random.choice([pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d])
                for _ in self.players
            ]
        for pl, k in zip(self.players, self._auto_dirs):
            v = pl.speed / FPS * 1.0
            move_and_collide(
                self.grid,
                pl,
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

        # 협동(2P) 경로는 메인메뉴 "협동" 버튼 클릭부터 실제로 지나가야 의미가 있어서
        # (위 1인 실행은 "play"에서 바로 시작해 메뉴를 건너뛴다) 이번엔 title부터 시작한다.
        g2 = Game(headless=True)
        g2.selftest_mode = "2p"
        g2.run(max_frames=1800)
        print("selftest OK (2p)")
        return
    Game().run()


if __name__ == "__main__":
    main()
