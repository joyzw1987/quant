import os
import sys


def prepare_ctp_sdk(sdk_path: str):
    if not sdk_path:
        raise RuntimeError("CTP SDK 路径为空，请在 config.json 配置 ctp.sdk_path")
    sdk_path = os.path.abspath(sdk_path)
    if not os.path.exists(sdk_path):
        raise RuntimeError(f"CTP SDK 路径不存在: {sdk_path}")
    if sdk_path not in sys.path:
        sys.path.insert(0, sdk_path)
    return sdk_path
