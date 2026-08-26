### Lens

A log viewer for the Frappe fleet. Reads logs stored in ClickHouse (via the Datum telemetry service) and presents them in a searchable, filterable UI built with frappe-ui.

### Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/20vikash/Lens.git --branch develop
bench install-app lens
```

### Setup

1. Create a ClickHouse data source in the **Insights Data Source v3** doctype (database type: ClickHouse), pointing at the Datum `logs` table.
2. Visit `/logs` to open the viewer.

### Frontend development

```bash
cd apps/lens/frontend
yarn install
yarn dev    # dev server on :8085, proxies to bench
yarn build  # builds to lens/public/frontend/ and copies index.html to www/logs.html
```

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/lens
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
