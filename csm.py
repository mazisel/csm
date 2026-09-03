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
import concurrent.futures
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.platform == "win32" and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VERSION = "2.4.0"
APP_NAME = "Codex"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
STORE_DIR = Path.home() / ".codex-multi"
ACCOUNTS_DIR = STORE_DIR / "accounts"
ACTIVE_FILE = STORE_DIR / "active"

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
RESET_CREDITS_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
AUTH_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

# ANSI Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_CYAN = "\033[36m"
C_BRIGHT_CYAN = "\033[96m"
C_GREEN = "\033[32m"
C_BRIGHT_GREEN = "\033[92m"
C_YELLOW = "\033[33m"
C_BRIGHT_YELLOW = "\033[93m"
C_RED = "\033[31m"
C_BRIGHT_RED = "\033[91m"
C_MAGENTA = "\033[35m"
C_BRIGHT_MAGENTA = "\033[95m"
C_GRAY = "\033[90m"
C_WHITE = "\033[97m"

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

def fmt_expiry(exp_iso: str) -> str:
    if not exp_iso:
        return ""
    try:
        if exp_iso.endswith("Z"):
            exp_clean = exp_iso[:-1] + "+00:00"
        else:
            exp_clean = exp_iso
        dt = datetime.fromisoformat(exp_clean)
        formatted_date = dt.strftime("%d %b")
        seconds_left = max(0, int(dt.timestamp() - time.time()))
        rel = fmt_seconds(seconds_left)
        return f"expires {formatted_date} ({rel} left)"
    except Exception:
        return f"expires {exp_iso[:10]}"

def reset_in(w: dict) -> str:
    if not w:
        return "?"
    if w.get("reset_after_seconds") is not None:
        return fmt_seconds(w["reset_after_seconds"])
    if w.get("reset_at") is not None:
        return fmt_seconds(w["reset_at"] - int(time.time()))
    return "?"

def progress_bar(left_pct: float, anim_ratio: float = 1.0) -> str:
    val = max(0.0, min(100.0, left_pct * anim_ratio))
    filled = round(val / 5)
    unfilled = 20 - filled
    
    if left_pct >= 50:
        fill_col = C_BRIGHT_GREEN
    elif left_pct >= 20:
        fill_col = C_BRIGHT_YELLOW
    else:
        fill_col = C_BRIGHT_RED
        
    blocks = "█" * filled
    spaces = "░" * unfilled
    return f"{fill_col}{blocks}{C_GRAY}{spaces}{C_RESET}"

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
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)

def fetch_reset_credits(auth: dict) -> dict:
    tokens = auth.get("tokens") or {}
    access = tokens.get("access_token")
    if not access:
        return {}

    headers = {"Authorization": f"Bearer {access}"}
    account_id = tokens.get("account_id")
    if account_id:
        headers["ChatGPT-Account-ID"] = account_id

    req = urllib.request.Request(RESET_CREDITS_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception:
        return {}

def fetch_account_data(path: Path):
    name = path.stem
    try:
        auth = json.loads(path.read_text(encoding="utf-8"))
        auth = refresh_auth(auth, path)
        usage_data = fetch_usage(auth)
        reset_data = fetch_reset_credits(auth)
        return (name, usage_data, reset_data, None)
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
            msg = json.loads(body).get("error", {}).get("code") or body[:120]
        except Exception:
            msg = f"HTTP {e.code}"
        return (name, None, None, msg)
    except Exception as e:
        return (name, None, None, str(e))

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

    is_tty = sys.stdout.isatty()
    results = {}
    done_count = 0
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    if is_tty:
        sys.stdout.write("\033[?25l")  # Hide cursor
        sys.stdout.flush()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(files)) as executor:
            futures = {executor.submit(fetch_account_data, p): p for p in files}
            spin_idx = 0
            while not all(f.done() for f in futures):
                done_count = sum(1 for f in futures if f.done())
                if is_tty:
                    spin = spinner[spin_idx % len(spinner)]
                    sys.stdout.write(f"\r\033[K{C_BRIGHT_CYAN}{spin}{C_RESET}  {C_BOLD}Checking Codex quotas...{C_RESET} {C_DIM}({done_count}/{len(files)}){C_RESET}")
                    sys.stdout.flush()
                time.sleep(0.05)
                spin_idx += 1

            for f in futures:
                name, usage_data, reset_data, err = f.result()
                results[name] = (usage_data, reset_data, err)

        if is_tty:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        # Header
        print(f"\n{C_BRIGHT_MAGENTA}╭────────────────────────────────────────────────────────────────╮{C_RESET}")
        print(f"{C_BRIGHT_MAGENTA}│{C_RESET}  {C_BOLD}{C_BRIGHT_CYAN}⚡ Codex Rate Limits & Live Quota{C_RESET}                            {C_BRIGHT_MAGENTA}│{C_RESET}")
        print(f"{C_BRIGHT_MAGENTA}╰────────────────────────────────────────────────────────────────╯{C_RESET}\n")

        rows = []
        for path in files:
            name = path.stem
            is_active = (name == active)
            mark = f"{C_BRIGHT_CYAN}●{C_RESET}" if is_active else " "
            name_str = f"{C_BOLD}{C_WHITE}{name}{C_RESET}" if is_active else f"{C_WHITE}{name}{C_RESET}"

            usage_data, reset_data, err = results.get(name, (None, None, None))
            if err or not usage_data:
                print(f"{mark} {name_str}")
                print(f"   {C_RED}❌ Could not retrieve usage: {err}{C_RESET}\n")
                continue

            rl = usage_data.get("rate_limit") or {}
            p = rl.get("primary_window") or {}
            s = rl.get("secondary_window") or {}

            p_used = float(p.get("used_percent", 0))
            s_used = float(s.get("used_percent", 0))
            p_left = max(0.0, 100.0 - p_used)
            s_left = max(0.0, 100.0 - s_used)
            plan = usage_data.get("plan_type") or "?"

            score = min(p_left, s_left)
            rows.append((score, p_left, s_left, name))

            active_badge = f" {C_DIM}{C_CYAN}(active){C_RESET}" if is_active else ""
            print(f"{mark} {name_str} {C_DIM}[{plan}]{C_RESET}{active_badge}")

            # Animated bar reveal if in TTY
            if is_tty:
                for step in range(1, 11):
                    ratio = step / 10.0
                    b5 = progress_bar(p_left, ratio)
                    val5 = p_left * ratio
                    sys.stdout.write(f"\r\033[K   {C_DIM}5h{C_RESET}  {b5} {C_BOLD}{val5:5.1f}%{C_RESET} left   {C_DIM}reset {reset_in(p)}{C_RESET}")
                    sys.stdout.flush()
                    time.sleep(0.008)
                print()
                for step in range(1, 11):
                    ratio = step / 10.0
                    b7 = progress_bar(s_left, ratio)
                    val7 = s_left * ratio
                    sys.stdout.write(f"\r\033[K   {C_DIM}7d{C_RESET}  {b7} {C_BOLD}{val7:5.1f}%{C_RESET} left   {C_DIM}reset {reset_in(s)}{C_RESET}")
                    sys.stdout.flush()
                    time.sleep(0.008)
                print()
            else:
                b5 = progress_bar(p_left)
                b7 = progress_bar(s_left)
                print(f"   5h  {b5} {p_left:5.1f}% left   reset {reset_in(p)}")
                print(f"   7d  {b7} {s_left:5.1f}% left   reset {reset_in(s)}")

            # Resets
            credits_list = reset_data.get("credits", []) if isinstance(reset_data, dict) else []
            avail = reset_data.get("available_count") if isinstance(reset_data, dict) else None
            rc = usage_data.get("rate_limit_reset_credits") or {}
            app_avail = rc.get("applicable_available_count", 0)
            if avail is None:
                avail = rc.get("available_count", 0)

            if avail > 0:
                earliest_exp = None
                for c in credits_list:
                    if c.get("status") == "available" and c.get("expires_at"):
                        exp_str = c.get("expires_at")
                        if not earliest_exp or exp_str < earliest_exp:
                            earliest_exp = exp_str

                exp_text = f" {C_DIM}• {fmt_expiry(earliest_exp)}{C_RESET}" if earliest_exp else ""
                status_note = f" {C_BRIGHT_GREEN}(can apply now){C_RESET}" if app_avail > 0 else ""
                print(f"   {C_BRIGHT_YELLOW}⚡ Resets:{C_RESET} {C_BOLD}{avail} available{C_RESET}{exp_text}{status_note}")
            else:
                print(f"   {C_DIM}⚡ Resets: 0{C_RESET}")

            credits = usage_data.get("credits")
            if isinstance(credits, dict) and credits.get("balance") is not None:
                bal = str(credits.get("balance"))
                if bal != "0":
                    print(f"   {C_BRIGHT_YELLOW}💵 Credits:{C_RESET} ${bal}")
            print()

        if rows:
            best = max(rows, key=lambda x: (x[0], x[1] + x[2]))
            print(f"{C_GRAY}────────────────────────────────────────────────────────────────{C_RESET}")
            print(f"🏆 {C_BOLD}Recommended:{C_RESET} {C_BRIGHT_GREEN}{best[3]}{C_RESET}  {C_DIM}(5h: {best[1]:.1f}% / 7d: {best[2]:.1f}% remaining){C_RESET}\n")
    finally:
        if is_tty:
            sys.stdout.write("\033[?25h")  # Restore cursor
            sys.stdout.flush()

def pick_account():
    save_active_auth()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        die(f"Could not access accounts directory: {e}")

    if not files:
        die("No saved accounts found. First run: csm add <name>")

    is_tty = sys.stdout.isatty()
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    if is_tty:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(files)) as executor:
            futures = {executor.submit(fetch_account_data, p): p for p in files}
            spin_idx = 0
            while not all(f.done() for f in futures):
                if is_tty:
                    spin = spinner[spin_idx % len(spinner)]
                    sys.stdout.write(f"\r\033[K{C_BRIGHT_CYAN}{spin}{C_RESET}  {C_BOLD}Evaluating healthiest Codex account...{C_RESET}")
                    sys.stdout.flush()
                time.sleep(0.05)
                spin_idx += 1

            for f in futures:
                name, usage_data, _, err = f.result()
                if usage_data and not err:
                    rl = usage_data.get("rate_limit") or {}
                    pw = rl.get("primary_window") or {}
                    sw = rl.get("secondary_window") or {}
                    pleft = max(0.0, 100 - float(pw.get("used_percent", 0)))
                    sleft = max(0.0, 100 - float(sw.get("used_percent", 0)))
                    score = (min(pleft, sleft), pleft + sleft)
                    results.append((score, name))

        if is_tty:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
    finally:
        if is_tty:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    if not results:
        die("Could not retrieve valid usage metrics from any saved accounts.")

    best = max(results, key=lambda x: x[0])
    picked = best[1]
    print(f"\n🏆 {C_BOLD}Best account found:{C_RESET} {C_BRIGHT_GREEN}{picked}{C_RESET}")
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
    cache_buster = int(time.time())
    download_url = f"https://raw.githubusercontent.com/mazisel/csm/main/csm?t={cache_buster}"
    
    try:
        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "csm-updater",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
        )
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
