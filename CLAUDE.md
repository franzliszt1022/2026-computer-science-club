# Project: 동아리 부스 전시용 타워 디펜스 게임

## Overview
동아리 부스에서 전시할 웹 브라우저 타워 디펜스 게임. Phaser 3 기반, 빌드 도구 없이 순수 `<script>` 태그로 로드. 사용자는 코딩 초보이며 실제 코드는 대부분 Claude가 작성/검증하고, 사용자는 짧게 플레이해보고 피드백을 주는 방식으로 진행한다 (하루 가용 시간 약 30분).

원래 Godot 엔진으로 시작했으나, Claude가 Godot 창을 직접 볼 수 없어(버그를 사용자가 말로 설명해야 하는 병목) 웹으로 전환. 웹에서는 claude-in-chrome으로 Claude가 직접 브라우저를 열어 화면을 보고 클릭하고 콘솔 에러를 읽을 수 있음.

## Tech Stack
- Language: JavaScript (vanilla, 빌드 도구/번들러 없음)
- Framework: Phaser 3 (v3.87, `lib/phaser.min.js` 로컬 파일로 로드 — CDN 미사용, 부스 오프라인 환경 대비)
- Database: 없음 — `localStorage` 기반 로컬 리더보드만 사용
- 호스팅: GitHub Pages (`https://franzliszt1022.github.io/20260728project/`)

## Project Structure
```
index.html            # 스크립트 로드 순서가 곧 의존성 순서 (utils → entities → scenes → main.js)
lib/
└── phaser.min.js      # Phaser 로컬 파일
js/
├── main.js            # Phaser 게임 설정 (1920x1080, Scale.FIT + autoCenter)
├── scenes/
│   ├── BootScene.js      # 에셋 프리로드 (오디오)
│   ├── MenuScene.js      # 시작 화면, 난이도 선택, 전체화면 토글
│   ├── GameScene.js      # 메인 게임플레이 (가장 큰 파일)
│   └── GameOverScene.js  # 결과 화면 + 리더보드
├── entities/
│   ├── Tower.js / Enemy.js / Projectile.js
└── utils/
    ├── Theme.js         # 색상 팔레트, DIFFICULTY_PRESETS, drawBackground()
    ├── SFX.js           # 효과음 재생 (쿨다운/랜덤 디튠)
    ├── FX.js            # 파티클(수동 트윈 기반) / 화면 흔들림
    ├── DamageNumber.js  # 데미지 숫자 팝업
    └── Leaderboard.js   # localStorage 기반 로컬 Top 10
assets/
├── audio/             # Kenney.nl CC0 효과음(.ogg)
└── images/            # 아직 미사용 (도형/색상 플레이스홀더 단계)
```

## 이 프로젝트 고유 규칙
- 빌드 도구 없음 — 모든 JS가 classic `<script>` 태그로 로드되며 **전역 스코프를 공유**. 새 파일 추가 시 `index.html`에 의존성 순서대로 `<script>` 태그 추가 필수. 최상위 `const`/`class` 이름은 프로젝트 전체에서 유일해야 함(중복되면 SyntaxError로 페이지 전체가 크래시됨).
- Phaser 3.87에서 `add.particles(key).createEmitter()` API는 제거됨 — 파티클은 `FX.js`처럼 원 도형을 수동 트윈으로 움직여 구현.
- 주석은 최소화, 자명하지 않은 이유(WHY)가 있을 때만 작성.

## Commands
- 로컬 실행: 프로젝트 폴더에서 `python -m http.server 8000` 실행 후 브라우저에서 `localhost:8000` 접속 (`index.html`을 `file://`로 직접 열면 에셋 로딩이 브라우저 보안 정책에 막힘)
- 별도 빌드/테스트 명령 없음

## Important Notes
- **캐시 이슈**: 로컬/배포 수정 후 반드시 `Ctrl+Shift+R`(강력 새로고침)로 확인할 것 — 일반 새로고침은 예전에 캐시된 JS 파일을 계속 사용해서 변경사항이 반영 안 된 것처럼 보일 수 있음 (이 프로젝트에서 이미 여러 번 이 문제로 혼란을 겪음).
- **테스트 방법**: claude-in-chrome으로 브라우저를 직접 열어 콘솔 에러 확인 + 클릭 시뮬레이션으로 검증. 단, "재미/타격감/사운드 밸런스"처럼 주관적인 부분은 Claude가 판단할 수 없으므로 반드시 사용자가 실제로 플레이해보고 피드백을 줘야 함.
- **작업 리듬**: 사용자는 하루 약 30분만 가능. 코드는 Claude가 대화 세션 중 직접 작성/검증하고, 사용자는 짧게 플레이해보고 "이 부분 이렇게 바꿔줘" 식으로 피드백만 준다.
- **상세 로드맵/설계 문서**: `C:\Users\namhs\.claude\plans\proud-twirling-reddy.md` — 도파민 연출(Juice) 시스템 설계, 시스템 확장 설계(그리드 배치, 아이템 상점 등)의 세부 근거와 구현 배치가 정리되어 있음.

## 진행 상황 (2026-08-05 기준)
- [x] 기반 다지기: Phaser 세팅, 경로 위 적 이동, 클릭으로 타워 배치, 발사/데미지
- [x] 전투 시스템: 타워 3종(기본/스플래시/속사), 적 4종(기본/스웜/탱커/보스), 웨이브 스폰, 골드/목숨 UI, 승패 판정
- [x] 랭킹 시스템: localStorage 기반 로컬 Top 10, 이니셜 입력(최대 10자)
- [x] Juice Tier 1: 사운드, 파티클, 크리티컬, 화면 흔들림, 목숨 위험 비네트, 웨이브 클리어 배너, 온보딩 튜토리얼, 난이도 선택(쉬움/보통/어려움)
- [x] 시스템 확장 배치 A: 화면 꽉 채우기 + 캔버스 1920x1080(16:9) 재설계, 전체화면 버튼, 튜토리얼 가독성 개선, 배속 조절(0.5x/1x/2x)
- [x] 시스템 확장 배치 B: 수동 웨이브 시작("정비 시간"), 웨이브 10→20개 확장 + 재조정(웨이브 10 이후 적 개수 상한, 체력만 계속 증가), 난이도 상향
- [ ] 시스템 확장 배치 C: 그리드 기반 타워 배치 + 설치 미리보기 (다음 작업)
- [ ] 시스템 확장 배치 D~F: 타워 체력 스탯/정보창, 신규 몬스터·타워, 아이템 상점
- [ ] Juice Tier 2 (여유 있으면): 킬 콤보/피버타임, 웨이브 대기 진행바, 보물상자, 게임오버 화면 타워 통계 강조
- [ ] 테마 결정 + 에셋 교체 (도형 플레이스홀더 → 실제 스프라이트)
- [ ] 최종 페이싱 튜닝, 부스 환경(오프라인) 테스트
