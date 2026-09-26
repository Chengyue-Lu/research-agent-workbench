"""Pure synthetic review/measurement authority; no suite or execution imports."""

CREATED = "2026-09-11T12:01:00Z"
RECEIVED = "2026-09-11T12:02:00Z"
FROZEN = "2026-09-11T12:03:00Z"
REVEALED = "2026-09-11T12:04:00Z"
OBSERVED = "2026-09-11T12:05:00Z"
CHECKED = "2026-09-11T12:06:00Z"
ANALYZED = "2026-09-11T12:07:00Z"


def review_authority(payload):
    if payload["operation"] == "human-review":
        return payload["review"]["reviewer"]["actor_id"] == "synthetic-h4c-reviewer"
    return payload["operation"] in {"anonymize", "freeze", "reveal"}


def missing_authority(payload):
    """Explicit fixture permits no numeric claim or automatic Human scoring."""
    return (payload["operation"] == "measurement"
            and payload["measurement"]["status"] == "unavailable"
            and payload["measurement"]["value"] is None
            and payload["method"] is None and payload["observation"] is None)


AUTH = {"admission_verifier": lambda _: True, "projection_verifier": review_authority,
        "human_verifier": review_authority, "measurement_verifier": missing_authority}
