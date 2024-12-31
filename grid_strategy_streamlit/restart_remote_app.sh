#!/bin/bash

# 服务器配置
SERVER_HOST="47.99.47.213"
SERVER_USER="root"
APP_DIR="/root/a-stock/a-stock-grid-streamlit"

# 显示使用方法
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -u, --update-only    只更新代码，不重启应用"
    echo "  -r, --restart        更新代码并重启应用（默认）"
    echo "  -h, --help           显示此帮助信息"
}

# 解析命令行参数
UPDATE_ONLY=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--update-only)
            UPDATE_ONLY=true
            shift
            ;;
        -r|--restart)
            UPDATE_ONLY=false
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            show_usage
            exit 1
            ;;
    esac
done

# 执行远程命令
if [ "$UPDATE_ONLY" = true ]; then
    echo "正在更新代码..."
    ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
    cd /root/a-stock/a-stock-grid-streamlit
    git pull
    echo "代码已更新。如果更新了关键文件，请使用 -r 选项重启应用。"
ENDSSH
else
    echo "正在更新代码并重启应用..."
    ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
    # 更新代码
    cd /root/a-stock/a-stock-grid-streamlit
    git pull

    # 停止现有的streamlit进程
    pkill -f streamlit

    # 等待进程完全停止
    sleep 2

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
fi 