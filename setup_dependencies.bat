@echo off
setlocal EnableDelayedExpansion

REM ���� Python �汾
set "pythonVersion=3.11.9"
set "pythonVersionBrief=3.11"

REM ֻ���� pythonVersion �Ĵ����ֲ���
for /f "tokens=1-3 delims=." %%i in ("%pythonVersion%") do (
    set "pythonVersionNumericString=%%i%%j%%k"
)

set "installerUrl=https://mirrors.huaweicloud.com/python/%pythonVersion%/python-%pythonVersion%-amd64.exe"
set "installerFile=python-%pythonVersion%-amd64.exe"

REM ���尲װ·��
set "userInstallPath=%LOCALAPPDATA%\Programs\Python\Python%pythonVersionNumericString%"

REM ����Ƿ��Ѿ���װ�˴˰汾�� Python
set "pythonInstalled=false"

echo ���Python %pythonVersionBrief% ��װ���...

REM ����1�����ע���
echo 1. ��ע�����Python...
reg query "HKCU\SOFTWARE\Python\PythonCore\%pythonVersionBrief%" >nul 2>&1
if !errorlevel! equ 0 (
    echo ��ע������ҵ� Python %pythonVersionBrief%
    set "pythonInstalled=true"
)

REM ����2���ӿ�ʼ�˵����
if "%pythonInstalled%"=="false" (
    echo 2. �ӿ�ʼ�˵����Python...
    set "startMenuPath=%ProgramData%\Microsoft\Windows\Start Menu\Programs"
    set "userStartMenuPath=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
    
    REM ���ϵͳ����ʼ�˵�
    if exist "%startMenuPath%\Python %pythonVersionBrief%" (
        echo ��ϵͳ��ʼ�˵��ҵ� Python %pythonVersionBrief%
        set "pythonInstalled=true"
    ) else (
        for /d %%d in ("%startMenuPath%\Python*") do (
            echo %%~nxd | findstr /c:"Python %pythonVersionBrief%" >nul
            if !errorlevel! equ 0 (
                echo ��ϵͳ��ʼ�˵��ҵ� Python %pythonVersionBrief%
                set "pythonInstalled=true"
            )
        )
    )
    
    REM ����û�����ʼ�˵�
    if exist "%userStartMenuPath%\Python %pythonVersionBrief%" (
        echo ���û���ʼ�˵��ҵ� Python %pythonVersionBrief%
        set "pythonInstalled=true"
    ) else (
        for /d %%d in ("%userStartMenuPath%\Python*") do (
            echo %%~nxd | findstr /c:"Python %pythonVersionBrief%" >nul
            if !errorlevel! equ 0 (
                echo ���û���ʼ�˵��ҵ� Python %pythonVersionBrief%
                set "pythonInstalled=true"
            )
        )
    )
)

REM ����3��ֱ�Ӽ�鰲װ·��
if "%pythonInstalled%"=="false" (
    echo 3. ���Python��װ·��...
    if exist "%userInstallPath%\python.exe" (
        echo �� %userInstallPath% �ҵ�Python��ִ���ļ�
        set "pythonInstalled=true"
    )
    
    set "altPath=%LOCALAPPDATA%\Programs\Python\Python%pythonVersionBrief%"
    if exist "!altPath!\python.exe" (
        echo �� !altPath! �ҵ�Python��ִ���ļ�
        set "pythonInstalled=true"
    )
)

REM ����4������ִ��Python�����汾
if "%pythonInstalled%"=="false" (
    echo 4. ����ִ��Python���汾...
    where python >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%v in ('python -V 2^>^&1') do (
            echo %%v | findstr /b "%pythonVersionBrief%" >nul
            if !errorlevel! equ 0 (
                echo �ҵ�ƥ��汾��Python: %%v
                set "pythonInstalled=true"
            )
        )
    )
)

if "%pythonInstalled%"=="true" (
    echo Python %pythonVersion% �Ѱ�װ�ڼ�����ϡ�
) else (
    echo Python %pythonVersion% δ�ڼ�����ϰ�װ��׼���Զ���װPython %pythonVersion%
    echo ���ڼ����У������ĵȴ�������رմ˴��ڣ�

    REM ���� Python ��װ����
    echo �������� Python ��װ����...
    powershell -Command "Invoke-WebRequest -Uri %installerUrl% -OutFile %installerFile%"

    REM ��װ Python
    echo ���ڰ�װ Python����ע�ⵯ����Ȩ�����봰�ڣ�������ִ��...
    start /wait "" "%installerFile%" /quiet InstallAllUsers=0 PrependPath=1 DefaultJustForMeTargetDir="%userInstallPath%"

    REM �� Python ��ӵ�ϵͳ����������
    setx PATH "%PATH%;%userInstallPath%"

    REM �� Python ��ӵ�ע���
    set "pythonPath=%userInstallPath%\python.exe"
    reg add "HKCU\Software\Python\PythonCore\%pythonVersionBrief%" /ve /d "%pythonVersion%" /f
    reg add "HKCU\Software\Python\PythonCore\%pythonVersionBrief%" /v "InstallPath" /d "%userInstallPath%" /f
    reg add "HKCU\Software\Python\PythonCore\%pythonVersionBrief%" /v "ExecutablePath" /d "%pythonPath%" /f

    REM ɾ����װ����
    echo Python ��װ��ɣ�ɾ����װ����...
    del "%installerFile%"

    echo Python %pythonVersion% �Ѱ�װ�ɹ�
)

REM ȷ�� userInstallPath ��������ȷ����
if not exist "%userInstallPath%\python.exe" (
    for /f "tokens=*" %%p in ('where python 2^>nul') do (
        set "userInstallPath=%%~dpp"
        set "userInstallPath=!userInstallPath:~0,-1!"
    )
)

REM �������⻷��
echo ����Python���⻷��...
python%pythonVersionBrief% -m venv venv 2>nul
if %errorlevel% neq 0 (
    echo ʹ��python%pythonVersionBrief%����ʧ�ܣ�����ʹ������·��...
    if exist "%userInstallPath%\python.exe" (
        echo ʹ�ð�װ·��: %userInstallPath%\python.exe
        "%userInstallPath%\python.exe" -m venv venv
    ) else (
        echo ���Բ���Python��ִ���ļ�...
        where python 2>nul
        if %errorlevel% equ 0 (
            echo ʹ��ϵͳPython�������⻷��
            python -m venv venv
        ) else (
            echo δ���ҵ����õ�Python�����⻷������ʧ�ܣ�
            exit /b 1
        )
    )
) else (
    echo �ɹ�ʹ��python%pythonVersionBrief%�������⻷��
)


REM �������⻷��
call venv\Scripts\activate.bat

@REM call run.bat

REM ���н����������˳�
pause