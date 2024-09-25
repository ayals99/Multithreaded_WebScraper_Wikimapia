# All Imports:
import re
import random
import json
import logging
from threading import Lock 
from sys import exit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from concurrent.futures import ThreadPoolExecutor

from bs4 import BeautifulSoup
from bs4 import SoupStrainer


# Global Variables:
baseURL = 'https://wikimapia.org/country/'

ErrorDuringOperation = False

entriesPerPage = 50

# soupStrainer object, so we don't have to read the whole HTML file:
parseList = SoupStrainer('div', class_='row-fluid')

# HTTP Connection Variables:
retryRule = Retry(total = 3,
                  backoff_factor = 2)
session = requests.Session()
adapter = HTTPAdapter(max_retries=retryRule)
session.mount("http://", adapter)
session.mount("https://", adapter)

userAgentList = ['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246',
                'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9',
                'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0',
                'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1' ]

headers = {
    'User-Agent': random.choice(userAgentList),
    'Accept' : 'text/html, application/xhtml+xml, application/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
}








# Start of function implementation:

# getFromURL will try to connect to the URL up to three times with different IP addresses:
def getFromURL(URL : str):
    try:
        allCountriesPage = session.get(URL, headers=headers, timeout=5)
        allCountriesPage.raise_for_status()
        # time.sleep(random.randrange(3)) # sleep to avoid being blocked
    except requests.exceptions.Timeout:
        log.critical("CRITICAL ERROR: Request timed out")
        ErrorDuringOperation = True
        return None
    except requests.exceptions.HTTPError as err:
        log.critical("CRITICAL ERROR: HTTP error")
        ErrorDuringOperation = True
        return None
    except requests.exceptions.RequestException as err:
        log.critical("CRITICAL ERROR: Requests Exception")
        ErrorDuringOperation = True
        return None
    else:
        log.info("Successfully got page from %s", URL)
        return allCountriesPage

# Description - parseCoordinates:
#   Takes a dictionary of a city as an argument
#   Fills it with all geographical sites in city
#   For each site name we associate a list in the dictionary with
#           1. description tag
#           2. map
#           3. coordinates
def parseCoordinates(coordinatesStr:str) -> dict:
    coordinatesDict = {}
    # split coordinate string into groups, according to the site's format.
    # Example of a coordinate string: 31°18\'58"N35°21\'14"E
    match = re.match(r'(\d+)°(\d+)\'(\d+)"([NS])(\d+)°(\d+)\'(\d+)"([EW])', coordinatesStr)

    if match:
        # Extract latitude components
        latitudeDegrees = int(match.group(1))
        latitudeMinutes = int(match.group(2))
        latitudeSeconds = int(match.group(3))
        latitudeDirection = match.group(4)
        
        # Extract longitude components
        longitudeDegrees = int(match.group(5))
        longitudeMinutes = int(match.group(6))
        longitudeSeconds = int(match.group(7))
        longitudeDirection = match.group(8)

        # Convert to decimal degrees
        latitude = latitudeDegrees + latitudeMinutes / 60 + latitudeSeconds / 3600
        if latitudeDirection == 'S':
            latitude *= -1

        longitude = longitudeDegrees + longitudeMinutes / 60 + longitudeSeconds / 3600
        if longitudeDirection == 'W':
            longitude *= -1
        
        coordinatesDict['Longitude'] = latitude
        coordinatesDict['Latitude'] = longitude
    return coordinatesDict

# Description - fillGeoSiteData:
#       1. Receives URL of Geographical site
#       2. Extracts the site's coordinates
#       3. Stores coordinates them in siteDict['Coordinates']
def fillGeoSiteData(geoSiteURL : str, siteDict : dict):
    page = getFromURL(geoSiteURL)
    if (page is None):
        return
    geoSiteSoup = BeautifulSoup(page.content,'lxml')
    NearCitiesAndCoordiantes = geoSiteSoup.find_all('b')

    # there are two "b" tags: Nearby Cities and Coordinates.
    # We want the second one, but we want the parent tag it's held in and not the "Coordinates" label itself:
    if len(NearCitiesAndCoordiantes) > 1:
        CoordinatesString = NearCitiesAndCoordiantes[1].parent.text.strip()
        
        # Because of the formatting that the website uses:
        CoordinatesString = CoordinatesString.replace(u'\xa0', u'')
        CoordinatesString = CoordinatesString.replace(u'\\', u' ')
        CoordinatesString = CoordinatesString.replace(" ", "")
        
        coordinateList = CoordinatesString.split(':') # remove the "Coordinates:" prefix from the string
        coordinates = parseCoordinates(coordinateList[1])
        with lock:
            log.info('parsed coordinates from %s', geoSiteURL)
            siteDict['Coordinates'] = coordinates

def fillCitySubpageDict(citySubpageURL : str, cityDict: dict):
    citySubpage = getFromURL(citySubpageURL)
    if (citySubpage is None):
        return
    citySubpageSoup = BeautifulSoup(citySubpage.content,'lxml')
    pageContent = citySubpageSoup.find('div',id='page-content')
    siteBox = pageContent.find('div', class_='row-fluid')
    for geoSite in siteBox.find_all('a', href=True):
        geoSiteName = geoSite.text.strip()
        if geoSiteName == 'map':
            continue
        with lock:
            cityDict[geoSiteName] = {}
        fillGeoSiteData(geoSite['href'], cityDict[geoSiteName])

def findAmountOfSubpages(cityFirstPageSoup) -> int:
    amountOfSubpages = 1
    subpagesBar = cityFirstPageSoup.find('div', class_='pagination pagination-centered')
    if subpagesBar is not None:
        subpageLinks = subpagesBar.find_all('a', href=True)
        for link in subpageLinks:
            if link.text.strip().isdigit():
                amountOfSubpages = max(amountOfSubpages, int(link.text.strip()))
    return amountOfSubpages

def fillCityDict(cityURL : str, cityDict : dict):
    log.info('started scannig City at %s', cityURL)

    cityPage = getFromURL(cityURL)
    if(cityPage is None):
        return
    cityFirstPageSoup = BeautifulSoup(cityPage.content,'lxml')
    amountOfSubpages = findAmountOfSubpages(cityFirstPageSoup)
    
    for pageNumber in range(0, amountOfSubpages - 1):
        offset = str(entriesPerPage * pageNumber) + '/'
        fillCitySubpageDict(cityURL + offset, cityDict)
        
# Description - fillDistrictDict
#       Takes a dictionary of a specific district inside a country as an argument
#       and fills it with an entry for each city in that district:
def fillDistrictDict(districtURL : str, districtDict : dict):
    log.info('started scannig District at %s', districtURL)
        
    districtPage = getFromURL(districtURL)
    if districtPage is None:
        return
    # time.sleep(random.randrange(7)) # sleep to avoid being blocked
    districtAndStateSoup = BeautifulSoup(districtPage.content,'lxml', parse_only=parseList)
    for cityLinkSuffix in districtAndStateSoup.find_all('a', href=True):
        cityName = cityLinkSuffix.text.strip()
        if cityName == 'map':
            continue
        with lock:
            districtDict[cityName] = {} # initialize dict for city in district
        fillCityDict(districtURL + cityLinkSuffix['href'], districtDict[cityName])

# takes a dictionary of a specitic country as an argument and fills it with all districts:
def fillCountryDict(countryURL : str, countryDict: dict):
    log.info('started scanning country at %s', countryURL)
    
    countryPage = getFromURL(countryURL)
    if countryPage is None:
        return
    # time.sleep(random.randrange(5)) # sleep to avoid being blocked
    countrySoup = BeautifulSoup(countryPage.content,'lxml', parse_only=parseList)
    for districtLinkSuffix in countrySoup.find_all('a', href=True):
        districtName = districtLinkSuffix.text.strip()
        with lock:
            countryDict[districtName] = {} # initialize a dict for a district
        fillDistrictDict(countryURL + districtLinkSuffix['href'], countryDict[districtName])

# End of helper function implementations



def threadSafeFillCountryDict(countryLink, countryName, MapDatabase):
    with lock:
        MapDatabase[countryName] = {}  # Initialize a dict for the country
    fillCountryDict(countryLink, MapDatabase[countryName])

# Start of usage - main:
def main():
    log.info('Started main()')

    MapDatabase = {}
    allCountriesPage = getFromURL(baseURL)
    if allCountriesPage is None:
        return
    allCountriesSoup = BeautifulSoup(allCountriesPage.content,'lxml', parse_only=parseList)
    with ThreadPoolExecutor(max_workers=5) as executor:
        print("Starting to parse all coordinates in", baseURL)
        for countryLinkSuffix in allCountriesSoup.find_all('a', href=True):
            countryName = countryLinkSuffix.text.strip()
            countryLink = baseURL + countryLinkSuffix['href'] # NOTE: can go through all countries by uncommenting this line and commenting next line:
            executor.submit(threadSafeFillCountryDict, countryLink, countryName, MapDatabase)

    with open('CountryDatabase.json', 'w') as db:
        json.dump(MapDatabase, db)

    if ErrorDuringOperation:
        print('JSON file creater with ERRORS')
    else:
        print("JSON file created successfully with Coordinates")

if __name__ == '__main__':
    lock = Lock()
    logging.basicConfig(format='%(asctime)s: %(message)s',
                    filemode='w',filename='webScraperLog.log',
                    encoding='utf-8', level=logging.INFO)
    log = logging.getLogger('webScraperLogger')
    main()