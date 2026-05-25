@echo off
setlocal

cd /d "%~dp0"

set "VIRTUAL_ENV=%CD%\.venv"
set "PATH=%VIRTUAL_ENV%\Scripts;%PATH%"
set "PYTHONPATH="
set "PYTHONNOUSERSITE=1"

echo Using Python:
python -c "import sys; print(sys.executable)"

python generate_voiceover.py --txt input\entry.txt --voice voice_samples\voice.wav --out-dir output --format wav

endlocal