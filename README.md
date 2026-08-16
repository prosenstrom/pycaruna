# pycaruna

Fork of [Jalle19/pycaruna](https://github.com/Jalle19/pycaruna) for the current [Caruna+](https://plus.caruna.fi/) API (2026).

Basic Python client for Caruna Plus. Enough to log in and pull electricity usage.

Supported features:

* Log in with the plus.caruna.fi email and password (not Suomi.fi)
* Get user profile information
* Get household metering points (`consumptionMeteringPoint`)
* Get consumption data (daily / monthly / yearly)

## Install

```
pip install git+https://github.com/prosenstrom/pycaruna.git
```

This fork is not published on PyPI. Upstream `pycaruna==1.0.3` still talks to an older login and JSON shape.

## Usage

```python
from pycaruna import Authenticator, CarunaPlus, TimeSpan, customer_ids_from_user

login = Authenticator(email, password).login()
client = CarunaPlus(login["token"])
customer_id = customer_ids_from_user(login["user"])[0]
meters = client.get_metering_points(customer_id)
hours = client.get_energy(
    customer_id, meters[0]["assetId"], TimeSpan.DAILY, 2026, 8, 16
)
```

`get_energy()` always returns `{ "results": [ { "data": [ ...rows ] } ] }`. Each row may use `totalConsumption` (current API) or `consumption` (older API).

The `examples/` directory has longer programs. `resources/` has older sample payloads; live energy data is now a flat list.

## Caveats

* Login is a long redirect dance. Reuse the token (`expiresAt`, typically ~60 minutes).
* Household meters live at `/api/customers/{id}/assets/meteringpoints`, not only `/assets`.
* The energy endpoint returns a list of hours, not the old `results` wrapper. This fork normalizes that.

## Related projects

* [caruna-influxdb](https://github.com/Jalle19/caruna-influxdb)
* Home Assistant custom component on the house box: `~/home-assistant-config/custom_components/caruna`

## Credits

* [kimmolinna/pycaruna](https://github.com/kimmolinna/pycaruna)
* [Jalle19/pycaruna](https://github.com/Jalle19/pycaruna)

## License

MIT
