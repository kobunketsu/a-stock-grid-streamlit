#!/bin/bash

# 更新系统
apt update
apt upgrade -y

# 安装必要的软件包
apt install -y python3-pip nginx certbot python3-certbot-nginx git

# 克隆项目
git clone https://github.com/kobunketsu/grid_strategy_streamlit.git
cd grid_strategy_streamlit

# 安装Python依赖
pip3 install -r requirements.txt
pip3 install streamlit

# 配置Nginx
cat > /etc/nginx/sites-available/dreapp.com << 'EOL'
server {
    listen 80;
    server_name dreapp.com www.dreapp.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
EOL

# 启用站点配置
ln -s /etc/nginx/sites-available/dreapp.com /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 测试Nginx配置
nginx -t

# 重启Nginx
systemctl restart nginx

# 配置SSL证书
certbot --nginx -d dreapp.com -d www.dreapp.com --non-interactive --agree-tos --email your-email@example.com

# 创建systemd服务
cat > /etc/systemd/system/streamlit.service << 'EOL'
[Unit]
Description=Streamlit Web App
After=network.target

[Service]
User=root
WorkingDirectory=/root/grid_strategy_streamlit
ExecStart=/usr/local/bin/streamlit run src/views/app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOL

# 启用并启动服务
systemctl daemon-reload
systemctl enable streamlit
systemctl start streamlit 