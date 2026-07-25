#!/bin/bash

# ============================================================================
# Git Repository Sync Script for notion-live-analyzer
# This script automatically merges unpushed changes and syncs your repository
# ============================================================================

set -e  # Exit on error

echo "🔄 Starting Repository Sync..."
echo "=================================="

# Step 1: Fetch all remote changes
echo ""
echo "📥 Step 1: Fetching remote changes..."
git fetch origin
echo "✅ Fetch complete"

# Step 2: Check differences between branches
echo ""
echo "🔍 Step 2: Checking differences between branches..."
echo "Differences found:"
git diff --stat main origin/codespace-silver-space-computing-machine-x57p46rxgp9p29pxv || true
echo ""

# Step 3: Create backup branch (safety measure)
echo "💾 Step 3: Creating backup branch..."
BACKUP_BRANCH="backup-sync-$(date +%Y%m%d-%H%M%S)"
git branch $BACKUP_BRANCH
echo "✅ Backup created: $BACKUP_BRANCH"

# Step 4: Checkout main
echo ""
echo "🌳 Step 4: Checking out main branch..."
git checkout main
echo "✅ Now on main branch"

# Step 5: Merge unpushed changes
echo ""
echo "🔗 Step 5: Merging unpushed changes from Codespace..."
git merge origin/codespace-silver-space-computing-machine-x57p46rxgp9p29pxv -m "Merge unpushed changes from Codespace workspace"
echo "✅ Merge complete"

# Step 6: Push to remote
echo ""
echo "📤 Step 6: Pushing merged changes to remote..."
git push origin main
echo "✅ Push complete"

# Step 7: Pull to ensure local sync
echo ""
echo "🔄 Step 7: Pulling latest changes..."
git pull origin main
echo "✅ Pull complete"

# Step 8: Check final status
echo ""
echo "📊 Step 8: Final repository status..."
git status
echo ""
git log --oneline -5
echo ""

# Step 9: Optional cleanup
echo ""
echo "🧹 Step 9: Cleaning up..."
read -p "Delete the old Codespace branch? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git branch -d codespace-silver-space-computing-machine-x57p46rxgp9p29pxv 2>/dev/null || true
    git push origin --delete codespace-silver-space-computing-machine-x57p46rxgp9p29pxv 2>/dev/null || true
    echo "✅ Codespace branch deleted"
fi

echo ""
echo "=================================="
echo "✨ Repository sync complete!"
echo "Backup branch saved as: $BACKUP_BRANCH"
echo "=================================="
