Personal Project:
A multithreaded Web scraper I wrote in Python, using the BeautifulSoup and requests libraries.

Result:
For each Geographical site in a Country on Wikimapia, this program gets the sites coordintaes in decimal format.
The final result is a JSON file, organized by:

{'Country Name' : {'District'  : {'City' : { "Geographical Site" : {'Latitude', 'Longitude'} } } } }

HTTP Connection:
In order to not get banned from the site, the program rotates between different User Agents for each request and waits a random amount of time after a request.

Threads:
The program splits the workload into five threads where each thread gets a country to scrape, since this the work is I/O intensive.

Scraping:
The Wikimapia website is organized by Country, District and then City.
Inside a City's webpage there can many subpages, each one holding up to 50 links to Geographocal sites.
The program can scroll through all thos subpages, enter every link and extract data about the Geographical Site.
