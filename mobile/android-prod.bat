@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "SAFE_DIR=%REPO_ROOT:\=/%/.git"

git config --global --get-all safe.directory | findstr /x /c:"%SAFE_DIR%" >nul
if errorlevel 1 call git config --global --add safe.directory "%SAFE_DIR%" || goto fail

if exist ".env" (
  for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "ENV_KEY=%%A"
    if not "!ENV_KEY!"=="" if not "!ENV_KEY:~0,1!"=="#" if not defined !ENV_KEY! set "!ENV_KEY!=%%B"
  )
)

if "%ADMOB_ANDROID_APP_ID%"=="" (
  echo Set ADMOB_ANDROID_APP_ID to the Android AdMob app ID before production builds.
  echo Example format: ca-app-pub-0000000000000000~0000000000
  goto fail
)

call npm ci || goto fail
call npm test || goto fail
call npm run typecheck || goto fail
call npm audit --omit=dev || goto fail
call npx expo-doctor || goto fail
call npx eas build --platform android --profile production || goto fail

popd
exit /b 0

:fail
popd
exit /b 1
