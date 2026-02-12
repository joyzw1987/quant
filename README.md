# Quant Backtest & CTP Setup

本项目支持回测、纸面模拟（paper）、批量回测报告、桌面实时监控，并预留了 CTP 接口对接框架。

## 0. 快速开始
初始化环境（Windows PowerShell）：
```
powershell -ExecutionPolicy Bypass -File scripts/setup_env.ps1
```

回测：
```
python main.py
```

回测 + 图形界面（集成入口）：
```
python main.py --gui
```

一键更新数据并回测：
```
python run_update_backtest.py --symbol M2609 --days 20 --out data/M2609.csv
```

## 1. 运行方式
方式 A：直接 CTP 启动
```
python ctp_runner.py
```

方式 A-0：CTP 配置自检（不连接）
```
python ctp_prepare.py
```

方式 A-1：CTP 健康检查（最小连通性）
```
python run.py --mode ctp_health
```

方式 B：统一入口
```
python run.py
```
组合回测：
```
python run.py --mode portfolio
```
一键全流程（批量回测 + 报告 + 组合 + 仪表盘）：
```
python run.py --mode all
```
Paper 一致性校验：
```
python run.py --mode paper_check
```
端到端回归（快速模式）：
```
python run.py --mode e2e --symbol M2609
```
模拟交易（本地，跑完整策略+风控+撮合）：
```
python run.py --mode sim
```
模拟交易 + 实时界面：
```
python run.py --mode sim_gui --auto-start
```
界面 + 自动启动实时模拟（推荐）：
```
python run.py --mode sim_gui --auto-start-live
```
准实时轮询模拟（自动抓取增量数据 + 自动回测循环）：
```
python run.py --mode sim_live --source akshare --interval-sec 60
```
默认会按 `config.json` 的 `market_hours` 自动启停（非交易时段自动等待，下个开盘自动恢复）。

准实时轮询模拟 + 自动修正策略：
```
python run.py --mode sim_live --source akshare --interval-sec 60 --auto-adjust --adjust-every-cycles 5
```
说明：自动修正默认带“变差回滚”保护，若新参数导致本轮结果差于基线，会自动恢复上一版参数并重跑。

若你需要忽略交易时段（24h连续跑）：
```
python run.py --mode sim_live --source akshare --interval-sec 60 --ignore-market-hours
```

研究周期自动化（重建样本 + 严格样本外验证 + 回测）：
```
python run.py --mode research_cycle
```
说明：默认包含样本覆盖门槛（`research_cycle.min_dataset_days`），当历史交易日不足时会阻断参数更新并写报告。

方式 C：批量回测（多合约）
```
python batch_runner.py
```

方式 D：批量回测曲线图
```
python batch_plot.py
```

方式 E：批量回测 HTML 汇总
```
python batch_html.py
```

方式 F：单合约 HTML 报告
```
python single_report.py --output-dir output
```

方式 G：合约仪表盘
```
python dashboard.py --output-dir output
```

方式 H：桌面实时监控界面（Tkinter）
```
python dashboard_gui.py
```
说明：界面中可选择 `数据源/source` 并点击 `抓取数据`（受 `data_policy` 白名单约束），再点击 `运行回测` 实时查看行情、资金和交易。

方式 I：报告索引页
```
python index_page.py
```

方式 J：日报/周报
```
python daily_weekly_report.py --output-dir output
```
输出：`output/daily_report.txt`、`output/weekly_report.csv`、`output/weekly_report.json`

方式 K：免费分钟数据更新（AKShare）
```
python data_update.py --symbol M2609 --days 20 --out data/M2609.csv
```
说明：默认会把抓取到的原始分钟数据同步归档到 `E:/quantData`，按“年目录/月份目录/交易日目录 + 交易时段文件”保存。

方式 K-1：增量合并更新（推荐）
```
python data_update_merge.py --symbol M2609 --out data/M2609.csv
```

方式 K-2：更新数据并回测（一键）
```
python run_update_backtest.py --symbol M2609 --days 20 --out data/M2609.csv
```

方式 K-3：从归档目录重建长样本（建议每周执行）
```
python build_dataset_from_archive.py --symbol M2609 --out data/M2609.csv --max-days 120
```
可输出构建报告：
```
python build_dataset_from_archive.py --symbol M2609 --out data/M2609.csv --max-days 120 --report-out output/dataset_build_report.json
```

方式 L：Walk-Forward 滚动验证（防过拟合）
```
python walk_forward_runner.py --symbol M2609 --train-size 480 --test-size 120 --step-size 120
```

方式 L-1：Walk-Forward 自动调参并写回配置
```
python walk_forward_tune.py --symbol M2609 --train-size 480 --test-size 120 --step-size 120
```
说明：当 `strategy.name` 为 `rsi_ma` 时，脚本会按 `rsi_ma` 真实信号逻辑评估 `fast/slow`，不再使用纯均线近似评分。

方式 L-2：严格样本外验证（训练段选参 + 留出段验收）
```
python strict_oos_validate.py --symbol M2609 --holdout-bars 240 --max-candidates 400
```
若留出段优于基线且满足生效门槛并自动写回参数：
```
python strict_oos_validate.py --symbol M2609 --holdout-bars 240 --max-candidates 400 --min-holdout-trades 4 --min-score-improve 0 --apply-best
```

方式 L-3：一键研究周期（推荐定时）
```
python research_cycle.py --symbol M2609 --max-days 120 --holdout-bars 240 --max-candidates 400 --min-holdout-trades 4 --min-score-improve 0 --require-positive-holdout
```

方式 L-4：参数版本查看/回滚
```
python param_rollback.py --list --symbol M2609 --limit 20
python param_rollback.py --version-id <version_id>
python param_rollback.py --latest --symbol M2609
```

方式 N：Windows 定时任务（自动抓数 + 自动研究周期）
```
python schedule_tasks.py --action show
python schedule_tasks.py --action install
python schedule_tasks.py --action status
python schedule_tasks.py --action uninstall
```

方式 M：月度收益/回撤/交易统计
```
python monthly_report.py --output-dir output
```

方式 M-1：参数稳定性热力图（fast/slow）
```
python param_heatmap.py --symbol M2609 --fast-min 3 --fast-max 12 --slow-min 10 --slow-max 80 --slow-step 2
```

方式 O：多合约组合回测（相关性约束 + 权重分配 + 可选再平衡）
```
python portfolio_runner.py
```
说明：支持 `portfolio.weight_method=equal/risk_budget`，以及 `portfolio.rebalance=none/weekly/monthly`。

方式 P：Paper 一致性校验（成交与PnL约束）
```
python paper_consistency_check.py --trades output/trades.csv
```

方式 Q：端到端回归（OOS -> 回测 -> 报告）
```
python e2e_regression.py --symbol M2609 --quick --output-dir output
```
说明：若 `data/<symbol>.csv` 缺失，会自动生成一份可复现实验数据；若希望强制要求已有数据，增加 `--require-existing-data`。

## 2. CTP 对接说明
- 参考 `docs/ctp_checklist.md`

## 3. 常用输出
- `output/performance.json` 回测指标
- `output/equity_curve.csv` 权益曲线
- `output/<symbol>/report.html` 单合约报告
- `output/walk_forward_<symbol>.csv` 滚动窗口明细
- `output/walk_forward_<symbol>.json` 滚动验证汇总
- `output/strict_oos_report.json` 严格样本外验证报告
- `output/strategy_optimization.json` 参数优化报告
- `output/research_cycle_summary.json` 一键研究周期摘要
- `output/dataset_build_report.json` 样本构建覆盖报告
- `state/param_versions.json` 参数版本历史
- `output/monthly_report.csv` 月度收益/回撤/交易统计
- `output/monthly_report.json` 月度汇总
- `output/weekly_report.csv` 周度收益/回撤/交易统计
- `output/weekly_report.json` 周度汇总
- `output/param_heatmap_<symbol>.csv` 参数稳定性热力图数据
- `output/param_heatmap_<symbol>.html` 参数稳定性热力图页面
- `output/portfolio/portfolio_summary.json` 组合回测汇总
  - 包含 `blocked_by_corr` 字段，记录因相关性上限被剔除的品种明细
- `output/portfolio/portfolio_equity.csv` 组合权益曲线
- `output/portfolio/portfolio_weight_events.json` 组合权重变更记录
- `output/paper_check_report.json` Paper 一致性检查报告
- `E:/quantData/<YYYY>/<MM>/<YYYY-MM-DD>/<symbol>_sN_HHMM_HHMM.csv` 原始分钟数据（交易时段分桶）
- `E:/quantData/<YYYY>/<MM>/<YYYY-MM-DD>/<symbol>_other.csv` 不在配置时段内的数据

## 4. 数据前置要求
- 运行 `main.py`、`walk_forward_runner.py` 前，需先准备 `data/<symbol>.csv` 分钟线数据。
- 示例命令：
```
python data_update.py --symbol M2609 --days 20 --out data/M2609.csv
```

## 5. 数据合规模式
- `research`：个人研究/内部回测模式（默认）。
- `commercial`：商用模式，只允许 `data_policy.approved_sources` 中列出的数据源。

配置示例（`config.json`）：
```json
"data_policy": {
  "mode": "research",
  "approved_sources": [],
  "commercial_ack": ""
}
```

商用模式示例：
```json
"data_policy": {
  "mode": "commercial",
  "approved_sources": ["licensed_vendor"],
  "commercial_ack": "contract_id: ABC-2026-001"
}
```

说明：
- `data_update.py`、`data_update_merge.py`、`run_update_backtest.py` 已接入该策略。
- 当前抓取脚本默认数据源参数：`--source akshare`。
- 原始数据目录在 `config.json -> data_storage` 中配置：
```json
"data_storage": {
  "save_raw": true,
  "raw_root": "E:/quantData"
}
```

研究周期配置（`config.json`）：
```json
"research_cycle": {
  "enabled": false,
  "max_days": 120,
  "min_dataset_days": 60,
  "holdout_bars": 240,
  "max_candidates": 400,
  "dd_penalty": 0.4,
  "min_trades": 4,
  "min_holdout_trades": 4,
  "min_score_improve": 0.0,
  "require_positive_holdout": false,
  "apply_best": true,
  "run_backtest_after": true
}
```

定时任务配置：
```json
"scheduler": {
  "enabled": false,
  "task_prefix": "Quant_M2609",
  "days": "MON,TUE,WED,THU,FRI",
  "source": "akshare",
  "fetch_times": ["11:35", "15:05", "23:05"],
  "research_time": "23:20"
}
```

交易日历高级配置（临时休市 / 特殊开市时段）：
```json
"market_hours": {
  "sessions": [
    {"start": "09:00", "end": "11:30"},
    {"start": "13:30", "end": "15:00"},
    {"start": "21:00", "end": "23:00"}
  ],
  "weekdays": [1, 2, 3, 4, 5],
  "holidays": {
    "dates": [],
    "file": "data/holidays.txt"
  },
  "special_closures": [
    {"date": "2026-10-10", "start": "09:00", "end": "10:00", "reason": "临时停盘"},
    {"date": "2026-10-11", "reason": "全日休市"}
  ],
  "special_sessions": [
    {"date": "2026-10-12", "start": "10:00", "end": "10:30", "reason": "补开盘"}
  ]
}
```

成本模型（按时段区分滑点/手续费倍率/成交率）：
```json
"cost_model": {
  "profiles": [
    {
      "name": "day",
      "start": "09:00",
      "end": "15:00",
      "slippage": 1.0,
      "commission_multiplier": 1.0,
      "fill_ratio_min": 0.95,
      "fill_ratio_max": 1.0
    },
    {
      "name": "night",
      "start": "21:00",
      "end": "23:00",
      "slippage": 1.5,
      "commission_multiplier": 1.1,
      "fill_ratio_min": 0.9,
      "fill_ratio_max": 1.0
    }
  ]
}
```
说明：配置校验会对时段重叠给出警告，避免多个 profile 相互覆盖造成回测偏差。

数据质量闸门（可阻断低质量样本）：
```json
"data_quality": {
  "enabled": true,
  "min_rows": 200,
  "max_missing_bars": null,
  "max_missing_ratio": null,
  "warn_missing_ratio": 0.2
}
```

Paper 一致性校验（回测结束自动执行）：
```json
"paper_check": {
  "enabled": true,
  "strict": false
}
```

监控告警（统一通道：日志 + 可选 webhook）：
```json
"monitor": {
  "alert_file": "logs/alerts.log",
  "webhook_url": "",
  "drawdown_alert_threshold": 8000,
  "no_new_data_error_threshold": 3
}
```

组合回测配置：
```json
"portfolio": {
  "enabled": false,
  "symbols": ["M2609"],
  "max_corr": 0.8,
  "weight_method": "equal",
  "rebalance": "none",
  "min_rebalance_bars": 100,
  "output_dir": "output/portfolio"
}
```

## 6. 回测专用风控开关
```
"backtest": {
  "disable_halt_on_backtest": true
}
```
