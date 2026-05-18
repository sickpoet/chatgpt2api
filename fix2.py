"""修复：在 _create_account 中用 self._current_email 获取域名"""
code = open('/app/services/register/openai_register.py').read()

# 修改 _create_account 中的域名获取方式：用 self._current_email 代替 email
old_pattern = '_dm = email.split("@")[-1] if "@" in email else ""'
new_pattern = '_dm = getattr(self, "_current_email", "").split("@")[-1] if hasattr(self, "_current_email") else ""'

count = code.count(old_pattern)
if count > 0:
    code = code.replace(old_pattern, new_pattern)
    print(f"fixed {count} occurrences of email -> self._current_email")
else:
    print("pattern not found (maybe already fixed)")

# 确保 _current_email 在 __init__ 中初始化
if 'self._current_email' not in code.split('def __init__')[1].split('def ')[0] if 'def __init__' in code else '':
    code = code.replace(
        'self.device_id = str(uuid.uuid4())',
        'self.device_id = str(uuid.uuid4())\n        self._current_email = ""'
    )
    print("added _current_email to __init__")

open('/app/services/register/openai_register.py', 'w').write(code)
print("done")
