# Project: 동아리 부스 전시용 게임 — PATHFINDER SURVIVORS

## Overview
동아리 부스에서 전시할 뱀서라이크(vampire-survivors류) 게임. 동아리 부원이 파이썬+pygame으로 만들어 보내준 걸 기반으로 확장 중. A* 경로탐색이 핵심 시스템(적이 벽/바위에 막히면 우회). 사용자는 코딩 초보이며 실제 코드는 대부분 Claude가 작성/검증하고, 사용자는 짧게 플레이해보고 피드백을 주는 방식으로 진행한다 (하루 가용 시간 약 30분).

원래 Godot → Phaser(웹) 타워 디펜스로 진행했으나, 부원이 보내준 이 게임의 완성도가 높아서 완전히 갈아탐 — **기존 웹 프로젝트 파일(`js/`, `index.html`, `lib/`, `assets/`)은 전부 삭제함**(git 히스토리에는 남아있으므로 필요하면 복구 가능). 지금 저장소에는 이 pygame 프로젝트만 있다.

**2026-08-10: 부원이 보스 원거리 공격을 추가한 새 버전(`game_before_boss.py`→`game.py`, 코드 내 `[ChatGPT 수정]` 주석 — 부원이 챗GPT로 작업)을 보내줘서 그 버전으로 교체함.** 교체 과정에서 기존 작업 폴더(배치 A `sfx.py` 포함)가 git 미추적 상태였던 탓에 유실됨.

**2026-08-10 (같은 날, 2차 교체): 부원이 훨씬 커진 정식 배포판 형태의 새 패키지(`README.md`/`LICENSE`/`requirements.txt`/`run.bat`/`diagnose.bat`/`docs/` 포함, `game.py` 2368줄)를 보내줘서 다시 그 버전으로 교체함.** 사용자가 이전 작업 폴더는 직접 정리(삭제)한 상태였다고 확인. 이 버전에서 중요한 변화:
- **사운드(배치 A)가 해결됨** — 단, 유실된 우리 `sfx.py`가 아니라 부원이 만든 `gen_sounds.py`(효과음 18종 + BGM 5종을 numpy로 절차 합성) + `game.py`의 `Audio` 클래스(쿨다운 있는 재생기, 오디오 장치 없으면 조용히 무음 처리)로 대체됨. **더 이상 `sfx.py`를 만들 필요 없음** — 배치 A는 완료로 간주.
- **난이도 선택(배치 C2/J1 상당)이 이미 구현됨** — `DIFFICULTIES` 딕셔너리에 easy/normal/hard/very_hard 4단계, `self.state == "difficulty"` 화면에서 키보드로 선택 가능(마우스는 아직 안 됨 — 배치 B 대상).
- **승리 조건이 생김** — `WIN_WAVE = 30`(보스전 6회, `BOSS_EVERY = 5`), 웨이브 30 클리어 시 `self.state = "win"`. **기존에 확정했던 "승리 화면 없이 자연스럽게 게임오버로 끝남" 방향을 뒤집고, 부원이 만든 이 승리 조건을 그대로 쓰기로 사용자가 결정함.** 부스 세션(2~6분) 목표와 실제로 맞는지는 플레이해보고 튜닝 필요.
- `game_before_boss.py`는 보스 원거리 공격 추가 전 버전이라 diff 참고용으로 계속 남겨둠(기능상 불필요하면 나중에 정리).

**2026-08-16: 공동 작업을 위해 새 GitHub 저장소(`franzliszt1022/2026-computer-science-club`)를 만들어 origin을 이걸로 변경함.** 부원이 이 새 저장소에 먼저 BGM(배경음악) 재생 + 전용 음량 조절 기능이 추가된 버전(`pathfinder-survivors-BGM-VOLUME` 폴더, 코드 내 `[ChatGPT 수정]` 주석)을 올려놨었고, 이번 세션까지의 우리 작업(마우스 UI/메인메뉴/배속 위젯 등) 위에 순수 추가된 내용이라 그대로 로컬에 반영함:
- `game.py`에 `Audio.start_bgm/stop_bgm/toggle_bgm_mute/step_bgm_volume` 추가, `M`은 여전히 효과음만 음소거하고 **BGM 음소거/음량(10%씩)은 별도 위젯**(`draw_bgm_widget`/`draw_bgm_volume_widget`, 배속 위젯 바로 아래)으로 조절. 일시정지 화면 위에도 같은 위젯이 밝게(foreground) 다시 그려져서 계속 조작 가능.
- 새 파일 `assets/bgm_underclocked.mp3` 추가(`gen_sounds.py`가 생성하는 게 아니라 부원이 직접 준비한 실제 오디오 파일) — **출처/라이선스 불명, `RAMCHE.TTF` 폰트와 마찬가지로 부스 전시 전 확인 필요**.
- `README.md`는 부원이 제목을 "A-star Survivors"로 바꾸고 승리 조건 문구를 실제 값(30웨이브)에 맞게 고친 것도 같이 반영함.
- `ui.py`/`pathfinding.py`/`gen_assets.py`/`gen_sounds.py`/`requirements.txt`/`LICENSE`는 부원 버전과 완전히 동일해서 손댈 것 없었음.

## Tech Stack
- Language: Python 3.12
- Framework: pygame (2.6.1) + Pillow(에셋 코드 생성) + numpy(사운드 합성)
- 실행: `py game.py` (이 컴퓨터에서 `python` 명령어는 MS 스토어로 연결되는 깨진 alias라 반드시 `py` 사용)
- Database: 없음 — 로컬 JSON 파일 기반 저장 예정(`save.py`, 배치 F)

## Project Structure
```
C:\SDG\20260728project\
└── pathfinder-survivors\pathfinder-survivors\   # 실제 게임 폴더 (중첩 경로 주의)
    ├── game.py            # 게임 루프, 렌더링, 적 AI, 무기, 레벨업, 보스 원거리 공격, 난이도 선택, 승리/패배 — self.state 문자열 스위치로 화면 전환
    ├── game_before_boss.py # 보스 원거리 공격 추가 전 버전 (diff 참고용, 부원이 같이 보내줌)
    ├── pathfinding.py     # Grid, A*, DDA 가시선, string pulling, flow field — 게임의 '수학 파트'
    ├── gen_assets.py      # Pillow로 모든 스프라이트를 코드로 그려서 assets/에 저장 (외부 이미지 없음)
    ├── gen_sounds.py      # numpy로 효과음 18종 + BGM 5종(현재 미사용, 아래 참고)의 파형을 합성해 assets/sfx/에 WAV로 저장 (배치 A는 이걸로 완료)
    ├── ui.py              # 마우스 버튼 공용 헬퍼 (screen_to_logical 좌표변환 + Button, 배치 B에서 신규 작성, 완료)
    ├── README.md / LICENSE / requirements.txt / run.bat / diagnose.bat / docs/  # 부원이 정식 배포판 형태로 패키징한 부분, 그대로 유지
    ├── assets/            # gen_assets.py/gen_sounds.py가 생성한 PNG·WAV + 폰트(RAMCHE.TTF, 출처: IKINA GAMES 2023 — 부스 전시 전 라이선스 확인 필요) + bgm_underclocked.mp3(2026-08-16 추가, 실제 재생되는 BGM, 출처 불명 — 마찬가지로 확인 필요). PNG·WAV·폰트는 소스에서 파생되므로 .gitignore로 커밋 제외, mp3는 파생물이 아니라서 커밋 대상
    └── __pycache__/
```
확장 예정 파일(계획서 참고): `save.py`(리더보드+설정 JSON 저장, 배치 F) — 부원의 "관심사별로만 파일 분리" 스타일을 따름. `sfx.py`는 더 이상 필요 없음(부원의 `gen_sounds.py`로 대체됨).

## 이 프로젝트 고유 규칙 (부원 코드 스타일 — 반드시 따를 것)
- **화면 전환은 별도 파일이 아니라 `Game.self.state` 문자열 스위치로** (`"title"`/`"play"`/`"levelup"`/`"pause"`/`"over"` 등, 앞으로 `"menu"`/`"shop"`/`"codex"`/`"settings"`/`"stats"` 추가 예정). Phaser 프로젝트처럼 화면마다 Scene 파일을 따로 만들지 않음.
- 모듈 최상단에 설계 의도/수학적 근거를 설명하는 docstring
- 튜닝 가능한 상수는 파일 상단에 ALL_CAPS로 모아둠 ("밸런스는 여기 숫자만 바꾸면 된다")
- `# ---------------------------------------------------------------- 섹션명` 구분선 주석
- 엔티티 클래스는 `__slots__` 사용
- UI 문자열은 전부 `TEXT = {"ko": {...}, "en": {...}}` 이중언어 딕셔너리, `find_korean_font()`가 한글 폰트 없으면 자동으로 영어 UI 전환
- 주석은 "왜"를 설명 (자명한 것은 안 씀)

## Commands
- 실행: `cd pathfinder-survivors\pathfinder-survivors` 후 `py game.py`
- 헤드리스 자동 테스트: `py game.py --selftest` (더미 SDL 드라이버로 1800프레임 자동 실행, "selftest OK" 출력되면 정상)
- 의존성 설치: `py -m pip install pygame pillow numpy`

## Important Notes
- **Claude는 이 게임 화면을 볼 수 없음** — pygame은 네이티브 창이라 claude-in-chrome(브라우저 자동화)이 안 통함. `--selftest`로 크래시/예외 여부만 기계적으로 확인 가능하고, 사운드 품질·밸런스·조작감처럼 "느낌"이 필요한 부분은 반드시 사용자가 직접 플레이해서 말로 피드백을 줘야 함 (Godot 시절과 동일한 제약으로 되돌아간 것 — 이번엔 게임 자체 완성도가 높아서 감수하기로 함).
- **작업 리듬**: 사용자는 하루 약 30분만 가능. 코드는 Claude가 세션 중 직접 작성/검증하고, 사용자는 짧게 플레이해보고 피드백만 준다.
- **부스 타겟 플레이타임**: 2~6분. **(2026-08-10 변경) 승리 조건 있음** — `WIN_WAVE = 30`(보스전 6회) 클리어 시 승리 화면. 부원이 만든 이 구조를 그대로 쓰기로 사용자가 결정(기존의 "승리 화면 없이 자연스럽게 게임오버" 방향은 폐기). 실제 플레이 시간이 부스 목표(2~6분)에 맞는지는 플레이해보고 웨이브 페이싱 상수(`WAVE_*`, `WIN_WAVE`, `BOSS_EVERY`)로 튜닝 필요.
- **재화(업그레이드용)는 판마다 리셋** — 세션 간 누적 없음, 부스 방문객마다 공평한 시작.
- **상세 로드맵**: `C:\Users\namhs\.claude\plans\proud-twirling-reddy.md` — 배치 A(사운드)~K(멀티플레이) 순서와 각 배치 상세 내용이 정리되어 있음.
- **GitHub 저장소**: `franzliszt1022/2026-computer-science-club` (2026-08-16부터 origin, 부원과 공동 작업용으로 새로 만듦). 그 전 origin(`franzliszt1022/20260728project`)은 더 이상 안 씀.

## 진행 상황 (2026-08-10 기준)
- [x] 부원 원본 게임 실행 확인 (pygame/pillow 설치, `--selftest` 통과)
- [x] 기존 Phaser 타워 디펜스 프로젝트 파일 삭제
- [x] 부원이 보스 원거리 공격 추가한 새 버전으로 게임 베이스 교체 (2026-08-10)
- [x] 부원이 정식 배포판 형태(사운드 포함)의 2차 새 버전을 보내줘서 그 버전으로 다시 교체 (2026-08-10, 같은 날 2차)
- [x] 배치 A: 사운드 — 부원의 `gen_sounds.py` + `Audio` 클래스로 이미 해결됨(우리 `sfx.py`는 안 씀). `--selftest` 통과 확인
- [x] 배치 A-stretch: BGM 실제 재생 (2026-08-16) — 부원이 `bgm_underclocked.mp3` + `Audio.start_bgm/stop_bgm/toggle_bgm_mute/step_bgm_volume` + 전용 위젯(배속 위젯 아래)을 추가해서 해결. `gen_sounds.py`가 만드는 BGM 5종 WAV는 여전히 미사용(정리 여지 있으나 급하지 않음)
- [x] 난이도 선택 (배치 C2/J1 상당) — `DIFFICULTIES` 4단계 + `"difficulty"` 화면, 부원 버전에 이미 있음
- [x] 배치 B: 마우스 버튼 UI 기반 (2026-08-10) — `ui.py` 신규(`screen_to_logical` 좌표변환 + `Button` 헬퍼), `Game.on_click`/`mouse_logical_pos` 추가, 레벨업 화면 카드에 호버+클릭 지원(키보드 1/2/3과 `confirm_levelup_choice()` 공유), `--selftest`의 `auto_play`도 실제 `on_click` 경로를 타도록 갱신. `--selftest` 통과.
- [x] 배치 B 후속 피드백 반영 (2026-08-10) — (1) `draw_center_text()`가 고정 시작 높이 대신 전체 블록 높이를 재서 화면 세로 중앙에 맞추도록 수정(타이틀/일시정지/승리/패배 화면 전부 적용, 줄 수 많은 화면이 아래로 넘쳐 위쪽에 쏠려 보이던 문제). (2) 난이도 화면을 `draw_center_text` 대신 전용 `draw_difficulty()`로 새로 그려서 4단계를 카드형 버튼으로 만들고 마우스 클릭 지원 추가(`confirm_difficulty_choice()`를 키보드 1~4와 공유). `--selftest` 통과. 사용자 확인 완료(2026-08-10) — "괜찮은거 같아"
- [x] 배치 C: 메인 메뉴 허브 (2026-08-10) — `"title"` 상태를 그대로 허브로 확장(별도 "menu" 상태 안 만듦), `draw_title()` 신규: 싱글/멀티/설정/리더보드 버튼 4개. 싱글만 활성(난이도 화면으로 이동), 나머지 셋은 화면 자체가 없어서(배치 K/I/F 대상) 회색 비활성 + 클릭 시 "준비 중" 배너만 표시. `TEXT["start"]`는 안 쓰게 돼서 삭제, `menu_*`/`coming_soon` 문구 추가. `--selftest` 통과. **사용자 확인 필요**: 메뉴 버튼 레이아웃 피드백 아직 없음
- [x] 일시정지 화면에 메인 메뉴 복귀 추가 (2026-08-10, 사용자 요청) — 처음엔 "ESC로 메인 메뉴"로 만들었다가 사용자가 반대로 정정: **ESC는 원래대로 재개(변경 없음)**, **H가 일시정지에서도 메인 메뉴(`"title"`)로 나가기**(기존엔 over/win 상태에서만 되던 H를 pause로 확장). `TEXT["resume"]`은 "ESC로 계속하기"로 원복, `pause_home`을 "H로 메인 메뉴"로 수정, 일시정지 화면에 두 줄 다 표시. `--selftest` 통과
- [ ] 배치 D: 재화 + 별도 업그레이드 트랙
- [ ] 배치 E: 보스 + 시간제한 (보스 자체·요격 예측·투기장 전환은 이미 있음 — 남은 건 별도 체력바 UI·제한시간 UI 다듬기 정도)
- [ ] 배치 F: 통계 + 리더보드 연동
- [ ] 배치 G: 크리티컬/비네트/피버타임 (Juice 포팅)
- [x] 배치 H: 배속 기능 (2026-08-10, 사용자 요청으로 D~G보다 먼저 진행) — `self.game_speed`(기본 1.0, `GAME_SPEEDS = (1.0, 1.5, 2.0)`) 추가, `run()`에서 `self.update(dt * self.game_speed, keys)`로 시뮬레이션 시간만 배속(렌더링/입력 반응성은 그대로).
  - 처음엔 일시정지 화면에 배속 버튼 3개를 넣었다가, 사용자가 "ESC 눌러서 하지 말고 인게임 화면 상단에 작게 배속 조절 칸을 투명하게, 화살표로"라고 정정 → **일시정지 화면은 원래대로(재개/메인메뉴 안내만) 되돌리고**, `draw_hud()`에서 플레이 중에만 미니맵 바로 밑에 반투명 위젯(`draw_speed_widget()`)을 그려서 `<`/`>` 화살표 클릭으로 `GAME_SPEEDS` 안에서 한 단계씩 오르내리게(`step_game_speed()`) 만듦. 경계에서는 화살표가 흐리게 비활성 표시.
  - `--selftest`도 플레이 중 주기적으로 위젯의 `>` 화살표를 클릭해보도록 `auto_play` 확장. `--selftest` 통과. **사용자 확인 필요**: 위젯 위치/화살표 클릭감 피드백 아직 없음
- [ ] 배치 I: 게임 중 설정창 + 도감 + 온보딩
- [ ] 배치 J (스트레치): 난이도 선택 완성 — 상당 부분 이미 완료, 남은 건 점수 배율 반영 정도
- [ ] 배치 K (스트레치): 로컬 2인 협동 멀티플레이
