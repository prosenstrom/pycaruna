# Change log

## Unreleased
* Fix login against the current plus.caruna.fi Wicket form: read the form action from the page, follow `Ajax-Location` or an XML `<redirect>`, and raise `CarunaAuthError` / `CarunaApiError` instead of a raw `KeyError` when the dance changes again.
* `CarunaPlus.get_metering_points()` loads household meters from `/assets/meteringpoints` (`consumptionMeteringPoint`) and falls back to `/assets`.
* `CarunaPlus.get_energy()` accepts a flat `totalConsumption` list as well as the older `{results:[{data:[…]}]}` wrapper. Use `energy_kwh()` for the kWh value.

## 1.0.3
* Fix authentication flow (https://github.com/Jalle19/pycaruna/pull/14, thanks to @jarmoruuth)

## 1.0.2
* First version published on PyPI

## 1.0.1
* Fix authentication flow (https://github.com/Jalle19/pycaruna/pull/10, thanks to @jerop and @kimmolinna)
* Replace `setup.py` with `pyproject.toml` (https://github.com/Jalle19/pycaruna/pull/11)

## 1.0.0
* Major redesign to support the new Caruna Plus API (https://github.com/Jalle19/pycaruna/issues/3)

## 0.0.2
* Fix authentication after Caruna's latest changes

## 0.0.1
Initial fork, add `setup.py` to make it installable with `pip`
