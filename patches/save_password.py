"""
补丁：注册成功后保存密码到账号数据
"""
import json, sqlite3, os

DB_PATH = os.environ.get("DB_PATH", "/app/data/accounts.db")

def save_password(access_token: str, email: str, password: str):
    """把密码存到账号的 data JSON 里"""
    conn = sqlite3.connect(DB_PATH)
    try:
        row = conn.execute("SELECT data FROM accounts WHERE access_token = ?", (access_token,)).fetchone()
        if row:
            data = json.loads(row[0])
            data["password"] = password
            data["email"] = email
            conn.execute("UPDATE accounts SET data = ? WHERE access_token = ?",
                        (json.dumps(data, ensure_ascii=False), access_token))
            conn.commit()
            return True
    except Exception as e:
        print(f"[patch] save_password error: {e}")
    finally:
        conn.close()
    return False
