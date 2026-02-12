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

    if not selected:
        selected = list(symbols)
    weight = 1.0 / len(selected) if selected else 0.0
    out = {sym: (weight if sym in selected else 0.0) for sym in symbols}
    return out, selected
