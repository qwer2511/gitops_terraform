@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py"

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo.
  echo [ServerOps] Python을 찾을 수 없습니다.
  echo Python 3.8 이상을 설치한 뒤 다시 실행하세요.
  echo 설치할 때 "Add Python to PATH" 옵션을 선택하는 것을 권장합니다.
  echo.
  pause
  exit /b 1
)

echo [ServerOps] GUI를 시작합니다...
%PYTHON_CMD% serverops_gui.py

if errorlevel 1 (
  echo.
  echo [ServerOps] 실행 중 오류가 발생했습니다.
  echo 위 오류 메시지를 캡처해서 확인하세요.
  echo.
  pause
)

endlocal
