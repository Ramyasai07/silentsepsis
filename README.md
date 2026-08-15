# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

---

## Backend Testing

The backend test suite is powered by `pytest`. Tests run inside the API container against the database service configured in `docker-compose.yml`.

### How to Run Tests

Ensure the docker services are running:
```bash
docker compose up -d
```

Run the pytest suite inside the API container:
```bash
docker compose exec api pytest
```

### Test Database Configuration & Isolation

- **Connection**: Tests run against the database URL configured in the `DATABASE_URL` environment variable inside the container (defaulting to the shared `silentsepsis` database).
- **Schema Migration**: On session start, `alembic` migrations are automatically executed via a session-scoped fixture to ensure the schema is up-to-date with `head`.
- **Data Isolation**: Since tests share the database, data isolation between tests is maintained by table-cleaning fixtures (e.g. `clean_data` or `clean_users` with `autouse=True`) in each test file. These fixtures perform `DELETE` queries on all model tables before and after each test run.
- **Environment Variables**:
  - `DATABASE_URL`: Connection string for PostgreSQL database.
  - `REDIS_URL`: Connection string for Redis instance.
  - `BOOTSTRAP_SECRET`: Secret header key for admin bootstrapping.
