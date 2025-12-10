# Claude Code Skills for Rattrap API Docs

This directory contains custom skills for the Rattrap API documentation project.

## Available Skills

### 🚀 Deploy Skill

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
