# Safe Migration Plan: Extract Voxtral to Independent Repository with Submodule

This plan safely extracts the `Voxtral` directory from the `VJ` repository while **preserving commit history** and includes backup/rollback procedures.

---

## 📋 Overview

| Aspect | Details |
|--------|---------|
| **Source** | `D:\VJ` (parent repo) |
| **Target** | New independent `Voxtral` repository |
| **History** | ✅ Preserved using `git filter-repo` |
| **Backup** | ✅ Full backup before any changes |
| **Rollback** | ✅ Documented rollback steps |

---

## 🔧 Prerequisites

### Install git-filter-repo
```bash
pip install git-filter-repo
```

### Verify tools
```bash
git --version
git-filter-repo --version
```

---

## 📝 Phase 1: Backup (Critical)

### 1.1 Backup Parent Repository (VJ)
```bash
# Navigate to parent repo
cd D:\VJ

# Create timestamped backup
robocopy D:\VJ D:\VJ_BACKUP_$(Get-Date -Format "yyyyMMdd_HHmmss") /MIR /NFL /NDL /NJH /NJS

# Verify backup exists
dir D:\VJ_BACKUP_*
```

### 1.2 Backup Voxtral Folder Separately
```bash
robocopy D:\VJ\Voxtral D:\Voxtral_BACKUP_$(Get-Date -Format "yyyyMMdd_HHmmss") /MIR /NFL /NDL /NJH /NJS
```

### 1.3 Export Current Git State
```bash
cd D:\VJ
git log --oneline -20 > D:\VJ_git_state_before.txt
git status > D:\VJ_git_status_before.txt
```

---

## 🚀 Phase 2: Create New Voxtral Repository with History

### 2.1 Clone VJ to Temporary Location
```bash
# Create temp directory
mkdir D:\TEMP_MIGRATION
cd D:\TEMP_MIGRATION

# Clone the entire VJ repo (preserves all history)
git clone D:\VJ voxtral_temp_repo
cd voxtral_temp_repo
```

### 2.2 Extract Voxtral History Using filter-repo
```bash
# This keeps ONLY the Voxtral folder and its history
git filter-repo --path Voxtral/ --path-rename Voxtral/:.

# Verify the history is preserved
git log --oneline --stat
```

### 2.3 Set Up Remote and Push
```bash
# Add the new remote repository URL
git remote add origin <YOUR_NEW_VOXTRAL_REPO_URL>

# Push all branches and tags
git push -u origin main --force
git push --tags

# Verify on remote (open browser to check)
```

### 2.4 Verify New Repository
```bash
# Clone fresh from remote to verify
cd D:\TEMP_MIGRATION
git clone <YOUR_NEW_VOXTRAL_REPO_URL> voxtral_verify
cd voxtral_verify

# Check files exist
dir /s

# Check history
git log --oneline
```

---

## 🔗 Phase 3: Convert to Submodule in Parent Repo

### 3.1 Remove Voxtral from Parent (VJ)
```bash
cd D:\VJ

# Ensure clean state
git status

# Remove Voxtral folder from git tracking (keeps files locally)
git rm -r --cached Voxtral

# Commit the removal
git commit -m "Remove Voxtral to prepare for submodule conversion"
```

### 3.2 Add Voxtral as Submodule
```bash
# Add submodule
git submodule add <YOUR_NEW_VOXTRAL_REPO_URL> Voxtral

# This will:
# - Remove existing Voxtral folder
# - Clone the submodule into Voxtral/
# - Create .gitmodules file

# Verify .gitmodules was created
cat .gitmodules

# Stage and commit
git add .gitmodules
git commit -m "Add Voxtral as Git submodule"
```

### 3.3 Initialize Submodule for Existing Clones
```bash
# For this local copy
git submodule init
git submodule update

# Verify submodule status
git submodule status
```

### 3.4 Push Changes to Parent Repo
```bash
git push origin <YOUR_VJ_BRANCH_NAME>
```

---

## ✅ Phase 4: Verification Checklist

### 4.1 Parent Repository (VJ)
```bash
cd D:\VJ

# Check submodule is registered
git submodule status

# Check .gitmodules content
cat .gitmodules

# Verify Voxtral folder exists and is accessible
dir Voxtral

# Check git sees it as submodule, not regular folder
git ls-files --stage | grep Voxtral
```

### 4.2 New Voxtral Repository
```bash
# Check remote repository via browser/CLI
# Verify all files are present
# Verify commit history is preserved
git log --oneline --graph
```

### 4.3 Submodule Operations
```bash
# Test submodule update
git submodule update --init --recursive

# Test fetching updates in submodule
cd Voxtral
git fetch
git log --oneline -5
```

### 4.4 File Integrity Check
```bash
# Compare file counts
# Before (from backup log)
# After
dir Voxtral /s /b | find /c /v ""
```

---

## 🔄 Phase 5: Rollback Procedures (If Something Goes Wrong)

### Scenario 1: Problem During Phase 2 (Creating New Repo)
```bash
# Simply abandon the temp directory
cd D:\VJ

# Restore from backup
robocopy D:\VJ_BACKUP_YYYYMMDD_HHMMSS D:\VJ /MIR /NFL /NDL /NJH /NJS

# Verify restoration
git status
```

### Scenario 2: Problem During Phase 3 (Submodule Conversion)
```bash
cd D:\VJ

# Remove broken submodule
git submodule deinit -f Voxtral
rm -rf .git\modules/Voxtral
git rm -f Voxtral

# Restore Voxtral folder from backup
robocopy D:\Voxtral_BACKUP_YYYYMMDD_HHMMSS D:\VJ\Voxtral /MIR /NFL /NDL /NJH /NJS

# Reset git state
git reset --hard HEAD~1  # Undo the submodule commit
git reset --hard HEAD~1  # Undo the rm --cached commit

# Verify restoration
git status
dir Voxtral
```

### Scenario 3: Full Rollback
```bash
cd D:\VJ

# Complete restore from backup
robocopy D:\VJ_BACKUP_YYYYMMDD_HHMMSS D:\VJ /MIR /NFL /NDL /NJH /NJS

# Verify
git status
git log --oneline -5
dir Voxtral
```

---

## 📌 Post-Migration Tasks

### 5.1 Update Documentation
- Update README.md in both repos to reflect submodule structure
- Update any CI/CD pipelines to handle submodules

### 5.2 Team Notification
```markdown
## Migration Complete

Voxtral is now a submodule. If you're cloning VJ:

# For new clones
git clone --recursive <VJ_REPO_URL>

# For existing clones
git submodule init
git submodule update
```

### 5.3 Cleanup
```bash
# After confirming everything works (wait 1-2 days)
rmdir /s D:\TEMP_MIGRATION
rmdir /s D:\VJ_BACKUP_YYYYMMDD_HHMMSS
rmdir /s D:\Voxtral_BACKUP_YYYYMMDD_HHMMSS
```

---

## ⚠️ Important Notes

1. **URL Placeholders**: Replace `<YOUR_NEW_VOXTRAL_REPO_URL>` with actual repository URL
2. **Branch Names**: Replace `<YOUR_VJ_BRANCH_NAME>` with your actual branch (main/master)
3. **Permissions**: Ensure you have write access to both repositories
4. **Network**: Stable internet connection required for pushing

---

## 📊 Command Quick Reference

| Task | Command |
|------|---------|
| Backup VJ | `robocopy D:\VJ D:\VJ_BACKUP_YYYYMMDD_HHMMSS /MIR` |
| Extract with history | `git filter-repo --path Voxtral/ --path-rename Voxtral/:.` |
| Add submodule | `git submodule add <URL> Voxtral` |
| Check submodule | `git submodule status` |
| Rollback | `robocopy D:\VJ_BACKUP_* D:\VJ /MIR` |

---

## ✅ Pre-Flight Checklist

Before starting, confirm:
- [ ] Backup completed successfully
- [ ] `git-filter-repo` installed
- [ ] New repository URL created on GitHub/GitLab
- [ ] Write permissions verified
- [ ] Stable internet connection
- [ ] All local changes committed
- [ ] Team members notified (if applicable)

---

**Estimated Time**: 30-45 minutes  
**Risk Level**: Low (with backup and rollback plan)
