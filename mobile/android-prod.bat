@echo off
setlocal
pushd "%~dp0"

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "SAFE_DIR=%REPO_ROOT:\=/%/.git"

git config --global --get-all safe.directory | findstr /x /c:"%SAFE_DIR%" >nul
if errorlevel 1 call git config --global --add safe.directory "%SAFE_DIR%" || goto fail

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
