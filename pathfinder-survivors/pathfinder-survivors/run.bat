@echo off
setlocal
title Pathfinder Survivors

REM 배치파일이 있는 폴더로 이동 (바탕화면 바로가기로 실행해도 경로가 맞게)
cd /d "%~dp0"

REM ---------------------------------------------------------- 1. 파이썬 찾기
set "PY="
py -3 --version >nul 2>nul && set "PY=py -3"
if not defined PY (
    python --version >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo.
    echo  [오류] 파이썬을 찾을 수 없습니다.
    echo.
    echo  https://www.python.org/downloads/ 에서 설치한 뒤
    echo  설치 화면 맨 아래 "Add python.exe to PATH" 를 반드시 체크하세요.
    echo.
    pause
    exit /b 1
)

REM ---------------------------------------------------------- 2. 게임 파일 확인
if not exist "game.py" (
    echo.
    echo  [오류] game.py 를 찾을 수 없습니다.
    echo  이 배치파일은 game.py 와 같은 폴더에 있어야 합니다.
    echo.
    echo  현재 위치: %CD%
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------- 3. 라이브러리 설치 확인
%PY% -c "import pygame, PIL, numpy" >nul 2>nul
if errorlevel 1 (
    echo.
    echo  처음 실행이라 필요한 라이브러리를 설치합니다. 잠시만 기다려 주세요...
    echo.
    %PY% -m pip install pygame pillow numpy
    if errorlevel 1 (
        echo.
        echo  [오류] 설치에 실패했습니다. 인터넷 연결을 확인하세요.
        echo  회사/학교 네트워크라면 방화벽이 막고 있을 수 있습니다.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  설치 완료. 게임을 시작합니다.
    echo.
)

REM ---------------------------------------------------------- 4. 실행
%PY% game.py

REM 오류로 종료됐을 때만 창을 붙잡아 메시지를 보여준다
if errorlevel 1 (
    echo.
    echo  ============================================
    echo   게임이 오류로 종료되었습니다.
    echo   위에 표시된 메시지를 확인하세요.
    echo  ============================================
    echo.
    pause
)

endlocal
