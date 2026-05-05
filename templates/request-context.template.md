# MaDongMei Request Context Template

## Request
- query: {{query}}
- workspace: {{workspace_id}}
- profile: {{profile}}

## Memory
- summary: {{memory_summary}}
- recent notes: <redacted public template>
- recall mode: <summary_only | summary_then_raw | skip>

## Wiki
- summary: {{wiki_summary}}
- route: <selected topic or none>
- action: <promote | skip>

## Skill
- summary: {{skill_summary}}
- route: <selected skill or none>
- action: <autoload | memory_only>

## Install
- note: {{install_note}}

## Template Rules
- Keep private paths, secrets, and device-local state out of the template.
- Replace placeholders with public, reusable summaries only.
