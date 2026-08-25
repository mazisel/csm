# ⚡ csm (Codex Account Switcher & Quota Manager)

[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://apple.com)
[![Shell](https://img.shields.io/badge/shell-zsh-blue.svg)](https://www.zsh.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](https://github.com/mazisel/csm)

A powerful, safe, and lightning-fast **Multi-Account Switcher & Real-Time Quota Manager** for OpenAI Codex on macOS.

Easily switch between personal, work, and secondary accounts, monitor 5-hour and 7-day rate limits live, and let `csm` automatically pick the account with the most remaining quota.

---

## ✨ Features

- 🔄 **Zero-Disruption Account Switching:** Switch active Codex accounts instantly without losing project history or session data.
- 📊 **Live Quota & Rate-Limit Visualizer (`csm status`):** See remaining percentages and reset countdowns for both **5-hour** and **7-day** windows for all your saved accounts.
- 🏆 **Smart Auto-Pick (`csm pick`):** Automatically evaluates all your accounts and switches to the one with the highest available quota.
- 🔐 **Isolated Safe Login:** Uses isolated temporary credential sandboxes during `csm add` to prevent existing refresh tokens from being revoked by OpenAI.
- 🖥️ **Codex Desktop App Integration:** Automatically restarts the macOS Codex app to apply the newly switched account immediately.
- 🚀 **Self-Updating:** Keep `csm` up to date with a single `csm update` command.

---

## 📦 Quick Installation

Run the one-line installer in your macOS terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/mazisel/csm/main/install.sh | bash
```

### Manual Installation (Alternative)

```bash
# Download and install to ~/.local/bin
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/mazisel/csm/main/csm -o ~/.local/bin/csm
chmod +x ~/.local/bin/csm

# Ensure ~/.local/bin is in your PATH (if not already)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
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
Codex kullanım hakları
────────────────────────────────────────────────────────────────
● personal [plus]
   5h  ████████████████░░░░  80.0% left   reset 3h 12m
   7d  ████████████████████ 100.0% left   reset ?

  work [team]
   5h  ████░░░░░░░░░░░░░░░░  20.0% left   reset 45m
   7d  ██████████████░░░░░░  70.0% left   reset 2d 4h
   Credits: $15.00

────────────────────────────────────────────────────────────────
Önerilen: personal  (5h 80.0% / 7d 100.0% kaldı)
```

### 3. Switch accounts
```bash
# Switch to an account and reload Codex Desktop App:
csm use work

# Or switch without restarting the Desktop App:
csm use work --no-restart
```

### 4. Automatically switch to the healthiest account
```bash
csm pick
```

---

## 📖 Command Reference

| Command | Description |
| :--- | :--- |
| `csm add <name>` | Securely login to a new Codex account and save it. |
| `csm refresh <name>` | Re-authenticate an existing account without revoking others. |
| `csm use <name>` | Switch active account and restart Codex Desktop App. |
| `csm use <name> --no-restart` | Switch account without restarting Codex Desktop App. |
| `csm status` | Show live 5h & 7d quota percentages, reset countdowns, and balance. |
| `csm pick` | Automatically select and switch to the account with the most quota. |
| `csm list` | List all saved accounts and show which one is currently active. |
| `csm current` | Print the name of the currently active account. |
| `csm remove <name>` | Delete a saved account from the local store. |
| `csm update` | Update `csm` directly to the latest version from GitHub. |
| `csm version` | Display the installed version of `csm`. |
| `csm help` | Show help and usage instructions. |

---

## 🔒 Security & Storage

- **Local Storage:** All authentication tokens are stored strictly on your local machine under `~/.codex-multi/accounts/`.
- **Strict File Permissions:** Files are secured with `chmod 600` (readable only by your user account).
- **No Telemetry / No Third-party:** `csm` directly connects only to official OpenAI API endpoints (`auth.openai.com` and `chatgpt.com`).

---

## 🔄 Updating & Uninstalling

### Update
```bash
csm update
```

### Uninstall
```bash
rm -f ~/.local/bin/csm
rm -rf ~/.codex-multi
```

---

## 🇹🇷 Türkçe Açıklama

`csm`, macOS üzerinde Codex kullanıcıları için geliştirilmiş çoklu hesap geçiş ve anlık kota takip yöneticisidir.

- **Kurulum:** `curl -fsSL https://raw.githubusercontent.com/mazisel/csm/main/install.sh | bash`
- **Hesap Ekleme:** `csm add hesap_adi`
- **Kotaları Görüntüleme:** `csm status`
- **Hesap Değiştirme:** `csm use hesap_adi`
- **En Yüksek Kotalı Hesaba Otomatik Geçiş:** `csm pick`
- **Güncelleme:** `csm update`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
