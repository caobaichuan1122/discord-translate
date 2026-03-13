#!/bin/bash
# Discord Translate Bot - Ubuntu Deploy Script
# Usage: bash deploy.sh

set -e

echo "=== Installing system dependencies ==="
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git

echo "=== Creating virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python dependencies ==="
pip install --upgrade pip

# CPU-only PyTorch (no GPU on most servers, saves disk space)
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt

echo "=== Checking .env file ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo ">>> Please edit .env and set your DISCORD_TOKEN <<<"
    echo "    nano .env"
    echo ""
fi

echo "=== Creating systemd service ==="
# Get current directory and user
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
echo "=== Deploy complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit config:    nano .env"
echo "  2. Start service:  sudo systemctl start discord-translate"
echo "  3. View logs:      sudo journalctl -u discord-translate -f"
echo "  4. Stop service:   sudo systemctl stop discord-translate"
echo "  5. Restart:        sudo systemctl restart discord-translate"
