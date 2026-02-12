def pearson_corr(xs, ys):
    n = min(len(xs), len(ys))
    if n <= 1:
        return 0.0
    x = [float(v) for v in xs[-n:]]
    y = [float(v) for v in ys[-n:]]
    mx = sum(x) / n
    my = sum(y) / n
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    vx = sum((v - mx) ** 2 for v in x)
    vy = sum((v - my) ** 2 for v in y)
    if vx <= 0 or vy <= 0:
        return 0.0
    return cov / ((vx ** 0.5) * (vy ** 0.5))


def build_corr_matrix(return_map):
    symbols = list(return_map.keys())
    matrix = {}
    for s1 in symbols:
        matrix[s1] = {}
        for s2 in symbols:
            if s1 == s2:
                matrix[s1][s2] = 1.0
            elif s2 in matrix and s1 in matrix[s2]:
                matrix[s1][s2] = matrix[s2][s1]
            else:
                matrix[s1][s2] = pearson_corr(return_map.get(s1, []), return_map.get(s2, []))
    return matrix


def allocate_weights(symbols, corr_matrix, max_corr=0.8):
    weights, selected, _ = allocate_weights_with_method(
        symbols=symbols,
        corr_matrix=corr_matrix,
        return_map=None,
        max_corr=max_corr,
        weight_method="equal",
    )
    return weights, selected


def _filter_by_corr(symbols, corr_matrix, max_corr=0.8):
    selected = []
    for sym in symbols:
        blocked = False
        for kept in selected:
            corr = corr_matrix.get(sym, {}).get(kept, 0.0)
            if corr > max_corr:
                blocked = True
                break
        if not blocked:
            selected.append(sym)
    return selected


def _std(values):
    n = len(values)
    if n <= 1:
        return 0.0
    m = sum(values) / n
    v = sum((x - m) ** 2 for x in values) / n
    return v ** 0.5


def _weights_equal(symbols, selected):
    if not selected:
        return {sym: 0.0 for sym in symbols}
    w = 1.0 / len(selected)
    return {sym: (w if sym in selected else 0.0) for sym in symbols}


def _weights_risk_budget(symbols, selected, return_map):
    if not selected:
        return {sym: 0.0 for sym in symbols}, {}

    inv_vol_map = {}
    vol_map = {}
    for sym in selected:
        series = [float(v) for v in (return_map or {}).get(sym, [])]
        vol = _std(series)
        if vol <= 1e-8:
            vol = 1e-8
        vol_map[sym] = vol
        inv_vol_map[sym] = 1.0 / vol

    total = sum(inv_vol_map.values())
    if total <= 0:
        return _weights_equal(symbols, selected), vol_map

    weights = {}
    for sym in symbols:
        if sym in inv_vol_map:
            weights[sym] = inv_vol_map[sym] / total
        else:
            weights[sym] = 0.0
    return weights, vol_map


def allocate_weights_with_method(symbols, corr_matrix, return_map=None, max_corr=0.8, weight_method="equal"):
    selected = _filter_by_corr(symbols, corr_matrix, max_corr=max_corr)
    if not selected:
        selected = list(symbols)

    method = str(weight_method or "equal").lower()
    if method == "risk_budget":
        weights, vol_map = _weights_risk_budget(symbols, selected, return_map or {})
        return weights, selected, {"method": "risk_budget", "volatility": vol_map}

    weights = _weights_equal(symbols, selected)
    return weights, selected, {"method": "equal", "volatility": {}}
