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
    duplicates = int(report.get("duplicates", 0) or 0)
    max_jump_ratio = float(report.get("max_jump_ratio", 0.0) or 0.0)
    coverage_ratio = report.get("coverage_ratio", None)

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

    max_duplicates = cfg.get("max_duplicates")
    if max_duplicates is not None and duplicates > int(max_duplicates):
        errors.append(f"DUPLICATES_EXCEEDED duplicates={duplicates} > max_duplicates={int(max_duplicates)}")

    max_jump = cfg.get("max_jump_ratio")
    if max_jump is not None and max_jump_ratio > float(max_jump):
        errors.append(f"JUMP_RATIO_EXCEEDED max_jump_ratio={max_jump_ratio:.4f} > limit={float(max_jump):.4f}")

    if coverage_ratio is not None:
        try:
            coverage = float(coverage_ratio)
        except Exception:
            coverage = None
        if coverage is not None:
            min_cov = cfg.get("min_coverage_ratio")
            warn_cov = cfg.get("warn_coverage_ratio")
            if min_cov is not None and coverage < float(min_cov):
                errors.append(f"COVERAGE_TOO_LOW coverage_ratio={coverage:.4f} < min_coverage_ratio={float(min_cov):.4f}")
            if warn_cov is not None and coverage < float(warn_cov):
                warnings.append(
                    f"COVERAGE_WARN coverage_ratio={coverage:.4f} < warn_coverage_ratio={float(warn_cov):.4f}"
                )

    return len(errors) == 0, errors, warnings
