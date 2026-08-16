import json
import os
import sys

sys.path.append("../pycaruna")
from pycaruna import CarunaPlus, TimeSpan

if __name__ == "__main__":
    token = os.getenv("CARUNA_PLUS_TOKEN")
    customer_id = os.getenv("CARUNA_CUSTOMER_ID")

    if token is None or customer_id is None:
        raise Exception("CARUNA_PLUS_TOKEN and CARUNA_CUSTOMER_ID must be defined")

    # Create a Caruna Plus client
    client = CarunaPlus(token)

    # Get customer details and metering points so we can get the required identifiers
    customer = client.get_user_profile(customer_id)
    # print(customer)

    # Household meters are on /assets/meteringpoints (consumptionMeteringPoint).
    metering_points = client.get_metering_points(customer_id)
    # print(metering_points)

    # Get daily usage for the month of January 2023 for the first metering point. Yes, this means TimeSpan.MONTHLY. If
    # you want hourly usage, use TimeSpan.DAILY.
    asset_id = metering_points[0]["assetId"]
    january_energy = client.get_energy(
        customer_id, asset_id, TimeSpan.MONTHLY, 2023, 1, 1
    )
    # print(january_energy)

    # Rows may use totalConsumption (current API) or consumption (older API).
    from pycaruna import energy_kwh

    january_energy_filtered = [
        data
        for data in january_energy["results"][0]["data"]
        if energy_kwh(data) is not None
    ]
    january_energy_mapped = list(
        map(
            lambda data: {
                "date": data["timestamp"],
                "consumption": energy_kwh(data),
            },
            january_energy_filtered,
        )
    )

    print(json.dumps(january_energy_mapped, indent=2))
