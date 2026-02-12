def build_cost_model(config):
    contract = config.get("contract", {})
    model = config.get("cost_model") or {}
    profiles = model.get("profiles") or []
    normalized = []
    for item in profiles:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "name": item.get("name", "profile"),
                "start": item.get("start", ""),
                "end": item.get("end", ""),
                "slippage": item.get("slippage", contract.get("slippage", 0.0)),
                "commission_multiplier": item.get("commission_multiplier", 1.0),
                "fill_ratio_min": item.get("fill_ratio_min", contract.get("fill_ratio_min", 1.0)),
                "fill_ratio_max": item.get("fill_ratio_max", contract.get("fill_ratio_max", 1.0)),
            }
        )
    return {"profiles": normalized}
