@echo off
chcp 936 >nul
echo ==============================
echo    CDown 网易云音乐下载器
echo ==============================
echo.
echo 正在启动应用...
echo.
python main.py
if errorlevel 1 (
    echo.
    echo 启动失败！请确保已安装所有依赖：
    echo pip install -r requirements.txt
    echo.
    pause
)
