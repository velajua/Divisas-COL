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

if "%DIVISAS_UPLOAD_STORE_FILE%"=="" (
  echo Set DIVISAS_UPLOAD_STORE_FILE to the local Android upload keystore path.
  goto fail
)

if not exist "%DIVISAS_UPLOAD_STORE_FILE%" (
  echo Keystore not found: %DIVISAS_UPLOAD_STORE_FILE%
  goto fail
)

if "%DIVISAS_UPLOAD_STORE_PASSWORD%"=="" (
  echo Set DIVISAS_UPLOAD_STORE_PASSWORD before building a release AAB.
  goto fail
)

if "%DIVISAS_UPLOAD_KEY_ALIAS%"=="" (
  echo Set DIVISAS_UPLOAD_KEY_ALIAS before building a release AAB.
  goto fail
)

if "%DIVISAS_UPLOAD_KEY_PASSWORD%"=="" (
  echo Set DIVISAS_UPLOAD_KEY_PASSWORD before building a release AAB.
  goto fail
)

call npm ci || goto fail
call npm test || goto fail
call npm run typecheck || goto fail
call npm audit --omit=dev || goto fail
call npx expo-doctor || goto fail

call :backup_package_files || goto fail
set "EXPO_NO_GIT_STATUS=1"
call npx expo prebuild --platform android --clean
set "PREBUILD_EXIT=%ERRORLEVEL%"
call :restore_package_files || goto fail
if not "%PREBUILD_EXIT%"=="0" goto fail
call node scripts\configureAndroidReleaseSigning.js || goto fail

pushd android
call gradlew.bat bundleRelease || goto fail_nested
popd

set "AAB_PATH=%CD%\android\app\build\outputs\bundle\release\app-release.aab"
if not exist "%AAB_PATH%" (
  echo Android App Bundle was not created at %AAB_PATH%
  goto fail
)

echo Android App Bundle created:
echo %AAB_PATH%
popd
exit /b 0

:fail_nested
popd

:fail
popd
exit /b 1

:backup_package_files
set "PACKAGE_JSON_BACKUP=%TEMP%\divisas-col-package-%RANDOM%.json"
set "PACKAGE_LOCK_BACKUP=%TEMP%\divisas-col-package-lock-%RANDOM%.json"
copy /y package.json "%PACKAGE_JSON_BACKUP%" >nul || exit /b 1
if exist package-lock.json copy /y package-lock.json "%PACKAGE_LOCK_BACKUP%" >nul || exit /b 1
exit /b 0

:restore_package_files
if not "%PACKAGE_JSON_BACKUP%"=="" if exist "%PACKAGE_JSON_BACKUP%" copy /y "%PACKAGE_JSON_BACKUP%" package.json >nul || exit /b 1
if not "%PACKAGE_LOCK_BACKUP%"=="" if exist "%PACKAGE_LOCK_BACKUP%" copy /y "%PACKAGE_LOCK_BACKUP%" package-lock.json >nul || exit /b 1
exit /b 0
