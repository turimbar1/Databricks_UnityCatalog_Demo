#!/usr/bin/env python3
"""Put demo schema drift into the prod catalog so Flyway's drift report has something to show.

  python demo-drift/prod_drift.py reset    wipe prod, migrate it from this checkout (saving a snapshot), add drift
  python demo-drift/prod_drift.py inject   snapshot prod as it is now, then add drift (prod must be clean)
  python demo-drift/prod_drift.py check    run the drift check and write demo-drift/reports/prod-drift.html

Options: --environment prod (any Flyway environment whose catalog starts with demo_), --yes (no prompt),
         --profile <databricks cli profile>.
Needs: Python 3.9+, `pip install databricks-sdk`, the Flyway CLI (Enterprise) on PATH, and Databricks auth
       (DATABRICKS_TOKEN, a `databricks auth login` profile, or Azure CLI). Run from the repo root.
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRIFT_DIR = Path(__file__).resolve().parent
REPORT = DRIFT_DIR / "reports" / "prod-drift.html"
SCHEMA = "default"
SNAPSHOT_NAME = "snapshotHistory:demo-pre-drift"


# ---------------------------------------------------------------- config

def env_url(environment: str) -> str:
    """Read environments.<name>.url from flyway.toml (flyway.user.toml as fallback)."""
    for name in ("flyway.toml", "flyway.user.toml"):
        path = ROOT / name
        if not path.exists():
            continue
        section = None
        for line in path.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^\s*\[([^\]]+)\]\s*$", line)
            if m:
                section = m.group(1).strip()
                continue
            m = re.match(r'^\s*url\s*=\s*"([^"]+)"', line)
            if m and section == f"environments.{environment}":
                return m.group(1)
    sys.exit(f"No url for environment '{environment}' in flyway.toml / flyway.user.toml")


def parse_url(url: str):
    host = re.search(r"jdbc:databricks://([^:/;]+)", url)
    wh = re.search(r"httpPath=/sql/1\.0/warehouses/([A-Za-z0-9]+)", url, re.I)
    cat = re.search(r"ConnCatalog=([A-Za-z0-9_]+)", url, re.I)
    if not (host and wh and cat):
        sys.exit(f"Couldn't read host / warehouse / ConnCatalog from: {url}")
    return host.group(1), wh.group(1), cat.group(1)


# ---------------------------------------------------------------- databricks

class Dbx:
    def __init__(self, host, warehouse_id, catalog, profile=None):
        try:
            from databricks.sdk import WorkspaceClient
            from databricks.sdk.service.sql import StatementState
        except ImportError:
            sys.exit("Install the Databricks SDK first: pip install databricks-sdk")
        self.state = StatementState
        self.w = WorkspaceClient(host=f"https://{host}", profile=profile) if profile else WorkspaceClient(host=f"https://{host}")
        self.warehouse_id, self.catalog = warehouse_id, catalog

    def sql(self, statement, quiet=False):
        if not quiet:
            print(f"  SQL> {' '.join(statement.split())[:160]}", flush=True)
        r = self.w.statement_execution.execute_statement(
            statement=statement, warehouse_id=self.warehouse_id,
            catalog=self.catalog, schema=SCHEMA, wait_timeout="50s")
        while r.status.state in (self.state.PENDING, self.state.RUNNING):
            time.sleep(2)
            r = self.w.statement_execution.get_statement(r.statement_id)
        if r.status.state != self.state.SUCCEEDED:
            raise RuntimeError(r.status.error.message if r.status.error else str(r.status.state))
        return r.result.data_array if r.result and r.result.data_array else []


def q(name):
    return "`" + name.replace("`", "``") + "`"


def wipe_schema(db: Dbx):
    """Drop everything in <catalog>.default: FKs first, then views, then tables (incl. Flyway's history tables)."""
    cat = q(db.catalog)
    fks = db.sql(f"SELECT table_name, constraint_name FROM {cat}.information_schema.table_constraints "
                 f"WHERE table_schema = '{SCHEMA}' AND constraint_type = 'FOREIGN KEY'", quiet=True)
    for table, fk in fks:
        db.sql(f"ALTER TABLE {q(SCHEMA)}.{q(table)} DROP CONSTRAINT IF EXISTS {q(fk)}")
    objs = db.sql(f"SELECT table_name, table_type FROM {cat}.information_schema.tables "
                  f"WHERE table_schema = '{SCHEMA}'", quiet=True)
    order = {"VIEW": 0, "MATERIALIZED_VIEW": 0}
    for name, ttype in sorted(objs, key=lambda o: order.get(o[1], 1)):
        kind = {"VIEW": "VIEW", "MATERIALIZED_VIEW": "MATERIALIZED VIEW"}.get(ttype, "TABLE")
        db.sql(f"DROP {kind} IF EXISTS {q(SCHEMA)}.{q(name)}")


def apply_drift(db: Dbx):
    files = sorted(DRIFT_DIR.glob("[0-9][0-9]_*.sql"))
    if not files:
        sys.exit(f"No drift scripts in {DRIFT_DIR}")
    for f in files:
        print(f"Drift: {f.name}")
        text = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--"))
        for stmt in (s.strip() for s in text.split(";")):
            # USE CATALOG lines are for people running the file in the SQL editor; the target catalog comes from Flyway config.
            if stmt and not re.match(r"(?i)^USE\s+CATALOG\b", stmt):
                db.sql(stmt)


# ---------------------------------------------------------------- flyway

def flyway(*args):
    exe = shutil.which("flyway")
    if not exe:
        sys.exit("Flyway CLI not found on PATH")
    cmd = [exe, *args]
    print(f"> flyway {' '.join(args)}", flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    if rc != 0:
        sys.exit(f"flyway {args[0]} failed (exit {rc})")


def check(environment):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    flyway("check", "-drift", f"-environment={environment}", "-failOnDrift=false",
           "-generateDriftResolutionScripts=true", f"-reportFilename={REPORT}")
    print(f"\nDrift report: {REPORT}")


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("command", choices=["reset", "inject", "check"])
    p.add_argument("--environment", default="prod")
    p.add_argument("--profile", help="Databricks CLI profile for SQL calls")
    p.add_argument("--yes", action="store_true", help="don't ask for confirmation")
    a = p.parse_args()

    host, warehouse, catalog = parse_url(env_url(a.environment))
    if not catalog.startswith("demo_"):
        sys.exit(f"Refusing to touch catalog '{catalog}': only demo_* catalogs are allowed.")

    if a.command == "check":
        check(a.environment)
        return

    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    print(f"Environment {a.environment}: {catalog}.{SCHEMA} on {host} (warehouse {warehouse}); git branch: {branch}")
    if a.command == "reset":
        print(f"This DROPS every table and view in {catalog}.{SCHEMA} and rebuilds it from ./migrations.")
        if branch not in ("master", "main"):
            print(f"WARNING: you're on '{branch}', so prod will be rebuilt from that branch's migrations.")
    if not a.yes and input("Continue? [y/N] ").strip().lower() != "y":
        sys.exit("Cancelled")

    db = Dbx(host, warehouse, catalog, a.profile)
    if a.command == "reset":
        print("\n1/3 Wiping prod schema")
        wipe_schema(db)
        print("\n2/3 Migrating prod and saving the clean snapshot")
        flyway("migrate", f"-environment={a.environment}", "-saveSnapshot=true")
    else:
        print("\n1/2 Saving a snapshot of prod as it is now")
        flyway("snapshot", f"-environment={a.environment}", f"-source={a.environment}", f"-filename={SNAPSHOT_NAME}")

    print("\nApplying drift")
    apply_drift(db)
    print("\nVerifying")
    check(a.environment)


if __name__ == "__main__":
    main()
