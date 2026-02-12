ALLOWED_DATA_POLICY_MODES = {"research", "commercial"}


def get_data_policy(config):
    policy = dict(config.get("data_policy") or {})
    mode = str(policy.get("mode", "research")).lower()
    approved_sources = policy.get("approved_sources")
    if not isinstance(approved_sources, list):
        approved_sources = []
    approved_sources = [str(x).lower() for x in approved_sources if str(x).strip()]
    policy.setdefault("commercial_ack", "")
    return {
        "mode": mode,
        "approved_sources": approved_sources,
        "commercial_ack": str(policy.get("commercial_ack", "")).strip(),
    }


def validate_data_policy(config):
    errors = []
    warnings = []
    policy = get_data_policy(config)

    if policy["mode"] not in ALLOWED_DATA_POLICY_MODES:
        errors.append("data_policy.mode must be 'research' or 'commercial'.")
        return errors, warnings

    if policy["mode"] == "commercial":
        if not policy["approved_sources"]:
            errors.append("data_policy.approved_sources is required for commercial mode.")
        if not policy["commercial_ack"]:
            warnings.append("data_policy.commercial_ack is empty. Add your contract/license note.")

    return errors, warnings


def assert_source_allowed(config, source):
    policy = get_data_policy(config)
    source_key = str(source).lower()

    if policy["mode"] == "research":
        return

    if source_key not in policy["approved_sources"]:
        approved_text = ", ".join(policy["approved_sources"]) if policy["approved_sources"] else "(none)"
        raise SystemExit(
            f"[DATA_POLICY] blocked source={source_key} in commercial mode. "
            f"approved_sources={approved_text}"
        )
