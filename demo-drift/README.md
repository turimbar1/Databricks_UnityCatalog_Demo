# Prod drift for demos

These scripts give `demo_prod` some realistic hand-made changes that never went through Flyway, so the drift report always has something to show.

| Script | Drift | What the report shows |
|---|---|---|
| 01 | `orders.priority_flag` column added during an incident | Changed table, extra column |
| 02 | `recent_orders` widened to 14 days, plus `shipped_date` | Changed view definition |
| 03 | `orders_backup_inc4471` left behind | Extra table |
| 04 | `products.unit_price` comment edited | Unity Catalog metadata drift |
| 05 | `orders_shippers_fk` dropped | Missing object (delete the file if you don't want this one) |

None of these block the `demo-samples` changes (V004) from deploying. Script 02 is the hook for the story: `demo-samples/04` rewrites `recent_orders`, so deploying it without a drift check would silently overwrite the prod hotfix.

## How the drift gets detected

Drift is measured against a **Flyway snapshot**. The order matters:

1. Prod is migrated and a snapshot is saved (`migrate -saveSnapshot=true`, stored in prod's snapshot history table).
2. The drift scripts run **after** the snapshot.
3. `flyway check -drift -environment=prod` compares prod with that snapshot and reports 01–05.

Why not compare against a build from `shadow`? `V002` only runs when `${flyway:environment}==prod` (see its `.conf`), so a build in `shadow` would never have `orders` or `recent_orders`. They'd show up as false drift.

## Set it up (once)

On your machine:

```powershell
pip install databricks-sdk
databricks auth login --host https://adb-7405611424302232.12.azuredatabricks.net   # or set DATABRICKS_TOKEN
```

You also need the Flyway CLI (Enterprise) on PATH. It uses the prod credentials already in your `flyway.user.toml`.

For the nightly GitHub Action, add these repo secrets:

| Secret | Value |
|---|---|
| `DATABRICKS_TOKEN` | A PAT (preferably for a service principal) that owns `demo_prod` and can use warehouse `353a9a5f7ad7299f` |
| `FLYWAY_EMAIL` / `FLYWAY_TOKEN` | Redgate account email and personal access token with an Enterprise licence |

## Use it

| When | Run |
|---|---|
| Before a demo, prod in any state | `python demo-drift/prod_drift.py reset`. This drops everything in `demo_prod.default`, migrates it from your checkout (B001 → V002 → V003), saves the snapshot and adds the drift. |
| Prod is already clean, keep it as it is | `python demo-drift/prod_drift.py inject`. This saves a snapshot of prod as it is now, then adds the drift. |
| Just regenerate the report | `python demo-drift/prod_drift.py check` → `demo-drift/reports/prod-drift.html` |
| Hands-off | GitHub Actions → **prod-drift-reset** runs at 01:23 UTC on weekdays, or click **Run workflow** before a call |

`reset` rebuilds from whatever branch you have checked out and warns if that isn't `master`. It won't run against any catalog whose name doesn't start with `demo_`.

## In the demo

After the `demo-samples` steps (V004 generated in dev), before you deploy to prod:

**Flyway Desktop:** go to **Migration scripts**, set the target to **Prod Demo**, choose the **Check** command, tick **drift**, and click **Run check**. The report lists the five objects. Drill into `recent_orders` to show the before and after of the view.

**CLI / pipeline:**

```powershell
flyway check -drift -environment=prod -failOnDrift=true -generateDriftResolutionScripts=true
```

With `-failOnDrift=true` the check exits with `CHECK_DRIFT_DETECTED`, which is the "pipeline stopped a deploy that would have overwritten a prod hotfix" moment. The generated resolution scripts show the two ways out: pull the drift into a migration, or revert it.

Then deploy V004 with `flyway migrate -environment=prod -saveSnapshot=true`, so the next drift check has a fresh baseline. Run `reset` afterwards, or let the nightly job do it.

## Note

All of this is unverified against your workspace. Do one dry run of `reset` and check that the report shows 01–05 and nothing else. If Flyway's own tables (`flyway_schema_history` or the snapshot history table) show up as drift, tell me and I'll add a filter.
