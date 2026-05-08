@echo off
setlocal EnableExtensions

REM Run this ONCE from an elevated (Administrator) cmd.exe.
REM Installs an on-demand Scheduled Task that runs the ACL fix as SYSTEM (highest).

set "REPO=%~dp0"
set "TASK=\DivisasCOL\FixGitAcl"
set "CMD_FILE=%REPO%acl_fix_git.cmd"

if not exist "%CMD_FILE%" (
  echo ERROR: "%CMD_FILE%" not found.
  exit /b 1
)

REM If task exists, exit cleanly.
schtasks /query /tn "%TASK%" >nul 2>&1 && (
  echo Task already exists: %TASK%
  echo Run with: schtasks /run /tn "%TASK%"
  exit /b 0
)

set "XML=%TEMP%\divisas_fix_git_acl_task.xml"

REM Create XML definition (Task Scheduler 2.0 schema)
> "%XML%" echo ^<?xml version="1.0" encoding="UTF-16"?^>
>>"%XML%" echo ^<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task"^>
>>"%XML%" echo   ^<RegistrationInfo^>^<Author^>Divisas-COL^</Author^>^</RegistrationInfo^>
>>"%XML%" echo   ^<Triggers /^>
>>"%XML%" echo   ^<Principals^>
>>"%XML%" echo     ^<Principal id="Author"^>
>>"%XML%" echo       ^<UserId^>S-1-5-18^</UserId^>
>>"%XML%" echo       ^<RunLevel^>HighestAvailable^</RunLevel^>
>>"%XML%" echo     ^</Principal^>
>>"%XML%" echo   ^</Principals^>
>>"%XML%" echo   ^<Settings^>
>>"%XML%" echo     ^<MultipleInstancesPolicy^>IgnoreNew^</MultipleInstancesPolicy^>
>>"%XML%" echo     ^<DisallowStartIfOnBatteries^>false^</DisallowStartIfOnBatteries^>
>>"%XML%" echo     ^<StopIfGoingOnBatteries^>false^</StopIfGoingOnBatteries^>
>>"%XML%" echo     ^<AllowHardTerminate^>true^</AllowHardTerminate^>
>>"%XML%" echo     ^<StartWhenAvailable^>true^</StartWhenAvailable^>
>>"%XML%" echo     ^<RunOnlyIfNetworkAvailable^>false^</RunOnlyIfNetworkAvailable^>
>>"%XML%" echo     ^<Enabled^>true^</Enabled^>
>>"%XML%" echo     ^<Hidden^>false^</Hidden^>
>>"%XML%" echo     ^<WakeToRun^>false^</WakeToRun^>
>>"%XML%" echo     ^<ExecutionTimeLimit^>PT10M^</ExecutionTimeLimit^>
>>"%XML%" echo     ^<Priority^>7^</Priority^>
>>"%XML%" echo   ^</Settings^>
>>"%XML%" echo   ^<Actions Context="Author"^>
>>"%XML%" echo     ^<Exec^>
>>"%XML%" echo       ^<Command^>%SystemRoot%\System32\cmd.exe^</Command^>
>>"%XML%" echo       ^<Arguments^>/c ""%CMD_FILE%""^</Arguments^>
>>"%XML%" echo     ^</Exec^>
>>"%XML%" echo   ^</Actions^>
>>"%XML%" echo ^</Task^>

echo Creating scheduled task: %TASK%
schtasks /create /tn "%TASK%" /xml "%XML%" /f >nul 2>&1
set "RC=%ERRORLEVEL%"

del /q "%XML%" >nul 2>&1

if not "%RC%"=="0" (
  echo ERROR: Failed to create task (exit %RC%).
  exit /b %RC%
)

echo OK: Installed. Run with: schtasks /run /tn "%TASK%"
exit /b 0
