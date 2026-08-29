from enum import Enum

import requests

import pycaruna.utils as utils


class TimeSpan(Enum):
    DAILY = 'daily'
    MONTHLY = 'monthly'
    YEARLY = 'yearly'


class CarunaPlus:
    def __init__(self, token):
        self.token = token

    def get_user_profile(self, customer_id):
        """
        Returns the user's profile information
        :param customer_id: the customer number
        :return: the user information
        """
        r = requests.get(
            url=utils.create_caruna_plus_url(f'/customers/{customer_id}/info'),
            headers=utils.create_caruna_plus_headers(self.token),
            timeout=30,
        )

        return r.json()

    def get_assets(self, customer_id):
        """
        Returns the assets available for the specified customer.

        Household meters are usually on get_metering_points() instead.
        :param customer_id: the customer ID
        :return: the assets, including a lot of metadata about them
        """
        r = requests.get(
            url=utils.create_caruna_plus_url(f'/customers/{customer_id}/assets'),
            headers=utils.create_caruna_plus_headers(self.token),
            timeout=30,
        )

        return r.json()

    def get_metering_points(self, customer_id):
        """
        Returns household metering points for the specified customer.

        Tries /assets/meteringpoints first, then /assets.
        :param customer_id: the customer ID
        :return: a list of metering-point dicts, each with assetId and customerId
        """
        points = []
        seen = set()
        for path in (
            f'/customers/{customer_id}/assets/meteringpoints',
            f'/customers/{customer_id}/assets',
        ):
            r = requests.get(
                url=utils.create_caruna_plus_url(path),
                headers=utils.create_caruna_plus_headers(self.token),
                timeout=30,
            )
            if not r.ok:
                continue
            try:
                payload = r.json()
            except ValueError:
                continue
            for asset in utils.asset_items(payload):
                if not utils.is_meter(asset):
                    continue
                asset_id = str(
                    asset.get('assetId')
                    or asset.get('meteringPointNumber')
                    or asset.get('id')
                    or ''
                )
                if not asset_id or asset_id in seen:
                    continue
                seen.add(asset_id)
                item = dict(asset)
                item['customerId'] = customer_id
                item['assetId'] = asset_id
                points.append(item)
        return points

    def get_contracts(self, customer_id):
        """
        Returns the contracts available for the specified customer
        :param customer_id: the customer ID
        :return: the contracts
        """
        r = requests.get(
            url=utils.create_caruna_plus_url(f'/customers/{customer_id}/contracts'),
            headers=utils.create_caruna_plus_headers(self.token),
            timeout=30,
        )

        return r.json()

    def get_energy(self, customer_id, asset_id, timespan, year, month, day):
        """
        Returns energy consumption for the specified metering point.

        Always returns {results:[{data:[...]}]}. Rows may use totalConsumption
        or consumption.
        :param customer_id: the customer ID
        :param asset_id: the asset ID
        :param timespan: the time span (a TimeSpan enum)
        :param year: the year
        :param month: the month
        :param day: the day
        :return: the consumption data
        """
        r = requests.get(
            url=utils.create_caruna_plus_url(
                f'/customers/{customer_id}/assets/{asset_id}/energy'
            ),
            params={
                'year': year,
                'month': month,
                'day': day,
                'timespan': timespan.value,
            },
            headers=utils.create_caruna_plus_headers(self.token),
            timeout=30,
        )

        return utils.normalize_energy(r.json())
