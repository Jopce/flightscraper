import requests
import csv
import os


def fetch_data(api_url, from_airport, to_airport, depart_date, return_date):
    params = {
        "from": from_airport,
        "to": to_airport,
        "depart": depart_date,
        "return": return_date,
    }

    response = requests.get(api_url, params=params)
    response.raise_for_status()
    return response.json()


def extract_flight_data(data, connection_airport=None):
    data = data.get("body", {}).get("data", {})
    total_availabilities = {
        item["recommendationId"]: item["total"]
        for item in data.get("totalAvailabilities", [])
    }
    flight_data = {}

    for journey in data.get("journeys", []):
        flights = journey.get("flights", [])

        # Allow at most 1 connection
        if len(flights) > 2:
            continue

        # Bonus: if provided, checks that the connection airport matches (if it is not direct)
        if connection_airport and len(flights) == 2:
            if flights[0].get("airportArrival", {}).get("code") != connection_airport:
                continue

        trip = {"tax": journey.get("importTaxAdl"), "flights": []}

        for flight in journey.get("flights", []):
            trip["flights"].append(
                {
                    "flight_number": flight.get("companyCode")
                    + str(flight.get("number")),
                    "departure_airport": flight.get("airportDeparture", {}).get("code"),
                    "arrival_airport": flight.get("airportArrival", {}).get("code"),
                    "departure_time": flight.get("dateDeparture"),
                    "arrival_time": flight.get("dateArrival"),
                }
            )

        recommendation_id = journey.get("recommendationId")

        if recommendation_id not in flight_data:
            flight_data[journey["recommendationId"]] = {"outbound": [], "inbound": []}

        if journey.get("direction") == "I":
            flight_data[recommendation_id]["outbound"].append(trip)
        elif journey.get("direction") == "V":
            flight_data[recommendation_id]["inbound"].append(trip)

    return flight_data, total_availabilities


def combine_flights(flight_data, total_availabilities):
    round_trips = []

    for recommendation_id, flights in flight_data.items():
        for outbound in flights["outbound"]:
            for inbound in flights["inbound"]:
                round_trips.append(
                    {
                        "outbound": outbound["flights"],
                        "inbound": inbound["flights"],
                        "price": total_availabilities[recommendation_id],
                        "taxes": float(format(outbound["tax"] + inbound["tax"], ".2f")),
                    }
                )

    return round_trips


def save_to_csv(round_trips, filename, is_first_write=False):

    fieldnames = ["Price", "Taxes"]
    for i in range(1, 3):
        fieldnames.extend(
            [
                f"outbound {i} airport departure",
                f"outbound {i} airport arrival",
                f"outbound {i} time departure",
                f"outbound {i} time arrival",
                f"outbound {i} flight number",
            ]
        )
    for i in range(1, 3):
        fieldnames.extend(
            [
                f"inbound {i} airport departure",
                f"inbound {i} airport arrival",
                f"inbound {i} time departure",
                f"inbound {i} time arrival",
                f"inbound {i} flight number",
            ]
        )

    with open(filename, mode="a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if is_first_write:
            writer.writeheader()

        for trip in round_trips:
            row = {
                "Price": trip["price"],
                "Taxes": trip["taxes"],
            }
            for i, flight in enumerate(trip["outbound"], start=1):
                row.update(
                    {
                        f"outbound {i} airport departure": flight["departure_airport"],
                        f"outbound {i} airport arrival": flight["arrival_airport"],
                        f"outbound {i} time departure": flight["departure_time"],
                        f"outbound {i} time arrival": flight["arrival_time"],
                        f"outbound {i} flight number": flight["flight_number"],
                    }
                )
            for i, flight in enumerate(trip["inbound"], start=1):
                row.update(
                    {
                        f"inbound {i} airport departure": flight["departure_airport"],
                        f"inbound {i} airport arrival": flight["arrival_airport"],
                        f"inbound {i} time departure": flight["departure_time"],
                        f"inbound {i} time arrival": flight["arrival_time"],
                        f"inbound {i} flight number": flight["flight_number"],
                    }
                )
            writer.writerow(row)


def find_cheapest_round_trip(round_trips):
    if not round_trips:
        return []

    min_price = round_trips[0]["price"]
    cheapest_round_trips = [round_trips[0]]

    for trip in round_trips[1:]:
        if trip["price"] == min_price:
            cheapest_round_trips.append(trip)
        if trip["price"] < min_price:
            min_price = trip["price"]
            cheapest_round_trips = [trip]

    return cheapest_round_trips


# scraper starts from here
if __name__ == "__main__":
    API_URL = "http://homeworktask.infare.lt/search.php"

    # Search parameters: (from_airport, to_airport, depart_date, return_date, connection_airport)
    search_parameters = [
        ("MAD", "AUH", "2024-07-09", "2024-07-16", None),
        ("MAD", "FUE", "2024-07-09", "2024-07-16", None),
        ("JFK", "AUH", "2024-07-09", "2024-07-16", None),
        ("JFK", "FUE", "2024-07-09", "2024-07-16", None),
        ("CPH", "FUE", "2024-07-09", "2024-07-16", None),
        ("MAD", "FUE", "2024-07-16", "2024-07-23", None),
        ("MAD", "AUH", "2024-06-28", "2024-08-01", None),
        ("CPH", "MAD", "2024-07-04", "2024-07-31", "IDK"),
        ("CPH", "MAD", "2024-07-09", "2024-07-16", "AMS"),
        ("MAD", "FUE", "2024-08-01", "2024-08-28", None),
    ]

    os.makedirs("csv_files", exist_ok=True)

    all_trips_file = os.path.join("csv_files", "all_trips.csv")
    cheapest_trips_file = os.path.join("csv_files", "cheapest_trips.csv")

    if os.path.exists(all_trips_file):
        os.remove(all_trips_file)
    if os.path.exists(cheapest_trips_file):
        os.remove(cheapest_trips_file)

    is_first_write = True

    for (
        from_airport,
        to_airport,
        depart_date,
        return_date,
        connection_airport,
    ) in search_parameters:
        try:
            data = fetch_data(
                API_URL, from_airport, to_airport, depart_date, return_date
            )
        except Exception:
            print(
                f"Error fetching data for '{from_airport}' to '{to_airport}' at {depart_date} until {return_date}, continuing..."
            )
            continue

        flight_data, total_availabilities = extract_flight_data(
            data, connection_airport
        )

        if not flight_data:
            print(
                f"No viable flights found from '{from_airport}' to '{to_airport}' at {depart_date} until {return_date}, continuing..."
            )
            continue

        round_trips = combine_flights(flight_data, total_availabilities)

        if not round_trips:
            print(
                f"No viable round trips found from '{from_airport}' to '{to_airport}' at {depart_date} until {return_date}, continuing..."
            )
            continue

        save_to_csv(
            round_trips,
            all_trips_file,
            is_first_write,
        )

        cheapest_trips = find_cheapest_round_trip(round_trips)

        save_to_csv(
            cheapest_trips,
            cheapest_trips_file,
            is_first_write,
        )

        is_first_write = False

    print("Data saved to csv_files subdirectory.")
