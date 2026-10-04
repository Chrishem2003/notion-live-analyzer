# Phase 86 — Authenticated FastAPI Query Integration & Request Context Binding

Connects Phase 85 authorization directly to the persistent Phase 83 query path.

Execution order:
1. authenticate/authorize
2. reject unauthorized requests before storage access
3. execute governed persistent query
4. bind actor/request authorization context to the response

The authorization context is deterministic evidence metadata, not a regulatory identity claim. Unauthorized requests never reach the evidence repository. Read-only behavior and fail-closed storage handling remain unchanged.
