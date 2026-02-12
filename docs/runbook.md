# 运行手册（Runbook）

## 1. 目标
- 在新机器 30 分钟内跑通：抓数 -> 回测 -> sim_live -> GUI 观察。
- 出现故障时可按步骤快速恢复，不依赖人工记忆。

## 2. 启动前检查
- Python 3.10+（建议与 CI 一致）。
- 安装依赖：`pip install -r requirements.txt`
- 配置文件：`config.json`
- 数据目录可写：`data/`、`output/`、`logs/`、`state/`
- 原始归档目录可写：`E:/quantData`

## 3. 标准启动流程
- 拉取最新代码：`git pull`
- 快速回归：`python -m unittest discover -s tests -p "test_*.py"`
- 抓数（离线回放可用 csv，在线可用 akshare）：
  - `python data_update.py --symbol M2609 --days 20 --out data/M2609.csv --source csv`
- 回测：
  - `python main.py --symbol M2609`
- 准实时模拟：
  - `python run.py --mode sim_live --symbol M2609 --source csv --interval-sec 60`
- GUI 观察：
  - `python run.py --mode sim_gui --auto-start-live`

## 4. 停止流程
- 前台运行：`Ctrl + C`
- GUI 模式：点击“停止模拟盘”，并确认状态由“运行中”变为“已停止”
- 若使用计划任务：`python schedule_tasks.py --action status` 后再 `--action uninstall`

## 5. 故障恢复
- 抓数失败：
  - 检查 `logs/alerts.log` 的 `sim_live_fetch_failed`
  - 改用 `--source csv` 验证流程是否恢复
- 无新数据：
  - 检查 `sim_live_no_new_data` 连续计数和告警级别
  - 核对 `data/<symbol>.csv` 最后一条时间
- 保护模式触发（CTP）：
  - 查看 `state/ctp_state.json` 的 `protection_mode`、`position_diffs`、`account_diffs`
  - 先排查对账差异，再恢复交易
- 参数异常回滚：
  - 查看 `sim_live_tune_rollback` 事件
  - 使用 `python param_rollback.py --latest --symbol M2609`

## 6. 日志与状态文件
- 运行日志：`logs/runtime.log`
- 告警日志：`logs/alerts.log`
- 实时状态：`state/runtime_state.json`
- CTP 状态：`state/ctp_state.json`
- 参数版本：`state/param_versions.json`
- 报告目录：`output/`、`output_ci/`

## 7. 值班检查清单
- 最近 1 小时是否有 `ERROR` 级告警。
- `runtime_state.json` 是否持续更新时间。
- `sim_live_no_new_data` 是否持续增长。
- `max_drawdown` 是否接近阈值。
- `paper_check_ok` 是否为 `true`。
