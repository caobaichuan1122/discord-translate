#!/bin/bash
# Discord 翻译机器人 - Ubuntu 部署脚本
# 用法: bash deploy.sh

set -e

echo "=== 安装系统依赖 ==="
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

echo "=== 创建虚拟环境 ==="
python3 -m venv venv
source venv/bin/activate

echo "=== 安装 Python 依赖 ==="
pip install --upgrade pip

# CPU-only PyTorch（服务器一般没 GPU，节省空间）
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt

echo "=== 检查 .env 文件 ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> 请编辑 .env 文件填入你的 DISCORD_TOKEN <<<"
    echo "    nano .env"
    echo ""
fi

echo "=== 创建 systemd 服务 ==="
# 获取当前目录和用户
BOT_DIR=$(pwd)
BOT_USER=$(whoami)

sudo tee /etc/systemd/system/discord-translate.service > /dev/null <<EOF
[Unit]
Description=Discord Translate Bot
After=network.target

[Service]
Type=simple
User=$BOT_USER
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable discord-translate

echo ""
echo "=== 部署完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑配置: nano .env"
echo "  2. 启动服务: sudo systemctl start discord-translate"
echo "  3. 查看日志: sudo journalctl -u discord-translate -f"
echo "  4. 停止服务: sudo systemctl stop discord-translate"
echo "  5. 重启服务: sudo systemctl restart discord-translate"
