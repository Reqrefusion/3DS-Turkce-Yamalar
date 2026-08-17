@echo off
setlocal
if "%~1"=="" (
  echo Kullanim: TUNE_DOTLESS_I.bat 1 ^| 2 ^| 3
  echo Orijinal decrypted/uncompressed code.bin dosyasini input\code.bin konumuna koyun.
  exit /b 1
)
if not exist input\code.bin (
  echo input\code.bin bulunamadi.
  exit /b 1
)
python tools\patch_codebin_v26.py input\code.bin code.bin --shift %1
if errorlevel 1 exit /b 1
echo Hazir: code.bin ^(i-dotsuz sola %1 px^)
