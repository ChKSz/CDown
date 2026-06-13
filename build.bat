@echo off
chcp 936 >nul
echo ==============================
echo    CDown 打包工具
echo ==============================
echo.
echo 正在检查依赖...
python -c "import PyQt6; import requests; import mutagen; import PyInstaller" 2>nul
if errorlevel 1 (
    echo 缺少依赖，正在安装...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 依赖安装失败！
        pause
        exit /b 1
    )
)
echo.
echo 开始打包应用...
echo.
pyinstaller CDown.spec
if errorlevel 1 (
    echo.
    echo 打包失败！
    pause
    exit /b 1
)
echo.
echo ==============================
echo 打包完成！
echo 可执行文件位置: dist\CDown.exe
echo ==============================
echo.
pause
