import argparse

from engine.param_version_store import ParamVersionStore


def main():
    parser = argparse.ArgumentParser(description="Rollback strategy params to a saved version.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--version-id", default=None, help="target version id")
    parser.add_argument("--latest", action="store_true", help="rollback to latest version for symbol")
    parser.add_argument("--list", action="store_true", help="list recent versions")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    store = ParamVersionStore("state/param_versions.json")

    if args.list:
        versions = store.list_versions(symbol=args.symbol, limit=max(1, int(args.limit)))
        print(f"count={len(versions)}")
        for item in versions:
            print(
                f"{item.get('version_id')} symbol={item.get('symbol')} "
                f"source={item.get('source')} created_at={item.get('created_at')}"
            )
        return

    target_id = args.version_id
    if args.latest and not target_id:
        versions = store.list_versions(symbol=args.symbol, limit=1)
        if not versions:
            raise SystemExit("No version found.")
        target_id = versions[0]["version_id"]

    if not target_id:
        raise SystemExit("Provide --version-id or --latest.")

    target = store.rollback_to(config_path="config.json", version_id=target_id)
    print("Rollback completed")
    print(f"version_id={target.get('version_id')}")
    print(f"symbol={target.get('symbol')}")
    print(f"source={target.get('source')}")
    print(f"created_at={target.get('created_at')}")
    print(f"params={target.get('params')}")


if __name__ == "__main__":
    main()
