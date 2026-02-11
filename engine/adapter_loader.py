import importlib
import os
import sys


def load_adapter(config):
    ctp = config.get("ctp", {})
    adapter_path = ctp.get("adapter_path", "")
    adapter_module = ctp.get("adapter_module", "")
    adapter_class = ctp.get("adapter_class", "CtpAdapter")

    if adapter_path:
        adapter_path = os.path.abspath(adapter_path)
        if os.path.exists(adapter_path):
            sys.path.insert(0, adapter_path)
    if not adapter_module:
        return None

    module = importlib.import_module(adapter_module)
    cls = getattr(module, adapter_class, None)
    if cls is None:
        raise RuntimeError(f"Adapter class not found: {adapter_class}")
    return cls()
