# Quant Backtest & CTP Setup

本项目支持回测、纸面模拟（paper）、批量回测报告、桌面实时监控，并预留了 CTP 接口对接框架。

## 0. 快速开始
回测：
```
python main.py
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

## 2. CTP 对接说明
- 参考 `docs/ctp_checklist.md`

## 3. 常用输出
- `output/performance.json` 回测指标
- `output/equity_curve.csv` 权益曲线
- `output/<symbol>/report.html` 单合约报告

## 4. 回测专用风控开关
```
"backtest": {
  "disable_halt_on_backtest": true
}
```
