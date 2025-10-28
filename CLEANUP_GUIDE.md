# Cleanup Guide

After verifying the monorepo structure works correctly, you can safely remove the following old directories and files:

## Directories to Remove

The following directories are now duplicated under `src/orby/` and can be removed:

```bash
# Old repositories that have been integrated
rm -rf digital-agent/
rm -rf prompt_template_manager/
rm -rf protos/  # (at root level, not src/orby/protos)

# Old subtask_benchmark structure (now at src/orby/subtask_benchmark)
rm -rf src/subtask_benchmark/
rm -rf src/__pycache__/
rm -rf src/__init__.py
rm -rf src/.DS_Store
```

## Files to Keep

**DO NOT REMOVE:**
- `src/orby/` - The new monorepo structure
- `scripts/` - Utility scripts (already updated)
- `custom_build.py` - Build script for webreplay-standalone
- `pyproject.toml` - Package configuration
- `setup.py` - Setup script
- `README.md` - Documentation
- `.git/` - Git repository
- `.env/` - Environment configurations

## Verification Before Cleanup

Before removing the old directories, verify:

1. **Test imports work:**
   ```bash
   python scripts/test_imports.py
   ```

2. **Check that the new package structure is accessible:**
   ```python
   import orby
   from orby.subtask_benchmark import config
   from orby.digitalagent.agent.sva_v4 import SvaV4
   from orby.protos.fm import action_data_pb2
   from orby.prompt_utils import template
   ```

3. **Verify webreplay-standalone is in the right place:**
   ```bash
   ls -la src/orby/subtask_benchmark/webreplay-standalone/
   ```

## Recommended Cleanup Command

After verification, run:

```bash
# Make a backup first!
tar -czf backup-old-structure.tar.gz digital-agent/ prompt_template_manager/ protos/ src/subtask_benchmark/

# Then remove old directories
rm -rf digital-agent/
rm -rf prompt_template_manager/
rm -rf protos/
rm -rf src/subtask_benchmark/
rm -rf src/__pycache__/

# Clean up old src/__init__.py if it exists
rm -f src/__init__.py
```

## What Changed

### Directory Structure
```
OLD:
├── src/subtask_benchmark/    → NEW: src/orby/subtask_benchmark/
├── digital-agent/orby/digitalagent/  → NEW: src/orby/digitalagent/
├── prompt_template_manager/  → NEW: src/orby/prompt_utils/
└── protos/                   → NEW: src/orby/protos/

NEW UNIFIED STRUCTURE:
src/orby/
├── subtask_benchmark/
├── digitalagent/
├── prompt_utils/
└── protos/
```

### Import Changes
All imports now use the `orby` namespace:
- `subtask_benchmark.X` → `orby.subtask_benchmark.X`
- `orby.digitalagent.X` → stays `orby.digitalagent.X`
- `prompt_template_manager.X` → `orby.prompt_utils.X`
- `fm.X` → `orby.protos.fm.X`

## Notes

- The `digital-agent/` directory contains a full git repository and virtual environment (`env/`), which takes up significant space
- The old structure files are safe to remove after the new package is verified working
- Keep this CLEANUP_GUIDE.md for reference until cleanup is complete
