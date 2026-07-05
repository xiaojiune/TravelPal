# WSL 本地开发环境配置

## SSH Agent（推送 GitHub 前）

```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

## 端口 8000 被占用（后端无法启动）

```bash
# WSL 内
sudo fuser -k 8000/tcp
# 或 Windows 进程
taskkill /f /im python.exe
```

## GBK 编码问题（emoji/中文 print 崩溃）

- 已在 `~/.bashrc` 配置 `export PYTHONIOENCODING=utf-8`
- 如果在新环境遇到，加此环境变量即可

## 启动后端

```bash
cd /mnt/d/AAA/TravelPal
.venv/bin/python -m backend.api.server
```

## 启动前端

```bash
cd frontend
npm run dev
```
