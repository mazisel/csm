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
import select
import concurrent.futures
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.platform == "win32" and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

VERSION = "2.7.0"
APP_NAME = "Codex"
CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
STORE_DIR = Path.home() / ".codex-multi"
ACCOUNTS_DIR = STORE_DIR / "accounts"
ACTIVE_FILE = STORE_DIR / "active"

USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
RESET_CREDITS_URL = "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
AUTH_URL = "https://auth.openai.com/oauth/token"
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"

# ANSI Colors & Styling
def rgb(r, g, b): return f"\033[38;2;{r};{g};{b}m"
def rgb_bg(r, g, b): return f"\033[48;2;{r};{g};{b}m"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# Catppuccin / Neon Palette
C_MAUVE   = rgb(203, 166, 247)
C_LAVENDER= rgb(180, 190, 254)
C_BLUE    = rgb(137, 180, 250)
C_CYAN    = rgb(137, 220, 235)
C_TEAL    = rgb(148, 226, 213)
C_GREEN   = rgb(166, 227, 161)
C_YELLOW  = rgb(249, 226, 175)
C_PEACH   = rgb(250, 179, 135)
C_RED     = rgb(243, 139, 168)
C_TEXT    = rgb(205, 214, 244)
C_SUBTEXT = rgb(166, 173, 200)
C_GRAY    = rgb(108, 112, 134)
C_SURFACE = rgb(69, 71, 90)
C_MANTLE  = rgb(30, 30, 46)
C_WHITE   = rgb(255, 255, 255)
C_BRIGHT_CYAN = rgb(137, 220, 235)

def strip_ansi(s: str) -> str:
    return re.sub(r"\033\[[0-9;]*m", "", s)

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
    print(f"\n{C_RED}❌ {msg}{RESET}", file=sys.stderr)
    sys.exit(1)

def info(msg: str):
    print(f"{C_CYAN}→{RESET} {msg}")

def safe_name(name: str) -> str:
    if not re.match(r"^[A-Za-z0-9._-]+$", name):
        die("Account name may only contain letters, numbers, dot, underscore, and dash.")
    return name

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
        fill_col = C_GREEN
    elif left_pct >= 20:
        fill_col = C_YELLOW
    else:
        fill_col = C_RED
        
    blocks = "█" * filled
    spaces = "░" * unfilled
    return f"{fill_col}{blocks}{C_SURFACE}{spaces}{RESET}"

def print_banner(total_accs: int = 0, total_resets: int = 0, active_acc: str = ""):
    banner = [
        "  ██████╗███████╗███╗   ███╗",
        " ██╔════╝██╔════╝████╗ ████║",
        " ██║     ███████╗██╔████╔██║",
        " ╚██████╗███████║██║ ╚═╝ ██║",
        "  ╚═════╝╚══════╝╚═╝     ╚═╝"
    ]
    gradient = [C_MAUVE, C_LAVENDER, C_BLUE, C_CYAN, C_GREEN]
    
    print()
    for line, col in zip(banner, gradient):
        print(f"{col}{BOLD}{line}{RESET}")
    print()
    print(f"  {C_CYAN}◆{RESET} {BOLD}{C_TEXT}Codex Account Engine{RESET} {DIM}v{VERSION}{RESET}")
    if total_accs > 0:
        act_str = f"{C_GREEN}{active_acc}{RESET}" if active_acc else f"{DIM}(none){RESET}"
        resets_str = f"{C_YELLOW}⚡ {total_resets} resets{RESET}" if total_resets > 0 else f"{DIM}⚡ 0 resets{RESET}"
        print(f"  {DIM}Fleet:{RESET} {BOLD}{total_accs}{RESET} accounts {DIM}•{RESET} {resets_str} {DIM}• Active:{RESET} {act_str}")
    print(f"  {C_SURFACE}{'─' * 62}{RESET}\n")

def usage():
    print_banner(0, 0, "")
    print(f"""{BOLD}Commands:{RESET}
  {C_GREEN}csm add <name>{RESET}          Login to a Codex account safely & isolate credentials
  {C_GREEN}csm refresh <name>{RESET}      Re-authenticate an account without revoking others
  {C_GREEN}csm use [name]{RESET}          Interactive switcher or switch to specified account
  {C_GREEN}csm pick{RESET}                Auto-evaluate & activate the account with highest quota
  {C_GREEN}csm status{RESET}              Live dashboard of 5h/7d quotas, reset timers & reset bank
  {C_GREEN}csm watch [sec]{RESET}         Live auto-refreshing monitor dashboard (default: 15s)
  {C_GREEN}csm list{RESET}                List all saved accounts
  {C_GREEN}csm current{RESET}             Show active account name
  {C_GREEN}csm remove <name>{RESET}       Delete a saved account
  {C_GREEN}csm completion install{RESET}  Install shell autocompletion for zsh/bash/fish/powershell
  {C_GREEN}csm update{RESET}              Update csm to latest release from GitHub
  {C_GREEN}csm version{RESET}             Display version info
  {C_GREEN}csm help{RESET}                Show this manual

{BOLD}Examples:{RESET}
  csm status
  csm watch
  csm use
  csm pick
  csm completion install""")

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

        print(f"\n🔐 {BOLD}Opening isolated Codex login for '{name}'...{RESET}")
        print(f"   {DIM}Existing credentials in {CODEX_HOME / 'auth.json'} are protected.{RESET}\n")

        env = os.environ.copy()
        env["CODEX_HOME"] = str(tmp_dir)

        res = subprocess.run([codex_bin, "login"], env=env)
        if res.returncode != 0:
            die("Login was canceled or failed.")

        tmp_auth = tmp_dir / "auth.json"
        if not tmp_auth.exists():
            die("Login completed but auth.json was not found in temp directory.")

        target = ACCOUNTS_DIR / f"{name}.json"
        shutil.copy2(tmp_auth, target)
        safe_chmod(target, 0o600)
        print(f"\n{C_GREEN}✅ Account '{name}' successfully saved!{RESET}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def restart_codex():
    info("Reloading Codex / ChatGPT Desktop App...")
    sys_plat = platform.system()
    if sys_plat == "Darwin":
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application id "com.openai.codex" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application "ChatGPT" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/osascript", "-e", 'tell application "Codex" to quit'], capture_output=True)
        subprocess.run(["/usr/bin/pkill", "-f", "codex.*app-server"], capture_output=True)
        time.sleep(1.5)
        
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

    print(f"\n{C_GREEN}✅ Active Codex account:{RESET} {BOLD}{C_WHITE}{name}{RESET}")
    print(f"   {DIM}Project and session history under ~/.codex were preserved.{RESET}")

    if restart:
        restart_codex()
    else:
        print(f"   {DIM}Restart Codex Desktop App manually to apply changes.{RESET}")

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

def render_card(name: str, plan: str, is_active: bool, p_left: float, s_left: float, p_reset: str, s_reset: str, extra_lines: list = None, animate: bool = True):
    width = 68
    dash = "─"
    is_tty = sys.stdout.isatty() and animate
    
    if is_active:
        border_col = C_CYAN
        title_col = f"{BOLD}{C_WHITE}"
        badge = f"{rgb_bg(30, 102, 245)}{BOLD}{C_WHITE} ACTIVE {RESET}"
        dot = f"{C_GREEN}●{RESET}"
    else:
        border_col = C_SURFACE
        title_col = f"{BOLD}{C_TEXT}"
        badge = f"{DIM}[{plan.upper()}]{RESET}"
        dot = " "

    header_left = f"╭─ [ {dot} {title_col}{name}{RESET} ]"
    right_str = f"[ {badge} ]─╮"
    
    left_len = len(strip_ansi(header_left))
    right_len = len(strip_ansi(right_str))
    fill_len = max(2, width - left_len - right_len)
    
    print(f"{border_col}{header_left}{dash * fill_len}{right_str}{RESET}")
    
    if is_tty and (p_left > 0 or s_left > 0):
        for step in range(1, 9):
            ratio = step / 8.0
            b5 = progress_bar(p_left, ratio)
            val5 = p_left * ratio
            content_5 = f"  {DIM}5h Limit{RESET}   {b5}  {BOLD}{val5:5.1f}%{RESET} {DIM}left   reset {p_reset}{RESET}"
            pad1 = width - len(strip_ansi(content_5)) - 2
            sys.stdout.write(f"\r\033[K{border_col}│{RESET}{content_5}{' ' * max(0, pad1)}{border_col}│{RESET}")
            sys.stdout.flush()
            time.sleep(0.007)
        print()
        
        for step in range(1, 9):
            ratio = step / 8.0
            b7 = progress_bar(s_left, ratio)
            val7 = s_left * ratio
            content_7 = f"  {DIM}7d Limit{RESET}   {b7}  {BOLD}{val7:5.1f}%{RESET} {DIM}left   reset {s_reset}{RESET}"
            pad2 = width - len(strip_ansi(content_7)) - 2
            sys.stdout.write(f"\r\033[K{border_col}│{RESET}{content_7}{' ' * max(0, pad2)}{border_col}│{RESET}")
            sys.stdout.flush()
            time.sleep(0.007)
        print()
    else:
        bar5 = progress_bar(p_left)
        bar7 = progress_bar(s_left)
        content_5 = f"  {DIM}5h Limit{RESET}   {bar5}  {BOLD}{p_left:5.1f}%{RESET} {DIM}left   reset {p_reset}{RESET}"
        pad1 = width - len(strip_ansi(content_5)) - 2
        print(f"{border_col}│{RESET}{content_5}{' ' * max(0, pad1)}{border_col}│{RESET}")
        
        content_7 = f"  {DIM}7d Limit{RESET}   {bar7}  {BOLD}{s_left:5.1f}%{RESET} {DIM}left   reset {s_reset}{RESET}"
        pad2 = width - len(strip_ansi(content_7)) - 2
        print(f"{border_col}│{RESET}{content_7}{' ' * max(0, pad2)}{border_col}│{RESET}")
    
    if extra_lines:
        for line in extra_lines:
            if not line:
                continue
            pad = width - len(strip_ansi(line)) - 4
            print(f"{border_col}│{RESET}  {line}{' ' * max(0, pad)}{border_col}│{RESET}")
        
    print(f"{border_col}╰{dash * (width - 2)}╯{RESET}\n")

def fetch_all_accounts_data(files: list, is_tty: bool, status_msg: str = "Checking Codex quotas"):
    results = {}
    done_count = 0
    spinner = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(files)) as executor:
        futures = {executor.submit(fetch_account_data, p): p for p in files}
        spin_idx = 0
        while not all(f.done() for f in futures):
            done_count = sum(1 for f in futures if f.done())
            if is_tty:
                spin = spinner[spin_idx % len(spinner)]
                sys.stdout.write(f"\r\033[K  {C_CYAN}{spin}{RESET}  {BOLD}{status_msg}...{RESET} {DIM}({done_count}/{len(files)}){RESET}")
                sys.stdout.flush()
            time.sleep(0.045)
            spin_idx += 1

        for f in futures:
            name, usage_data, reset_data, err = f.result()
            results[name] = (usage_data, reset_data, err)

    if is_tty:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        
    return results

def render_dashboard(results: dict, files: list, active: str, animate: bool = True):
    total_resets = 0
    for name, (_, reset_data, _) in results.items():
        if isinstance(reset_data, dict):
            total_resets += reset_data.get("available_count", 0)

    print_banner(len(files), total_resets, active)

    rows = []
    for path in files:
        name = path.stem
        is_active = (name == active)
        usage_data, reset_data, err = results.get(name, (None, None, None))
        
        if err or not usage_data:
            border_col = C_SURFACE
            print(f"{border_col}╭─ [ {name} ]{'─' * (58 - len(name))}─╮{RESET}")
            print(f"{border_col}│{RESET}  {C_RED}❌ Could not retrieve usage: {err}{RESET}")
            print(f"{border_col}╰{'─' * 60}╯{RESET}\n")
            continue

        rl = usage_data.get("rate_limit") or {}
        pw = rl.get("primary_window") or {}
        sw = rl.get("secondary_window") or {}

        p_used = float(pw.get("used_percent", 0))
        s_used = float(sw.get("used_percent", 0))
        p_left = max(0.0, 100.0 - p_used)
        s_left = max(0.0, 100.0 - s_used)
        plan = usage_data.get("plan_type") or "plus"

        score = min(p_left, s_left)
        rows.append((score, p_left, s_left, name))

        # Reset credits & expiration handling
        credits_list = reset_data.get("credits", []) if isinstance(reset_data, dict) else []
        avail = reset_data.get("available_count") if isinstance(reset_data, dict) else None
        rc = usage_data.get("rate_limit_reset_credits") or {}
        app_avail = rc.get("applicable_available_count", 0)
        if avail is None:
            avail = rc.get("available_count", 0)

        extra_lines = []
        available_credits = [c for c in credits_list if c.get("status") in ("available", None)]
        available_credits.sort(key=lambda x: x.get("expires_at") or "9999")

        status_note = f" {C_GREEN}(can apply now){RESET}" if app_avail > 0 else ""

        if len(available_credits) > 1:
            extra_lines.append(f"{C_YELLOW}⚡ Resets:{RESET} {BOLD}{len(available_credits)} available{RESET}{status_note}")
            for i, c in enumerate(available_credits):
                is_last = (i == len(available_credits) - 1)
                tree_char = "└─" if is_last else "├─"
                exp_str = c.get("expires_at")
                exp_text = fmt_expiry(exp_str) if exp_str else "no expiry date"
                extra_lines.append(f"   {DIM}{tree_char}{RESET} {C_YELLOW}#{i+1}:{RESET} {DIM}{exp_text}{RESET}")
        elif len(available_credits) == 1:
            c = available_credits[0]
            exp_str = c.get("expires_at")
            exp_text = f" {DIM}• {fmt_expiry(exp_str)}{RESET}" if exp_str else ""
            extra_lines.append(f"{C_YELLOW}⚡ Resets:{RESET} {BOLD}1 available{RESET}{exp_text}{status_note}")
        elif avail > 0:
            extra_lines.append(f"{C_YELLOW}⚡ Resets:{RESET} {BOLD}{avail} available{RESET}{status_note}")
        else:
            extra_lines.append(f"{DIM}⚡ Resets: 0{RESET}")

        credits_obj = usage_data.get("credits")
        if isinstance(credits_obj, dict) and credits_obj.get("balance") is not None:
            bal = str(credits_obj.get("balance"))
            if bal != "0":
                extra_lines.append(f"{C_YELLOW}💵 Credits:{RESET} ${bal}")

        render_card(name, plan, is_active, p_left, s_left, reset_in(pw), reset_in(sw), extra_lines=extra_lines, animate=animate)

    if rows:
        best = max(rows, key=lambda x: (x[0], x[1] + x[2]))
        width = 68
        card_top = f"{C_GREEN}╭─ [ 🏆 RECOMMENDED SWITCH ]{'─' * (width - 29)}─╮{RESET}"
        content = f"  {BOLD}{C_WHITE}{best[3]}{RESET} {DIM}→ {C_GREEN}{best[1]:.1f}%{RESET}{DIM} 5h / {C_GREEN}{best[2]:.1f}%{RESET}{DIM} 7d capacity available{RESET}"
        pad = width - len(strip_ansi(content)) - 2
        card_bot = f"{C_GREEN}╰{'─' * (width - 2)}╯{RESET}"
        
        print(card_top)
        print(f"{C_GREEN}│{RESET}{content}{' ' * max(0, pad)}{C_GREEN}│{RESET}")
        action_line = f"  {DIM}Run {C_CYAN}csm use {best[3]}{RESET}{DIM} or {C_CYAN}csm pick{RESET}{DIM} to activate.{RESET}"
        pad_act = width - len(strip_ansi(action_line)) - 2
        print(f"{C_GREEN}│{RESET}{action_line}{' ' * max(0, pad_act)}{C_GREEN}│{RESET}")
        print(card_bot + "\n")

def status_accounts():
    save_active_auth()
    active = get_active_account()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        die(f"Could not access accounts directory: {e}")

    if not files:
        print(f"{C_YELLOW}No saved accounts found. Run: csm add <name>{RESET}")
        return

    is_tty = sys.stdout.isatty()
    if is_tty:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    try:
        results = fetch_all_accounts_data(files, is_tty, f"Checking Codex quotas across {len(files)} accounts")
        render_dashboard(results, files, active, animate=True)
    finally:
        if is_tty:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

def check_quit_key(timeout_sec: float = 1.0) -> bool:
    if os.name == "nt":
        import msvcrt
        start = time.time()
        while time.time() - start < timeout_sec:
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch in (b"q", b"Q", b"\x03", b"\x1b"):
                    return True
            time.sleep(0.05)
        return False
    else:
        import termios, tty
        if not sys.stdin.isatty():
            time.sleep(timeout_sec)
            return False
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            rlist, _, _ = select.select([sys.stdin], [], [], timeout_sec)
            if rlist:
                ch = sys.stdin.read(1)
                if ch in ("q", "Q", "\x03", "\x1b"):
                    return True
            return False
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def watch_accounts(interval: int = 15):
    save_active_auth()
    try:
        files = sorted(ACCOUNTS_DIR.glob("*.json"))
    except Exception as e:
        die(f"Could not access accounts directory: {e}")

    if not files:
        die("No saved accounts found. Run: csm add <name>")

    is_tty = sys.stdout.isatty()
    if is_tty:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    try:
        first_run = True
        while True:
            active = get_active_account()
            if is_tty:
                sys.stdout.write("\033[2J\033[H") # Clear screen & home cursor
                sys.stdout.flush()

            results = fetch_all_accounts_data(files, is_tty, f"Refreshing Codex quotas across {len(files)} accounts")
            if is_tty:
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.flush()

            render_dashboard(results, files, active, animate=first_run)
            first_run = False

            # Live Countdown Loop
            for remaining in range(interval, 0, -1):
                if is_tty:
                    sys.stdout.write(f"\r\033[K  {C_CYAN}⟳{RESET} {BOLD}Auto-refreshing in {remaining}s...{RESET} {DIM}(Press {C_WHITE}Q{RESET}{DIM} or {C_WHITE}Ctrl+C{RESET}{DIM} to exit){RESET}")
                    sys.stdout.flush()
                
                if check_quit_key(1.0):
                    if is_tty:
                        sys.stdout.write("\r\033[K\n")
                    print(f"  {DIM}Watch mode stopped.{RESET}\n")
                    return
    except KeyboardInterrupt:
        if is_tty:
            sys.stdout.write("\r\033[K\n")
        print(f"  {DIM}Watch mode stopped.{RESET}\n")
    finally:
        if is_tty:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

def read_key():
    if os.name == "nt":
        import msvcrt
        k = msvcrt.getch()
        if k in (b"\x00", b"\xe0"):
            k2 = msvcrt.getch()
            if k2 == b"H": return "UP"
            elif k2 == b"P": return "DOWN"
        elif k == b"\r": return "ENTER"
        elif k in (b"\x03", b"q", b"Q"): return "QUIT"
        return "OTHER"
    else:
        import termios, tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A": return "UP"
                    elif ch3 == "B": return "DOWN"
            elif ch in ("\r", "\n"):
                return "ENTER"
            elif ch in ("\x03", "q", "Q"):
                return "QUIT"
            return "OTHER"
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

def interactive_picker():
    files = sorted(ACCOUNTS_DIR.glob("*.json"))
    if not files:
        die("No saved accounts found. First run: csm add <name>")

    active = get_active_account()
    account_names = [f.stem for f in files]
    
    if not sys.stdout.isatty():
        list_accounts()
        return

    print_banner(len(account_names), 0, active)
    print(f"  {BOLD}Select Codex account to switch to:{RESET} {DIM}(Use ↑/↓ arrows, Enter to select, Q to quit){RESET}\n")

    selected = 0
    if active in account_names:
        selected = account_names.index(active)

    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

    try:
        while True:
            for i, name in enumerate(account_names):
                is_curr = (i == selected)
                is_act = (name == active)
                
                pointer = f"{C_CYAN}❯{RESET}" if is_curr else " "
                dot = f"{C_GREEN}●{RESET}" if is_act else f"{DIM}○{RESET}"
                act_badge = f" {C_DIM}(active){RESET}" if is_act else ""
                
                if is_curr:
                    print(f"  {pointer} {dot} {BOLD}{C_BRIGHT_CYAN}{name}{RESET}{act_badge}")
                else:
                    print(f"  {pointer} {dot} {C_TEXT}{name}{RESET}{act_badge}")

            key = read_key()
            if key == "UP":
                selected = (selected - 1) % len(account_names)
            elif key == "DOWN":
                selected = (selected + 1) % len(account_names)
            elif key == "ENTER":
                chosen = account_names[selected]
                print(f"\n{C_CYAN}→ Selected:{RESET} {BOLD}{chosen}{RESET}")
                switch_account(chosen, restart=True)
                break
            elif key == "QUIT":
                print(f"\n{DIM}Canceled.{RESET}")
                break

            sys.stdout.write(f"\033[{len(account_names)}A")
            sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25h")
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
    if is_tty:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

    results = []
    try:
        fetch_map = fetch_all_accounts_data(files, is_tty, f"Evaluating healthiest Codex account across {len(files)} accounts")
        for name, (usage_data, _, err) in fetch_map.items():
            if usage_data and not err:
                rl = usage_data.get("rate_limit") or {}
                pw = rl.get("primary_window") or {}
                sw = rl.get("secondary_window") or {}
                pleft = max(0.0, 100 - float(pw.get("used_percent", 0)))
                sleft = max(0.0, 100 - float(sw.get("used_percent", 0)))
                score = (min(pleft, sleft), pleft + sleft)
                results.append((score, pleft, sleft, name))
    finally:
        if is_tty:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

    if not results:
        die("Could not retrieve valid usage metrics from any saved accounts.")

    best = max(results, key=lambda x: x[0])
    picked = best[3]
    print(f"\n🏆 {BOLD}Healthiest account found:{RESET} {C_GREEN}{picked}{RESET} {DIM}(5h: {best[1]:.1f}% / 7d: {best[2]:.1f}% remaining){RESET}")
    switch_account(picked, restart=True)

def list_accounts():
    active = get_active_account()
    files = sorted(ACCOUNTS_DIR.glob("*.json"))
    print_banner(len(files), 0, active)
    if not files:
        print(f"  {DIM}(no accounts saved yet — run: csm add <name>){RESET}\n")
        return
    for f in files:
        name = f.stem
        if name == active:
            print(f"  {C_GREEN}●{RESET} {BOLD}{C_WHITE}{name}{RESET} {C_CYAN}(active){RESET}")
        else:
            print(f"  {DIM}○{RESET} {C_TEXT}{name}{RESET}")
    print()

def list_raw_accounts():
    files = sorted(ACCOUNTS_DIR.glob("*.json"))
    for f in files:
        print(f.stem)

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
    print(f"{C_GREEN}✅ Account '{name}' removed.{RESET}")

def get_completion_script(shell: str) -> str:
    if shell == "zsh":
        return """#compdef csm

_csm() {
    local curcontext="$curcontext" state line
    typeset -A opt_args

    _arguments -C \\
        '1: :->command' \\
        '*: :->args'

    case $state in
        command)
            local -a subcommands
            subcommands=(
                'add:Login to a Codex account safely'
                'use:Switch active Codex account'
                'switch:Interactive switcher or switch to specified account'
                'pick:Auto-evaluate & switch to healthiest account'
                'status:Live dashboard of rate limits & quota'
                'watch:Live auto-refreshing monitor dashboard'
                'list:List all saved accounts'
                'current:Show active account name'
                'refresh:Re-authenticate an account'
                'remove:Delete a saved account'
                'completion:Install shell autocompletion'
                'update:Update csm to latest version'
                'version:Display version info'
                'help:Show help'
            )
            _describe -t subcommands 'csm commands' subcommands
            ;;
        args)
            case $words[2] in
                use|switch|remove|refresh)
                    local -a accounts
                    accounts=(${(f)"$(csm _list_raw 2>/dev/null)"})
                    _describe -t accounts 'saved accounts' accounts
                    ;;
                completion)
                    local -a subopts
                    subopts=('install:Install autocompletion automatically' 'zsh:Print zsh script' 'bash:Print bash script' 'fish:Print fish script' 'powershell:Print powershell script')
                    _describe -t subopts 'completion options' subopts
                    ;;
            esac
            ;;
    esac
}

compdef _csm csm
"""
    elif shell == "bash":
        return """_csm_completions() {
    local cur prev commands
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="add use switch pick status watch list current refresh remove update completion version help"

    if [ $COMP_CWORD -eq 1 ]; then
        COMPREPLY=($(compgen -W "${commands}" -- "${cur}"))
        return 0
    fi

    case "${prev}" in
        use|switch|remove|refresh)
            local accounts
            accounts=$(csm _list_raw 2>/dev/null)
            COMPREPLY=($(compgen -W "${accounts}" -- "${cur}"))
            return 0
            ;;
        completion)
            COMPREPLY=($(compgen -W "install zsh bash fish powershell" -- "${cur}"))
            return 0
            ;;
    esac
}
complete -F _csm_completions csm
"""
    elif shell == "fish":
        return """function __fish_csm_accounts
    csm _list_raw 2>/dev/null
end

complete -c csm -f
complete -c csm -n "__fish_use_subcommand" -a "add use switch pick status watch list current refresh remove update completion version help"
complete -c csm -n "__fish_seen_subcommand_from use switch remove refresh" -a "(__fish_csm_accounts)"
complete -c csm -n "__fish_seen_subcommand_from completion" -a "install zsh bash fish powershell"
"""
    elif shell == "powershell":
        return """Register-ArgumentCompleter -Native -CommandName csm -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @('add','use','switch','pick','status','watch','list','current','refresh','remove','update','completion','version','help')
    $tokens = $commandAst.Tokens
    if ($tokens.Count -le 2) {
        $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
            [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
        }
    } else {
        $prev = $tokens[1].Value
        if ($prev -in @('use','switch','remove','refresh')) {
            $accounts = csm _list_raw
            $accounts | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
                [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
            }
        }
    }
}
"""
    return ""

def install_completion():
    sh = os.environ.get("SHELL", "")
    shell_name = "zsh" if "zsh" in sh else ("bash" if "bash" in sh else ("fish" if "fish" in sh else ""))
    if sys.platform == "win32":
        shell_name = "powershell"

    if not shell_name:
        shell_name = "zsh"

    print(f"\n⚙️  {BOLD}Installing autocompletion for {C_CYAN}{shell_name}{RESET}...")

    home = Path.home()
    if shell_name == "zsh":
        zfunc_dir = home / ".zfunc"
        zfunc_dir.mkdir(parents=True, exist_ok=True)
        comp_file = zfunc_dir / "_csm"
        comp_file.write_text(get_completion_script("zsh"), encoding="utf-8")

        zshrc = home / ".zshrc"
        rc_lines = zshrc.read_text(encoding="utf-8") if zshrc.exists() else ""
        additions = []
        if "fpath=(~/.zfunc $fpath)" not in rc_lines and "fpath=(~/.zfunc" not in rc_lines:
            additions.append('fpath=(~/.zfunc $fpath)')
        if "autoload -Uz compinit" not in rc_lines:
            additions.append('autoload -Uz compinit && compinit')
            
        if additions:
            with zshrc.open("a", encoding="utf-8") as f:
                f.write("\n# csm autocompletion\n" + "\n".join(additions) + "\n")

        print(f"{C_GREEN}✅ Zsh completion script installed to {comp_file}!{RESET}")
        print(f"👉 Please reload your terminal or run: {BOLD}source ~/.zshrc{RESET}\n")

    elif shell_name == "bash":
        bashrc = home / ".bashrc"
        snippet = '\neval "$(csm completion bash)"\n'
        rc_lines = bashrc.read_text(encoding="utf-8") if bashrc.exists() else ""
        if "csm completion bash" not in rc_lines:
            with bashrc.open("a", encoding="utf-8") as f:
                f.write(snippet)
        print(f"{C_GREEN}✅ Bash completion added to ~/.bashrc!{RESET}")
        print(f"👉 Please reload your terminal or run: {BOLD}source ~/.bashrc{RESET}\n")

    elif shell_name == "fish":
        fish_dir = home / ".config" / "fish" / "completions"
        fish_dir.mkdir(parents=True, exist_ok=True)
        comp_file = fish_dir / "csm.fish"
        comp_file.write_text(get_completion_script("fish"), encoding="utf-8")
        print(f"{C_GREEN}✅ Fish completion installed to {comp_file}!{RESET}\n")

    elif shell_name == "powershell":
        print(f"{C_GREEN}✅ Add the following to your PowerShell $PROFILE:{RESET}\n")
        print(get_completion_script("powershell"))

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
        print(f"{C_GREEN}✅ csm successfully updated to latest version at {target_path}!{RESET}")
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
    cmd = args[0] if args else "status"

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

    elif cmd in ("use", "switch"):
        if len(args) == 1:
            interactive_picker()
        else:
            name = safe_name(args[1])
            no_restart = "--no-restart" in args[2:]
            switch_account(name, restart=not no_restart)

    elif cmd == "list":
        list_accounts()

    elif cmd == "_list_raw":
        list_raw_accounts()

    elif cmd == "status":
        status_accounts()

    elif cmd == "watch":
        sec = 15
        if len(args) > 1:
            try:
                sec = max(2, int(args[1]))
            except ValueError:
                pass
        watch_accounts(interval=sec)

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

    elif cmd == "completion":
        if len(args) > 1:
            sub = args[1].lower()
            if sub == "install":
                install_completion()
            elif sub in ("zsh", "bash", "fish", "powershell"):
                print(get_completion_script(sub))
            else:
                die("Usage: csm completion [install|zsh|bash|fish|powershell]")
        else:
            install_completion()

    elif cmd == "update":
        update_csm()

    elif cmd in ("version", "-v", "--version"):
        print(f"{BOLD}csm{RESET} version {C_GREEN}v{VERSION}{RESET}")

    elif cmd in ("help", "-h", "--help"):
        usage()

    else:
        usage()
        sys.exit(1)

if __name__ == "__main__":
    main()
