@echo off
setlocal
title Pathfinder Survivors - 진단
cd /d "%~dp0"
set "LOG=%~dp0diagnose_log.txt"

echo 진단을 시작합니다. 잠시만 기다려 주세요...
echo.

> "%LOG%" echo ===== Pathfinder Survivors 진단 로그 =====
>>"%LOG%" echo 시각: %DATE% %TIME%
>>"%LOG%" echo 폴더: %CD%
>>"%LOG%" echo.

>>"%LOG%" echo --- [1] 폴더 안 파일 목록 ---
>>"%LOG%" dir /b
>>"%LOG%" echo.

>>"%LOG%" echo --- [2] assets 폴더 ---
if exist "assets" (
    >>"%LOG%" dir /b assets
) else (
    >>"%LOG%" echo assets 폴더 없음
)
>>"%LOG%" echo.

>>"%LOG%" echo --- [3] 파이썬 확인 ---
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    >>"%LOG%" echo 파이썬을 찾을 수 없음 ^(py, python 둘 다 실패^)
    >>"%LOG%" echo.
    >>"%LOG%" echo --- where py / where python ---
    >>"%LOG%" 2>&1 where py
    >>"%LOG%" 2>&1 where python
    goto :done
)
>>"%LOG%" echo 사용할 명령: %PY%
>>"%LOG%" 2>&1 %PY% --version
>>"%LOG%" 2>&1 %PY% -c "import sys; print(sys.executable); print(sys.version)"
>>"%LOG%" echo.

>>"%LOG%" echo --- [4] 라이브러리 확인 ---
>>"%LOG%" 2>&1 %PY% -c "import pygame; print('pygame', pygame.version.ver)"
>>"%LOG%" 2>&1 %PY% -c "import PIL; print('pillow', PIL.__version__)"
>>"%LOG%" 2>&1 %PY% -c "import numpy; print('numpy', numpy.__version__)"
>>"%LOG%" echo.

>>"%LOG%" echo --- [5] 이미지 생성 테스트 ---
>>"%LOG%" 2>&1 %PY% gen_assets.py
>>"%LOG%" echo.

>>"%LOG%" echo --- [6] 게임 자체 테스트 ^(창 없이 실행^) ---
>>"%LOG%" 2>&1 %PY% game.py --selftest
>>"%LOG%" echo.

>>"%LOG%" echo --- [7] 실제 실행 ---
echo 게임 창이 뜨는지 확인하세요. 뜨면 그냥 닫으면 됩니다.
>>"%LOG%" 2>&1 %PY% game.py
>>"%LOG%" echo 종료 코드: %ERRORLEVEL%

:done
>>"%LOG%" echo.
>>"%LOG%" echo ===== 진단 끝 =====

echo.
echo  진단이 끝났습니다. diagnose_log.txt 파일이 만들어졌습니다.
echo  메모장으로 열어서 내용을 전부 복사해 주세요.
echo.
start notepad "%LOG%"
pause
endlocal
