import regex as re
import requests
import lxml
from lxml.html.soupparser import fromstring
import prettify
import numbers
import htmltext
import pandas as pd

from bs4 import BeautifulSoup
# from selenium import webdriver
# from selenium.webdriver.common.keys import Keys
# from selenium.webdriver.common.by import By

import general

#add headers in case you use chromedriver (captchas are no fun); namely used for chromedriver
REQ_HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'accept-encoding': 'gzip, deflate, br',
    'accept-language': 'en-US,en;q=0.8',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
}

#create url variables for each zillow page
def getZillowPages():
    with requests.Session() as s:    
        url = 'https://www.zillow.com/homes/Ravenswood,-Chicago,-IL_rb/'
        url2 = 'https://www.zillow.com/ravenswood-chicago-il/sold/2_p/?searchQueryState=%7B%22pagination%22%3A%7B%22currentPage%22%3A2%7D%2C%22usersSearchTerm%22%3A%22Ravenswood%2C%20Chicago%2C%20IL%22%2C%22mapBounds%22%3A%7B%22west%22%3A-87.71724421978759%2C%22east%22%3A-87.66119678021239%2C%22south%22%3A41.94853278970545%2C%22north%22%3A41.98880070258272%7D%2C%22regionSelection%22%3A%5B%7B%22regionId%22%3A33597%2C%22regionType%22%3A8%7D%5D%2C%22isMapVisible%22%3Atrue%2C%22filterState%22%3A%7B%22fsba%22%3A%7B%22value%22%3Afalse%7D%2C%22fsbo%22%3A%7B%22value%22%3Afalse%7D%2C%22nc%22%3A%7B%22value%22%3Afalse%7D%2C%22fore%22%3A%7B%22value%22%3Afalse%7D%2C%22cmsn%22%3A%7B%22value%22%3Afalse%7D%2C%22auc%22%3A%7B%22value%22%3Afalse%7D%2C%22pmf%22%3A%7B%22value%22%3Afalse%7D%2C%22pf%22%3A%7B%22value%22%3Afalse%7D%2C%22rs%22%3A%7B%22value%22%3Atrue%7D%2C%22ah%22%3A%7B%22value%22%3Atrue%7D%7D%2C%22isListVisible%22%3Atrue%2C%22mapZoom%22%3A14%7D'

        r = s.get(url, headers=REQ_HEADERS)
        r2 = s.get(url2, headers=REQ_HEADERS)
        
        return {"req1" : r, "req2": r2, "url_links" : [url, url2]}

def gatherZillowDetails(all_homes_df, soup):
    
    df = pd.DataFrame()
    
    #all for loops are pulling the specified variable using beautiful soup and inserting into said variable
    for i in soup:
        address = soup.find_all (class_= 'list-card-addr')
        price = list(soup.find_all (class_='list-card-price'))
        beds = list(soup.find_all("ul", class_="list-card-details"))
        details = soup.find_all ('div', {'class': 'list-card-details'})
        home_type = soup.find_all ('div', {'class': 'list-card-footer'})
        last_updated = soup.find_all ('div', {'class': 'list-card-top'})
        brokerage = list(soup.find_all(class_= 'list-card-brokerage list-card-img-overlay',text=True))
        link = soup.find_all (class_= 'list-card-link')

        #create dataframe columns out of variables
        df['price'] = price
        df['address'] = address
        df['beds'] = beds

    #create empty url list
    urls = []

    #loop through url, pull the href and strip out the address tag
    for link in soup.find_all("article"):
        href = link.find('a',class_="list-card-link")
        addresses = href.find('address')
        addresses.extract()
        urls.append(href)

    #import urls into a links column and remove html text
    df['links'] = urls
    df['links'] = df['links'].astype('str') 
    df['links'] = [link.split('href="')[-1].split('"')[0] for link in df['links']]
    
    if len(all_homes_df.columns) > 0: # Not the first page
        #append first two dataframes
        return all_homes_df.append(df, ignore_index = True) 
    else:
        return df

def getBedsBathsSqFt(html_str):
    if 'Land for sale' in html_str or 'sqft lot' in html_str: return -1,-1,-1 # This is land, not a residence
    split_strs = [s.split('>') for s in html_str.split('<')]
    key_stats = []
    for split_str in split_strs:
        for short_str in split_str:
            try:
                key_stats.append(int(short_str.replace(',','')))
            except:
                pass
    if len(key_stats) == 3: # All data available
        beds, baths, sqft = key_stats
    elif len(key_stats) == 0: # Degenerate case
        return -1,-1,-1
    else:
        try:
            beds, baths = key_stats
            sqft = -1
        except:
            print(key_stats, html_str)
    return beds, baths, sqft

def parseZillowDetails(df):

    #convert columns to str
    df['price'] = df['price'].astype('str')
    df['address'] = df['address'].astype('str')
    df['beds'] = df['beds'].astype('str')
    
    #remove html tags
    df['price'] = df['price'].replace('<div class="list-card-price">', ' ', regex=True)
    df['address'] = df['address'].replace('<address class="list-card-addr">', ' ', regex=True)
    df['price'] = df['price'].replace('</div>', ' ', regex=True)
    df['address'] = df['address'].replace('</address>', ' ', regex=True)
    df['price'] = df['price'].str.replace(r'\D', '')

    #split beds column into beds, bath and sq_feet
    df['beds'], df['baths'], df['sq_feet'] = zip(*df.beds.apply(getBedsBathsSqFt))

    #remove commas from sq_feet and convert to float
    df.replace(',','', regex=True, inplace=True)

    #drop nulls
    df = df[(df['price'] != '') & (df['price']!= ' ')]

    #convert column to float
    df['price'] = df['price'].astype('int')

    #remove spaces from link column
    df['links'] = df.links.str.replace(' ','')

    #rearrange the columns
    df = df[['price', 'address', 'links', 'beds', 'baths', 'sq_feet']]
    return df