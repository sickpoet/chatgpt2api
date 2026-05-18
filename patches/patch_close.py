import re

path = "/app/services/openai_backend_api.py"
with open(path, "r") as f:
    content = f.read()

if "def close" in content:
    print("Already has close(), skipping")
    exit()

marker = 'self.session.headers["Authorization"] = f"Bearer {self.access_token}"'
patch = '''

    def close(self) -> None:
        """Close HTTP session."""
        try:
            self.session.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()'''

if marker in content:
    content = content.replace(marker, marker + patch)
    with open(path, "w") as f:
        f.write(content)
    print("OK patched close()")
else:
    print("FAIL marker not found")
