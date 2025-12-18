#!/bin/bash
# Bash script to set up GitHub repository for temporary account
# Usage: ./setup_github_repo.sh your-repo-name

if [ -z "$1" ]; then
    echo "Error: Repository name required"
    echo "Usage: ./setup_github_repo.sh your-repo-name"
    exit 1
fi

REPO_NAME=$1

echo "Setting up GitHub repository: $REPO_NAME"
echo "Account: KishanMunjpara (kishanmunjpara2710@gmail.com)"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "Error: Git repository not initialized!"
    exit 1
fi

# Set local git config (doesn't affect global)
echo "Setting local git config..."
git config user.name "KishanMunjpara"
git config user.email "kishanmunjpara2710@gmail.com"

echo "✓ Git config set for this repository only"
echo ""

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    echo "Remote 'origin' already exists: $(git remote get-url origin)"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote set-url origin "https://github.com/KishanMunjpara/$REPO_NAME.git"
        echo "✓ Remote updated"
    else
        echo "Keeping existing remote"
    fi
else
    git remote add origin "https://github.com/KishanMunjpara/$REPO_NAME.git"
    echo "✓ Remote added"
fi

echo ""
echo "Next steps:"
echo "1. Create the repository on GitHub: https://github.com/new"
echo "   - Name: $REPO_NAME"
echo "   - DO NOT initialize with README, .gitignore, or license"
echo ""
echo "2. Push to GitHub:"
echo "   git push -u origin main"
echo ""
echo "3. When prompted for credentials:"
echo "   - Username: KishanMunjpara"
echo "   - Password: Use Personal Access Token (not password)"
echo "   - Generate token: https://github.com/settings/tokens"
echo ""
echo "Repository is ready to push!"

