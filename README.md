Personal Project:
A multithreaded Web scraper I wrote in Python, using the BeautifulSoup and requests libraries.

Result:
For each Geographical site in a Country on Wikimapia.org, this program gets the site's coordinates in decimal format.
The final result is a JSON file, organized by:

{'Country Name' : {'District'  : {'City' : { "Geographical Site" : {'Latitude', 'Longitude'} } } } }

HTTP Connection:
To avoid getting banned from the site, the program rotates between different User Agents for each request and waits a random amount of time after a request.

Threads:
The program splits the workload into five threads where each thread gets a country to scrape since the work is I/O intensive.

Scraping:
The Wikimapia website is organized by Country, District, and then City.
Inside a City's webpage, there can be many subpages, each one holding up to 50 links to Geographical sites.
The program can scroll through all those subpages, enter every link they old, and extract data about the Geographical Site (in this case Latitude and Longitude).
