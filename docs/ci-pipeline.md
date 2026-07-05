# CI: GitHub Actions 流水线

## 触发条件

- 推送（push）到 `main` 分支
- 向 `main` 发起 Pull Request

## 流水线步骤

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - uses: actions/cache@v6
        with:
          path: ~/.cache/pypoetry
          key: poetry-${{ hashFiles('poetry.lock') }}
      - run: pip install poetry && poetry install
      - run: poetry run pytest -v -m "not slow"
```

1. **checkout** — 拉取代码
2. **setup-python** — 配置 Python 3.12
3. **缓存** — 缓存 Poetry 虚拟环境加速后续安装
4. **安装依赖** — `poetry install`
5. **测试** — 运行 pytest，跳过 `slow` 标记用例

## 跳过 slow 标记

`pytest.ini` 中定义了 `slow` 标记，用于大数据集或长时间运行的测试。CI 中使用 `-m "not slow"` 排除这些用例，确保流水线在 3 分钟内完成。slow 用例可手动在本地触发。

## 状态图标

| 状态 | GitHub 图标 | 含义 |
|------|-------------|------|
| 通过 | ✅ 绿色勾 | 所有步骤成功 |
| 失败 | ❌ 红色叉 | 至少一步出错（需检查日志） |

## Branch Protection（可选）

建议在 GitHub 仓库设置中启用 Branch Protection：

- 要求 PR 通过 CI 后方可合入 `main`
- 要求线性历史（线性历史选项）
- 禁止直接推送到 `main`
