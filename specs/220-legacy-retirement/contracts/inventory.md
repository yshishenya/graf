# Inventory Contract

The inventory adapter MUST emit deterministic JSON:

```json
{
  "schema_version": 1,
  "source_sha": "<40-hex>",
  "generated_at": "<UTC timestamp>",
  "contours": [
    {
      "contour_id": "L001",
      "category": "migration",
      "source_path": "apps/server/src/...",
      "source_digest": "sha256:<64-hex>",
      "owner": "team-or-person",
      "risk": "high",
      "classification": "retain-with-exception",
      "status": "candidate",
      "evidence": ["#6145"]
    }
  ],
  "counts": {"total": 1, "by_category": {}, "by_classification": {}},
  "snapshot_digest": "sha256:<64-hex>"
}
```

Rules: paths are relative and contained in the repository; records are sorted by `contour_id`; SHA and digest are required; raw content, secrets, credentials, signed URLs, audio and transcripts are forbidden; incomplete discovery is `blocked`/`partial`; a changed SHA invalidates the snapshot.
