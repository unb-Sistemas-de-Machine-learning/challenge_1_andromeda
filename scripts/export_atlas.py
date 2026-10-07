"""Export the active Atlas snapshot to a compact read-only mobile asset."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

database = Path(".data/news_analysis.sqlite3")
output = Path("android/app/src/main/assets/atlas-domains.json")
connection = sqlite3.connect(database)
row = connection.execute("select active_snapshot_id from atlas_sync_state where id=1").fetchone()
snapshot_id = row[0] if row else None
domains = sorted({item[0] for item in connection.execute(
    "select distinct domain from atlas_domain_links where snapshot_id=?", (snapshot_id,)
)}) if snapshot_id else []
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"version": 1, "snapshot_id": snapshot_id,
                              "exported_at": datetime.now(timezone.utc).isoformat(),
                              "domains": domains}, separators=(",", ":")), encoding="utf-8")
print(f"exported {len(domains)} Atlas domains to {output}")
