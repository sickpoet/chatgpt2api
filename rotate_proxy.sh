#!/bin/bash
# 代理轮询脚本 - 代理没变则不重启
PROXIES_FILE="/opt/chatgpt2api/proxies.txt"
CONFIG_FILE="/opt/chatgpt2api/config.json"

# 当前代理
CURRENT=$(python3 -c "import json; print(json.load(open(\"$CONFIG_FILE\")).get(\"proxy\",\"\"))")

# 随机选一个
PROXY=$(shuf -n 1 "$PROXIES_FILE")

# 没变就不重启
if [ "$CURRENT" = "$PROXY" ]; then
    echo "$(date): 代理未变 ($PROXY)，跳过"
    exit 0
fi

# 更新配置
python3 -c "
import json
with open(\"$CONFIG_FILE\", \"r\") as f:
    config = json.load(f)
config[\"proxy\"] = \"$PROXY\"
with open(\"$CONFIG_FILE\", \"w\") as f:
    json.dump(config, f, indent=2)
"

echo "$(date): 已切换代理: $CURRENT → $PROXY"
docker restart chatgpt2api
