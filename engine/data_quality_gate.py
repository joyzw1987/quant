def evaluate_data_quality(report, cfg):
    """
    Return: (ok: bool, errors: list[str], warnings: list[str])
    """
    cfg = cfg or {}
    if not cfg.get("enabled", True):
        return True, [], []

    errors = []
    warnings = []
    total = int(report.get("total", 0) or 0)
    missing = int(report.get("missing", 0) or 0)

    min_rows = cfg.get("min_rows")
    if min_rows is not None and total < int(min_rows):
        errors.append(f"DATA_TOO_SHORT total={total} < min_rows={int(min_rows)}")

    max_missing_bars = cfg.get("max_missing_bars")
    if max_missing_bars is not None and missing > int(max_missing_bars):
        errors.append(f"MISSING_BARS_EXCEEDED missing={missing} > max_missing_bars={int(max_missing_bars)}")

    max_missing_ratio = cfg.get("max_missing_ratio")
    if max_missing_ratio is not None and total > 0:
        ratio = float(missing) / float(total)
        if ratio > float(max_missing_ratio):
            errors.append(
                f"MISSING_RATIO_EXCEEDED ratio={ratio:.4f} > max_missing_ratio={float(max_missing_ratio):.4f}"
            )

    warn_missing_ratio = cfg.get("warn_missing_ratio")
    if warn_missing_ratio is not None and total > 0:
        ratio = float(missing) / float(total)
        if ratio > float(warn_missing_ratio):
            warnings.append(
                f"MISSING_RATIO_WARN ratio={ratio:.4f} > warn_missing_ratio={float(warn_missing_ratio):.4f}"
            )

    return len(errors) == 0, errors, warnings
