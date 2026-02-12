# 数据合规模式说明

## 1. 模式定义
- `research`：个人研究/内部回测模式，默认开启。
- `commercial`：商用模式，要求在 `approved_sources` 中声明已授权数据源。

## 2. 配置项
在 `config.json` 中增加：
```json
"data_policy": {
  "mode": "research",
  "approved_sources": [],
  "commercial_ack": ""
}
```

字段解释：
- `mode`：`research` 或 `commercial`
- `approved_sources`：商用模式允许的数据源标识列表
- `commercial_ack`：商用授权备注（例如合同编号）

## 3. 生效范围
- `data_update.py`
- `data_update_merge.py`
- `run_update_backtest.py`

以上脚本在商用模式下会拦截未授权数据源。
