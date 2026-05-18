#!/bin/bash
# Apply patches before starting
python3 /patches/patch_close.py 2>/dev/null || true
python3 /patches/patch_dedup.py 2>/dev/null || true
# Run original command
exec "$@"
python3 /patches/patch_save_password.py 2>/dev/null || true
