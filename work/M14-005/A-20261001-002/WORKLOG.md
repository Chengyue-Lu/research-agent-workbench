# M14-005 live governance / activation implementation

The user authorized continuing after PR117 integration and rebuilt #116 evidence.
This feature branch starts at develop 331809fc7d8fc0a72bb9bc72f59363495e2917c8.
Live release PR metadata now enters full R2 governance using the same preflight's
source CI and independent pins, followed by metadata reobservation after install.
Active curated topology and direct-develop rejection are proposed together.
Policy 1.5.0 adds only the helper; previous policies and frozen archives remain.

Local verification is retained in outputs/VERIFICATION.md. Hosted exact-head
component/governance results and cross-owner review follow in the implementation
PR. Remote protection, main, release candidate and tag remain unchanged. Integration
requires R2 acceptance; actual source CI and a new-source candidate rebuild follow.

The complete interactive call stream was not retained. The trace records this
capture gap and never claims complete telemetry or reconstructs omitted events.
