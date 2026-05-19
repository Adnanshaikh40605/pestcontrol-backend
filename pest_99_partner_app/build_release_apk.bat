@echo off
set "JAVA_HOME=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot"
set "PATH=C:\Program Files\Microsoft\jdk-21.0.8.9-hotspot\bin;%PATH%"
cd /d "%~dp0"
echo Building release APK (production API: api.vacationbna.site)...
call C:\flutter\bin\flutter.bat pub get
call C:\flutter\bin\flutter.bat build apk --release --dart-define=API_BASE_URL=https://api.vacationbna.site
if %ERRORLEVEL% EQU 0 (
  echo.
  echo APK ready:
  echo   build\app\outputs\flutter-apk\app-release.apk
) else (
  echo Build failed with code %ERRORLEVEL%
)
pause
