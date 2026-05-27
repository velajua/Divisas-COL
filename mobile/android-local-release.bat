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
call npm audit --omit=dev --audit-level=high || goto fail
call npx expo-doctor || echo expo-doctor reported issues; continuing after tests, typecheck, and high severity audit gate passed.

call node scripts\prepareAndroidReleaseBuild.js || goto fail
call local-signing\release-signing.cmd || goto fail

call :backup_package_files || goto fail
set "EXPO_NO_GIT_STATUS=1"
call npx expo prebuild --platform android --clean
set "PREBUILD_EXIT=%ERRORLEVEL%"
call :restore_package_files || goto fail
if not "%PREBUILD_EXIT%"=="0" goto fail

call node scripts\prepareAndroidReleaseBuild.js || goto fail
call node scripts\configureAndroidReleaseSigning.js || goto fail
call local-signing\release-signing.cmd || goto fail

pushd android
call gradlew.bat assembleRelease bundleRelease || goto fail_nested
popd

set "RELEASE_APK=%CD%\android\app\build\outputs\apk\release\app-release.apk"
set "RELEASE_AAB=%CD%\android\app\build\outputs\bundle\release\app-release.aab"
set "DIST_DIR=%CD%\dist"
set "DIST_APK=%DIST_DIR%\divisas-col-release.apk"
set "DIST_AAB=%DIST_DIR%\divisas-col-release.aab"

if not exist "%RELEASE_APK%" (
  echo Android release APK was not created at %RELEASE_APK%
  goto fail
)

if not exist "%RELEASE_AAB%" (
  echo Android release AAB was not created at %RELEASE_AAB%
  goto fail
)

if not exist "%DIST_DIR%" mkdir "%DIST_DIR%" || goto fail
copy /y "%RELEASE_APK%" "%DIST_APK%" >nul || goto fail
copy /y "%RELEASE_AAB%" "%DIST_AAB%" >nul || goto fail

echo Android release APK created:
echo %DIST_APK%
echo Android release AAB created:
echo %DIST_AAB%
echo Keep local-signing\release-signing.env and local-signing\divisas-upload-key.jks backed up. They are required for future Play Store updates.
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
