# pycaruna

Fork of [Jalle19/pycaruna](https://github.com/Jalle19/pycaruna) for the current [Caruna+](https://plus.caruna.fi/) API (2026).

Basic Python client for Caruna Plus. Enough to log in and pull electricity usage.

Supported features:

* Log in with the plus.caruna.fi email and password (not Suomi.fi)
* Get user profile information
* Get household metering points (`consumptionMeteringPoint`)
* Get consumption data (`TimeSpan.DAILY` is hourly for one day, `MONTHLY` daily for a month, `YEARLY` monthly for a year)

## Install

Requires Python 3.12 or newer.

```
uv add git+https://github.com/prosenstrom/pycaruna.git
```

Or with pip:

```
pip install git+https://github.com/prosenstrom/pycaruna.git
```

This fork is not published on PyPI. Upstream `pycaruna==1.0.3` still talks to an older login and JSON shape.

## Development

```
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run bandit -c pyproject.toml -r pycaruna
uv run ty check
```

## Usage

```python
from pycaruna import (
    Authenticator,
    CarunaPlus,
    TimeSpan,
    customer_ids_from_user,
    energy_kwh,
)

login = Authenticator(email, password).login()
client = CarunaPlus(login["token"])
customer_id = customer_ids_from_user(login["user"])[0]
meters = client.get_metering_points(customer_id)
hours = client.get_energy(
    customer_id, meters[0]["assetId"], TimeSpan.DAILY, 2026, 8, 16
)
kwh = [energy_kwh(row) for row in hours["results"][0]["data"]]
```

`get_energy()` always returns `{ "results": [ { "data": [ ...rows ] } ] }`. Use `energy_kwh(row)` for the kWh value — rows may use `totalConsumption` (current API), `consumption` (older API), or `invoicedConsumption`.

Login failures and expired tokens raise `CarunaAuthError`. Other HTTP or JSON failures raise `CarunaApiError`.

The `examples/` directory has longer programs. `resources/` has sample payloads, including the current flat energy list and meteringpoints.

## Caveats

* Login is a long redirect dance. Reuse the token (`expiresAt`, typically ~60 minutes).
* Household meters live at `/api/customers/{id}/assets/meteringpoints`, not only `/assets`.
* The energy endpoint returns a flat list, not the old `results` wrapper. This fork normalizes that.

## Related projects

* [caruna-influxdb](https://github.com/Jalle19/caruna-influxdb)
* [ha_caruna](https://github.com/petri-lipponen-movesense/ha_caruna) — Home Assistant custom component

## Credits

* [kimmolinna/pycaruna](https://github.com/kimmolinna/pycaruna)
* [Jalle19/pycaruna](https://github.com/Jalle19/pycaruna)

## License

MIT
