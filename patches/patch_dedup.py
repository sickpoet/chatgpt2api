#!/usr/bin/env python3
"""Patch conversation.py: limit 1 image per conversation (container image version)"""

path = "/app/services/protocol/conversation.py"
with open(path, "r") as f:
    content = f.read()

marker = '    image_urls = backend.resolve_conversation_image_urls(conversation_id, file_ids, sediment_ids)\n    if image_urls:'
patch = '''    image_urls = backend.resolve_conversation_image_urls(conversation_id, file_ids, sediment_ids)
    # Dedup: limit to 1 image per conversation (pool handles n>1)
    if image_urls:
        unique = []
        for u in image_urls:
            if u not in unique:
                unique.append(u)
        image_urls = unique[:1]
    if image_urls:'''

if "unique = []" in content:
    print("dedup: already patched")
elif marker in content:
    content = content.replace(marker, patch)
    with open(path, "w") as f:
        f.write(content)
    print("dedup: patched")
else:
    print("dedup: target not found")
