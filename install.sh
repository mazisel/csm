#!/usr/bin/env bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   Installing csm (Codex Switcher)      ${NC}"
echo -e "${BLUE}========================================${NC}"

# Check for Python 3
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}❌ Error: python3 is required but not found in PATH.${NC}"
  exit 1
fi

INSTALL_DIR="$HOME/.local/bin"
mkdir -p "$INSTALL_DIR"

RAW_URL="https://raw.githubusercontent.com/mazisel/csm/main/csm"
TARGET="$INSTALL_DIR/csm"

echo -e "⬇️  Downloading csm from GitHub..."
if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$RAW_URL" -o "$TARGET"
elif command -v wget >/dev/null 2>&1; then
  wget -qO "$TARGET" "$RAW_URL"
else
  echo -e "${RED}❌ Error: curl or wget is required to download csm.${NC}"
  exit 1
fi

chmod +x "$TARGET"

# Check if INSTALL_DIR is in PATH
SHELL_RC=""
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
  SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ] || [ -f "$HOME/.bashrc" ]; then
  SHELL_RC="$HOME/.bashrc"
fi

NEED_PATH_EXPORT=0
case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *) NEED_PATH_EXPORT=1 ;;
esac

if [ "$NEED_PATH_EXPORT" -eq 1 ]; then
  if [ -n "$SHELL_RC" ]; then
    echo "" >> "$SHELL_RC"
    echo "# Added by csm installer" >> "$SHELL_RC"
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$SHELL_RC"
    echo -e "${YELLOW}ℹ️  Added ~/.local/bin to your \$PATH in ${SHELL_RC}${NC}"
  fi
fi

echo ""
echo -e "${GREEN}✅ csm successfully installed to ${TARGET}!${NC}"
echo ""
if [ "$NEED_PATH_EXPORT" -eq 1 ]; then
  echo -e "${YELLOW}👉 Run this command now to activate it in your current terminal session:${NC}"
  echo -e "   ${BLUE}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
  echo ""
fi
echo -e "Try it out by running:"
echo -e "   ${BLUE}csm help${NC}"
echo -e "   ${BLUE}csm add <account-name>${NC}"
echo -e "${BLUE}========================================${NC}"
