# pycaruna

[![PyPI version](https://badge.fury.io/py/pycaruna.svg)](https://badge.fury.io/py/pycaruna)

Basic Python implementation for interfacing with Caruna Plus (sometimes called _Caruna+_). It supports only basic 
methods, but enough to extract electricity usage data for further processing.

Supported features:

* Log in with the plus.caruna.fi email and password (not Suomi.fi)
* Get user profile information
* Get household metering points (`consumptionMeteringPoint`)
* Get consumption data (`TimeSpan.DAILY` is hourly for one day, `MONTHLY` daily for a month, `YEARLY` monthly for a year)

Login failures and expired tokens raise `CarunaAuthError`. Other HTTP or JSON failures raise `CarunaApiError`. Non-OK JSON responses are no longer returned as payload.

```python
from pycaruna import (
    Authenticator,
    CarunaPlus,
    TimeSpan,
    customer_ids_from_user,
    energy_kwh,
)

login = Authenticator(email, password).login()
client = CarunaPlus(login['token'])
customer_id = customer_ids_from_user(login['user'])[0]
meters = client.get_metering_points(customer_id)
hours = client.get_energy(
    customer_id, meters[0]['assetId'], TimeSpan.DAILY, 2026, 8, 16
)
kwh = [energy_kwh(row) for row in hours['results'][0]['data']]
```

`get_energy()` always returns `{ "results": [ { "data": [ ...rows ] } ] }`. Use `energy_kwh(row)` for the kWh value — rows may use `totalConsumption` (current API), `consumption` (older API), or `invoicedConsumption`.

## Usage

The project is published on PyPI: https://pypi.org/project/pycaruna/ . You can use this package by adding the 
following to your `requirements.txt`:

```
pycaruna
```

The `examples/` directory has example Python programs illustrating how to use the library.

The `resources/` directory has examples of API response structures.

## Caveats

* The authentication procedure requires a lot of HTTP requests to be sent back and forth, so the process is 
  relatively slow. It's best to store and reuse the token produced by it (`expiresAt`, typically ~60 minutes)
  instead of doing the authentication process all over again all the time.
* The login form action is no longer hardcoded. The client reads the live Wicket action and accepts either
  an `Ajax-Location` header or an XML `<redirect>` after posting credentials.
* Household meters live at `/api/customers/{id}/assets/meteringpoints`, not only `/assets`.
* The energy endpoint returns a flat list, not the old `results` wrapper. `get_energy()` normalizes that.

Callers that already iterate the live flat energy list (rather than `results[0]["data"]`) need to switch to the documented wrapper, or use `energy_kwh()`. `caruna-influxdb` is in that group.
* ~~During daylight savings time changes, the API may return a duplicate datapoint (same timestamp in two consecutive 
  data points). See https://github.com/Jalle19/pycaruna/issues/7 for more details.~~ This has reportedly been fixed, see
  https://github.com/Jalle19/pycaruna/issues/7#issuecomment-2660900192

## Related projects

* [caruna-influxdb](https://github.com/Jalle19/caruna-influxdb) - a collection of scripts for ingesting your Caruna data 
into InfluxDB

## Credits

https://github.com/kimmolinna/pycaruna

## License

MIT
