@echo off
setlocal

REM Fixes the orphan DENY ACE that can block git writes under .git
REM Safe to re-run; no repo content changes.

set "REPO=%~dp0"
set "GITDIR=%REPO%.git"

if not exist "%GITDIR%" (
  echo ERROR: "%GITDIR%" not found.
  exit /b 1
)

echo [acl] Taking ownership of "%GITDIR%" (best-effort)...
takeown /F "%GITDIR%" /R /D S >nul 2>&1

echo [acl] Resetting ACLs under "%GITDIR%"...
icacls "%GITDIR%" /reset /T /C >nul

echo [acl] Verifying...
icacls "%GITDIR%" | findstr /i "(DENY)" >nul && (
  echo WARNING: DENY ACE still present on .git. Git may still fail.
  icacls "%GITDIR%"
  exit /b 2
)
icacls "%GITDIR%\\index" 2>nul | findstr /i "(DENY)" >nul && (
  echo WARNING: DENY ACE still present on .git\index. Git may still fail.
  icacls "%GITDIR%\\index"
  exit /b 2
)

echo OK: .git ACLs reset; no DENY detected.
exit /b 0

