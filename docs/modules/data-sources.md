# Data Sources Module

Owner files:

- `backend/app/warehouse.py`
- `backend/app/lianxing_api.py`
- `backend/app/config.py`
- `backend/app/validation.py`

## Warehouse Adapter

The warehouse adapter:

- Connects to MySQL using settings from environment or `backend/.env`.
- Optionally opens an SSH tunnel before connecting to MySQL.
- Aggregates metrics by period and store.
- Supports daily and monthly periods.
- Supports `sum` and `count` metrics.
- Applies optional store mapping from a warehouse table.
- Splits warehouse aggregate queries into calendar-month windows and reconnects
  for each window to reduce long-query timeouts over SSH tunnels.
- Retries transient MySQL disconnects (`2006`/`2013`) once per warehouse window.

The adapter quotes table and field identifiers and validates simple identifiers
before rule persistence. Metric SQL expressions allow arithmetic characters but
block obvious dangerous tokens such as semicolons and SQL comments.

## Lingxing OpenAPI Adapter

The Lingxing adapter:

- Reads API base URL, app key, app secret, access token, refresh token, and token
  expiry from settings.
- Refreshes access tokens through `/api/auth-server/oauth/access-token`.
- Persists refreshed token values back to `backend/.env`.
- Builds signed JSON POST requests using `access_token`, `app_key`,
  `timestamp`, and AES-encrypted `sign`.
- Retries once after auth errors by refreshing the token.
- Supports page-based and offset-based pagination.
- Defaults order-profit style endpoints to offset pagination.
- Forces `currencyCode` to `USD` in request params.
- Supports nested field extraction such as `data.field` and `data>>field`.
- Supports `request_month` period mode for APIs that do not return a date field.

## Store Mapping

`StoreMapping` can be enabled per source:

- `table`: mapping table name, default `seller`
- `id_field`: raw ID field, default `sid`
- `name_field`: display/comparison name, default `name`

For ERP sources, the raw store value is extracted from the API response and then
mapped through warehouse mapping data.

## Environment Variables

See `backend/.env.example` for the complete list. Important groups:

- SQLite: `SQLITE_PATH`
- MySQL: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`,
  `MYSQL_DATABASE`, `MYSQL_CONNECT_TIMEOUT`, `MYSQL_READ_TIMEOUT`,
  `MYSQL_WRITE_TIMEOUT`
- SSH tunnel: `SSH_TUNNEL_ENABLED`, `SSH_HOST`, `SSH_PORT`, `SSH_USER`,
  `SSH_PASSWORD`, `SSH_REMOTE_HOST`, `SSH_REMOTE_PORT`
- Lingxing API: `LINGXING_API_BASE_URL`, `LINGXING_APP_KEY`,
  `LINGXING_APP_SECRET`, `LINGXING_ACCESS_TOKEN`,
  `LINGXING_REFRESH_TOKEN`, `LINGXING_TOKEN_EXPIRES_AT`

## Change Checklist

- Add mocked tests for signing, pagination, token refresh, and field extraction.
- Never commit real `.env` values or API responses with sensitive fields.
- Update sanitized examples when adding support for a new Lingxing module.
