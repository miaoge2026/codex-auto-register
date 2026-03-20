#!/bin/bash
# Deploy Script for Codex Auto Registration
# 部署脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_NAME="codex-auto-register"
DOCKER_IMAGE="codex-register:latest"
COMPOSE_FILE="docker-compose.yml"
BACKUP_DIR="backups"
LOG_DIR="logs"

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# 帮助函数
show_help() {
    cat << EOF
Codex Auto Registration 部署脚本

使用方法:
    ./deploy.sh [选项]

选项:
    -h, --help          显示帮助信息
    -t, --test          测试模式（不实际执行）
    -b, --backup        部署前创建备份
    -r, --restore       从备份恢复
    -c, --clean         清理旧文件
    -u, --update        更新代码
    -d, --docker        使用Docker部署
    -p, --production    生产环境部署
    -v, --verbose       详细输出

示例:
    ./deploy.sh --docker          # 使用Docker部署
    ./deploy.sh --production      # 生产环境部署
    ./deploy.sh --backup --update # 备份后更新
EOF
}

# 参数解析
TEST_MODE=false
CREATE_BACKUP=false
RESTORE_BACKUP=false
CLEAN_FILES=false
UPDATE_CODE=false
DOCKER_DEPLOY=false
PRODUCTION=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        -b|--backup)
            CREATE_BACKUP=true
            shift
            ;;
        -r|--restore)
            RESTORE_BACKUP=true
            shift
            ;;
        -c|--clean)
            CLEAN_FILES=true
            shift
            ;;
        -u|--update)
            UPDATE_CODE=true
            shift
            ;;
        -d|--docker)
            DOCKER_DEPLOY=true
            shift
            ;;
        -p|--production)
            PRODUCTION=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            log_error "未知选项: $1"
            show_help
            exit 1
            ;;
    esac
done

# 检查命令
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "缺少命令: $1"
        exit 1
    fi
}

# 检查权限
check_permissions() {
    if [ "$EUID" -eq 0 ]; then
        log_warn "不建议使用root权限运行"
    fi
}

# 创建备份
create_backup() {
    if [ "$CREATE_BACKUP" = true ]; then
        log_info "创建备份..."
        
        BACKUP_NAME="pre_deploy_$(date +%Y%m%d_%H%M%S)"
        
        if [ "$TEST_MODE" = false ]; then
            mkdir -p "$BACKUP_DIR"
            
            # 备份重要文件
            tar -czf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" \
                accounts.json \
                sub2api_import.json \
                config.yaml \
                codex_register.log \
                requirements.txt \
                2>/dev/null || true
            
            log_info "备份创建成功: ${BACKUP_NAME}.tar.gz"
        else
            log_debug "测试模式: 跳过备份创建"
        fi
    fi
}

# 从备份恢复
restore_backup() {
    if [ "$RESTORE_BACKUP" = true ]; then
        log_info "从备份恢复..."
        
        if [ -z "$BACKUP_NAME" ]; then
            # 查找最新的备份
            LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | head -1)
            
            if [ -z "$LATEST_BACKUP" ]; then
                log_error "未找到备份文件"
                exit 1
            fi
            
            BACKUP_NAME=$(basename "$LATEST_BACKUP" .tar.gz)
        fi
        
        if [ "$TEST_MODE" = false ]; then
            log_info "从备份恢复: $BACKUP_NAME"
            tar -xzf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" -C .
            log_info "备份恢复完成"
        else
            log_debug "测试模式: 跳过恢复"
        fi
    fi
}

# 清理旧文件
clean_files() {
    if [ "$CLEAN_FILES" = true ]; then
        log_info "清理旧文件..."
        
        if [ "$TEST_MODE" = false ]; then
            # 清理日志文件
            find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null || true
            
            # 清理临时文件
            rm -rf __pycache__/*.pyc 2>/dev/null || true
            rm -rf .pytest_cache/ 2>/dev/null || true
            
            # 清理旧备份
            if [ -d "$BACKUP_DIR" ]; then
                find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete 2>/dev/null || true
            fi
            
            log_info "文件清理完成"
        else
            log_debug "测试模式: 跳过清理"
        fi
    fi
}

# 更新代码
update_code() {
    if [ "$UPDATE_CODE" = true ]; then
        log_info "更新代码..."
        
        if [ "$TEST_MODE" = false ]; then
            # 拉取最新代码
            git pull origin main
            
            # 安装依赖
            if [ "$PRODUCTION" = true ]; then
                pip install -r requirements.txt
            else
                pip install -r requirements-dev.txt
            fi
            
            log_info "代码更新完成"
        else
            log_debug "测试模式: 跳过更新"
        fi
    fi
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查Python
    check_command python3
    
    # 检查pip
    check_command pip
    
    if [ "$DOCKER_DEPLOY" = true ]; then
        # 检查Docker
        check_command docker
        
        # 检查docker-compose
        check_command docker-compose
    fi
    
    log_info "依赖检查通过"
}

# 配置环境
configure_environment() {
    log_info "配置环境..."
    
    if [ "$PRODUCTION" = true ]; then
        # 生产环境配置
        export FLASK_ENV=production
        export PYTHONUNBUFFERED=1
        
        # 创建必要的目录
        mkdir -p "$LOG_DIR"
        mkdir -p "$BACKUP_DIR"
        
        # 设置权限
        chmod 600 config.yaml
        chmod 600 requirements.txt
        
        log_info "生产环境配置完成"
    else
        # 开发环境配置
        export FLASK_ENV=development
        export PYTHONUNBUFFERED=1
        
        log_info "开发环境配置完成"
    fi
}

# Docker部署
deploy_docker() {
    if [ "$DOCKER_DEPLOY" = true ]; then
        log_info "使用Docker部署..."
        
        if [ "$TEST_MODE" = false ]; then
            # 构建镜像
            docker build -t "$DOCKER_IMAGE" .
            
            # 停止旧容器
            docker-compose down 2>/dev/null || true
            
            # 启动新容器
            docker-compose up -d
            
            # 等待服务启动
            log_info "等待服务启动..."
            sleep 10
            
            # 检查服务状态
            if docker ps | grep -q "$PROJECT_NAME"; then
                log_info "Docker部署成功"
                log_info "访问地址: http://localhost:5000"
            else
                log_error "Docker部署失败"
                exit 1
            fi
        else
            log_debug "测试模式: 跳过Docker部署"
        fi
    fi
}

# 传统部署
deploy_traditional() {
    if [ "$DOCKER_DEPLOY" = false ]; then
        log_info "使用传统方式部署..."
        
        if [ "$TEST_MODE" = false ]; then
            # 安装依赖
            if [ "$PRODUCTION" = true ]; then
                pip install -r requirements.txt
            else
                pip install -r requirements-dev.txt
            fi
            
            # 停止旧进程
            pkill -f "python.*app" 2>/dev/null || true
            
            # 启动服务
            if [ "$PRODUCTION" = true ]; then
                # 使用Gunicorn生产服务器
                nohup gunicorn -w 4 -b 0.0.0.0:5000 app_enhanced:app > "$LOG_DIR/gunicorn.log" 2>&1 &
            else
                # 使用Flask开发服务器
                nohup python app_enhanced.py > "$LOG_DIR/flask.log" 2>&1 &
            fi
            
            # 等待服务启动
            log_info "等待服务启动..."
            sleep 5
            
            # 检查服务状态
            if curl -s http://localhost:5000/api/status > /dev/null; then
                log_info "服务启动成功"
                log_info "访问地址: http://localhost:5000"
            else
                log_error "服务启动失败"
                exit 1
            fi
        else
            log_debug "测试模式: 跳过传统部署"
        fi
    fi
}

# 健康检查
health_check() {
    log_info "健康检查..."
    
    if [ "$TEST_MODE" = false ]; then
        # 检查服务是否正常运行
        for i in {1..10}; do
            if curl -s http://localhost:5000/api/status > /dev/null; then
                log_info "服务健康检查通过"
                return 0
            fi
            sleep 2
        done
        
        log_error "服务健康检查失败"
        return 1
    else
        log_debug "测试模式: 跳过健康检查"
    fi
}

# 显示部署信息
show_deployment_info() {
    log_info "部署信息"
    echo "================================"
    echo "项目: $PROJECT_NAME"
    echo "环境: $([ "$PRODUCTION" = true ] && echo '生产' || echo '开发')"
    echo "方式: $([ "$DOCKER_DEPLOY" = true ] && echo 'Docker' || echo '传统')"
    echo "访问地址: http://localhost:5000"
    echo "日志目录: $LOG_DIR/"
    echo "备份目录: $BACKUP_DIR/"
    echo "================================"
}

# 主函数
main() {
    log_info "开始部署 Codex Auto Registration"
    
    # 检查权限
    check_permissions
    
    # 检查依赖
    check_dependencies
    
    # 创建备份
    create_backup
    
    # 从备份恢复
    restore_backup
    
    # 清理文件
    clean_files
    
    # 更新代码
    update_code
    
    # 配置环境
    configure_environment
    
    # 部署
    if [ "$DOCKER_DEPLOY" = true ]; then
        deploy_docker
    else
        deploy_traditional
    fi
    
    # 健康检查
    health_check
    
    # 显示部署信息
    show_deployment_info
    
    log_info "部署完成"
}

# 运行主函数
main "$@"

# 退出处理
trap 'log_info "部署中断"' EXIT