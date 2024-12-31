#!/bin/bash

# 服务器配置
SERVER_HOST="47.99.47.213"
SERVER_USER="root"
APP_DIR="/root/a-stock/a-stock-grid-streamlit"

# 执行远程命令
ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
# 停止现有的streamlit进程
pkill -f streamlit

# 等待进程完全停止
sleep 2

# 切换到项目目录
cd /root/a-stock/a-stock-grid-streamlit

# 激活虚拟环境
source venv/bin/activate

# 切换到应用目录
cd grid_strategy_streamlit

# 启动应用
nohup streamlit run src/views/app.py --server.address 0.0.0.0 --server.port 8501 > streamlit.log 2>&1 &

# 等待应用启动
sleep 3

# 检查进程状态
ps aux | grep streamlit | grep -v grep

echo "Streamlit application restarted. Check streamlit.log for details."
ENDSSH

echo "Remote restart command sent. Application should be available at http://${SERVER_HOST}:8501" 