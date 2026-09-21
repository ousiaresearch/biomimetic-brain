#!/usr/bin/env python3
"""Self-test for the Ousia Mind Kit: proves the kit runs standalone, on a neutral agent.

Builds a throwaway agent directory from the shipped examples, generates the aggregate with the
shipped generator, and checks the result actually carries what the docs promise. Run it before
trusting the kit:

    python3 scripts/self_test.py

Two of these checks exist because the kit shipped without them. Check 7 runs the README's own
install block, because a test that seeds the tree its own way cannot see an install loop that seeds
it somewhere else. Check 8 verifies the published checksum manifest, because an integrity claim
nothing executes is a claim, not a guarantee.
"""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
# Add the name of the tree you lifted this kit out of; the release scan is this same check over
# every shipped file. Empty by default, because a neutral kit has nothing to hide.
SELF_NAMES: list[str] = []
results: list[tuple[bool, str]] = []

# The two lines of the README install block that cannot run verbatim inside this test.
_MIND_DIR_LINE = re.compile(r"^\s*export\s+MIND_AGENT_DIR=.*$", re.M)
_SELFTEST_LINE = re.compile(r"^\s*python3\s+scripts/self_test\.py.*$", re.M)


def documented_install_block() -> str | None:
    """The bash block a stranger copies out of README's "Install in five minutes".

    The placeholder agent path is dropped so the caller's ``$MIND_AGENT_DIR`` wins, and the recursive
    ``python3 scripts/self_test.py`` line is dropped because this test would otherwise call itself.
    Everything else — including the seeding loop — runs exactly as published.
    """
    readme = (KIT / "README.md").read_text()
    m = re.search(r"^##\s*Install in five minutes\s*$.*?```bash\n(.*?)```", readme, re.S | re.M)
    if not m:
        return None
    return _SELFTEST_LINE.sub("", _MIND_DIR_LINE.sub("", m.group(1)))


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


def manifest_failures() -> tuple[int, list[str]]:
    """Verify every entry in the shipped ``SHA256SUMS`` against the files on disk.

    ``SHA256SUMS`` is deliberately not listed inside itself: a file cannot contain its own digest, and
    the entry that used to be there could never verify. Returns ``(checked, problems)``.
    """
    lines = [l.split(None, 1) for l in (KIT / "SHA256SUMS").read_text().splitlines() if l.strip()]
    checked, problems = 0, []
    for want, rel in lines:
        rel = rel.strip()
        if rel == "SHA256SUMS":
            problems.append("SHA256SUMS lists itself (a file cannot contain its own digest)")
            continue
        path = KIT / rel
        if not path.is_file():
            problems.append(f"{rel} (missing)")
            continue
        checked += 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != want:
            problems.append(f"{rel} (digest mismatch)")
    return checked, problems


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

        # 7. THE DOCUMENTED PATH, EXECUTED. Regression guard for the defect shipped in 6b4bed3: the
        #    shell seeding loop in README/SETUP-GUIDE stripped the `brain/` component that this
        #    test's own loop keeps, so a stranger following the docs got 0/25 healthy while the kit's
        #    self-test stayed green. A test that seeds the tree its own way cannot see that.
        snippet = documented_install_block()
        check(snippet is not None, "README carries a runnable bash install block")
        if snippet:
            doc_agent = tmp / "doc-agent"
            proc = subprocess.run(["bash", "-c", snippet], cwd=KIT,
                                  env={**os.environ, "MIND_AGENT_DIR": str(doc_agent)},
                                  capture_output=True, text=True, timeout=300)
            doc_agg = doc_agent / "brain-state.json"
            health2 = json.loads(doc_agg.read_text()).get("health_summary", {}) if doc_agg.exists() else {}
            check(health2.get("healthy") == health2.get("total") == 25,
                  "the README's own install block yields "
                  f"{health2.get('healthy')}/{health2.get('total')} healthy (rc={proc.returncode})")

        # 8. the published integrity manifest verifies against the tree
        checked, problems = manifest_failures()
        check(not problems,
              f"SHA256SUMS verifies ({checked}/{checked + len(problems)} entries)"
              + (f" — {problems[:3]}" if problems else ""))

        # 9. an absent subsystem is missing, never stale. Guards issue #3: 18 of the 25 status sites
        #    had no existence test, so a file that was never installed read as `stale` — which the
        #    docs gloss as "gone quiet", implying present. A botched install then presented as a
        #    partially-live brain, and VALIDATION.md's own manual check (delete a file -> it reports
        #    `missing`) held for 7 of 25.
        empty = tmp / "empty-agent"
        (empty / "brain").mkdir(parents=True)
        subprocess.run([sys.executable, str(KIT / "scripts/generate-brain-state.py")],
                       env={**os.environ, "MIND_AGENT_DIR": str(empty)},
                       capture_output=True, text=True, timeout=120)
        empty_agg = empty / "brain-state.json"
        eh = json.loads(empty_agg.read_text()).get("health_summary", {}) if empty_agg.exists() else {}
        check(eh.get("missing") == eh.get("total") == 25 and not eh.get("stale") and not eh.get("healthy"),
              "an unseeded agent reports every subsystem missing, none stale "
              f"(healthy={eh.get('healthy')} stale={eh.get('stale')} missing={eh.get('missing')})")
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
