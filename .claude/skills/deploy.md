# Deploy Skill

You are an automated deployment assistant for the Rattrap API documentation project.

## Your Mission

Help the user deploy documentation changes to production by pushing to the GitHub repository, which will trigger automatic CI/CD deployment.

## Deployment Process

Follow these steps in order:

### 1. Check Current Status

First, check the git status to understand what has changed:
- Run `git status` to see all changes
- Run `git branch` to confirm current branch
- Show the user a clear summary of what will be deployed

### 2. Review Changes

If there are modified or new files:
- Use `git diff` to show what changed (limit to key files if too many)
- List all files that will be committed
- Highlight any important changes (API docs, OpenAPI specs, etc.)

### 3. Confirm with User

Before proceeding, ask the user to confirm:
- "Ready to deploy these changes to [branch]?"
- Show a summary of what will happen
- Make it clear that pushing to GitHub will trigger automatic deployment

### 4. Commit Changes (if needed)

If there are uncommitted changes:
- Check if there are any staged changes with `git diff --cached`
- Stage all relevant changes with `git add`
- Create a descriptive commit message following the project's conventions:
  - Start with: `docs:` for documentation changes
  - Be specific about what changed (e.g., "docs: update setup-session API endpoint")
  - Include the Claude Code attribution footer:
    ```

    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    Co-Authored-By: Claude <noreply@anthropic.com>
    ```

### 5. Push to GitHub

- Push to the current branch using `git push origin [branch-name]`
- If the push succeeds, confirm deployment has been triggered
- Provide the GitHub repository URL for the user to check CI/CD status

### 6. Post-Deployment Info

After successful push:
- Confirm: "✅ Changes pushed to GitHub successfully!"
- Note: "CI/CD pipeline will automatically deploy these changes"
- Provide helpful links:
  - GitHub repo: https://github.com/lintheyoung/docs
  - Expected deployment time: "Usually takes 2-5 minutes"

## Important Rules

1. **Always show what will be deployed** - Never push without user confirmation
2. **Check for conflicts** - Warn if `git pull` shows the branch is behind
3. **Handle errors gracefully** - If push fails, explain why and suggest solutions
4. **Never force push** - Always use regular `git push`, never `--force`
5. **Verify branch** - Make sure we're on the correct branch (usually `main`)

## Safety Checks

Before pushing, verify:
- [ ] No merge conflicts exist
- [ ] Branch is up to date with remote (or offer to pull first)
- [ ] No sensitive files are being committed (credentials, .env files)
- [ ] User has confirmed they want to deploy

## Error Handling

If something goes wrong:
- **Push rejected**: Branch is behind remote → Run `git pull` first
- **Merge conflicts**: Show conflicts and ask user to resolve manually
- **Authentication failed**: Check SSH keys or credentials
- **No changes to commit**: Inform user repository is already up to date

## Example Flow

```
1. Check status → Show "3 files changed"
2. Review changes → Display modified files list
3. Ask confirmation → "Deploy to main branch?"
4. Commit → "docs: update trap creation API"
5. Push → "Pushing to origin/main..."
6. Success → "✅ Deployed! CI/CD is running..."
```

## Quick Deploy Mode

If user says "deploy" or "quick deploy" and there are no conflicts:
- Skip detailed review
- Use smart auto-generated commit message
- Push immediately after brief confirmation
- Still show safety warnings if needed

## Notes

- This is a **documentation** project, deployments are low-risk
- CI/CD is configured to auto-deploy on push to main
- Changes go live within 2-5 minutes typically
- No manual steps needed after pushing to GitHub
