# Future Development Ideas

Collecting data first — these are planned for later.

## High value, low effort
- ~~**Reverse geocoding**~~ — **Done!** Trips and charge sessions now have addresses via Nominatim
- **Charge cost tracking** — Add electricity price (ct/kWh) to config, calculate cost per charge session and monthly totals
- **Grafana alerting** — Charge complete, low SoC, unexpected movement (Grafana built-in to email/Telegram)

## Medium effort
- **Token expiry monitoring** — Refresh tokens expire after 90 days, warn before silent data loss
- **Health/uptime panel** — Show polling gaps, API errors, last successful poll
- **Data retention policy** — Downsample old positions data (e.g. 1-min for 90d, then 5-min)

## Larger features
- **Scheduled preconditioning** — If Ford API supports write operations (start/stop climate)
- ~~**Multi-vehicle support**~~ — **Done!** Grafana dashboards have a Vehicle dropdown; poller already handles multiple VINs
- **Companion web UI** — Flask/FastAPI for config, token status, manual actions
- **Fleet comparison** — Central server that aggregates anonymized stats (avg consumption, degradation, charge speeds) from opt-in FordLogger instances. Each instance sends periodic summaries (no VIN, no GPS — just model/year, monthly consumption, battery capacity trend, charge speeds, rough region). Dashboard panels show "your car vs fleet" percentiles. Needs critical mass of users to be useful.
