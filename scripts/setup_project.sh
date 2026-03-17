#!/usr/bin/env bash
set -euo pipefail

# Setup a paper project to use TianXing
# Usage: bash /path/to/TianXing/scripts/setup_project.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_ROOT="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(pwd)"

echo "=== TianXing — Project Setup ==="
echo "Project directory: $PROJECT_DIR"
echo "Tools source: $TOOLS_ROOT"
echo ""

# Check we're in a git repo
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "ERROR: Not a git repository. Please run 'git init' first."
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p reviews logs/latex logs/tests logs/notifications status
mkdir -p .claude/commands

# Copy AGENT.md
if [ ! -f AGENT.md ]; then
    cp "$TOOLS_ROOT/templates/AGENT.md" AGENT.md
    echo "  ✓ Created AGENT.md"
else
    echo "  • AGENT.md already exists, skipping"
fi

# Copy config.yaml
if [ ! -f config.yaml ]; then
    cp "$TOOLS_ROOT/config.example.yaml" config.yaml
    echo "  ✓ Created config.yaml"
else
    echo "  • config.yaml already exists, skipping"
fi

# Copy slash command
if [ ! -f .claude/commands/review-loop.md ]; then
    cp "$TOOLS_ROOT/commands/review-loop.md" .claude/commands/review-loop.md
    echo "  ✓ Created .claude/commands/review-loop.md"
else
    echo "  • .claude/commands/review-loop.md already exists, skipping"
fi

# Initialize status
if [ ! -f status/current.json ]; then
    echo '{"round": 0, "phase": "init", "score": null, "message": "Not started", "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"}' > status/current.json
    echo "  ✓ Initialized status/current.json"
else
    echo "  • status/current.json already exists, skipping"
fi

# Add to .gitignore if needed
if [ -f .gitignore ]; then
    if ! grep -q "logs/" .gitignore 2>/dev/null; then
        echo "" >> .gitignore
        echo "# TianXing" >> .gitignore
        echo "logs/" >> .gitignore
        echo "  ✓ Added logs/ to .gitignore"
    fi
else
    echo "# TianXing" > .gitignore
    echo "logs/" >> .gitignore
    echo "  ✓ Created .gitignore with logs/"
fi

# Configure Claude Code permissions for TianXing
if [ ! -f .claude/settings.json ]; then
    cat > .claude/settings.json << 'SETTINGS'
{
  "permissions": {
    "allow": [
      "Bash(*python -m tianxing.*)",
      "Bash(*python3 -c \"import sys,json*)",
      "Bash(tianxing *)",
      "Bash(latexmk *)",
      "Bash(pdflatex *)",
      "Bash(xelatex *)",
      "Bash(bibtex *)",
      "Bash(biber *)",
      "Bash(pytest *)",
      "Bash(git tag *)",
      "Bash(git diff *)",
      "Bash(git status*)",
      "Bash(git log *)",
      "Read(**)",
      "Edit(paper/**)",
      "Edit(code/**)",
      "Edit(results/**)",
      "Edit(config.yaml)",
      "Edit(experiment_map.json)",
      "Write(reviews/**)",
      "Write(logs/**)",
      "Write(status/**)"
    ],
    "deny": [
      "Read(.env*)",
      "Read(secrets/**)"
    ]
  }
}
SETTINGS
    echo "  ✓ Created .claude/settings.json (TianXing permissions)"
else
    echo "  • .claude/settings.json already exists, skipping"
fi

# Generate experiment map
if command -v python &> /dev/null && python -c "import tianxing" 2>/dev/null; then
    if [ ! -f experiment_map.json ]; then
        if python -m tianxing.experiment_map --action discover > /dev/null 2>&1; then
            echo "  ✓ Generated experiment_map.json"
        else
            echo "  • Skipped experiment_map.json (will be generated on first /review-loop run)"
        fi
    else
        echo "  • experiment_map.json already exists, skipping"
    fi
else
    echo "  • Skipped experiment_map.json (install TianXing first, then run: tianxing map --action discover)"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  1. Edit config.yaml to match your project structure"
echo "  2. Make sure TianXing is installed: pip install -e $TOOLS_ROOT"
echo "  3. Run Claude Code and use: /review-loop"
echo "     (experiment_map.json will be auto-generated on first run)"
echo ""
