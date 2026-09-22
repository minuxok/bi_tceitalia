# Project Memory & AI Rules — Conversational BI

## Automatic Memory Protocol
- **Start of Session**: Query the MCP Memory Server (`search_nodes` / `read_graph`) for context on `Conversational_BI`, stack details, and user preferences.
- **End of Task / Session**: Automatically record key architectural choices, new endpoints, DB schemas, resolved bugs, and user preferences into MCP Memory Server via `create_entities` / `add_observations` / `create_relations`.
- Do NOT prompt the user to confirm saving memory; execute memory updates automatically.
