@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem Abre Codex con la raiz de trabajo fijada a este proyecto.
for %%I in ("%~dp0.") do set "PROYECTO=%%~fI"

if not exist "%PROYECTO%\main.py" (
    echo ERROR: No se encontro main.py en "%PROYECTO%".
    pause
    exit /b 1
)

rem El auxiliar del sandbox viene dentro de codex-resources, no junto al
rem lanzador principal. Se agrega al PATH solo para este proceso/proyecto.
rem La busqueda cubre todos los perfiles locales porque Codex puede haber sido
rem instalado por un administrador distinto al usuario que abre este archivo.
set "CODEX_RECURSOS_SANDBOX="
set "CODEX_EJECUTABLE_PROYECTO="
for /d %%U in ("%SystemDrive%\Users\*") do (
    for /f "delims=" %%F in ('where /r "%%~fU\.codex\packages\standalone\releases" codex-windows-sandbox-setup.exe 2^>nul') do (
        set "CANDIDATO_RECURSOS=%%~dpF"
        set "CANDIDATO_CODEX=%%~dpF..\bin\codex.exe"
        for %%I in ("!CANDIDATO_CODEX!") do set "CANDIDATO_CODEX=%%~fI"
        if exist "!CANDIDATO_CODEX!" (
            set "CODEX_RECURSOS_SANDBOX=!CANDIDATO_RECURSOS!"
            set "CODEX_EJECUTABLE_PROYECTO=!CANDIDATO_CODEX!"
        )
    )
)

if not defined CODEX_RECURSOS_SANDBOX (
    echo ERROR: No se encontro codex-windows-sandbox-setup.exe.
    echo Ejecuta "codex doctor" o reinstala/actualiza Codex.
    pause
    exit /b 1
)

for %%I in ("%CODEX_EJECUTABLE_PROYECTO%") do set "CODEX_EJECUTABLE_PROYECTO=%%~fI"
if not exist "%CODEX_EJECUTABLE_PROYECTO%" (
    echo ERROR: No se encontro el ejecutable del paquete Codex.
    pause
    exit /b 1
)

set "PATH=%CODEX_RECURSOS_SANDBOX%;%PATH%"

cd /d "%PROYECTO%"
if errorlevel 1 (
    echo ERROR: No se pudo establecer la carpeta de trabajo.
    pause
    exit /b 1
)

if /I "%~1"=="--comprobar" (
    echo Carpeta de trabajo: %CD%
    echo Recursos sandbox: %CODEX_RECURSOS_SANDBOX%
    echo Ejecutable Codex: %CODEX_EJECUTABLE_PROYECTO%
    where codex-windows-sandbox-setup.exe
    "%CODEX_EJECUTABLE_PROYECTO%" --version
    exit /b %ERRORLEVEL%
)

rem Abre una sesion nueva de Codex CLI en este proyecto.
rem Usa --reanudar solo si ya existe una sesion CLI anterior que quieras continuar.
title Codex CLI - Casos Judiciales
if /I "%~1"=="--reanudar" (
    "%CODEX_EJECUTABLE_PROYECTO%" resume --last
) else (
    "%CODEX_EJECUTABLE_PROYECTO%"
)

set "CODIGO_SALIDA=%ERRORLEVEL%"
if not "%CODIGO_SALIDA%"=="0" (
    echo.
    echo ERROR: Codex CLI termino con el codigo %CODIGO_SALIDA%.
    echo La ventana permanecera abierta para que puedas leer el error.
    pause
)
exit /b %CODIGO_SALIDA%
