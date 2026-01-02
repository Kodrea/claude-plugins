#!/bin/bash
# Install Cody's private Claude Code plugins
# Usage: curl -sL https://raw.githubusercontent.com/kodrea/claude-plugins/main/install.sh | bash

set -e

REPO_URL="${REPO_URL:-git@github.com:kodrea/claude-plugins.git}"
INSTALL_DIR="$HOME/.claude/plugins/marketplaces/local"
KNOWN_MARKETPLACES="$HOME/.claude/plugins/known_marketplaces.json"

echo "Installing private Claude Code plugins..."

# Create plugins directory if needed
mkdir -p "$HOME/.claude/plugins/marketplaces"

# Clone or update repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR" && git pull
else
    if [ -d "$INSTALL_DIR" ]; then
        echo "Backing up existing local plugins..."
        mv "$INSTALL_DIR" "$INSTALL_DIR.backup.$(date +%s)"
    fi
    echo "Cloning repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Register marketplace in known_marketplaces.json
if [ -f "$KNOWN_MARKETPLACES" ]; then
    # Check if "local" entry exists
    if grep -q '"local"' "$KNOWN_MARKETPLACES"; then
        echo "Marketplace 'local' already registered."
    else
        echo "Adding 'local' marketplace to known_marketplaces.json..."
        # Use jq if available, otherwise provide manual instructions
        if command -v jq &> /dev/null; then
            jq --arg path "$INSTALL_DIR" '.local = {
                "source": {"source": "directory", "path": $path},
                "installLocation": $path,
                "lastUpdated": (now | strftime("%Y-%m-%dT%H:%M:%S.000Z"))
            }' "$KNOWN_MARKETPLACES" > "$KNOWN_MARKETPLACES.tmp" && mv "$KNOWN_MARKETPLACES.tmp" "$KNOWN_MARKETPLACES"
        else
            echo "Please manually add 'local' marketplace to $KNOWN_MARKETPLACES"
        fi
    fi
else
    echo "Creating known_marketplaces.json..."
    cat > "$KNOWN_MARKETPLACES" << EOF
{
  "local": {
    "source": {
      "source": "directory",
      "path": "$INSTALL_DIR"
    },
    "installLocation": "$INSTALL_DIR",
    "lastUpdated": "$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
  }
}
EOF
fi

echo ""
echo "Installation complete!"
echo ""
echo "Available plugins:"
if [ -f "$INSTALL_DIR/.claude-plugin/marketplace.json" ]; then
    grep -o '"name": "[^"]*"' "$INSTALL_DIR/.claude-plugin/marketplace.json" | head -20 | sed 's/"name": "/ - /; s/"$//'
fi
echo ""
echo "To install a plugin, run:"
echo "  claude /plugin install <plugin-name>@local"
echo ""
echo "To enable a plugin in settings.json:"
echo '  "enabledPlugins": { "<plugin-name>@local": true }'
