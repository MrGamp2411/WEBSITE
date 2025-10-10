# mcMMO Plugin YAML Fix

The Paper server rejected the bundled `plugin.yml` with the error:

```
mapping values are not allowed here (SnakeYAML, line 476)
```

The offending line looked like this inside the permissions block:

```yaml
      mmo.admin.quest: true
```

Tabs were used for the indentation beneath the `children` mapping, so
SnakeYAML treated the entry as malformed. Replacing the tabs with spaces and
keeping each permission node as a nested mapping resolves the issue on Paper
1.21.8.

The corrected structure is included below so it can be copied straight into the
plugin before rebuilding the JAR.

```yaml
name: mcMMOPlugin
version: 0.1.0
main: com.example.mcmmoplugin.McMMOPlugin
api-version: '1.21'
description: >-
  Custom mcMMO administrative helpers for quest and skill management.
authors:
  - Siply Dev Team
commands:
  mcmmoadmin:
    description: Admin commands for mcMMO integration.
    usage: /<command> <subcommand>
    permission: mmo.admin
permissions:
  mmo.admin:
    description: Grants access to all administrative mcMMO tools.
    default: op
    children:
      mmo.admin.quest: true
      mmo.admin.skills: true
  mmo.admin.quest:
    description: Allows managing mcMMO quests.
    default: op
  mmo.admin.skills:
    description: Allows managing mcMMO skill data.
    default: op
```

## Usage

1. Replace the existing `plugin.yml` inside your plugin sources with the
   version tracked in this folder.
2. Confirm there are no tabs left in the file (`grep '\t' plugin.yml` should
   return nothing).
3. Rebuild the plugin JAR and copy it back to the server's `plugins/` folder.
4. Restart the Paper server; the plugin will now load without YAML errors.
