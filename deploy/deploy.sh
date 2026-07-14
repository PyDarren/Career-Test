#!/usr/bin/env bash
# ============================================================================
# 画己职测 — 生产环境部署脚本
#
# 品牌：画己职测
# 项目：career_test
#
# 功能：
#   1. 拉取最新代码
#   2. 激活虚拟环境
#   3. 安装 Python 依赖
#   4. 执行数据库迁移
#   5. 收集静态文件
#   6. 重启 Gunicorn 和 Celery
#   7. 健康检查
#
# 用法：
#   chmod +x deploy/deploy.sh
#   ./deploy/deploy.sh
#
# 前置条件：
#   - 服务器已安装 Python 3.11+、MySQL 8.0+、Redis 7.0+
#   - 已配置 .env 文件（从 .env.example 复制并填写真实值）
#   - 虚拟环境位于 /var/www/career_test/venv
#   - Supervisor 和 Nginx 已安装并配置
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 配置项（根据实际环境修改）
# ---------------------------------------------------------------------------
PROJECT_DIR="/var/www/career_test"
VENV_DIR="${PROJECT_DIR}/venv"
SETTINGS_MODULE="career_test.settings.prod"
GIT_BRANCH="main"
HEALTH_CHECK_URL="https://huajizhice.com/api/health/"
HEALTH_CHECK_MAX_RETRIES=5
HEALTH_CHECK_INTERVAL=3

# 日志颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------------------------------------------------------------------------
# 0. 前置检查
# ---------------------------------------------------------------------------
log_info "========== 画己职测部署开始 =========="
log_info "检查项目目录: ${PROJECT_DIR}"
if [[ ! -d "${PROJECT_DIR}" ]]; then
    log_error "项目目录不存在: ${PROJECT_DIR}"
    exit 1
fi

log_info "检查虚拟环境: ${VENV_DIR}"
if [[ ! -d "${VENV_DIR}" ]]; then
    log_error "虚拟环境不存在: ${VENV_DIR}"
    log_error "请先创建: python3.11 -m venv ${VENV_DIR}"
    exit 1
fi

log_info "检查 .env 文件"
if [[ ! -f "${PROJECT_DIR}/.env" ]]; then
    log_error ".env 文件不存在，请从 .env.example 复制并填写真实值"
    exit 1
fi

cd "${PROJECT_DIR}"

# ---------------------------------------------------------------------------
# 1. 拉取最新代码
# ---------------------------------------------------------------------------
log_info "[1/7] 拉取最新代码 (branch: ${GIT_BRANCH})"
git fetch origin
git checkout "${GIT_BRANCH}"
git pull origin "${GIT_BRANCH}"
log_info "当前提交: $(git rev-parse --short HEAD)"

# ---------------------------------------------------------------------------
# 2. 激活虚拟环境
# ---------------------------------------------------------------------------
log_info "[2/7] 激活虚拟环境"
source "${VENV_DIR}/bin/activate"
log_info "Python: $(python --version)"

# ---------------------------------------------------------------------------
# 3. 安装 Python 依赖
# ---------------------------------------------------------------------------
log_info "[3/7] 安装 Python 依赖"
pip install --upgrade pip
pip install -r requirements.txt
log_info "依赖安装完成"

# ---------------------------------------------------------------------------
# 4. 数据库迁移
# ---------------------------------------------------------------------------
log_info "[4/7] 执行数据库迁移"
python manage.py migrate --settings="${SETTINGS_MODULE}"
log_info "迁移完成"

# ---------------------------------------------------------------------------
# 5. 收集静态文件
# ---------------------------------------------------------------------------
log_info "[5/7] 收集静态文件"
python manage.py collectstatic --noinput --settings="${SETTINGS_MODULE}"
log_info "静态文件收集完成"

# ---------------------------------------------------------------------------
# 6. 重启 Gunicorn 和 Celery
# ---------------------------------------------------------------------------
log_info "[6/7] 重启服务（Supervisor）"

if command -v supervisorctl &> /dev/null; then
    log_info "重新读取 Supervisor 配置"
    sudo supervisorctl reread
    sudo supervisorctl update

    log_info "重启 Gunicorn"
    sudo supervisorctl restart career_test_gunicorn

    log_info "重启 Celery Worker"
    sudo supervisorctl restart career_test_celery_worker

    log_info "重启 Celery Beat"
    sudo supervisorctl restart career_test_celery_beat

    log_info "重载 Nginx"
    sudo nginx -t && sudo systemctl reload nginx
else
    log_warn "未找到 supervisorctl，尝试手动重启"
    # 手动重启 Gunicorn
    pkill -f "gunicorn.*career_test" || true
    gunicorn career_test.wsgi:application \
        --config deploy/gunicorn.conf.py \
        --daemon
    log_warn "Gunicorn 已以 daemon 模式启动（建议使用 Supervisor 管理）"
fi

# ---------------------------------------------------------------------------
# 7. 健康检查
# ---------------------------------------------------------------------------
log_info "[7/7] 健康检查"

retry=0
while [[ ${retry} -lt ${HEALTH_CHECK_MAX_RETRIES} ]]; do
    retry=$((retry + 1))
    log_info "健康检查尝试 ${retry}/${HEALTH_CHECK_MAX_RETRIES}"

    http_code=$(curl -s -o /dev/null -w "%{http_code}" "${HEALTH_CHECK_URL}" || echo "000")

    if [[ "${http_code}" == "200" ]]; then
        log_info "健康检查通过 (HTTP ${http_code})"
        log_info "========== 画己职测部署成功 =========="
        exit 0
    fi

    log_warn "健康检查未通过 (HTTP ${http_code})，${HEALTH_CHECK_INTERVAL} 秒后重试..."
    sleep ${HEALTH_CHECK_INTERVAL}
done

log_error "健康检查失败，服务可能未正常启动"
log_error "请检查日志:"
log_error "  Gunicorn:  /var/log/career_test/gunicorn_err.log"
log_error "  Celery:    /var/log/career_test/celery_worker_err.log"
log_error "  Nginx:     /var/log/nginx/career_test_error.log"
exit 1
