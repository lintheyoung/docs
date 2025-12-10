# Navigation Update Skill

You are a documentation navigation manager that ensures all new documentation pages are properly added to the navigation menu.

## Your Mission

Whenever a new `.mdx` or `.md` documentation file is created in the project, ensure it's added to the `docs.json` navigation configuration file.

## When to Use This Skill

This skill should be activated **automatically** whenever:
1. A new `.mdx` file is created in `rattrap-api/endpoint/` directory
2. A new `.md` file is created that should appear in documentation
3. User explicitly mentions creating documentation
4. User says "add to navigation" or similar phrases

## Navigation File Location

The navigation configuration is located at: `./docs.json`

## How to Update Navigation

### Step 1: Identify the New File

When a new documentation file is created, note:
- File path (e.g., `rattrap-api/endpoint/new-feature.mdx`)
- Category/group it belongs to (e.g., "AI 客服", "陷阱管理", "Setup Sessions")
- Position in the menu (usually add to end of relevant group)

### Step 2: Read docs.json

Open and read the current navigation structure:
```bash
Read /Users/ginman/projects/docs/docs.json
```

Look for the relevant group in the `navigation.tabs` array.

### Step 3: Add to Navigation

Add the new page to the appropriate group in `docs.json`:

**Format**: The page path should be **without** the `.mdx` extension.

```json
{
  "group": "AI 客服",
  "pages": [
    "rattrap-api/endpoint/rag-qa",
    "rattrap-api/endpoint/knowledge-upload",
    "rattrap-api/endpoint/get-knowledge",
    "rattrap-api/endpoint/new-feature"  // Add here (no .mdx extension)
  ]
}
```

### Step 4: Verify

After updating, remind the user:
```
✅ Added 'new-feature' to navigation menu under "AI 客服" group
📝 File: docs.json updated
🔍 Position: Added after 'get-knowledge'
```

## Navigation Groups

Current groups in the RatTrap API documentation:

| Group | Purpose | Example Files |
|-------|---------|---------------|
| 概览 | Introduction and overview | `introduction` |
| 认证 | Authentication endpoints | `login`, `refresh-token` |
| Setup Sessions | Setup session workflow | `create-setup-session`, `update-setup-session` |
| AI 智能推荐 | AI recommendation endpoints | `trap-recommendations`, `location-analyses` |
| 媒体资源 | Media asset management | `create-media-asset` |
| Webhooks | Webhook endpoints | `crisp-message-hook` |
| AI 客服 | AI customer service | `rag-qa`, `knowledge-upload`, `get-knowledge` |
| 陷阱管理 | Trap management | `list-traps`, `get-trap`, `create-trap-event` |

## Decision Logic

When a new file is created, determine which group it belongs to:

**By file prefix/category:**
- `/endpoint/login*` → 认证
- `/endpoint/*-setup-session*` → Setup Sessions
- `/endpoint/*-recommendation*` → AI 智能推荐
- `/endpoint/*-check*` → AI 智能推荐
- `/endpoint/*-analyses` → AI 智能推荐
- `/endpoint/*-annotations` → AI 智能推荐
- `/endpoint/media-*` → 媒体资源
- `/endpoint/*-hook` → Webhooks
- `/endpoint/rag-*` → AI 客服
- `/endpoint/knowledge-*` → AI 客服
- `/endpoint/*-trap*` → 陷阱管理

**If uncertain**, ask the user which group to add it to.

## Important Rules

1. **Always verify** the file exists before adding to navigation
2. **Remove .mdx extension** when adding to docs.json
3. **Maintain order** - add new items at logical positions (usually end of group)
4. **Check for duplicates** - don't add if already exists
5. **Validate JSON** - ensure docs.json remains valid JSON after editing

## Error Handling

If something goes wrong:

**File doesn't exist:**
```
❌ Error: File 'rattrap-api/endpoint/new-feature.mdx' not found
💡 Please create the file first, then add to navigation
```

**Invalid JSON:**
```
❌ Error: docs.json has invalid JSON syntax
💡 Please check the JSON syntax (commas, brackets, quotes)
```

**Group not found:**
```
⚠️  Warning: Group "New Group" not found in docs.json
💡 Available groups: 概览, 认证, Setup Sessions, AI 智能推荐...
```

## Workflow Example

```
1. User creates file: rattrap-api/endpoint/knowledge-search.mdx
   ↓
2. Skill activates: "Detected new documentation file"
   ↓
3. Read docs.json to find "AI 客服" group
   ↓
4. Add "rattrap-api/endpoint/knowledge-search" to pages array
   ↓
5. Verify and confirm:
   ✅ Added 'knowledge-search' to navigation
   📍 Group: AI 客服
   📝 Position: After 'delete-knowledge'
```

## Proactive Reminders

After creating ANY new `.mdx` file, **automatically** remind the user:

```
📋 New documentation file created: [filename]
⚠️  Don't forget to add it to the navigation menu!

Would you like me to add it to docs.json now?
- If yes: I'll detect the appropriate group and add it
- If no: You can add it manually later
```

## Quick Commands

User can trigger navigation updates with phrases like:
- "add to navigation"
- "update docs menu"
- "register new doc"
- "add [filename] to menu"

## Success Criteria

After updating navigation, the file should:
- ✅ Appear in the left sidebar menu on the documentation website
- ✅ Be clickable and navigate to the correct page
- ✅ Be in the correct group/category
- ✅ Have proper order relative to other items

## Notes

- Navigation updates are **critical** - docs won't be accessible without them
- Always test after updating by checking the deployed documentation site
- Keep navigation structure clean and logical
- Group related pages together for better UX
