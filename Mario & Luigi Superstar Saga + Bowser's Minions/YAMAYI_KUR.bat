@echo off
chcp 65001 >nul
setlocal EnableExtensions
set "BASE=%~dp0"
set "PATCH=%BASE%Yama\romfs"
set "TITLEID=00040000001B9000"

echo.
echo MLSS Türkçe Yama Kurulumu
echo =========================
echo 1 - Luma3DS SD kartına kur
echo 2 - Citra / Lime3DS / Azahar kullanıcı klasörüne kur
echo 3 - Çıkarılmış RomFS klasörüne kur
echo 0 - Çıkış
echo.
set /p "CHOICE=Seçim: "
if "%CHOICE%"=="0" exit /b 0
if "%CHOICE%"=="1" goto LUMA
if "%CHOICE%"=="2" goto CITRA
if "%CHOICE%"=="3" goto ROMFS
echo Geçersiz seçim.
pause
exit /b 1

:LUMA
set /p "TARGET=SD kart kök klasörü: "
if not exist "%TARGET%" goto BADPATH
set "DEST=%TARGET%\luma\titles\%TITLEID%\romfs"
goto COPY

:CITRA
set /p "TARGET=Emülatör kullanıcı klasörü: "
if not exist "%TARGET%" goto BADPATH
set "DEST=%TARGET%\load\mods\%TITLEID%\romfs"
goto COPY

:ROMFS
set /p "TARGET=RomFS kök klasörü: "
if not exist "%TARGET%" goto BADPATH
set "DEST=%TARGET%"
goto COPY

:COPY
if not exist "%PATCH%\Msg\EU_en\Area.msbt" (
  echo Mesaj yama dosyaları bulunamadı.
  pause
  exit /b 2
)
if not exist "%PATCH%\Obj\EU\BUI.dat" (
  echo Grafik UI yama dosyaları bulunamadı.
  pause
  exit /b 2
)
mkdir "%DEST%" 2>nul
robocopy "%PATCH%" "%DEST%" /E /R:1 /W:1 >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo Kurulum sırasında kopyalama hatası oluştu. Hata kodu: %RC%
  pause
  exit /b %RC%
)
echo.
echo Kurulum tamamlandı.
echo Hedef: %DEST%
echo Mesaj/font: %DEST%\Msg\EU_en
echo Grafik UI: %DEST%\Obj\EU
pause
exit /b 0

:BADPATH
echo Belirtilen klasör bulunamadı.
pause
exit /b 3
