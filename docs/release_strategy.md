# 版本与发布策略

## 1. 分支模型
- `main`：生产稳定分支，只接受通过验证的合并。
- `staging`：预发布验证分支，用于联调与模拟盘验收。
- `dev`：日常开发分支，功能迭代默认进入此分支。

## 2. 提交流程
- 开发在 `dev` 完成单项功能并自测。
- 合并到 `staging` 做回归与模拟盘验证。
- 验收通过后合并到 `main` 并打标签。

## 3. 发布标记规范
- 标签格式：`v<major>.<minor>.<patch>`
- 示例：`v1.3.2`
- 每次发布需包含：
  - 版本号
  - 变更清单（新增/修复/风险）
  - 回滚点（上一个稳定标签）

## 4. 回滚策略
- 代码回滚：`git checkout <tag>`
- 参数回滚：`python param_rollback.py --latest --symbol M2609` 或指定 `--version-id`
- 发布回滚目标：上一个 `main` 稳定标签

## 5. 发布前强制检查
- `python -m unittest discover -s tests -p "test_*.py"`
- `python e2e_regression.py --symbol M2609 --quick --output-dir output_ci --fetch-source csv`
- `python run.py --mode ctp_health`（接 CTP 时）

## 6. 发布后观察窗口
- 观察 `logs/alerts.log` 的 ERROR/WARN 事件
- 确认 `state/runtime_state.json` 持续更新
- 核对 `output/performance.json`、`paper_check_report.json` 指标是否异常漂移
