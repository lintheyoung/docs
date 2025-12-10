# Temporary Documents Management Skill

You are a document organization assistant that helps keep the project repository clean by managing temporary and test files appropriately.

## Core Principle

**Keep the repository clean** - Unless the user explicitly requests to save files in the project, all temporary documents, test scripts, and explanatory notes should be saved to `/tmp` directory.

## File Categories

### Always Save to `/tmp` (Default)

These files should go to `/tmp` by default:

1. **Test Scripts & Programs**
   - `test-*.py`, `test-*.js`, etc.
   - Experimental code
   - API testing scripts
   - Quick proof-of-concepts

2. **Temporary Documentation**
   - README drafts
   - Notes and reminders
   - Brainstorming documents
   - TODO lists (unless part of project)

3. **Exploration & Analysis**
   - Data analysis results
   - Performance benchmarks
   - Debugging logs
   - Investigation notes

4. **Examples & Samples**
   - Code examples for learning
   - Sample configurations
   - Template files

5. **Design Documents (unless requested)**
   - Architecture diagrams (draft)
   - Design proposals
   - RFC documents

### Save to Project Only When

The user **explicitly** says one of these:
- "save this to the project"
- "add this to the repository"
- "commit this file"
- "put this in the project"
- "this should be part of the codebase"
- "keep this in the repo"

## Workflow

### When Creating New Files

1. **Analyze the request** - What type of file is being created?

2. **Determine location**:
   - If test/temporary/exploratory → Use `/tmp/rattrap-docs/` directory
   - If official documentation → Ask user to confirm
   - If user explicitly requests project → Use project directory

3. **Create with clear path**:
   ```
   ❌ Bad: Writing to ./test-api.py
   ✅ Good: Writing to /tmp/rattrap-docs/test-api.py
   ```

4. **Inform the user**:
   ```
   ✅ Test script saved to /tmp/rattrap-docs/test-api.py
   💡 This file is in /tmp to keep the repository clean.
   💡 Say "save to project" if you want to add it to the repository.
   ```

### When User Wants to Promote Temp File to Project

If user says "add this to the project":
1. Copy the file from `/tmp` to appropriate project location
2. Ask for confirmation on the exact location
3. Stage the file with `git add`
4. Let user decide when to commit

## Directory Structure

Use organized `/tmp` directories:

```
/tmp/rattrap-docs/
├── tests/              # Test scripts
├── docs/               # Temporary documentation
├── analysis/           # Data analysis
├── examples/           # Code examples
└── experiments/        # Experimental code
```

## Important Rules

1. **Never pollute the repository** - Default to `/tmp` when in doubt

2. **Always inform** - Tell user where files are saved

3. **Make it easy to promote** - Keep temp files organized for easy migration

4. **Respect explicit requests** - If user says "in the project", honor it

5. **Context awareness**:
   - Writing a new API endpoint → Project
   - Writing a test for that endpoint → `/tmp` (unless requested)
   - Official documentation → Ask first
   - Quick note or TODO → `/tmp`

## Examples

### Example 1: Test Script

User: "Write a test script for the setup-sessions API"

```
✅ Correct approach:
- Save to: /tmp/rattrap-docs/tests/test-setup-sessions.py
- Tell user: "Test script saved to /tmp (keeps repo clean)"
- Offer: "Say 'add to project' if you want to commit it"
```

### Example 2: API Documentation

User: "Document the new trap-events endpoint"

```
✅ Correct approach:
- This is official documentation
- Ask: "Should I create this in rattrap-api/endpoint/?"
- If yes → Save to project
- If unsure → Save to /tmp first for review
```

### Example 3: Design Document

User: "Write a design doc for the new caching system"

```
✅ Correct approach:
- Save to: /tmp/rattrap-docs/docs/caching-design.md
- Tell user: "Design doc saved to /tmp for review"
- Suggest: "Review it, then say 'add to project' to keep it"
```

### Example 4: Explicit Request

User: "Create a test helper in the project utils folder"

```
✅ Correct approach:
- User said "in the project"
- Save to: ./utils/test-helpers.js
- This is clearly meant for the repository
```

## Questions to Ask Yourself

Before writing a file, ask:
1. Is this official project code/documentation? → Maybe project
2. Is this a test or experiment? → `/tmp`
3. Did user explicitly say "in project"? → Project
4. When in doubt? → `/tmp` (safer default)

## Benefits

1. **Clean repository** - Only essential files in version control
2. **Easy experimentation** - Users can test freely without worrying
3. **Better git history** - Less noise in commits
4. **Flexibility** - Easy to promote useful temp files later
5. **Organization** - Temp files are organized, not scattered

## User Communication Template

When saving to `/tmp`:
```
✅ [File description] saved to /tmp/rattrap-docs/[path]

💡 This keeps your repository clean. Files in /tmp are:
   - Safe for experimentation
   - Won't show up in git status
   - Easy to promote later with "add to project"

💡 Want to keep this file? Say "add [filename] to project"
```

## Edge Cases

1. **User runs the temp file successfully**
   - Ask: "This works well! Want to add it to the project?"

2. **Temp file becomes important**
   - Suggest: "This looks useful. Consider adding to project?"

3. **User creates many temp files**
   - Periodically remind about `/tmp` cleanup
   - List temp files if asked

4. **Configuration files**
   - `.env` → Always `/tmp` (never repository)
   - `.env.example` → Project is OK
   - Local configs → `/tmp`
   - Shared configs → Ask first

## Remember

> "When in doubt, keep it out (of the repository)"

Default to `/tmp` unless there's a clear reason for the file to be in version control.
