@echo off
chcp 65001 >nul
echo ========================================
echo   TaskMaster - 本地脚本统一管理平台
echo ========================================
echo.

cd /d "%~dp0"

:: 检查虚拟环境
if not exist "purlo_python\Scripts\python.exe" (
    echo [1/3] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 创建虚拟环境失败，请确认已安装 Python 3.9+
        pause
        exit /b 1
    )

    echo [2/3] 正在安装依赖...
    purlo_python\Scripts\pip.exe install -r requirements.txt -q
    if errorlevel 1 (
        echo 依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo [1/2] 虚拟环境已就绪
    echo [2/2] 检查依赖更新...
    purlo_python\Scripts\pip.exe install -r requirements.txt -q
)

echo.
echo [3/3] 启动后端服务...
echo.
echo   地址: http://127.0.0.1:8765
echo   账号: admin / admin
echo   按 Ctrl+C 停止服务
echo.

purlo_python\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
pause