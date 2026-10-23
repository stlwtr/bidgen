@echo off
REM 投标文件生成助手 - Windows 一键打包脚本（生成 dist\BidgenGUI.exe）
cd /d "%~dp0\.."

if not exist .venv (
    echo 创建虚拟环境 .venv ...
    python -m venv .venv
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
