## Short description of the scraper.

The scraper depends on requests, it can be installed via pip:
- `pip install requests`

How to run the scraper:
- `python scraper.py`

Please note that the scraper creates a csv_files subdirectory, in which 2 files will be placed: all_trips.csv and cheapest_trips.csv.

all_trips.csv contains all the valid trips that were obtained from the API.
cheapest_trips.csv contains the trips with the lowest prices for each search query.

If there is an error, it will print out the error message and continue to the next search query.
By default there are a few invalid search queries just to show how the scraper handles them.

Hopefully I met all the requirements, including the bonus one. 
