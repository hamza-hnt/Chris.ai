from pathlib import Path
import sys


def keys(path: Path) -> set[str]:
    found = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        found.add(line.split("=", 1)[0].strip())
    return found


def main() -> int:
    example = Path(".env.example")
    local = Path(".env")
    if not local.exists():
        print("Missing .env. Create it with: cp .env.example .env", file=sys.stderr)
        return 1

    expected = keys(example)
    actual = keys(local)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        if missing:
            print("Missing keys in .env: " + ", ".join(missing), file=sys.stderr)
        if extra:
            print("Unexpected keys in .env: " + ", ".join(extra), file=sys.stderr)
        return 1

    print(".env matches .env.example keys")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
