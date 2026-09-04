# ⚡ csm (Codex Account Switcher & Quota Manager)

[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey.svg)](https://github.com/mazisel/csm)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.7.0-green.svg)](https://github.com/mazisel/csm)

A powerful, safe, cross-platform **Multi-Account Switcher & Real-Time Quota Manager** for OpenAI Codex on **macOS**, **Windows**, and **Linux**.

<p align="center">
  <img src="demo.gif" alt="csm Terminal Demo" width="700">
</p>

Easily switch between personal, work, and secondary accounts, monitor 5-hour and 7-day rate limits live, and let `csm` automatically pick the account with the most remaining quota.

---

## ✨ Features

- 🌐 **Cross-Platform:** Works natively on **macOS**, **Windows (PowerShell & CMD)**, and **Linux** with zero external pip dependencies.
- 🔄 **Zero-Disruption Account Switching:** Switch active Codex accounts in milliseconds without losing project history or session data.
- 🎮 **Interactive Arrow-Key Switcher (`csm use`):** Select accounts interactively using `↑/↓` arrow keys with live status previews.
- 📊 **Live Quota & Rate-Limit Visualizer (`csm status`):** Modern Cyberpunk cards with smooth progress bar fill animations, reset timers, and multi-credit expiration breakdown.
- ⏱️ **Live Watch / Monitor Mode (`csm watch`):** Real-time auto-refreshing dashboard with live countdown ticker and non-blocking exit.
- ⌨️ **Shell Tab Autocompletion (`csm completion install`):** Tab completion for zsh, bash, fish, and PowerShell.
- 🏆 **Smart Auto-Pick (`csm pick`):** Automatically evaluates all your accounts concurrently and switches to the healthiest one.
- 🔐 **Isolated Safe Login:** Uses isolated temporary credential sandboxes during `csm add` to prevent existing refresh tokens from being revoked by OpenAI.
- 🖥️ **Codex Desktop App Integration:** Automatically restarts the macOS or Windows Codex desktop app to apply the newly switched account immediately.
- 🚀 **Self-Updating:** Keep `csm` up to date with a single `csm update` command.

---

## 📦 Quick Installation

### 🍎 macOS & 🐧 Linux (Terminal)
Run this one-liner in your terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/mazisel/csm/main/install.sh | bash
```

### 🪟 Windows (PowerShell)
Open PowerShell and run:
```powershell
irm https://raw.githubusercontent.com/mazisel/csm/main/install.ps1 | iex
```

---

## 🚀 Quick Start

### 1. Add your accounts safely
```bash
csm add personal
csm add work
```
*(Each account will open a browser login safely without overriding or revoking other accounts).*

### 2. View remaining quotas and limits
```bash
csm status
```

**Example Output:**
```text
  ██████╗███████╗███╗   ███╗
 ██╔════╝██╔════╝████╗ ████║
 ██║     ███████╗██╔████╔██║
 ╚██████╗███████║██║ ╚═╝ ██║
  ╚═════╝╚══════╝╚═╝     ╚═╝

  ◆ Codex Account Engine v2.7.0
  Fleet: 4 accounts • ⚡ 6 resets • Active: personal
  ──────────────────────────────────────────────────────────────

╭─ [ ● personal ]─────────────────────────────────────[  ACTIVE  ]─╮
│  5h Limit   ████████████████████  100.0% left   reset in 5h      │
│  7d Limit   ████░░░░░░░░░░░░░░░░   20.0% left   reset in 2d 23h  │
│  ⚡ Resets: 2 available                                           │
│     ├─ #1: expires 20 Sep (16d 10h left)                         │
│     └─ #2: expires 04 Oct (29d 12h left)                         │
╰──────────────────────────────────────────────────────────────────╯

╭─ [   work ]───────────────────────────────────────────[ [TEAM] ]─╮
│  5h Limit   ████████████████████  100.0% left   reset in 5h      │
│  7d Limit   ███████████░░░░░░░░░   54.0% left   reset in 4d 7h   │
│  ⚡ Resets: 1 available • expires 04 Oct (29d 11h left)           │
│  💵 Credits: $15.00                                               │
╰──────────────────────────────────────────────────────────────────╯

╭─ [ 🏆 RECOMMENDED SWITCH ]────────────────────────────────────────╮
│  work → 100.0% 5h / 54.0% 7d capacity available                  │
│  Run csm use work or csm pick to activate.                       │
╰──────────────────────────────────────────────────────────────────╯
```

### 3. Switch accounts
```bash
# Interactive menu with arrow keys:
csm use

# Direct switch:
csm use personal

# Or switch without restarting the Desktop App:
csm use work --no-restart
```

### 4. Live Monitor (Watch Mode)
```bash
csm watch       # Auto-refreshes every 15 seconds (Press Q to exit)
csm watch 30    # Custom 30-second interval
```

### 5. Automatically switch to the healthiest account
```bash
csm pick
```

---

## 📖 Command Reference

| Command | Description |
| :--- | :--- |
| `csm add <name>` | Securely login to a new Codex account and save it. |
| `csm refresh <name>` | Re-authenticate an existing account without revoking others. |
| `csm use [name]` | Interactive arrow-key switcher or switch to specified account. |
| `csm use <name> --no-restart` | Switch account without restarting Codex Desktop App. |
| `csm status` | Show live 5h & 7d quota cards, reset timers, and reset expiration dates. |
| `csm watch [sec]` | Live auto-refreshing monitor dashboard (default: 15s, press Q to exit). |
| `csm pick` | Automatically select and switch to the account with the most quota. |
| `csm list` | List all saved accounts and show which one is currently active. |
| `csm current` | Print the name of the currently active account. |
| `csm remove <name>` | Delete a saved account from the local store. |
| `csm completion install` | Install shell autocompletion for `zsh`, `bash`, `fish`, or `powershell`. |
| `csm update` | Update `csm` directly to the latest version from GitHub. |
| `csm version` | Display the installed version of `csm`. |
| `csm help` | Show help and usage instructions. |

---

## 🔒 Security & Storage

- **Local Storage:** All authentication tokens are stored strictly on your local machine under `~/.codex-multi/accounts/` (or `%USERPROFILE%\.codex-multi\accounts\` on Windows).
- **Strict File Permissions:** Files are secured with `chmod 600` on Unix systems.
- **No Telemetry / No Third-party:** `csm` connects directly and solely to official OpenAI API endpoints (`auth.openai.com` and `chatgpt.com`).

---

## 🔄 Updating & Uninstalling

### Update
```bash
csm update
```

### Uninstall
- **macOS / Linux:**
  ```bash
  rm -f ~/.local/bin/csm
  rm -rf ~/.codex-multi ~/.zfunc/_csm
  ```
- **Windows (PowerShell):**
  ```powershell
  Remove-Item -Recurse -Force "$HOME\.local\bin\csm*"
  Remove-Item -Recurse -Force "$HOME\.codex-multi"
  ```

---

## 🇹🇷 Türkçe Açıklama

`csm`, **macOS**, **Windows** ve **Linux** üzerinde OpenAI Codex için geliştirilmiş çoklu hesap geçiş, canlı kota takip ve izleme yöneticisidir.

### Kurulum
- **macOS / Linux:** `curl -fsSL https://raw.githubusercontent.com/mazisel/csm/main/install.sh | bash`
- **Windows (PowerShell):** `irm https://raw.githubusercontent.com/mazisel/csm/main/install.ps1 | iex`

### Temel Komutlar
- **Hesap Ekle:** `csm add hesap_adi`
- **Kotaları Görüntüle:** `csm status`
- **Canlı İzleme (Watch):** `csm watch` (veya `csm watch 30`)
- **Hesap Değiştir:** `csm use` (ok tuşlarıyla) veya `csm use hesap_adi`
- **En Yüksek Kotalı Hesaba Geç:** `csm pick`
- **Tab Tamamlamayı Kur:** `csm completion install`
- **Güncelle:** `csm update`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
