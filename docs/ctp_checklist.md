# CTP 对接清单（无 SDK 前的准备）

## 向期货公司申请或确认
- 交易权限：是否开通程序化交易（CTP）
- 行情前置地址（MD Front）
- 交易前置地址（TD Front）
- 经纪商代码（Broker ID）
- 资金账号（User ID）
- 密码
- AppID / AuthCode / ProductInfo（部分公司要求）

## 本地运行环境准备
- Python 版本（建议 3.8+）
- 操作系统与位数（CTP SDK 通常区分 32/64 位）
- 依赖动态库（dll/so/dylib）路径配置
- `config.json` 中填入账号/前置地址

## 代码侧已预留入口
- `engine/gateway_ctp.py`：CTP 行情/交易网关骨架
- `ctp_runner.py`：读取配置并连接的示例
- `run.py`：统一入口（`config.json` 的 `run_mode` 控制）
- `ctp_prepare.py`：CTP 配置自检（不连接）

## 获取 SDK 后需要提供
- SDK 文件夹路径或 Python 包名
- 示例回调代码（如有）

## 推荐流程
1. 在 `config.json` 填写 `ctp.*` 配置（`simulate=false`）
2. 运行 `python ctp_prepare.py` 检查配置与 SDK 路径
3. 运行 `python ctp_runner.py` 连接测试
