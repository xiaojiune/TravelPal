#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/你的用户名/TravelPal.git"
PROJECT_DIR="TravelPal"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

info "=== TravelPal 一键部署脚本 ==="
echo ""

# ---------- 前置检查 ----------
info "检查依赖..."
command -v git       >/dev/null 2>&1 || { error "未安装 git";          exit 1; }
command -v docker    >/dev/null 2>&1 || { error "未安装 docker";       exit 1; }
docker compose version >/dev/null 2>&1 || { error "未安装 docker compose"; exit 1; }
info "所有依赖已就绪"
echo ""

# ---------- 克隆 / 拉取 ----------
if [ -d "$PROJECT_DIR" ]; then
    info "项目目录已存在，拉取最新代码..."
    cd "$PROJECT_DIR"
    git pull
else
    info "克隆项目..."
    git clone "$REPO_URL"
    cd "$PROJECT_DIR"
fi
echo ""

# ---------- 环境变量 ----------
if [ ! -f ".env" ]; then
    warn ".env 不存在，从 .env.example 创建"
    cp .env.example .env
    info "请编辑 .env 填入你的 API Key，然后重新运行本脚本"
    exit 0
fi
info ".env 已存在"
echo ""

# ---------- 构建并启动 ----------
info "构建并启动服务..."
docker compose up -d --build
echo ""

# ---------- 验证 ----------
sleep 3
if curl -sf http://localhost:8000/docs >/dev/null 2>&1; then
    info "✅ 后端 API 可用（http://localhost:8000/docs）"
else
    warn "⚠️  后端 API 暂未响应，可查看日志：docker compose logs -f backend"
fi

SERVER_IP=$(curl -sf http://checkip.amazonaws.com 2>/dev/null || echo "<服务器IP>")
echo ""
info "=========================================="
info "✅ 部署完成"
info "   本地访问： http://localhost"
info "   公网访问： http://$SERVER_IP"
info "=========================================="
info "常用命令："
info "   查看日志：  docker compose logs -f"
info "   重启服务：  docker compose restart"
info "   停止服务：  docker compose down"
