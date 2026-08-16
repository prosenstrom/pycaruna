CARUNA_PLUS_API_BASE_URL = 'https://plus.caruna.fi/api'
PYCARUNA_USER_AGENT = 'pycaruna'


def create_caruna_plus_url(path):
    return f'{CARUNA_PLUS_API_BASE_URL}{path}'


def create_caruna_plus_headers(token):
    return {
        'Authorization': f'Bearer {token}',
        'User-Agent': PYCARUNA_USER_AGENT,
    }


def get_hidden_form_vars(soup):
    vars = {}

    for var in soup.find_all("input"):
        name = var.get("name")
        if not name:
            continue
        if (var.get("type") or "text").lower() == "hidden":
            vars[name] = var.get("value") or ""

    return vars


def flatten_ids(value):
    """Customer numbers may be strings, ints, or nested lists."""
    ids = []
    if value is None:
        return ids
    if isinstance(value, (list, tuple, set)):
        for item in value:
            ids.extend(flatten_ids(item))
        return ids
    text = str(value).strip()
    if not text or text in {"None", "[]"}:
        return ids
    if "," in text:
        for part in text.split(","):
            ids.extend(flatten_ids(part.strip()))
        return ids
    ids.append(text)
    return ids


def customer_ids_from_user(user):
    """ownCustomerNumbers + representedCustomerNumbers from a login user object."""
    ids = flatten_ids((user or {}).get("ownCustomerNumbers"))
    ids.extend(flatten_ids((user or {}).get("representedCustomerNumbers")))
    unique = []
    for item in ids:
        if item not in unique:
            unique.append(item)
    return unique


def asset_items(payload):
    """Flatten an assets / meteringpoints API payload into a list of dicts."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in (
            "results",
            "data",
            "assets",
            "meteringPoints",
            "meteringpoints",
            "items",
        ):
            if isinstance(payload.get(key), list):
                return [item for item in payload[key] if isinstance(item, dict)]
        if (
            payload.get("assetId")
            or payload.get("gsrn")
            or payload.get("meteringPointNumber")
        ):
            return [payload]
    return []


def is_meter(asset):
    """True if this asset looks like a consumption or production metering point."""
    kind = str(asset.get("type") or "").lower()
    if any(word in kind for word in ("meter", "consumption", "production")):
        return True
    if asset.get("assetId") and (
        asset.get("gsrn")
        or asset.get("meteringPointNumber")
        or "consumption" in (asset.get("tabs") or [])
    ):
        return True
    return bool(asset.get("assetId") and asset.get("address"))


def normalize_energy(payload):
    """
    Accept the old results-wrapper, the current flat hourly list, or empty.

    Hour rows may use `consumption` or `totalConsumption`.
    """
    if isinstance(payload, list):
        return {"results": [{"data": payload}]}
    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            return payload
        for key in ("data", "hours", "days", "values", "items"):
            if isinstance(payload.get(key), list):
                return {"results": [{"data": payload[key]}]}
        if payload.get("timestamp") and (
            payload.get("totalConsumption") is not None
            or payload.get("consumption") is not None
        ):
            return {"results": [{"data": [payload]}]}
    return {"results": [{"data": []}]}


def energy_kwh(row):
    """kWh from a single energy row, whichever field Caruna used."""
    for key in ("consumption", "totalConsumption", "invoicedConsumption"):
        if row.get(key) is not None:
            return float(row[key])
    return None
