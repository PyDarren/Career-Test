# 画己职测 — 部署说明

> 品牌：画己职测
> 项目：career_test
> 架构：Nginx → Gunicorn → Django → MySQL + Redis + Celery

---

## 1. 服务器环境要求

| 组件 | 最低版本 | 说明 |
|------|----------|------|
| Python | 3.11+ | 推荐 3.11 或 3.12 |
| MySQL | 8.0+ | 字符集 utf8mb4 |
| Redis | 7.0+ | 缓存 & Celery Broker |
| Nginx | 1.18+ | 反向代理 & SSL |
| Supervisor | 4.0+ | 进程管理 |
| Node.js | 无需 | 纯后端项目 |

### 操作系统

- Ubuntu 22.04 LTS / Debian 12+（推荐）
- CentOS 8+（需额外配置）

---

## 2. 目录结构

```
/var/www/career_test/              # 项目根目录
├── career_test/                    # Django 项目配置
│   ├── settings/
│   │   ├── base.py                 # 基础配置
│   │   ├── dev.py                  # 开发环境
│   │   └── prod.py                 # 生产环境
│   ├── celery.py                   # Celery 应用
│   ├── wsgi.py                     # WSGI 入口
│   └── asgi.py                     # ASGI 入口
├── common/                         # 公共模块
├── assessment/                     # 测评应用
├── personality/                    # 人格应用
├── careers/                        # 职业应用
├── payment/                        # 支付应用
├── stats/                          # 统计应用
├── deploy/                         # 部署配置
│   ├── nginx/
│   │   └── career_test.conf        # Nginx 配置
│   ├── gunicorn.conf.py            # Gunicorn 配置
│   ├── supervisor.conf             # Supervisor 配置
│   ├── deploy.sh                   # 部署脚本
│   └── README.md                   # 本文档
├── static/                         # 静态文件源
├── staticfiles/                    # collectstatic 输出
├── media/                          # 用户上传文件
├── logs/                           # 日志目录
├── venv/                           # Python 虚拟环境
├── .env                            # 环境变量（不提交）
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python 依赖
└── manage.py                       # Django 管理入口
```

---

## 3. 部署步骤

### 3.1 系统依赖安装

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-dev \
    build-essential libmysqlclient-dev \
    nginx supervisor redis-server mysql-server
```

### 3.2 创建部署用户和目录

```bash
sudo mkdir -p /var/www/career_test
sudo chown -R $USER:$USER /var/www/career_test
```

### 3.3 克隆代码

```bash
cd /var/www
git clone <仓库地址> career_test
cd career_test
```

### 3.4 创建虚拟环境

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3.5 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写真实值（数据库密码、密钥、Sentry DSN 等）
vim .env
```

### 3.6 创建日志目录

```bash
mkdir -p logs
mkdir -p /var/log/career_test
```

### 3.7 初始化数据库

```bash
# 在 MySQL 中创建数据库和用户
mysql -u root -p
```

```sql
CREATE DATABASE caretest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'caretest'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON caretest.* TO 'caretest'@'localhost';
FLUSH PRIVILEGES;
```

### 3.8 执行迁移和收集静态文件

```bash
python manage.py migrate --settings=career_test.settings.prod
python manage.py collectstatic --noinput --settings=career_test.settings.prod
```

### 3.9 配置 Nginx

```bash
sudo cp deploy/nginx/career_test.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/career_test.conf /etc/nginx/sites-enabled/
# 编辑配置，替换 SSL 证书路径
sudo vim /etc/nginx/sites-available/career_test.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 3.10 配置 Supervisor

```bash
sudo cp deploy/supervisor.conf /etc/supervisor/conf.d/career_test.conf
sudo supervisorctl reread
sudo supervisorctl update
```

### 3.11 启动服务

```bash
sudo supervisorctl start career_test:*
```

---

## 4. 一键部署

完成首次部署后，后续更新可使用部署脚本：

```bash
cd /var/www/career_test
./deploy/deploy.sh
```

部署脚本会自动执行：
1. 拉取最新代码
2. 安装依赖
3. 数据库迁移
4. 收集静态文件
5. 重启 Gunicorn 和 Celery
6. 健康检查

---

## 5. 服务管理

### Nginx

```bash
sudo systemctl start nginx       # 启动
sudo systemctl stop nginx        # 停止
sudo systemctl restart nginx     # 重启
sudo systemctl reload nginx      # 重载配置
sudo nginx -t                    # 检查配置
```

### Gunicorn（通过 Supervisor）

```bash
sudo supervisorctl status career_test_gunicorn          # 查看状态
sudo supervisorctl start career_test_gunicorn           # 启动
sudo supervisorctl stop career_test_gunicorn            # 停止
sudo supervisorctl restart career_test_gunicorn         # 重启
```

### Celery（通过 Supervisor）

```bash
# Celery Worker
sudo supervisorctl status career_test_celery_worker
sudo supervisorctl restart career_test_celery_worker

# Celery Beat
sudo supervisorctl status career_test_celery_beat
sudo supervisorctl restart career_test_celery_beat
```

### 全部服务

```bash
sudo supervisorctl status career_test:*                  # 查看全部状态
sudo supervisorctl restart career_test:*                 # 重启全部
```

---

## 6. 日志查看

### 应用日志

```bash
# DEBUG 日志
tail -f /var/www/career_test/logs/debug.log

# INFO 日志
tail -f /var/www/career_test/logs/info.log

# ERROR 日志
tail -f /var/www/career_test/logs/error.log
```

### Supervisor 进程日志

```bash
# Gunicorn
tail -f /var/log/career_test/gunicorn_out.log
tail -f /var/log/career_test/gunicorn_err.log

# Celery Worker
tail -f /var/log/career_test/celery_worker_out.log
tail -f /var/log/career_test/celery_worker_err.log

# Celery Beat
tail -f /var/log/career_test/celery_beat_out.log
tail -f /var/log/career_test/celery_beat_err.log
```

### Nginx 日志

```bash
tail -f /var/log/nginx/career_test_access.log
tail -f /var/log/nginx/career_test_error.log
```

### Sentry

- 在 Sentry 控制台查看错误追踪和性能监控
- 生产环境异常会自动上报到 Sentry（需配置 SENTRY_DSN）

---

## 7. 回滚流程

### 7.1 通过 Git 回滚

```bash
cd /var/www/career_test

# 查看最近提交
git log --oneline -10

# 回滚到指定版本
git checkout <commit-hash>

# 重新执行迁移和收集静态文件
source venv/bin/activate
python manage.py migrate --settings=career_test.settings.prod
python manage.py collectstatic --noinput --settings=career_test.settings.prod

# 重启服务
sudo supervisorctl restart career_test:*
```

### 7.2 数据库回滚

```bash
# 回滚最近一次迁移
python manage.py migrate <app_name> <previous_migration> --settings=career_test.settings.prod
```

### 7.3 紧急回滚（保留上一版本）

```bash
# 保留当前版本备份
cp -r /var/www/career_test /var/www/career_test_backup_$(date +%Y%m%d%H%M%S)

# 切换到备份版本
cd /var/www
mv career_test career_test_failed
mv career_test_backup_xxxx career_test
sudo supervisorctl restart career_test:*
```

---

## 8. 健康检查

```bash
# 本地检查
curl -I https://huajizhice.com/api/health/

# Django 系统检查
python manage.py check --settings=career_test.settings.prod

# Supervisor 状态
sudo supervisorctl status career_test:*
```

---

## 9. SSL 证书

### 使用 Let's Encrypt（免费）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d huajizhice.com
```

证书自动续期：

```bash
sudo crontab -e
# 添加：每天凌晨检查续期
0 3 * * * certbot renew --quiet --post-hook "systemctl reload nginx"
```

### 手动替换证书

将证书文件放置到 Nginx 配置中指定的路径，然后重载 Nginx：

```bash
sudo systemctl reload nginx
```

---

## 10. 安全注意事项

1. **.env 文件**：确保 .env 不被提交到 Git（已在 .gitignore 中忽略）
2. **密钥强度**：所有密钥使用足够强度的随机字符串
3. **数据库密码**：使用强密码，限制访问来源
4. **防火墙**：仅开放 80/443 端口，SSH 限制 IP
5. **日志权限**：日志目录权限设置为 750
6. **Sentry PII**：已配置 `send_default_pii=False`，不上报用户隐私
7. **HTTPS**：强制 HTTPS 重定向，启用 HSTS
8. **安全头**：X-Frame-Options DENY, X-Content-Type-Options nosniff
