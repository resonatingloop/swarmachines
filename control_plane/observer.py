"""Observe task claims and GitHub facts without dispatching or changing either."""

import argparse
import hashlib
import html
import json
import re
import subprocess
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

MAX_BYTES = 2_000_000
PR_LIMIT = 200
ROW = re.compile(
    r"^- \[(open|doing|blocked|done)\] (T-\d+|swarmachines-[\w-]+): "
    r"(.+?) — owner: (.+?)(?: — updated: (\S+))?$"
)
STATES = ("blocked", "doing", "open", "done")


def now():
    """Return a UTC observation timestamp."""
    return datetime.now(UTC).isoformat()


def display(value):
    """Escape markup and make invisible format/control characters visible."""
    text = str(value)
    visible = "".join(
        f"\\u{ord(c):04x}" if unicodedata.category(c) in {"Cf", "Cc"} else c
        for c in text
    )
    return html.escape(visible, quote=True)


def parse_ledger(text):
    """Parse supported task rows while retaining explicit coverage diagnostics.

    Args:
        text: UTF-8 ledger text obtained from a pinned git object.

    Returns:
        A pair of task dictionaries and diagnostic strings. Duplicate ids are
        excluded rather than silently selecting one author's claim.
    """
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("ledger exceeds size limit")
    tasks, issues = [], []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("- ["):
            continue
        match = ROW.fullmatch(line)
        if not match:
            issues.append(
                f"ledger line {line_number}: unsupported task row; not counted"
            )
            continue
        state, task_id, title, owner, updated = match.groups()
        if updated:
            try:
                date = datetime.fromisoformat(updated)
                if date.tzinfo is None:
                    raise ValueError()
            except ValueError:
                issues.append(f"{task_id}: invalid update timestamp; freshness unknown")
                updated = None
        if not updated:
            issues.append(f"{task_id}: update time unknown")
        tasks.append(
            {
                "id": task_id,
                "reported_state": state,
                "title": title,
                "owner": owner,
                "updated_at": updated,
                "source_line": line_number,
                "pr_mentions": sorted(
                    {
                        int(n)
                        for n in re.findall(r"\bPR\s*#(\d+)\b", title, re.IGNORECASE)
                    }
                ),
            }
        )
    counts = Counter(task["id"] for task in tasks)
    for task_id, count in counts.items():
        if count > 1:
            issues.append(f"{task_id}: {count} conflicting/duplicate rows excluded")
    return [task for task in tasks if counts[task["id"]] == 1], issues


def validate_prs(value):
    """Accept only the small GitHub metadata shape consumed by this observer."""
    if not isinstance(value, list) or len(value) > PR_LIMIT:
        raise ValueError("invalid PR collection")
    seen = set()
    fields = ("number", "title", "state", "headRefOid", "updatedAt")
    result = []
    for row in value:
        if not isinstance(row, dict) or any(key not in row for key in fields):
            raise ValueError("invalid PR metadata")
        number = row["number"]
        if type(number) is not int or number <= 0 or number in seen:
            raise ValueError("invalid or duplicate PR number")
        if row["state"] not in {"OPEN", "CLOSED", "MERGED"}:
            raise ValueError("invalid PR state")
        if not all(isinstance(row[key], str) for key in fields[1:]):
            raise ValueError("invalid PR field type")
        if not re.fullmatch(r"[0-9a-f]{40}", row["headRefOid"]):
            raise ValueError("invalid PR head")
        if len(row["title"]) > 4096:
            raise ValueError("PR title exceeds size limit")
        date = datetime.fromisoformat(row["updatedAt"])
        if date.tzinfo is None:
            raise ValueError("PR timestamp lacks timezone")
        seen.add(number)
        result.append({key: row[key] for key in fields})
    return result


def command(args, cwd):
    """Run a fixed read-only command, suppressing credential-bearing errors.

    Args:
        args: Argument vector; never passed through a shell.
        cwd: Explicit repository directory.

    Returns:
        Bounded UTF-8 standard output.

    Raises:
        ValueError: The command failed, timed out, or returned excessive output.
    """
    try:
        result = subprocess.run(
            args, cwd=cwd, capture_output=True, timeout=30, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("source command unavailable or timed out") from exc
    if result.returncode or len(result.stdout) > MAX_BYTES:
        raise ValueError("source command failed or exceeded output limit")
    return result.stdout.decode("utf-8")


def collect(repo, github_repo, ledger_ref, worker_state_dir=None):
    """Collect independent source snapshots; unavailable never means empty."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", github_repo):
        raise ValueError("use an owner/repository identifier")
    if not re.fullmatch(r"[\w./-]+", ledger_ref) or ledger_ref.startswith("-"):
        raise ValueError("invalid ledger ref")
    snapshot = {
        "schema_version": 2,
        "observed_at": now(),
        "github_repo": github_repo,
        "tasks": [],
        "prs": [],
        "sources": {},
        "diagnostics": [],
    }
    try:
        revision = command(
            ["git", "rev-parse", "--verify", ledger_ref + "^{commit}"], repo
        ).strip()
        if not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ValueError("invalid git revision")
        raw = command(["git", "show", f"{revision}:TASKS.md"], repo)
        tasks, diagnostics = parse_ledger(raw)
        snapshot["tasks"] = tasks
        snapshot["diagnostics"].extend(diagnostics)
        snapshot["sources"]["ledger"] = {
            "status": "available",
            "revision": revision,
            "ref": ledger_ref,
            "sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "read_at": now(),
            "freshness": "local git ref; no remote freshness claim",
        }
    except (ValueError, UnicodeError):
        snapshot["sources"]["ledger"] = {"status": "unavailable", "read_at": now()}
        snapshot["diagnostics"].append("ledger unavailable; task count is unknown")
    try:
        raw = command(
            [
                "gh",
                "pr",
                "list",
                "--repo",
                github_repo,
                "--state",
                "all",
                "--limit",
                str(PR_LIMIT),
                "--json",
                "number,title,state,headRefOid,updatedAt",
            ],
            repo,
        )
        snapshot["prs"] = validate_prs(json.loads(raw))
        snapshot["sources"]["github"] = {
            "status": "available",
            "read_at": now(),
            "coverage": "possibly truncated"
            if len(snapshot["prs"]) == PR_LIMIT
            else "returned collection",
            "limit": PR_LIMIT,
            "sha256": hashlib.sha256(raw.encode()).hexdigest(),
        }
        if len(snapshot["prs"]) == PR_LIMIT:
            snapshot["diagnostics"].append(
                "PR query reached its limit; missing PRs are unknown"
            )
    except (ValueError, UnicodeError):
        snapshot["sources"]["github"] = {"status": "unavailable", "read_at": now()}
        snapshot["diagnostics"].append("github unavailable; PR state is unknown")
    prs = {pr["number"]: pr for pr in snapshot["prs"]}
    for task in snapshot["tasks"]:
        for number in task["pr_mentions"]:
            pr = prs.get(number)
            if not pr:
                snapshot["diagnostics"].append(
                    f"{task['id']}: PR #{number} not observed; state unknown"
                )
            elif task["reported_state"] != "done" and pr["state"] == "MERGED":
                snapshot["diagnostics"].append(
                    f"{task['id']}: nonterminal task mentions merged PR #{number}; reconcile scope, do not auto-close"
                )
    snapshot["workers"] = worker_reader(worker_state_dir)
    return snapshot


def worker_reader(directory=None):
    """Import the standalone reader without constructing the writable queue."""
    if __package__:
        from .worker_projection import collect_workers
    else:
        from worker_projection import collect_workers
    return collect_workers(directory)


def render_workers(workers):
    """Render only the validated worker projection, separate from ledger claims."""

    def fields(values):
        return (
            "<dl>"
            + "".join(
                f"<dt>{display(key.replace('_', ' '))}</dt><dd>{display('unknown' if value is None else value)}</dd>"
                for key, value in values.items()
            )
            + "</dl>"
        )

    status = workers.get("status", "not supplied")
    body = f"<p class='id'>worker source · {display(status)}</p>"
    body += fields({"read_at": workers.get("read_at"), "source": "local worker queue"})
    if workers.get("budget"):
        body += (
            "<div class='sources'><article><h3>local reservations</h3>"
            + fields(workers["budget"])
            + "</article>"
        )
        body += (
            "<article><h3>known-usage estimate · not a bill</h3>"
            + fields(workers["accounting"])
            + "</article></div>"
        )
    body += (
        "<ul>"
        + "".join(
            f"<li>{display(item)}</li>" for item in workers.get("diagnostics", [])
        )
        + "</ul>"
    )
    attempts = workers.get("attempts", [])
    if status == "available" and not attempts:
        body += "<p>no valid worker attempts observed; inspect diagnostics before treating this as empty.</p>"
    for attempt in attempts:
        body += (
            "<details class='worker-attempt'><summary>"
            + display(f"{attempt['task_id']} · {attempt['mode']} · {attempt['state']}")
            + "</summary>"
            + fields(attempt)
            + "</details>"
        )
    return body


def render(snapshot):
    """Render source text only as escaped text in a script-free local board."""
    if snapshot.get("schema_version") not in (1, 2):
        raise ValueError("unsupported snapshot version")
    template = Path(__file__).with_name("board.html").read_text()
    sources = "".join(
        f"<article><h3>{display(name)}</h3><dl>"
        + "".join(
            f"<dt>{display(key)}</dt><dd>{display(value)}</dd>"
            for key, value in source.items()
        )
        + "</dl></article>"
        for name, source in snapshot["sources"].items()
    )
    warnings = "".join(f"<li>{display(item)}</li>" for item in snapshot["diagnostics"])
    warnings = (
        warnings
        or "<li>no reconciliation hints detected; review gates are not evaluated.</li>"
    )
    lanes = []
    for state in STATES:
        tasks = [task for task in snapshot["tasks"] if task["reported_state"] == state]
        cards = "".join(
            f"<article class='task'><p class='id'>{display(task['id'])} · line {task['source_line']}</p>"
            f"<h3>{display(task['title'])}</h3><p>reported owner · {display(task['owner'])}</p>"
            f"<p class='muted'>updated · {display(task['updated_at'] or 'unknown')}</p></article>"
            for task in tasks
        )
        count = (
            str(len(tasks))
            if snapshot["sources"]["ledger"]["status"] == "available"
            else "?"
        )
        lanes.append(
            f"<section class='lane'><h2>{state} <span>{count}</span></h2>"
            + (cards or "<p>no supported rows observed.</p>")
            + "</section>"
        )
    prs = "".join(
        f"<tr><td>#{pr['number']}</td><td>{display(pr['title'])}</td>"
        f"<td>{display(pr['state'].lower())}</td><td><code>{display(pr['headRefOid'])}</code></td>"
        f"<td>{display(pr['updatedAt'])}</td></tr>"
        for pr in snapshot["prs"]
    )
    values = {
        "observed": display(snapshot["observed_at"]),
        "repo": display(snapshot["github_repo"]),
        "sources": sources,
        "warnings": warnings,
        "lanes": "".join(lanes),
        "prs": prs,
        "workers": render_workers(snapshot.get("workers", {"status": "not supplied"})),
    }
    # A single substitution prevents source text from becoming a template token.
    return re.sub(r"@@(\w+)@@", lambda m: values[m.group(1)], template)


def main():
    """Write a new private snapshot directory; never overwrite an earlier capture."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--github-repo", default="resonatingloop/swarmachines")
    parser.add_argument("--ledger-ref", default="origin/ledger")
    parser.add_argument("--worker-state-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    snapshot = collect(
        args.repo, args.github_repo, args.ledger_ref, args.worker_state_dir
    )
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, content in (
        ("snapshot.json", json.dumps(snapshot, indent=2) + "\n"),
        ("index.html", render(snapshot)),
    ):
        target = args.output / name
        with target.open("x", encoding="utf-8") as stream:
            target.chmod(0o600)
            stream.write(content)
    print(
        "observation captured; inspect source availability and diagnostics in index.html"
    )
    return (
        0
        if all(s["status"] == "available" for s in snapshot["sources"].values())
        and snapshot["workers"]["status"] in ("available", "not supplied")
        else 2
    )


if __name__ == "__main__":
    raise SystemExit(main())
