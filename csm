#!/usr/bin/env python3
"""
csm — Codex Multi-Account Switcher & Quota Manager
Cross-platform support for macOS, Windows, and Linux.
"""

import os
import sys
import json
import time
import base64
import urllib.request
import urllib.error
import pathlib
import shutil
import tempfile
import platform
import subprocess
import re
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.platform == "win32" and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VERSION = "2.1.0"
APP_NAME = "Codex"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
STORE_DIR = Path.home() / ".codex-multi"
ACCOUNTS_DIR = STORE_DIR / "accounts"
ACTIVE_FILE = STORE_DIR / "active"

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
AUTH_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

def init_store():
    try:
        ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_chmod(STORE_DIR, 0o700)
        safe_chmod(ACCOUNTS_DIR, 0o700)
    except Exception:
        pass

def get_active_account() -> str:
    try:
        if ACTIVE_FILE.is_file():
            return ACTIVE_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""

def safe_chmod(path: Path, mode: int):
    if os.name != "nt":
        try:
            os.chmod(path, mode)
        except Exception:
            pass

def die(msg: str):
    print(f"❌ {msg}", file=sys.stderr)
    sys.exit(1)

def info(msg: str):
    print(f"→ {msg}")

def usage():
    print(f"""csm v{VERSION} — Codex Multi-Account Switcher & Quota Manager

Commands:
  csm add <name>       Login to an account safely and save it
  csm refresh <name>   Re-login to an existing account safely
  csm use <name>       Switch Codex App to that account and restart it
  csm use <name> --no-restart
                       Switch auth without restarting Codex App
  csm list             List saved accounts
  csm status           Show remaining 5h/weekly limits for all accounts
  csm pick             Pick the healthiest account and switch to it
  csm current          Show active account
  csm remove <name>    Remove a saved account
  csm update           Update csm to the latest version from GitHub
  csm version          Show csm version
  csm help             Show this help

Examples:
  csm add personal
  csm add work
  csm status
  csm pick
  csm use personal""")

def safe_name(name: str) -> str:
    if not re.match(r"^[A-Za-z0-9._-]+$", name):
        die("Account name may only contain letters, numbers, dot, underscore, and dash.")
    return name

def save_active_auth():
    auth_file = CODEX_HOME / "auth.json"
    if ACTIVE_FILE.exists() and auth_file.exists():
        try:
            active = ACTIVE_FILE.read_text(encoding="utf-8").strip()
            target = ACCOUNTS_DIR / f"{active}.json"
            if active and target.exists():
                shutil.copy2(auth_file, target)
                safe_chmod(target, 0o600)
        except Exception:
            pass

def isolated_login(name: str):
    codex_bin = shutil.which("codex")
    if not codex_bin:
        die("Codex CLI ('codex') not found in PATH. Please make sure Codex CLI is installed.")

    tmp_dir = Path(tempfile.mkdtemp(prefix="csm-login-"))
    try:
        config_file = tmp_dir / "config.toml"
        config_file.write_text('cli_auth_credentials_store = "file"\n', encoding="utf-8")

        print(f"\n🔐 Opening isolated Codex login for '{name}'...")
        print(f"   Existing credentials in {CODEX_HOME / 'auth.json'} are protected from revocation.\n")

        env = os.environ.copy()
        env["CODEX_HOME"] = str(tmp_dir)

        # Run codex login
        res = subprocess.run([codex_bin, "login"], env=env)
        if res.returncode != 0:
            die("Login was canceled or failed.")

        tmp_auth = tmp_dir / "auth.json"
        if not tmp_auth.exists():
            die("Login completed but auth.json was not found in temp directory.")

        target = ACCOUNTS_DIR / f"{name}.json"
        shutil.copy2(tmp_auth, target)
        safe_chmod(target, 0o600)
        print(f"✅ Account '{name}' successfully saved!")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def restart_codex():
    info("Restarting Codex / ChatGPT App...")
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        # Try quitting by Bundle ID, then app names
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application id "com.openai.codex" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application "ChatGPT" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application "Codex" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/pkill", "-f", "codex.*app-server"], capture_output=True)
        time.sleep(1.5)
        
        # Re-open by bundle ID or fallback to app names
        res = subprocess.run(["/usr/bin/open", "-b", "com.openai.codex"], capture_output=True)
        if res.returncode != 0:
            res = subprocess.run(["/usr/bin/open", "-a", "ChatGPT"], capture_output=True)
        if res.returncode != 0:
            subprocess.run(["/usr/bin/open", "-a", "Codex"], capture_output=True)
    elif sys_plat == "Windows":
        subprocess.run(["taskkill", "/IM", "Codex.exe", "/F"], capture_output=True)
        subprocess.run(["taskkill", "/IM", "ChatGPT.exe", "/F"], capture_output=True)
        time.sleep(1)
        try:
            os.startfile("Codex")
        except Exception:
            try:
                os.startfile("ChatGPT")
            except Exception:
                try:
                    subprocess.Popen(["cmd", "/c", "start", "codex"], shell=True)
                except Exception as e:
                    print(f"⚠️  Could not automatically restart Desktop App: {e}")
    elif sys_plat == "Linux":
        subprocess.run(["killall", "codex"], capture_output=True)
        time.sleep(1)
        try:
            subprocess.Popen(["codex"], start_new_session=True)
        except Exception:
            pass

def switch_account(name: str, restart: bool = True):
    acc_file = ACCOUNTS_DIR / f"{name}.json"
    if not acc_file.exists():
        die(f"No saved account named '{name}'. Run: csm add {name}")

    CODEX_HOME.mkdir(parents=True, exist_ok=True)
    save_active_auth()

    target_auth = CODEX_HOME / "auth.json"
    shutil.copy2(acc_file, target_auth)
    safe_chmod(target_auth, 0o600)
    ACTIVE_FILE.write_text(name, encoding="utf-8")

    print(f"✅ Active Codex account: {name}")
    print("   Project and session history under ~/.codex were not changed.")

    if restart:
        restart_codex()
    else:
        print("   Restart Codex App manually to load the new account.")

def b64url_decode(s: str) -> bytes:
    s += "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s.encode())

def jwt_payload(token: str) -> dict:
    try:
        return json.loads(b64url_decode(token.split(".")[1]))
    except Exception:
        return {}

def is_expired(token: str, skew: int = 60) -> bool:
    p = jwt_payload(token)
    exp = p.get("exp")
    return isinstance(exp, (int, float)) and exp <= time.time() + skew

def refresh_auth(auth: dict, path: Path) -> dict:
    tokens = auth.get("tokens") or {}
    access = tokens.get("access_token")
    refresh = tokens.get("refresh_token")
    if not access or not refresh or not is_expired(access):
        return auth

    body = json.dumps({
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }).encode()

    req = urllib.request.Request(
        AUTH_URL, data=body, method="POST",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)

    for k in ("access_token", "refresh_token", "id_token"):
        if not data.get(k):
            raise RuntimeError(f"refresh response missing {k}")

    auth["tokens"] = {
        **tokens,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "id_token": data["id_token"],
    }
    auth["last_refresh"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps(auth, indent=2), encoding="utf-8")
    safe_chmod(path, 0o600)
    return auth

def fmt_seconds(sec) -> str:
    if sec is None:
        return "?"
    try:
        sec = max(0, int(sec))
    except Exception:
        return "?"
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    out = []
    if d: out.append(f"{d}d")
    if h: out.append(f"{h}h")
    if m and not d: out.append(f"{m}m")
    return " ".join(out) if out else "<1m"

def reset_in(w: dict) -> str:
    if not w:
        return "?"
    if w.get("reset_after_seconds") is not None:
        return fmt_seconds(w["reset_after_seconds"])
    if w.get("reset_at") is not None:
        return fmt_seconds(w["reset_at"] - int(time.time()))
    return "?"

def progress_bar(left: float) -> str:
    left = max(0.0, min(100.0, left))
    filled = round(left / 5)
    return "█" * filled + "░" * (20 - filled)

def fetch_usage(auth: dict) -> dict:
    tokens = auth.get("tokens") or {}
    access = tokens.get("access_token")
    if not access:
        raise RuntimeError("No OAuth access token available")

    headers = {"Authorization": f"Bearer {access}"}
    account_id = tokens.get("account_id")
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id

    req = urllib.request.Request(USAGE_URL, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)

def status_accounts():
    save_active_auth()
    active = get_active_account()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        print(f"❌ Could not access accounts directory: {e}")
        return

    if not files:
        print("No saved accounts found. First run: csm add <name>")
        return

    print("\nCodex Rate Limits & Usage")
    print("────────────────────────────────────────────────────────────────")

    rows = []
    for path in files:
        name = path.stem
        mark = "●" if name == active else " "
        try:
            auth = json.loads(path.read_text(encoding="utf-8"))
            auth = refresh_auth(auth, path)
            data = fetch_usage(auth)
            rl = data.get("rate_limit") or {}
            p = rl.get("primary_window") or {}
            s = rl.get("secondary_window") or {}

            p_used = float(p.get("used_percent", 0))
            s_used = float(s.get("used_percent", 0))
            p_left = max(0.0, 100.0 - p_used)
            s_left = max(0.0, 100.0 - s_used)
            plan = data.get("plan_type") or "?"

            score = min(p_left, s_left)
            rows.append((score, p_left, s_left, name))

            print(f"{mark} {name} [{plan}]")
            print(f"   5h  {progress_bar(p_left)} {p_left:5.1f}% left   reset {reset_in(p)}")
            print(f"   7d  {progress_bar(s_left)} {s_left:5.1f}% left   reset {reset_in(s)}")

            credits = data.get("credits")
            if isinstance(credits, dict) and credits.get("balance") is not None:
                print(f"   Credits: ${credits.get('balance')}")
            print()
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")
                msg = json.loads(body).get("error", {}).get("code") or body[:120]
            except Exception:
                msg = f"HTTP {e.code}"
            print(f"{mark} {name}")
            print(f"   ❌ Could not retrieve usage: {msg}\n")
        except Exception as e:
            print(f"{mark} {name}")
            print(f"   ❌ {e}\n")

    if rows:
        best = max(rows, key=lambda x: (x[0], x[1] + x[2]))
        print("────────────────────────────────────────────────────────────────")
        print(f"Recommended: {best[3]}  (5h: {best[1]:.1f}% / 7d: {best[2]:.1f}% remaining)")

def pick_account():
    save_active_auth()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        die(f"Could not access accounts directory: {e}")

    best = None
    for path in files:
        try:
            auth = json.loads(path.read_text(encoding="utf-8"))
            auth = refresh_auth(auth, path)
            tokens = auth.get("tokens") or {}
            headers = {"Authorization": "Bearer " + tokens["access_token"]}
            if tokens.get("account_id"):
                headers["ChatGPT-Account-ID"] = tokens["account_id"]

            req = urllib.request.Request(USAGE_URL, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as r:
                u = json.load(r)

            rl = u.get("rate_limit") or {}
            pw = rl.get("primary_window") or {}
            sw = rl.get("secondary_window") or {}
            pleft = max(0.0, 100 - float(pw.get("used_percent", 0)))
            sleft = max(0.0, 100 - float(sw.get("used_percent", 0)))
            score = (min(pleft, sleft), pleft + sleft)

            if best is None or score > best[0]:
                best = (score, path.stem)
        except Exception:
            pass

    if not best:
        die("Could not retrieve valid usage metrics from any saved accounts.")

    picked = best[1]
    print(f"🏆 Best account found: {picked}")
    switch_account(picked, restart=True)

def list_accounts():
    print("Saved accounts:")
    active = get_active_account()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        print(f"  ❌ Could not read accounts directory ({e})")
        return

    if not files:
        print("  (none)")
        return
    for f in files:
        name = f.stem
        if name == active:
            print(f"  * {name}  (active)")
        else:
            print(f"    {name}")

def remove_account(name: str):
    target = ACCOUNTS_DIR / f"{name}.json"
    if not target.exists():
        die(f"No saved account named '{name}'.")
    target.unlink()
    if get_active_account() == name:
        try:
            ACTIVE_FILE.unlink()
        except Exception:
            pass
    print(f"✅ Account '{name}' removed.")

def update_csm():
    info("Checking for updates and downloading latest csm...")
    target_path = Path(os.path.realpath(__file__))
    download_url = "https://raw.githubusercontent.com/mazisel/csm/main/csm"
    
    try:
        req = urllib.request.Request(download_url, headers={"User-Agent": "csm-updater"})
        with urllib.request.urlopen(req, timeout=20) as r:
            new_content = r.read()

        target_path.write_bytes(new_content)
        safe_chmod(target_path, 0o755)
        print(f"✅ csm successfully updated to latest version at {target_path}!")
    except PermissionError:
        print(f"⚠️  Permission denied when writing to {target_path}.")
        if sys.platform != "win32":
            print("   Please try running: sudo csm update")
        else:
            print("   Please run your terminal as Administrator and try again.")
    except Exception as e:
        die(f"Failed to update csm: {e}")

def main():
    init_store()
    args = sys.argv[1:]
    cmd = args[0] if args else "help"

    if cmd == "add":
        if len(args) < 2:
            die("Usage: csm add <name>")
        name = safe_name(args[1])
        if (ACCOUNTS_DIR / f"{name}.json").exists():
            die(f"'{name}' already exists. Use: csm refresh {name}")
        isolated_login(name)

    elif cmd == "refresh":
        if len(args) < 2:
            die("Usage: csm refresh <name>")
        name = safe_name(args[1])
        if not (ACCOUNTS_DIR / f"{name}.json").exists():
            die(f"No saved account named '{name}'.")
        isolated_login(name)

    elif cmd == "use":
        if len(args) < 2:
            die("Usage: csm use <name> [--no-restart]")
        name = safe_name(args[1])
        no_restart = "--no-restart" in args[2:]
        switch_account(name, restart=not no_restart)

    elif cmd == "list":
        list_accounts()

    elif cmd == "status":
        status_accounts()

    elif cmd == "pick":
        pick_account()

    elif cmd == "current":
        curr = get_active_account()
        print(curr if curr else "(not set)")

    elif cmd == "remove":
        if len(args) < 2:
            die("Usage: csm remove <name>")
        name = safe_name(args[1])
        remove_account(name)

    elif cmd == "update":
        update_csm()

    elif cmd in ("version", "-v", "--version"):
        print(f"csm v{VERSION}")

    elif cmd in ("help", "-h", "--help"):
        usage()

    else:
        usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
