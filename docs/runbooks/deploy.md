# 部署指引

## 一、服务器选购

| 参数 | 推荐规格 | 说明 |
|------|---------|------|
| CPU | 2 核 | 单体服务够用 |
| 内存 | **4 GB** | PostgreSQL 约需 500MB+，留有余量 |
| 硬盘 | 40 GB SSD | 系统 + 数据库 + Docker 镜像 |
| 带宽 | 5 Mbps | 演示场景足够 |
| 系统 | **Ubuntu 24.04** | Docker 兼容性最好 |
| 厂商 | 腾讯云/阿里云 轻量应用服务器 | ~80 元/月 |

> 学生认证可享受优惠价（腾讯云"云+校园"约 40 元/月）。

## 二、服务器初始化

### 安装 Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 退出 SSH 重登录以使分组生效
```

验证安装：

```bash
docker --version
docker compose version
```

### 配置安全组（防火墙）

在云厂商控制台开放以下端口：

| 端口 | 用途 | 建议 |
|------|------|------|
| 80 | HTTP（Nginx） | 必须开放 |
| 443 | HTTPS（可选） | 后期配置域名时开放 |
| 22 | SSH | 默认已开放，建议修改默认端口 |

## 三、部署项目

```bash
# 1. 克隆仓库
git clone https://github.com/你的用户名/TravelPal.git
cd TravelPal

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key
# 至少需要配置：AMAP_API_KEY、AMAP_JS_KEY、LLM_API_KEY

# 3. 启动全部服务
docker compose up -d

# 4. 查看启动日志
docker compose logs -f

# 5. 验证
curl http://localhost/api/poi-lookup
# 应返回 422（缺少参数），说明后端正常运行
```

### 首次启动耗时

- `docker compose build`：首次约 5-15 分钟（取决于网络和机器性能）
- 后续启动（镜像已缓存）：约 10 秒

## 四、常见问题

### 高德 API 白名单

在**高德开放平台控制台** → 应用管理 → 你的应用 → 添加 `http://你的服务器IP/` 到 **Web 服务 API** 白名单。

### 查看后端日志

```bash
docker compose logs -f --tail=100 backend
```

### 重启服务

```bash
docker compose restart backend
# 或全部重启
docker compose restart
```

### 更新到最新版本

```bash
git pull
docker compose up -d --build
```

## 五、可选：域名 + HTTPS

### 域名备案

国内服务器必须完成 ICP 备案，备案通过后获取备案号，在 `frontend/src/App.vue` 底部添加。

### 申请证书 + 配置 Nginx

本项目的 Nginx 容器通过 bind mount 读取宿主机 `/etc/letsencrypt/` 证书文件。

```bash
# 1. 停 nginx 容器（释放 80 端口给 certbot）
docker compose stop nginx

# 2. 申请证书（standalone 模式，不自动修改 Nginx 配置）
sudo certbot certonly --standalone -d trippal.site -d www.trippal.site

# 3. 容器化配置
#    - docker/nginx.conf 已预置 SSL server block
#    - docker-compose.yml 已暴露 443 端口并挂载 /etc/letsencrypt:ro
#    确认后重新构建并启动：
docker compose build nginx && docker compose up -d
```

### 证书自动续期

certbot 证书有效期 90 天，需配置定时任务自动续期并刷新 Nginx 容器：

```bash
# 编辑 crontab
sudo crontab -e
# 添加以下行（每天凌晨 3 点检查续期，成功后重启 nginx 容器）
0 3 * * * certbot renew --quiet && cd /path/to/TravelPal && docker compose restart nginx
```

> 续期后 `/etc/letsencrypt/live/` 下的证书文件会更新，但运行中的 Nginx 容器不会自动感知文件变化。必须执行 `docker compose restart nginx` 让容器重新加载证书。
