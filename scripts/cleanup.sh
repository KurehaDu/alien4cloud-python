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
DEFAULT_BACKUP_DAYS=30
DEFAULT_LOG_DAYS=7
DEFAULT_TEMP_DAYS=3

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# 帮助信息
show_help() {
    cat << EOF
用法: $0 [选项]

选项:
  -h, --help                显示帮助信息
  -i, --install-dir DIR     指定安装目录 (默认: $DEFAULT_INSTALL_DIR)
  -d, --data-dir DIR        指定数据目录 (默认: $DEFAULT_DATA_DIR)
  -l, --log-dir DIR         指定日志目录 (默认: $DEFAULT_LOG_DIR)
  --backup-days N           备份保留天数 (默认: $DEFAULT_BACKUP_DAYS)
  --log-days N              日志保留天数 (默认: $DEFAULT_LOG_DAYS)
  --temp-days N             临时文件保留天数 (默认: $DEFAULT_TEMP_DAYS)
  --force                   强制清理，不提示确认
  --dry-run                 仅显示将要删除的文件，不实际删除

示例:
  $0 --backup-days 15 --log-days 5
  $0 --dry-run
  $0 --force

EOF
    exit 0
}

# 检查目录是否存在
check_directory() {
    local dir="$1"
    if [ ! -d "$dir" ]; then
        log_warn "目录不存在: $dir"
        return 1
    fi
    return 0
}

# 计算文件大小
calculate_size() {
    local dir="$1"
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null | cut -f1
    else
        echo "0B"
    fi
}

# 清理备份文件
cleanup_backups() {
    local dry_run="$1"
    local dirs_to_check=(
        "$INSTALL_DIR"
        "$DATA_DIR"
        "$LOG_DIR"
        "/etc/supervisor/conf.d"
        "/etc/nginx/conf.d"
        "/var/www/alien4cloud"
    )
    
    log_info "清理备份文件..."
    
    for dir in "${dirs_to_check[@]}"; do
        if check_directory "$dir"; then
            # 查找备份文件
            local backup_files=(
                "$dir"_backup_*
                "$dir"*.bak
                "$dir"*.backup
                "$dir"*.old
            )
            
            for pattern in "${backup_files[@]}"; do
                if [ -n "$(ls $pattern 2>/dev/null)" ]; then
                    local size=$(calculate_size "$pattern")
                    if [ "$dry_run" = "true" ]; then
                        log_info "将删除备份: $pattern (大小: $size)"
                    else
                        log_info "删除备份: $pattern (大小: $size)"
                        rm -rf $pattern
                    fi
                fi
            done
        fi
    done
}

# 清理日志文件
cleanup_logs() {
    local dry_run="$1"
    
    log_info "清理日志文件..."
    
    if check_directory "$LOG_DIR"; then
        # 查找旧的日志文件
        local log_patterns=(
            "*.log.*"
            "deploy_*.log"
            "*.gz"
            "*.zip"
        )
        
        for pattern in "${log_patterns[@]}"; do
            local files=$(find "$LOG_DIR" -type f -name "$pattern" -mtime +$LOG_DAYS 2>/dev/null)
            if [ -n "$files" ]; then
                while IFS= read -r file; do
                    local size=$(calculate_size "$file")
                    if [ "$dry_run" = "true" ]; then
                        log_info "将删除日志: $file (大小: $size)"
                    else
                        log_info "删除日志: $file (大小: $size)"
                        rm -f "$file"
                    fi
                done <<< "$files"
            fi
        done
    fi
}

# 清理临时文件
cleanup_temp() {
    local dry_run="$1"
    
    log_info "清理临时文件..."
    
    local temp_dirs=(
        "/tmp/alien4cloud_*"
        "$DATA_DIR/tmp"
        "$INSTALL_DIR/tmp"
    )
    
    for dir in "${temp_dirs[@]}"; do
        if [ -n "$(ls $dir 2>/dev/null)" ]; then
            local files=$(find $dir -type f -mtime +$TEMP_DAYS 2>/dev/null)
            if [ -n "$files" ]; then
                while IFS= read -r file; do
                    local size=$(calculate_size "$file")
                    if [ "$dry_run" = "true" ]; then
                        log_info "将删除临时文件: $file (大小: $size)"
                    else
                        log_info "删除临时文件: $file (大小: $size)"
                        rm -f "$file"
                    fi
                done <<< "$files"
            fi
        fi
    done
}

# 清理空目录
cleanup_empty_dirs() {
    local dry_run="$1"
    local dirs=(
        "$INSTALL_DIR"
        "$DATA_DIR"
        "$LOG_DIR"
    )
    
    log_info "清理空目录..."
    
    for dir in "${dirs[@]}"; do
        if check_directory "$dir"; then
            local empty_dirs=$(find "$dir" -type d -empty 2>/dev/null)
            if [ -n "$empty_dirs" ]; then
                while IFS= read -r empty_dir; do
                    if [ "$dry_run" = "true" ]; then
                        log_info "将删除空目录: $empty_dir"
                    else
                        log_info "删除空目录: $empty_dir"
                        rmdir "$empty_dir" 2>/dev/null
                    fi
                done <<< "$empty_dirs"
            fi
        fi
    done
}

# 主函数
main() {
    # 默认值
    INSTALL_DIR="$DEFAULT_INSTALL_DIR"
    DATA_DIR="$DEFAULT_DATA_DIR"
    LOG_DIR="$DEFAULT_LOG_DIR"
    BACKUP_DAYS="$DEFAULT_BACKUP_DAYS"
    LOG_DAYS="$DEFAULT_LOG_DAYS"
    TEMP_DAYS="$DEFAULT_TEMP_DAYS"
    FORCE=false
    DRY_RUN=false
    
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
            --backup-days)
                BACKUP_DAYS="$2"
                shift 2
                ;;
            --log-days)
                LOG_DAYS="$2"
                shift 2
                ;;
            --temp-days)
                TEMP_DAYS="$2"
                shift 2
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            *)
                log_error "未知选项: $1"
                exit 1
                ;;
        esac
    done
    
    # 检查root权限
    if [[ $EUID -ne 0 ]]; then
        log_error "此脚本需要root权限运行"
        exit 1
    fi
    
    # 显示配置信息
    log_info "清理配置:"
    log_info "- 安装目录: $INSTALL_DIR"
    log_info "- 数据目录: $DATA_DIR"
    log_info "- 日志目录: $LOG_DIR"
    log_info "- 备份保留天数: $BACKUP_DAYS"
    log_info "- 日志保留天数: $LOG_DAYS"
    log_info "- 临时文件保留天数: $TEMP_DAYS"
    log_info "- 强制模式: $FORCE"
    log_info "- 仅显示: $DRY_RUN"
    
    # 确认提示
    if [ "$FORCE" != "true" ] && [ "$DRY_RUN" != "true" ]; then
        read -p "确定要执行清理操作吗？[y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    # 执行清理
    cleanup_backups "$DRY_RUN"
    cleanup_logs "$DRY_RUN"
    cleanup_temp "$DRY_RUN"
    cleanup_empty_dirs "$DRY_RUN"
    
    if [ "$DRY_RUN" = "true" ]; then
        log_info "这是一次模拟运行，没有文件被实际删除"
    else
        log_info "清理完成"
    fi
}

# 执行主函数
main "$@" 