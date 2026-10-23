# SlothDesk frontend

The local-first SlothDesk dashboard connects to the FastAPI backend to scan a configured directory, generate an Ollama-powered organization plan, and apply only the actions a user approves.

## Run locally

```bash
npm install
cp .env.example .env
npm run dev
```

The backend defaults to `http://127.0.0.1:8000`. Set `VITE_API_BASE_URL` in `.env` when running it elsewhere. The frontend expects `/api/health`, `/api/scan`, `/api/plan`, and `/api/apply` as described in the project brief.

```bash
npm run build
npm run test:run
npm run lint
```

The UI intentionally shows honest empty or disconnected states when optional backend capabilities (history, duplicates, model metadata, or rollback) are not available.

## Template notes

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
