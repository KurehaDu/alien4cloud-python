#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
DEFAULT_INSTALL_DIR="/opt/alien4cloud"
DEFAULT_DATA_DIR="/var/lib/alien4cloud"
DEFAULT_LOG_DIR="/var/log/alien4cloud"
DEFAULT_USER="alien4cloud"
DEFAULT_GROUP="alien4cloud"
DEFAULT_PORT=8088
DEFAULT_UI_PORT=8080
PYTHON_VERSION="3.10"

# 镜像源配置
APT_MIRRORS=(
    "mirrors.aliyun.com"
    "mirrors.tuna.tsinghua.edu.cn"
    "mirrors.ustc.edu.cn"
    "mirrors.huaweicloud.com"
)

PIP_MIRRORS=(
    "https://mirrors.aliyun.com/pypi/simple/"
    "https://pypi.tuna.tsinghua.edu.cn/simple/"
    "https://pypi.mirrors.ustc.edu.cn/simple/"
    "https://repo.huaweicloud.com/repository/pypi/simple/"
)

# 全局变量
INSTALL_DIR=""
DATA_DIR=""
LOG_DIR=""
USER=""
GROUP=""
PORT=""
UI_PORT=""
SKIP_DEPS=false
MAX_RETRIES=3
RETRY_INTERVAL=5
LOG_FILE=""
TEMP_DIR=""
PUBLIC_IP=""
ENABLE_K8S=false

# 帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help                显示帮助信息
  -i, --install-dir DIR     指定安装目录 (默认: $DEFAULT_INSTALL_DIR)
  -d, --data-dir DIR        指定数据目录 (默认: $DEFAULT_DATA_DIR)
  -l, --log-dir DIR         指定日志目录 (默认: $DEFAULT_LOG_DIR)
  -u, --user USER           指定运行用户 (默认: $DEFAULT_USER)
  -g, --group GROUP         指定运行用户组 (默认: $DEFAULT_GROUP)
  -p, --port PORT           指定API端口 (默认: $DEFAULT_PORT)
  --ui-port PORT            指定UI端口 (默认: $DEFAULT_UI_PORT)
  --skip-deps               跳过依赖安装
  --max-retries N          最大重试次数 (默认: 3)
  --retry-interval N       重试间隔(秒) (默认: 5)
  --public-ip IP            指定公网IP
  --enable-k8s              启用MicroK8s

示例:
  $0 --install-dir /custom/path

EOF
    exit 0
}

# 日志函数
setup_logging() {
    TEMP_DIR=$(mktemp -d)
    LOG_FILE="${TEMP_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"
    exec 1> >(tee -a "$LOG_FILE")
    exec 2> >(tee -a "$LOG_FILE" >&2)
    log_info "日志文件: $LOG_FILE"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 错误处理
handle_error() {
    local error_msg="$1"
    local exit_code="${2:-1}"
    local do_rollback="${3:-true}"
    
    log_error "$error_msg"
    
    if [[ "$do_rollback" == "true" ]]; then
        rollback "$error_msg"
    fi
    
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        cp "$LOG_FILE" "${LOG_DIR}/deploy_error_$(date +%Y%m%d_%H%M%S).log"
        rm -rf "$TEMP_DIR"
    fi
    
    exit "$exit_code"
}

# 清理函数
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "安装过程中断，退出码: $exit_code"
        if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
            cp "$LOG_FILE" "${LOG_DIR}/deploy_error_$(date +%Y%m%d_%H%M%S).log"
            rm -rf "$TEMP_DIR"
        fi
    else
        if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
            cp "$LOG_FILE" "${LOG_DIR}/deploy_success_$(date +%Y%m%d_%H%M%S).log"
            rm -rf "$TEMP_DIR"
        fi
    fi
}

trap cleanup EXIT

# 重试函数
retry_command() {
    local cmd="$1"
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        if eval "$cmd"; then
            return 0
        fi
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $MAX_RETRIES ]; then
            log_warn "命令失败，${RETRY_INTERVAL}秒后重试 ($retry_count/$MAX_RETRIES): $cmd"
            sleep $RETRY_INTERVAL
        fi
    done
    
    return 1
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        return 1
    fi
    return 0
}

# 检查系统要求
check_system_requirements() {
    log_info "检查系统要求..."
    
    # 检查操作系统
    if [[ ! -f /etc/os-release ]]; then
        handle_error "无法确定操作系统类型"
    fi
    
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        handle_error "仅支持Ubuntu系统"
    fi
    
    # 检查系统版本
    if [[ "${VERSION_ID}" != "22.04" ]]; then
        log_warn "推荐使用Ubuntu 22.04 LTS，当前版本: ${VERSION_ID}"
    fi
    
    # 检查CPU
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -lt 2 ]]; then
        log_warn "建议至少使用2核CPU，当前: ${cpu_cores}核"
    fi
    
    # 检查内存
    local mem_total=$(free -m | awk '/^Mem:/{print $2}')
    if [[ $mem_total -lt 2048 ]]; then
        handle_error "系统内存不足，最低要求2GB，当前: ${mem_total}MB"
    fi
    
    # 检查磁盘空间
    local disk_free=$(df -m / | awk 'NR==2 {print $4}')
    if [[ $disk_free -lt 10240 ]]; then
        handle_error "磁盘空间不足，最低要求10GB，当前可用: ${disk_free}MB"
    fi
    
    # 检查网络连接
    if ! ping -c 1 8.8.8.8 &> /dev/null; then
        log_warn "无法连接到外网，可能影响安装过程"
    fi
}

# 配置镜像源
configure_mirrors() {
    log_info "配置镜像源..."
    
    # 备份原始源
    cp /etc/apt/sources.list /etc/apt/sources.list.bak
    
    # 测试镜像源速度并选择最快的
    local fastest_mirror=""
    local best_time=999999
    
    for mirror in "${APT_MIRRORS[@]}"; do
        log_info "测试镜像源: $mirror"
        local start_time=$(date +%s.%N)
        if curl -s -m 5 "http://$mirror" &> /dev/null; then
            local end_time=$(date +%s.%N)
            local time_diff=$(echo "$end_time - $start_time" | bc)
            if (( $(echo "$time_diff < $best_time" | bc -l) )); then
                best_time=$time_diff
                fastest_mirror=$mirror
            fi
        fi
    done
    
    if [ -n "$fastest_mirror" ]; then
        log_info "使用最快的镜像源: $fastest_mirror"
        # 生成新的sources.list
        cat > /etc/apt/sources.list << EOF
deb http://${fastest_mirror}/ubuntu/ jammy main restricted universe multiverse
deb http://${fastest_mirror}/ubuntu/ jammy-updates main restricted universe multiverse
deb http://${fastest_mirror}/ubuntu/ jammy-backports main restricted universe multiverse
deb http://${fastest_mirror}/ubuntu/ jammy-security main restricted universe multiverse
EOF
    else
        log_warn "无法找到可用的镜像源，使用默认源"
    fi
    
    # 配置pip镜像源
    mkdir -p ~/.pip
    cat > ~/.pip/pip.conf << EOF
[global]
index-url = ${PIP_MIRRORS[0]}
extra-index-url = 
    ${PIP_MIRRORS[1]}
    ${PIP_MIRRORS[2]}
    ${PIP_MIRRORS[3]}
trusted-host = 
    mirrors.aliyun.com
    pypi.tuna.tsinghua.edu.cn
    pypi.mirrors.ustc.edu.cn
    repo.huaweicloud.com
EOF
}

# 安装系统依赖
install_system_dependencies() {
    log_info "安装系统依赖..."
    
    # 更新包列表
    retry_command "apt-get update" || handle_error "无法更新包列表"
    
    # 安装基础依赖
    local base_deps=(
        curl
        wget
        git
        python3-dev
        python3-pip
        python3-venv
        sqlite3
        supervisor
        net-tools
        libssl-dev
        libyaml-dev
        nginx
    )
    
    # 安装依赖
    local deps_str="${base_deps[*]}"
    retry_command "apt-get install -y $deps_str" || handle_error "无法安装基础依赖"
}

# 安装Python
install_python() {
    log_info "安装Python ${PYTHON_VERSION}..."
    
    # 安装Python
    retry_command "apt-get install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-venv" || handle_error "无法安装Python"
    
    # 创建虚拟环境
    python${PYTHON_VERSION} -m venv "${INSTALL_DIR}/venv" || handle_error "无法创建虚拟环境"
    
    # 激活虚拟环境并安装依赖
    source "${INSTALL_DIR}/venv/bin/activate"
    retry_command "pip install --upgrade pip wheel"
    retry_command "pip install -r requirements.txt" || handle_error "无法安装Python依赖"
    
    if [[ "$ENABLE_K8S" == "true" ]]; then
        install_microk8s
    fi
}

# 安装Nginx
install_nginx() {
    log_info "安装Nginx..."
    
    # 创建Nginx配置
    cat > /etc/nginx/conf.d/alien4cloud.conf << EOF
server {
    listen 80;
    server_name _;
    
    root /var/www/alien4cloud/ui;
    index index.html;
    
    # UI
    location / {
        try_files \$uri \$uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        add_header Pragma "no-cache";
        add_header Expires "0";
    }
    
    # API
    location /api {
        proxy_pass http://localhost:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # 删除默认配置
    rm -f /etc/nginx/sites-enabled/default
    
    # 设置Nginx用户权限
    usermod -a -G ${GROUP} www-data
    
    # 重启Nginx
    systemctl restart nginx || handle_error "无法重启Nginx"
}

# 创建服务用户
create_service_user() {
    log_info "创建服务用户..."
    
    # 创建用户组
    if ! getent group ${GROUP} >/dev/null; then
        groupadd ${GROUP} || handle_error "无法创建用户组 ${GROUP}"
    fi
    
    # 创建用户
    if ! id -u ${USER} >/dev/null 2>&1; then
        useradd -r -g ${GROUP} -d ${INSTALL_DIR} -s /bin/false ${USER} || handle_error "无法创建用户 ${USER}"
    fi
}

# 创建目录结构
create_directories() {
    log_info "创建目录结构..."
    
    # 检查并清理已存在的目录
    if [ -d "${INSTALL_DIR}" ]; then
        log_warn "安装目录已存在: ${INSTALL_DIR}"
        if [ -d "${INSTALL_DIR}/.git" ]; then
            log_info "保留git仓库目录"
        else
            rm -rf "${INSTALL_DIR}"
            mkdir -p "${INSTALL_DIR}"
        fi
    else
        mkdir -p "${INSTALL_DIR}"
    fi

    # 检查并清理数据目录
    if [ -d "${DATA_DIR}" ]; then
        log_warn "数据目录已存在: ${DATA_DIR}"
        local backup_dir="${DATA_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        mv "${DATA_DIR}" "${backup_dir}"
        log_info "已备份数据目录到: ${backup_dir}"
    fi
    
    # 创建数据目录结构
    mkdir -p "${DATA_DIR}"/{templates,instances,storage}
    mkdir -p "${DATA_DIR}"/k8s
    
    # 创建日志目录结构
    mkdir -p "${LOG_DIR}"/{app,nginx,supervisor}
    
    # 创建必要的日志文件
    touch "${LOG_DIR}/app/alien4cloud.log"
    touch "${LOG_DIR}/supervisor/alien4cloud.err.log"
    touch "${LOG_DIR}/supervisor/alien4cloud.out.log"
    touch "${LOG_DIR}/supervisor/nginx.err.log"
    touch "${LOG_DIR}/supervisor/nginx.out.log"
    
    # 创建临时目录
    mkdir -p "${INSTALL_DIR}/tmp"
    
    # 创建配置目录
    mkdir -p "${INSTALL_DIR}/etc"
    
    # 设置权限
    chown -R "${USER}:${GROUP}" "${INSTALL_DIR}"
    chown -R "${USER}:${GROUP}" "${DATA_DIR}"
    chown -R "${USER}:${GROUP}" "${LOG_DIR}"
    
    # 设置目录权限
    find "${INSTALL_DIR}" -type d -exec chmod 755 {} \;
    find "${DATA_DIR}" -type d -exec chmod 755 {} \;
    find "${LOG_DIR}" -type d -exec chmod 755 {} \;
    
    # 设置文件权限
    find "${LOG_DIR}" -type f -exec chmod 644 {} \;
    
    log_info "目录结构创建完成"
}

# 配置应用
configure_application() {
    log_info "配置应用..."
    
    mkdir -p ${INSTALL_DIR}/etc
    
    # 生成配置文件
    cat > ${INSTALL_DIR}/etc/config.yaml << EOF
app:
  name: alien4cloud
  version: 0.1.0
  debug: false

server:
  host: 0.0.0.0
  port: ${PORT}
  ui_port: ${UI_PORT}
  workers: 4
  allowed_hosts: ["localhost", "127.0.0.1"$([ -n "$PUBLIC_IP" ] && echo ", \"$PUBLIC_IP\"")]
  
database:
  url: sqlite:///${DATA_DIR}/alien4cloud.db
  
storage:
  path: ${DATA_DIR}/storage
  
logging:
  level: INFO
  file: ${LOG_DIR}/app/alien4cloud.log
  max_size: 100MB
  backup_count: 10
  
cloud:
  default_provider: "mock"
  providers:
    mock:
      enabled: true
    k8s:
      enabled: ${ENABLE_K8S}
      kubeconfig: "${DATA_DIR}/k8s/kubeconfig"

tosca:
  templates_dir: ${DATA_DIR}/templates
  instances_dir: ${DATA_DIR}/instances
EOF

    chown ${USER}:${GROUP} ${INSTALL_DIR}/etc/config.yaml
    chmod 640 ${INSTALL_DIR}/etc/config.yaml
}

# 配置Supervisor
configure_supervisor() {
    log_info "配置Supervisor..."
    
    # 创建Supervisor配置
    cat > /etc/supervisor/conf.d/alien4cloud.conf << EOF
[program:alien4cloud]
command=${INSTALL_DIR}/venv/bin/uvicorn alien4cloud.web.main:app --host 0.0.0.0 --port ${PORT} --workers 4
directory=${INSTALL_DIR}
user=${USER}
group=${GROUP}
autostart=true
autorestart=true
startsecs=10
startretries=3
stopwaitsecs=60
stopsignal=TERM
stderr_logfile=${LOG_DIR}/supervisor/alien4cloud.err.log
stdout_logfile=${LOG_DIR}/supervisor/alien4cloud.out.log
environment=PATH="${INSTALL_DIR}/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",PYTHONPATH="${INSTALL_DIR}",CONFIG_FILE="${INSTALL_DIR}/etc/config.yaml"

[program:nginx]
command=nginx -g "daemon off;"
user=root
autostart=true
autorestart=true
startsecs=5
startretries=3
stopwaitsecs=30
stopsignal=QUIT
stderr_logfile=${LOG_DIR}/supervisor/nginx.err.log
stdout_logfile=${LOG_DIR}/supervisor/nginx.out.log

[group:alien4cloud]
programs=alien4cloud,nginx
priority=999
EOF
    
    # 创建日志目录
    mkdir -p ${LOG_DIR}/supervisor
    chown -R ${USER}:${GROUP} ${LOG_DIR}/supervisor
    
    # 重新加载Supervisor配置
    supervisorctl reread || handle_error "无法重新加载Supervisor配置"
    supervisorctl update || handle_error "无法更新Supervisor配置"
    
    # 等待服务启动
    local retry_count=0
    while ! supervisorctl status | grep -q "RUNNING" && [ $retry_count -lt $MAX_RETRIES ]; do
        retry_count=$((retry_count + 1))
        log_warn "等待服务启动 ($retry_count/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查服务状态
    if ! systemctl is-active --quiet nginx; then
        log_error "服务 nginx 未正常运行"
        return 1
    fi
    
    if ! systemctl is-active --quiet supervisor; then
        log_error "服务 supervisor 未正常运行"
        return 1
    fi
    
    # 检查端口
    if ! netstat -tuln | grep -q ":${PORT} "; then
        log_error "API端口 ${PORT} 未正常监听"
        return 1
    fi
    
    # 检查UI文件
    if [ ! -f "/var/www/alien4cloud/ui/index.html" ]; then
        log_error "UI文件不存在"
        return 1
    fi
    
    # 检查数据库和目录
    if [ ! -f "${DATA_DIR}/alien4cloud.db" ]; then
        log_error "数据库文件不存在"
        return 1
    fi
    
    # 检查MicroK8s（如果启用）
    if [[ "$ENABLE_K8S" == "true" ]]; then
        if ! microk8s status --wait-ready &> /dev/null; then
            log_error "MicroK8s未正常运行"
            return 1
        fi
        
        if [ ! -f "${DATA_DIR}/k8s/kubeconfig" ]; then
            log_error "K8s配置文件不存在"
            return 1
        fi
    fi
    
    log_info "健康检查通过"
    return 0
}

# 克隆项目代码
clone_project() {
    log_info "克隆项目代码..."
    
    # 检查目标目录是否为空
    if [ -d "${INSTALL_DIR}" ] && [ "$(ls -A ${INSTALL_DIR})" ]; then
        if [ -d "${INSTALL_DIR}/.git" ]; then
            log_info "更新已存在的代码..."
            cd "${INSTALL_DIR}"
            git pull origin main || handle_error "无法更新代码"
            return
        else
            handle_error "安装目录不为空且不是git仓库: ${INSTALL_DIR}"
        fi
    fi
    
    # 克隆代码
    git clone https://github.com/KurehaDu/alien4cloud-python.git "${INSTALL_DIR}" || handle_error "无法克隆代码"
    cd "${INSTALL_DIR}"
}

# 构建前端
build_frontend() {
    log_info "构建前端..."
    
    # 检查Node.js
    if ! command -v node &> /dev/null; then
        log_info "安装Node.js..."
        retry_command "curl -fsSL https://deb.nodesource.com/setup_18.x | bash -" || handle_error "无法添加Node.js源"
        retry_command "apt-get install -y nodejs" || handle_error "无法安装Node.js"
    fi
    
    # 检查yarn
    if ! command -v yarn &> /dev/null; then
        log_info "安装yarn..."
        retry_command "npm install -g yarn" || handle_error "无法安装yarn"
    fi
    
    # 创建UI目录
    mkdir -p /var/www/alien4cloud/ui || handle_error "无法创建UI目录"
    chown -R ${USER}:${GROUP} /var/www/alien4cloud
    
    # 构建UI
    cd "${INSTALL_DIR}/alien4cloud/web/ui"
    retry_command "yarn install" || handle_error "无法安装UI依赖"
    retry_command "yarn build" || handle_error "无法构建UI"
    
    # 复制构建文件
    cp -r dist/* /var/www/alien4cloud/ui/ || handle_error "无法复制UI文件"
    chown -R ${USER}:${GROUP} /var/www/alien4cloud/ui
}

# 回滚函数
rollback() {
    local error_msg="$1"
    log_error "执行回滚: $error_msg"
    
    # 停止服务
    supervisorctl stop alien4cloud:* &> /dev/null || true
    
    # 备份数据目录（如果存在）
    if [ -d "${DATA_DIR}" ] && [ -n "$(ls -A ${DATA_DIR})" ]; then
        local backup_dir="${DATA_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
        mv "${DATA_DIR}" "${backup_dir}"
        log_info "数据已备份到: ${backup_dir}"
    fi
    
    # 清理安装目录（保留git仓库）
    if [ -d "${INSTALL_DIR}" ]; then
        if [ -d "${INSTALL_DIR}/.git" ]; then
            # 保留.git目录，清理其他文件
            find "${INSTALL_DIR}" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
        else
            rm -rf "${INSTALL_DIR}"
        fi
    fi
    
    # 移除supervisor配置
    rm -f /etc/supervisor/conf.d/alien4cloud.conf
    
    # 移除nginx配置
    rm -f /etc/nginx/conf.d/alien4cloud.conf
    
    # 重新加载supervisor配置
    supervisorctl reread &> /dev/null || true
    supervisorctl update &> /dev/null || true
    
    # 保存部署日志
    if [ -n "$LOG_FILE" ] && [ -f "$LOG_FILE" ]; then
        local error_log="${LOG_DIR}/deploy_error_$(date +%Y%m%d_%H%M%S).log"
        cp "$LOG_FILE" "$error_log"
        log_info "部署日志已保存到: $error_log"
    fi
    
    log_error "回滚完成。请检查日志并解决问题后重新运行安装脚本。"
    exit 1
}

# 添加MicroK8s安装函数
install_microk8s() {
    log_info "安装MicroK8s..."
    
    # 检查系统资源
    local mem_total=$(free -m | awk '/^Mem:/{print $2}')
    local cpu_cores=$(nproc)
    local disk_free=$(df -m / | awk 'NR==2 {print $4}')
    
    if [[ $mem_total -lt 8192 ]]; then
        handle_error "MicroK8s需要至少8GB内存，当前: ${mem_total}MB"
    fi
    
    if [[ $cpu_cores -lt 4 ]]; then
        handle_error "MicroK8s需要至少4核CPU，当前: ${cpu_cores}核"
    fi
    
    if [[ $disk_free -lt 30720 ]]; then
        handle_error "MicroK8s需要至少30GB磁盘空间，当前可用: ${disk_free}MB"
    fi
    
    # 安装MicroK8s
    retry_command "snap install microk8s --classic" || handle_error "无法安装MicroK8s"
    
    # 等待MicroK8s就绪
    local retry_count=0
    while ! microk8s status --wait-ready &> /dev/null && [ $retry_count -lt $MAX_RETRIES ]; do
        retry_count=$((retry_count + 1))
        log_warn "等待MicroK8s就绪 ($retry_count/$MAX_RETRIES)"
        sleep $RETRY_INTERVAL
    done
    
    # 配置必要的插件
    microk8s enable dns storage ingress
    
    # 配置用户权限
    usermod -a -G microk8s ${USER}
    
    # 生成kubeconfig
    mkdir -p ${DATA_DIR}/k8s
    microk8s config > ${DATA_DIR}/k8s/kubeconfig
    chown ${USER}:${GROUP} ${DATA_DIR}/k8s/kubeconfig
    chmod 600 ${DATA_DIR}/k8s/kubeconfig
    
    log_info "MicroK8s安装完成"
}

# 主函数
main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                ;;
            -i|--install-dir)
                INSTALL_DIR="$2"
                shift 2
                ;;
            -d|--data-dir)
                DATA_DIR="$2"
                shift 2
                ;;
            -l|--log-dir)
                LOG_DIR="$2"
                shift 2
                ;;
            -u|--user)
                USER="$2"
                shift 2
                ;;
            -g|--group)
                GROUP="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            --ui-port)
                UI_PORT="$2"
                shift 2
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --max-retries)
                MAX_RETRIES="$2"
                shift 2
                ;;
            --retry-interval)
                RETRY_INTERVAL="$2"
                shift 2
                ;;
            --public-ip)
                PUBLIC_IP="$2"
                shift 2
                ;;
            --enable-k8s)
                ENABLE_K8S=true
                shift
                ;;
            *)
                handle_error "未知选项: $1"
                ;;
        esac
    done
    
    # 设置默认值
    INSTALL_DIR=${INSTALL_DIR:-$DEFAULT_INSTALL_DIR}
    DATA_DIR=${DATA_DIR:-$DEFAULT_DATA_DIR}
    LOG_DIR=${LOG_DIR:-$DEFAULT_LOG_DIR}
    USER=${USER:-$DEFAULT_USER}
    GROUP=${GROUP:-$DEFAULT_GROUP}
    PORT=${PORT:-$DEFAULT_PORT}
    UI_PORT=${UI_PORT:-$DEFAULT_UI_PORT}
    
    # 检查root权限
    if [[ $EUID -ne 0 ]]; then
        handle_error "此脚本需要root权限运行"
    fi
    
    # 设置日志
    setup_logging
    
    # 显示配置信息
    log_info "安装配置:"
    log_info "- 安装目录: ${INSTALL_DIR}"
    log_info "- 数据目录: ${DATA_DIR}"
    log_info "- 日志目录: ${LOG_DIR}"
    log_info "- 运行用户: ${USER}"
    log_info "- 运行用户组: ${GROUP}"
    log_info "- API端口: ${PORT}"
    log_info "- UI端口: ${UI_PORT}"
    
    # 执行安装步骤
    check_system_requirements
    configure_mirrors
    
    if [[ "$SKIP_DEPS" != "true" ]]; then
        install_system_dependencies
    fi
    
    create_service_user
    clone_project
    create_directories
    install_python
    build_frontend
    install_nginx
    configure_application
    configure_supervisor
    
    if ! health_check; then
        handle_error "健康检查失败" 1 true
    fi
    
    log_info "安装完成！"
    if [[ -n "$PUBLIC_IP" ]]; then
        log_info "您可以通过以下地址访问服务："
        log_info "Web界面: http://${PUBLIC_IP}:${UI_PORT}"
        log_info "API接口: http://${PUBLIC_IP}:${PORT}"
    else
        log_info "您可以通过以下地址访问服务："
        log_info "Web界面: http://localhost:${UI_PORT}"
        log_info "API接口: http://localhost:${PORT}"
    fi
    
    if [[ "$ENABLE_K8S" == "true" ]]; then
        log_info "MicroK8s已启用并配置完成"
        log_info "K8s配置文件位置: ${DATA_DIR}/k8s/kubeconfig"
    fi
    
    log_info "安装日志已保存到: ${LOG_FILE}"
    log_info "配置文件位置: ${INSTALL_DIR}/etc/config.yaml"
    log_info "使用以下命令管理服务："
    log_info "- 启动服务: supervisorctl start all"
    log_info "- 停止服务: supervisorctl stop all"
    log_info "- 重启服务: supervisorctl restart all"
    log_info "- 查看状态: supervisorctl status"
}

# 执行主函数
main "$@" 