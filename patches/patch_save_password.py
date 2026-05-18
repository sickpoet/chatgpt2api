"""
补丁：注册成功后保存密码到账号数据
修改 worker() 函数，在 add_accounts 之后保存 password
"""
import os

TARGET = "/app/services/register/openai_register.py"

with open(TARGET, "r") as f:
    content = f.read()

if "save_password_to_db" in content:
    print("[patch] save_password already applied")
    exit(0)

old = '        account_service.add_accounts([access_token])\n        account_service.refresh_accounts([access_token])'
new = '        account_service.add_accounts([access_token])\n        save_password_to_db(access_token, result)\n        account_service.refresh_accounts([access_token])'

if old not in content:
    print("[patch] ERROR: target code not found")
    exit(1)

content = content.replace(old, new)

patch_func = '''

def save_password_to_db(access_token, reg_result):
    """Save password to account data JSON"""
    import json, sqlite3
    db_path = "/app/data/accounts.db"
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT data FROM accounts WHERE access_token = ?", (access_token,)).fetchone()
        if row:
            data = json.loads(row[0])
            data["password"] = reg_result.get("password", "")
            data["email"] = reg_result.get("email", "")
            conn.execute("UPDATE accounts SET data = ? WHERE access_token = ?",
                        (json.dumps(data, ensure_ascii=False), access_token))
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"[patch] save_password error: {e}")
'''

content += patch_func

with open(TARGET, "w") as f:
    f.write(content)

print("[patch] save_password applied")
