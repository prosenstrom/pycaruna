import logging
from enum import Enum

import requests

import pycaruna.utils as utils
from pycaruna.exceptions import CarunaApiError

_LOGGER = logging.getLogger(__name__)


def _error_excerpt(payload, limit=120):
    if isinstance(payload, dict):
        for key in ("message", "error", "errorMessage", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:limit]
    return str(payload)[:limit]


class TimeSpan(Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class CarunaPlus:
    def __init__(self, token):
        self.token = token

    def _get_json(self, path, params=None):
        response = requests.get(
            url=utils.create_caruna_plus_url(path),
            params=params,
            headers=utils.create_caruna_plus_headers(self.token),
            timeout=30,
        )
        try:
            payload = response.json()
        except ValueError as err:
            raise CarunaApiError(
                f"Non-JSON response from {path} ({response.status_code})",
                status_code=response.status_code,
            ) from err
        if not response.ok:
            if response.status_code in (401, 403):
                raise CarunaApiError(
                    f"Unauthorized calling {path}",
                    status_code=response.status_code,
                )
            raise CarunaApiError(
                f"Caruna+ request failed ({response.status_code}) for {path}: "
                f"{_error_excerpt(payload)}",
                status_code=response.status_code,
            )
        return payload

    def get_user_profile(self, customer_id):
        """
        Returns the user's profile information
        :param customer_id: the customer number
        :return: the user information
        """
        return self._get_json(f"/customers/{customer_id}/info")

    def get_assets(self, customer_id):
        """
        Returns the assets available for the specified customer.

        Household meters are usually *not* on this endpoint anymore; use
        get_metering_points() instead.
        :param customer_id: the customer ID
        :return: the assets, including a lot of metadata about them
        """
        return self._get_json(f"/customers/{customer_id}/assets")

    def get_metering_points(self, customer_id):
        """
        Returns household metering points for the specified customer.

        Tries /assets/meteringpoints first (current plus.caruna.fi, type
        consumptionMeteringPoint), then the older /assets list.
        :param customer_id: the customer ID
        :return: a list of metering-point dicts, each with assetId and customerId
        """
        points = []
        seen = set()
        last_error = None
        any_success = False
        for path in (
            f"/customers/{customer_id}/assets/meteringpoints",
            f"/customers/{customer_id}/assets",
        ):
            try:
                payload = self._get_json(path)
            except CarunaApiError as err:
                if err.status_code in (401, 403):
                    raise
                _LOGGER.debug("Skipping %s: %s", path, err)
                last_error = err
                continue
            any_success = True
            for asset in utils.asset_items(payload):
                if not utils.is_meter(asset):
                    continue
                asset_id = str(
                    asset.get("assetId")
                    or asset.get("meteringPointNumber")
                    or asset.get("id")
                    or ""
                )
                if not asset_id or asset_id in seen:
                    continue
                seen.add(asset_id)
                item = dict(asset)
                item["customerId"] = customer_id
                item["assetId"] = asset_id
                points.append(item)
        if not any_success and last_error is not None:
            raise last_error
        return points

    def get_contracts(self, customer_id):
        """
        Returns the contracts available for the specified customer
        :param customer_id: the customer ID
        :return: the contracts
        """
        return self._get_json(f"/customers/{customer_id}/contracts")

    def get_energy(self, customer_id, asset_id, timespan, year, month, day):
        """
        Returns energy consumption for the specified metering point.

        Accepts both the current flat hourly list (totalConsumption) and the
        older {results:[{data:[...]}]} wrapper. Always returns the wrapper
        form so callers can iterate results[].data[].
        :param customer_id: the customer ID
        :param asset_id: the asset ID
        :param timespan: the time span (a TimeSpan enum)
        :param year: the year
        :param month: the month
        :param day: the day
        :return: the consumption data
        """
        payload = self._get_json(
            f"/customers/{customer_id}/assets/{asset_id}/energy",
            params={
                "year": year,
                "month": month,
                "day": day,
                "timespan": timespan.value,
            },
        )
        return utils.normalize_energy(payload)
