#!/bin/bash
# chatgpt2api 启动后自动应用补丁
sleep 5
docker exec chatgpt2api python3 /tmp/patch_close.py 2>/dev/null || true
