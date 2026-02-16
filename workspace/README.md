# Workspace mount

This folder is mounted into containers at `/workspace`.

The local actions tool is sandboxed to this path. By default:
- `LOCAL_ACTIONS_ENABLED=0`

If enabled, local actions remain approval-gated via policy/orchestrator.
