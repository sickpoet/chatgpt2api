"""修复：在 _register_user 和 _create_account 中记录域名信誉"""
code = open('/app/services/register/openai_register.py').read()

# 在 _register_user 中，400 错误时记录域名
old = '''            if data.get("message") == "Failed to create account. Please try again.":
                step(index, "注册失败提示: 邮箱域名很可能因滥用被封禁，请更换邮箱域名", "yellow")'''
new = '''            if data.get("message") == "Failed to create account. Please try again.":
                step(index, "注册失败提示: 邮箱域名很可能因滥用被封禁，请更换邮箱域名", "yellow")
                try:
                    _dm = email.split("@")[-1] if "@" in email else ""
                    if _dm: _dr_fail(_dm, "domain_blocked_400", blocked=True)
                except: pass'''

if old in code and '_dr_fail(_dm, "domain_blocked_400"' not in code:
    code = code.replace(old, new, 1)
    print("patched _register_user 400 handler")

# 同样在 _create_account 中，400 错误时记录域名
old2 = '''            if data.get("message") == "Failed to create account. Please try again.":
                step(index, "创建账号失败提示: 邮箱域名很可能因滥用被封禁，请更换邮箱域名", "yellow")'''
new2 = '''            if data.get("message") == "Failed to create account. Please try again.":
                step(index, "创建账号失败提示: 邮箱域名很可能因滥用被封禁，请更换邮箱域名", "yellow")
                try:
                    _dm = email.split("@")[-1] if "@" in email else ""
                    if _dm: _dr_fail(_dm, "create_account_400", blocked=True)
                except: pass'''

if old2 in code and '_dr_fail(_dm, "create_account_400"' not in code:
    code = code.replace(old2, new2, 1)
    print("patched _create_account 400 handler")

open('/app/services/register/openai_register.py', 'w').write(code)
print("done")
