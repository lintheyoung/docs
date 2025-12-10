# Claude Code Skills for Rattrap API Docs

This directory contains custom skills for the Rattrap API documentation project.

## Available Skills

### 🚀 Deploy Skill (`deploy.md`)

Automates the deployment process by pushing changes to GitHub, which triggers CI/CD.

**Usage:**
```
/deploy
```

Or simply say:
- "deploy this"
- "push to production"
- "deploy these changes"

**What it does:**
1. Checks git status and shows what will be deployed
2. Reviews changes and asks for confirmation
3. Commits changes with proper formatting
4. Pushes to GitHub (triggers automatic deployment)
5. Confirms deployment status

**Features:**
- ✅ Automatic commit message formatting
- ✅ Safety checks (no force push, conflict detection)
- ✅ User confirmation before deploying
- ✅ Clear deployment status feedback
- ✅ Handles errors gracefully

**Quick Deploy:**
Just say "quick deploy" for fast deployments with auto-generated commit messages.

---

### 📁 Temporary Documents Management (`temp-docs.md`)

Keeps the repository clean by defaulting temporary files to `/tmp` directory.

**Core Principle:**
Unless you explicitly say "save to project", all temporary and test files go to `/tmp/rattrap-docs/`

**Automatically uses `/tmp` for:**
- Test scripts (`test-*.py`, `test-*.js`)
- Temporary documentation and notes
- Exploration and analysis files
- Code examples and experiments
- Design document drafts

**What it does:**
1. Analyzes if a file is temporary or permanent
2. Defaults to `/tmp` for temporary files
3. Saves to project only when explicitly requested
4. Keeps temp files organized for easy promotion
5. Reminds you where files are saved

**Usage examples:**
```
❌ "Write a test for the API" → Saves to project (bad)
✅ "Write a test for the API" → Saves to /tmp (with this skill)

✅ "Write a test and save to project" → Saves to project (explicit)
```

**Promoting temp files to project:**
```
Say: "add test-api.py to project"
Or:  "move this to the repository"
```

**Benefits:**
- ✅ Clean git status (no test files clutter)
- ✅ Safe experimentation without polluting repo
- ✅ Organized `/tmp` directory structure
- ✅ Easy to promote useful files later
- ✅ Better git history

## How Skills Work

Skills in Claude Code are specialized agents that help with specific tasks. When you invoke a skill:
1. Claude enters "skill mode" with specialized instructions
2. The skill follows its defined workflow
3. Claude handles all the steps automatically
4. You get clear feedback at each stage

## Project Structure

```
.claude/
├── skills/
│   ├── deploy.md       # Deployment automation skill
│   └── README.md       # This file
└── settings.local.json # Local Claude Code settings
```

## Contributing

To add new skills:
1. Create a new `.md` file in `.claude/skills/`
2. Follow the skill template format (see `deploy.md` for reference)
3. Document the skill in this README

## Tips

- Skills work best for repetitive tasks
- Keep skills focused on one specific workflow
- Use clear confirmation steps for destructive operations
- Provide helpful error messages and recovery suggestions
