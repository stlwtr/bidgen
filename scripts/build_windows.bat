@echo off
REM 本文件为 UTF-8 编码：先切换控制台到 UTF-8 代码页，否则中文 echo/注释在默认 GBK 下乱码
chcp 65001 >nul
REM 投标助手 - Windows 一键打包脚本（生成 dist\BidgenGUI.exe）
cd /d "%~dp0\.."

if not exist .venv (
    echo 创建虚拟环境 .venv ...
    REM 官方安装器默认不把 python 加入 PATH，优先用 py 启动器
    where py >nul 2>nul && (py -m venv .venv) || (python -m venv .venv)
)
if not exist .venv\Scripts\activate.bat (
    echo 错误：未找到可用的 Python。请先安装 Python 3.9+（安装时勾选 Add python to PATH，或保留 py 启动器）。
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

echo 安装依赖...
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

echo 开始打包...
pyinstaller --onefile --windowed --name BidgenGUI ^
    --icon assets\logo.ico ^
    --add-data "assets;assets" ^
    --collect-all fitz --collect-all pdf2docx --collect-all cv2 ^
    --collect-all docx --collect-all yaml --collect-all bidgen ^
    --hidden-import PySide6 app_gui.py

echo.
echo 打包完成: dist\BidgenGUI.exe
pause
