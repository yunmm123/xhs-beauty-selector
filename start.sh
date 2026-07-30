#!/bin/bash
cd "$(dirname "$0")"

# 检查并安装依赖
pip3 install -r requirements.txt --break-system-packages -q 2>/dev/null

# 启动服务
python3 app.py
