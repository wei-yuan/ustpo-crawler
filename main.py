# import library
import datetime
import math
import re
import logging
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
        self.abstract = list()
        self.claim = list()
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

    international_class_offset = 4
    
    if title_image: international_class_offset += 1
    if html.text.find('Applicant:') > 0: international_class_offset += 1
    if html.text.find('Prior Publication Data') > 0: international_class_offset += 1
    if html.text.find('Foreign Application Priority Data') > 0: international_class_offset += 1
    if html.text.find('Related U.S. Patent Documents') > 0: international_class_offset += 1
    international_class = soup.find_all('table')[international_class_offset].find_all('td')[3].get_text().replace('\xa0', ' ')
    filed_date = soup.find_all('td', align='left', width='90%')[-1].get_text().replace('\n', '')
    assignee = soup.find_all('td', align='left', width='90%')[2].get_text().replace('\n', '')

    # append each patent data to CrawlerInfo instance
    data_container.patent_name.append(title)
    data_container.abstract.append(abstract)
    data_container.claim.append(claim)
    data_container.cpc_number.append(international_class)

    # print result
    print(f"title: {title}\nabstract: {abstract}\ncpc number: {international_class}\nclaim: {claim}\n")
    logging.info(f"title: {title}\nabstract: {abstract}\ncpc number: {international_class}\nclaim: {claim}")
    return data_container


def main():
    logging.basicConfig(
        filename=f'patent_crawler_{datetime.datetime.now().strftime("%y%m%d%h%m")}',
        format='%(asctime)s %(message)s',
        encoding='utf-8',
        level=logging.DEBUG
    )
    page = 1
    url = 'https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p='+str(page)+'&u=%2Fnetahtml%2FPTO%2Fsearch-adv.htm&r=0&f=S&l=50&d=PTXT&Query='+term
    html = requests.get(url, headers=headers)

    soup = BeautifulSoup(html.text, 'html.parser')
    total = int(soup.find_all('strong')[2].string)
    total_page = math.ceil(total / 50)
    print(f'Total page number: {total_page} pages\n')
    print(f'------------------------------------------')

    list_df = list()
    for page in range(1, total_page):
        logging.info(f'Start parsing current page: {page}')
        print(f'Current page: {page}\n')

        # create instance for recording patent information
        c_info = CrawlerInfo()

        url = 'https://patft.uspto.gov/netacgi/nph-Parser?Sect1=PTO2&Sect2=HITOFF&p='+str(page)+'&u=%2Fnetahtml%2FPTO%2Fsearch-adv.htm&r=0&f=S&l=50&d=PTXT&Query='+term
        html = requests.get(url, headers=headers)
        soup = BeautifulSoup(html.text, 'html.parser')
        table = soup.find_all('table')[1]
        links = table.find_all(href=re.compile("/netacgi/nph-Parser\?Sect1=PTO2&Sect2="))
        number = 0
        for row in links:
            number += 1
            if number % 2 == 0:
                prefix_string = str(row.attrs.get('href'))
                logging.info(f'Parsing (page, number): ({page}, {number})')
                try:
                    c_info = parse_search_page(prefix_string, c_info)
                except:
                    pass
                finally:
                    logging.info(f'*** Exception: Parsing Error at page: {page}, number: {number} ***')

                # create dataframe
                df = pd.DataFrame()
                df[field_names[0]] = c_info.patent_name
                df[field_names[1]] = c_info.abstract
                df[field_names[2]] = c_info.claim
                df[field_names[3]] = c_info.cpc_number
                df[field_names[4]] = pd.Series(np.nan, dtype=float)  # just create an empty column
                df[field_names[5]] = pd.Series(np.nan, dtype=float)
                list_df.append(df)

                # write to file
                df.to_csv(f'patent_info_{page}.csv', index=False)
                logging.info(f'Output csv file: patent_info_{page}.csv')
        print(f'------------------------------------------')

    # merge all dataframe
    merged_df = pd.concat(list_df, axis=0)

    # write to file
    merged_df.to_csv('patent_info.csv', index=False)


if __name__ == "__main__":
    main()
