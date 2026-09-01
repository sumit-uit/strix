#!/bin/bash
# Setup script for Kiro + Strix integration

set -e

echo "🚀 Setting up Strix for Kiro..."
echo ""

# Check if running on macOS, Linux, or WSL
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="Linux"
else
    echo "❌ Unsupported platform: $OSTYPE"
    exit 1
fi

echo "📍 Detected platform: $PLATFORM"
echo ""

# Check prerequisites
echo "✅ Checking prerequisites..."

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   macOS: https://docs.docker.com/desktop/install/mac-install/"
    echo "   Linux: https://docs.docker.com/engine/install/"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "   ✓ Docker is installed and running"

# Check if Strix is installed
if ! command -v strix &> /dev/null; then
    echo ""
    echo "📦 Installing Strix..."
    curl -sSL https://strix.ai/install | bash

    # Source the updated PATH
    export PATH="$HOME/.local/bin:$PATH"

    if ! command -v strix &> /dev/null; then
        echo "❌ Strix installation failed. Please try manual installation:"
        echo "   curl -sSL https://strix.ai/install | bash"
        exit 1
    fi
fi

STRIX_VERSION=$(strix --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "unknown")
echo "   ✓ Strix $STRIX_VERSION is installed"

# Check Python and uv
if command -v uv &> /dev/null; then
    echo "   ✓ uv is installed"
else
    echo "   ⚠️  uv is not installed (optional, for development)"
fi

echo ""
echo "🔧 Configuring LLM provider..."
echo ""

# Check if environment variables are already set
if [[ -n "$STRIX_LLM" ]] && [[ -n "$LLM_API_KEY" ]]; then
    echo "   ✓ LLM already configured:"
    echo "     STRIX_LLM=$STRIX_LLM"
    echo "     LLM_API_KEY=***${LLM_API_KEY: -4}"
else
    echo "You need to configure your LLM provider. Popular options:"
    echo ""
    echo "1) OpenAI (GPT-5.4) - Recommended"
    echo "2) Anthropic (Claude Sonnet 4.6)"
    echo "3) Google (Gemini 3 Pro)"
    echo "4) OpenRouter (Multiple models)"
    echo "5) Skip (configure manually later)"
    echo ""
    read -p "Select provider (1-5): " PROVIDER_CHOICE

    case $PROVIDER_CHOICE in
        1)
            PROVIDER="openai/gpt-5.4"
            read -p "Enter your OpenAI API key: " API_KEY
            ;;
        2)
            PROVIDER="anthropic/claude-sonnet-4.6"
            read -p "Enter your Anthropic API key: " API_KEY
            ;;
        3)
            PROVIDER="vertex_ai/gemini-3-pro-preview"
            read -p "Enter your Google Cloud API key: " API_KEY
            ;;
        4)
            PROVIDER="openrouter/anthropic/claude-3.5-sonnet"
            read -p "Enter your OpenRouter API key: " API_KEY
            ;;
        5)
            echo ""
            echo "⚠️  Skipping LLM configuration. You'll need to set these manually:"
            echo "   export STRIX_LLM=\"openai/gpt-5.4\""
            echo "   export LLM_API_KEY=\"your-api-key\""
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac

    if [[ $PROVIDER_CHOICE != 5 ]]; then
        # Add to shell config
        SHELL_CONFIG=""
        if [[ -f "$HOME/.zshrc" ]]; then
            SHELL_CONFIG="$HOME/.zshrc"
        elif [[ -f "$HOME/.bashrc" ]]; then
            SHELL_CONFIG="$HOME/.bashrc"
        fi

        if [[ -n "$SHELL_CONFIG" ]]; then
            echo "" >> "$SHELL_CONFIG"
            echo "# Strix LLM Configuration" >> "$SHELL_CONFIG"
            echo "export STRIX_LLM=\"$PROVIDER\"" >> "$SHELL_CONFIG"
            echo "export LLM_API_KEY=\"$API_KEY\"" >> "$SHELL_CONFIG"

            echo "   ✓ Configuration saved to $SHELL_CONFIG"

            # Set for current session
            export STRIX_LLM="$PROVIDER"
            export LLM_API_KEY="$API_KEY"
        else
            echo "   ⚠️  Could not find shell config. Please add these manually:"
            echo "      export STRIX_LLM=\"$PROVIDER\""
            echo "      export LLM_API_KEY=\"$API_KEY\""
        fi
    fi
fi

echo ""
echo "🎨 Installing Kiro skill..."

# Check if skills directory exists
if [[ -d "./skills/kiro-pentesting-with-strix" ]]; then
    echo "   ✓ Kiro skill is available at ./skills/kiro-pentesting-with-strix/"
else
    echo "   ⚠️  Kiro skill not found. Run this script from the Strix repository root."
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Restart your terminal or run: source ~/.zshrc (or ~/.bashrc)"
echo "2. Test Strix: strix --version"
echo "3. Tell Kiro to use Strix skills:"
echo "   - 'Run a security scan on this project'"
echo "   - 'Check for vulnerabilities in the API'"
echo "   - 'Set up automated security scanning'"
echo ""
echo "📚 Documentation:"
echo "   - Kiro Skill: ./skills/kiro-pentesting-with-strix/SKILL.md"
echo "   - CLI Docs: https://docs.strix.ai"
echo "   - Agent Guide: ./AGENTS.md"
echo ""
echo "🐛 Troubleshooting:"
echo "   - Ensure Docker is running: docker info"
echo "   - Check LLM config: echo \$STRIX_LLM"
echo "   - Test scan: strix -n -t https://example.com --scan-mode quick --max-budget 1"
echo ""
echo "Happy pentesting! 🎯"
