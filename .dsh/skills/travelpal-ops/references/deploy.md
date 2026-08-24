# 部署规范（TravelPal deploy）

> 部署项目、配置服务器、域名/HTTPS。服务器已部署好时，常用的是"更新到最新版本"。

## 部署项目

```bash
git clone https://github.com/<用户名>/TravelPal.git  # 或 git pull 更新
cd TravelPal
cp .env.example .env   # 编辑 .env，至少配置 AMAP_API_KEY / AMAP_JS_KEY / LLM_API_KEY
docker compose up -d --build
docker compose logs -f
curl http://localhost/api/poi-lookup   # 应返回 422（缺参数），说明后端正常
```

- 首次 `docker compose build` 约 5-15 分钟；后续（镜像缓存）约 10 秒。

## 更新到最新版本

```bash
git pull
docker compose up -d --build
```

## 查看/重启服务

```bash
docker compose logs -f --tail=100 backend   # 后端日志
docker compose restart backend              # 重启单个
docker compose restart                      # 全部重启
```

## 常见问题

- **高德 API 白名单**：高德开放平台 → 应用管理 → 你的应用 → 添加 `http://<服务器IP>/` 到 Web 服务 API 白名单。

## 域名 + HTTPS（可选）

- **备案**：国内服务器必须 ICP 备案，备案号在 `frontend/src/App.vue` 底部。
- **证书**：Nginx 容器 bind mount 读取宿主机 `/etc/letsencrypt/`：
  ```bash
  docker compose stop nginx
  sudo certbot certonly --standalone -d trippal.site -d www.trippal.site
  docker compose build nginx && docker compose up -d
  ```
- **自动续期**：crontab 每天续期并重启 nginx 容器。
  ```
  0 3 * * * certbot renew --quiet && cd /path/to/TravelPal && docker compose restart nginx
  ```
  > 续期后证书更新，但运行中容器不感知，必须 `docker compose restart nginx` 重载证书。

## 服务器参考（已部署，仅参考）

2 核 / 4GB / 40GB SSD / 5 Mbps / Ubuntu 24.04。开放 80（HTTP）/443（HTTPS）/22（SSH）。
