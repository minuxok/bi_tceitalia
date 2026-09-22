# Automatic Session & Project Memory Rule

## Memory Management Protocol for AI Assistants (Antigravity, Claude Code, Codex)

1. **Session Start (Context Recall)**:
   - At the start of any task, check the MCP Memory Server (`search_nodes` / `read_graph`) and project memory files for existing architecture, conventions, and user preferences.

2. **Automatic Post-Task Memory Recording**:
   - At the end of every task, bugfix, or feature addition, automatically record key findings:
     - Architectural choices, API contracts, database schemas, and dependencies.
     - Environment setup, ports, and configuration changes.
     - Resolved bugs and user preferences.
   - Use MCP Memory tools (`create_entities`, `add_observations`, `create_relations`) to update the knowledge graph without requiring explicit prompt commands from the user.
