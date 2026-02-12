# Quant Backtest & CTP Setup

本项目支持回测、纸面模拟（paper）、批量回测报告、桌面实时监控，并预留了 CTP 接口对接框架。

## 0. 快速开始
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

方式 B：统一入口
```
python run.py
```
模拟交易（本地，跑完整策略+风控+撮合）：
```
python run.py --mode sim
```
模拟交易 + 实时界面：
```
python run.py --mode sim_gui --auto-start
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
python single_report.py
```

方式 G：合约仪表盘
```
python dashboard.py
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
python daily_weekly_report.py
```

方式 K：免费分钟数据更新（AKShare）
```
python data_update.py --symbol M2609 --days 20 --out data/M2609.csv
```

方式 K-1：增量合并更新（推荐）
```
python data_update_merge.py --symbol M2609 --out data/M2609.csv
```

方式 K-2：更新数据并回测（一键）
```
python run_update_backtest.py --symbol M2609 --days 20 --out data/M2609.csv
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

方式 M：月度收益/回撤/交易统计
```
python monthly_report.py
```

## 2. CTP 对接说明
- 参考 `docs/ctp_checklist.md`

## 3. 常用输出
- `output/performance.json` 回测指标
- `output/equity_curve.csv` 权益曲线
- `output/<symbol>/report.html` 单合约报告
- `output/walk_forward_<symbol>.csv` 滚动窗口明细
- `output/walk_forward_<symbol>.json` 滚动验证汇总
- `output/monthly_report.csv` 月度收益/回撤/交易统计
- `output/monthly_report.json` 月度汇总

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

## 6. 回测专用风控开关
```
"backtest": {
  "disable_halt_on_backtest": true
}
```
