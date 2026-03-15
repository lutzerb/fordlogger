# Contributing to FordLogger

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork and set up the dev environment:

```bash
git clone https://github.com/YOUR_USERNAME/fordlogger.git
cd fordlogger
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

3. Start PostgreSQL for testing:

```bash
docker compose up -d db
```

## Running Tests

Tests use a separate `fordlogger_test` database (never the production `fordlogger` database):

```bash
FORDLOGGER_DB_HOST=localhost python3 -m pytest tests/ --ignore=tests/test_live_api.py -v
```

Live API tests call the real Ford API and require valid credentials in `config.json`:

```bash
FORDLOGGER_DB_HOST=localhost python3 -m pytest tests/test_live_api.py -v
```

## Pull Requests

- Create a feature branch from `main`
- Add tests for new functionality
- Make sure all tests pass before submitting
- Keep PRs focused — one feature or fix per PR

## Reporting Issues

When reporting bugs, please include:

- Steps to reproduce
- Relevant log output (`docker compose logs fordlogger`)
- Your vehicle model and year (if relevant to the issue)

## Ford API Quirks

If you discover new API behaviors, please document them. Known quirks:

- Some metrics are lists, not dicts (`doorLockStatus`, `tirePressure`, `doorStatus`, `windowStatus`, `seatBeltStatus`)
- `heading.value` is a nested dict, not a scalar
- `speed` reports ~0.09 km/h when parked (GPS noise)
- Rate limit is ~1 request per minute (429 errors are common)

## License

By contributing, you agree that your contributions will be licensed under the [AGPL-3.0](LICENSE) license.
