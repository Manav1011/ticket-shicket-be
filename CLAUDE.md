## Repo Rules

- Before answering architecture or codebase questions, read `graphify-out/GRAPH_REPORT.md` for the current graph structure and high-connectivity nodes.
- If `graphify-out/wiki/index.md` exists, navigate it instead of reading raw files.
- After modifying code files in this session, run `python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current.
- The project uses LocalStack S3 in local development. The default bucket in the current environment is `ticket-shicket-media`.

## Common Commands

Use `uv` for all project commands.

```bash
# Install dependencies
uv sync

# Start local infrastructure
docker compose up -d

# Start the development server
uv run main.py run --debug

# Start the server on a custom host or port
uv run main.py run --host 0.0.0.0 --port 8080 --debug

# Create database migrations from model changes
uv run main.py makemigrations

# Apply pending migrations
uv run main.py migrate

# Show migration status
uv run main.py showmigrations

# Roll back the last migration
uv run main.py rollback

# Create a new app module
uv run main.py startapp <app_name>

# Create multiple app modules
uv run main.py startapps <app_name_1> <app_name_2>
```

The app entrypoint is `main.py`, so commands should always be run through `uv run main.py ...`.
