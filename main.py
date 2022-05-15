# import library
import math
import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


term = '("stylus+pen"+OR+"electronic+stylus")+AND+coil'
headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}

field_names = ['patent_name', 'patent_ID', 'claim1', 'cpc number', 'claim1_feature_vector', 'cluster']


class CrawlerInfo:
    def __init__(self):
        self.patent_name = list()
        self.patent_id = list()
        self.claim1 = list()
        self.cpc_number = list()
        self.claim1_feature_vector = list()
        self.cluster = list()


def parse_search_page(url: str, data_container: CrawlerInfo):
    prefix = 'https://patft.uspto.gov'
    html = requests.get(prefix+url, headers=headers)
    soup = BeautifulSoup(html.text, 'html.parser')

    title_image = False
    if html.text.find('**Please see images for:') > 0: title_image = True

    num = soup.find_all('table')[2].find_all('b')[1].string.strip()
    date = soup.find_all('table')[2].find_all('b')[3].string.strip()
    
    title_offset = 6 if title_image else 3
    title = soup.find_all('font')[title_offset].get_text().replace('\n', '').replace('  ', '')

    abstract = soup.find_all('p')[0].get_text(strip=True).replace('\n', '').replace('  ', '')

    target = soup.find_all('p')[1]
    claim = BeautifulSoup(
        str(target)[str(target).index('<center><b><i>Claims</i></b></center>')+38:str(target).index('<center><b><i>Description</i></b></center>')],
        features='html.parser'
    ).get_text().replace('\n', ' ')
    description = BeautifulSoup(
        str(target)[str(target).index('<center><b><i>Description</i></b></center>')+43:str(target).index('<center><b>* * * * *</b></center>')],
        features='html.parser'
    ).get_text().replace('\n', ' ')

    international_class_offset = 5
    if title_image: international_class_offset += 1
    if html.text.find('Prior Publication Data') > 0: international_class_offset += 1
    if html.text.find('Foreign Application Priority Data') > 0: international_class_offset += 1
    if html.text.find('Related U.S. Patent Documents') > 0: international_class_offset += 1
    international_class = soup.find_all('table')[international_class_offset].find_all('td')[3].get_text().replace('\xa0', ' ')
    filed_date = soup.find_all('td', align='left', width='90%')[-1].get_text().replace('\n', '')
    assignee = soup.find_all('td', align='left', width='90%')[2].get_text().replace('\n', '')

    # append each patent data to CrawlerInfo instance
    data_container.patent_name.append(title)
    data_container.patent_id.append(num)
    data_container.claim1.append(claim)
    data_container.cpc_number.append(international_class)

    # print result
    print(f"title: {title}\nnumber: {num}\ncpc number: {international_class}\nclaim: {claim}")
    return data_container


def main():
    page = 1
    url = 'https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p='+str(page)+'&u=%2Fnetahtml%2FPTO%2Fsearch-adv.htm&r=0&f=S&l=50&d=PTXT&Query='+term
    html = requests.get(url, headers=headers)

    soup = BeautifulSoup(html.text, 'html.parser')
    total = int(soup.find_all('strong')[2].string)
    total_page = math.ceil(total / 50)
    print(total_page)

    # create instance for recording patent information
    c_info = CrawlerInfo()

    for page in range(1, total_page):
        url = 'https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p='+str(page)+'&u=%2Fnetahtml%2FPTO%2Fsearch-adv.htm&r=0&f=S&l=50&d=PTXT&Query='+term
        html = requests.get(url, headers=headers)
        soup = BeautifulSoup(html.text, 'html.parser')
        table = soup.find_all('table')[1]
        links = table.find_all(href=re.compile("/netacgi/nph-Parser\?Sect1=PTO2&Sect2="))
        i = 0
        add = []
        print('page:' + str(page))
        for row in links:
            i += 1
            if i % 2 == 0:
                add.append(row.attrs.get('href'))
                print('row: ' + str(row.attrs.get('href')))
                prefix_string = str(row.attrs.get('href'))
                c_info = parse_search_page(prefix_string, c_info)

        # if page == 3:
            # create dataframe
            df = pd.DataFrame()
            df[field_names[0]] = c_info.patent_name
            df[field_names[1]] = c_info.patent_id
            df[field_names[2]] = c_info.claim1
            df[field_names[3]] = c_info.cpc_number
            df[field_names[4]] = pd.Series(np.nan, dtype=float)  # just create an empty column
            df[field_names[5]] = pd.Series(np.nan, dtype=float)

            # write to file
            df.to_csv('patent_info.csv', index=False)


    # create dataframe
    df = pd.DataFrame()
    df[field_names[0]] = c_info.patent_name
    df[field_names[1]] = c_info.patent_id
    df[field_names[2]] = c_info.claim1
    df[field_names[3]] = c_info.cpc_number
    df[field_names[4]] = pd.Series(np.nan, dtype=float)  # just create an empty column
    df[field_names[5]] = pd.Series(np.nan, dtype=float)

    # write to file
    df.to_csv('patent_info.csv', index=False)


if __name__ == "__main__":
    main()
