# Frontend UI Module

Owner files:

- `frontend/src/App.vue`
- `frontend/src/api.js`
- `frontend/src/style.css`
- `frontend/dist/`

## Technology

- Vue 3
- Vite
- Plain CSS

## Screens

### Rule Management

Features:

- Rule list and search.
- Create/edit/delete rule.
- Warehouse configuration.
- ERP configuration.
- Request config JSON.
- Store mapping for warehouse and ERP.
- Metric list with aggregation and tolerance.
- OrderProfit-specific warning when the ERP store field is likely confused with
  a request parameter.

### Run Reconciliation

Features:

- Select multiple rules.
- Choose start/end date and day/month granularity.
- Use quick date ranges for current month, previous month, recent three full
  natural months, or custom dates.
- Start background batch job.
- Poll progress every two seconds.
- Cancel running job from the selected-rule status bar.
- Show failed rule records and link to failed run details when available.

### Result Viewer

Features:

- List and filter run history.
- Select multiple runs.
- Compare by month and metric.
- Filter by month, metric, and rule name.
- Expand store-level details.
- Delete run records.
- Export selected comparison.

## API Client

`frontend/src/api.js` wraps fetch calls and throws an `Error` with parsed backend
detail when possible.

## Dist Behavior

`frontend/dist` is committed. The backend serves this directory when present.
If `frontend/src` changes and the committed `dist` is not rebuilt, users running
the root `.bat` or Linux service may still see old UI behavior.

## Change Checklist

- Update API wrappers when backend routes or payloads change.
- Consider loading, empty, and error states for every user action.
- Rebuild `frontend/dist` when shipping source changes through the committed app
  bundle.
- Update screenshots or workflow docs if added later.
