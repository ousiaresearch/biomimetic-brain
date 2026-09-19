#!/usr/bin/env python3
"""Self-test for the Ousia Mind Kit: proves the kit runs standalone, on a neutral agent.

Builds a throwaway agent directory from the shipped examples, generates the aggregate with the
shipped generator, and checks the result actually carries what the docs promise. Run it before
trusting the kit:

    python3 scripts/self_test.py
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
# Add the name of the tree you lifted this kit out of; the release scan is this same check over
# every shipped file. Empty by default, because a neutral kit has nothing to hide.
SELF_NAMES: list[str] = []
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((bool(ok), label))


def leaked_identity(text: str, names: list[str]) -> str | None:
    """The two failure modes worth asserting on a shipped kit.

    1. an absolute user path from the machine the kit was lifted out of
    2. the agent's own name baked into the artefact rather than configured
    """
    for probe in ("/Users/", "/home/"):
        if probe in text:
            return f"absolute path {probe!r}"
    low = text.lower()
    for name in names:
        if name and name.lower() in low:
            return f"baked-in name {name!r}"
    return None


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="mind-kit-selftest-"))
    agent = tmp / "example-agent"
    (agent / "brain").mkdir(parents=True)
    try:
        # 1. every example drops into place as a live file
        seeded = 0
        for example in sorted((KIT / "brain").rglob("*.example.json")):
            rel = example.relative_to(KIT / "brain")
            dest = agent / "brain" / str(rel).replace(".example.json", ".json")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(example, dest)
            seeded += 1
        check(seeded >= 25, f"seeded {seeded} subsystem files from examples (expect >= 25)")

        # 2. the generator runs against a neutral agent dir and writes the aggregate
        env = {**os.environ, "MIND_AGENT_DIR": str(agent)}
        proc = subprocess.run([sys.executable, str(KIT / "scripts/generate-brain-state.py")],
                              env=env, capture_output=True, text=True, timeout=120)
        agg_path = agent / "brain-state.json"
        check(proc.returncode == 0 and agg_path.exists(),
              f"generator ran and wrote brain-state.json (rc={proc.returncode})")
        if not agg_path.exists():
            print(proc.stdout[-800:], proc.stderr[-800:])
            return report()

        agg = json.loads(agg_path.read_text())

        # 3. the aggregate carries a health summary and per-system blocks
        health = agg.get("health_summary") or {}
        systems = agg.get("systems") or {}
        check(isinstance(health, dict) and health.get("total", 0) >= 20,
              f"health_summary reports a total (got {health.get('total')})")
        check(len(systems) >= 20, f"aggregate carries per-system blocks (got {len(systems)})")

        # 4. staleness is real, not cosmetic
        with_age = [k for k, v in systems.items()
                    if isinstance(v, dict) and "age_h" in v and "max_age_h" in v]
        check(len(with_age) == len(systems),
              f"every system block carries age_h + max_age_h ({len(with_age)}/{len(systems)})")

        # 5. nothing borrowed: no identity residue in the aggregate or the shipped examples
        blob = agg_path.read_text() + "".join(
            p.read_text(errors="replace") for p in (KIT / "brain").rglob("*.example.json"))
        leak = leaked_identity(blob, SELF_NAMES)
        check(leak is None,
              f"generated aggregate carries no identity residue{'' if leak is None else f' ({leak})'}")

        # 6. the agent dir is respected: nothing was written outside it
        check(not (KIT / "brain-state.json").exists(),
              "generator wrote into $MIND_AGENT_DIR, not into the kit")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return report()


def report() -> int:
    failed = [label for ok, label in results if not ok]
    for ok, label in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
