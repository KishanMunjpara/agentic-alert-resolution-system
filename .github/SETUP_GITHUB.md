# GitHub Repository Setup Guide

This guide helps you push this repository to GitHub using a temporary account.

## Prerequisites

1. Create a new repository on GitHub:
   - Go to https://github.com/KishanMunjpara
   - Click "New repository"
   - Name: `agentic-alert-resolution-system` (or your preferred name)
   - Description: "Multi-Agent Banking Transaction Monitoring System"
   - Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)

## Option 1: Push with Temporary Credentials (Recommended)

### Step 1: Add Remote Repository

```bash
# Replace YOUR_REPO_NAME with your actual repository name
git remote add origin https://github.com/KishanMunjpara/YOUR_REPO_NAME.git
```

### Step 2: Configure Local Repository (Temporary)

```bash
# Set git config for this repository only (doesn't affect global config)
git config user.name "KishanMunjpara"
git config user.email "kishanmunjpara2710@gmail.com"
```

### Step 3: Push to GitHub

```bash
# Push to main branch
git push -u origin main
```

When prompted for credentials:
- Username: `KishanMunjpara`
- Password: Use a **Personal Access Token** (not your GitHub password)
  - Generate one at: https://github.com/settings/tokens
  - Select scopes: `repo` (full control of private repositories)

## Option 2: Use SSH (Alternative)

### Step 1: Generate SSH Key (if you don't have one for this account)

```bash
ssh-keygen -t ed25519 -C "kishanmunjpara2710@gmail.com" -f ~/.ssh/id_ed25519_github_temp
```

### Step 2: Add SSH Key to GitHub

1. Copy the public key:
   ```bash
   cat ~/.ssh/id_ed25519_github_temp.pub
   ```

2. Go to: https://github.com/settings/keys
3. Click "New SSH key"
4. Paste the key and save

### Step 3: Configure SSH

```bash
# Add to ~/.ssh/config (or C:\Users\YourName\.ssh\config on Windows)
Host github-temp
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github_temp
```

### Step 4: Add Remote and Push

```bash
git remote add origin git@github-temp:KishanMunjpara/YOUR_REPO_NAME.git
git push -u origin main
```

## Option 3: Use GitHub CLI (Easiest)

```bash
# Install GitHub CLI if not installed
# Windows: winget install GitHub.cli
# Mac: brew install gh
# Linux: See https://cli.github.com/manual/installation

# Login to temporary account
gh auth login

# Create and push repository
gh repo create YOUR_REPO_NAME --public --source=. --remote=origin --push
```

## Verify Setup

After pushing, verify:

```bash
# Check remote URL
git remote -v

# Check repository status
git status

# View commits
git log --oneline
```

## Restore Original Config (After Pushing)

If you want to restore the original git config for this repository:

```bash
# Remove local config (will use global config)
git config --local --unset user.name
git config --local --unset user.email
```

Or keep the local config - it only affects this repository.

## Troubleshooting

### Authentication Failed
- Use Personal Access Token instead of password
- Check token has `repo` scope

### Permission Denied
- Verify repository name is correct
- Check you have write access to the repository

### Remote Already Exists
```bash
# Remove existing remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/KishanMunjpara/YOUR_REPO_NAME.git
```

