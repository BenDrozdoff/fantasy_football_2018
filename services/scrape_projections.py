# coding: utf8

import urllib.request
import time
from bs4 import BeautifulSoup

# credit to https://intoli.com/blog/fantasy-football-for-hackers/


def fetch_projections_page(week, position_id):
    assert 1 <= week <= 17, f"Invalid week: {week}"

    base_url = "https://www.fantasysharks.com/apps/bert/forecasts/projections.php"
    url = f"{base_url}?League=-1&Position={position_id}&scoring=1&Segment={659+week}&uid=4"

    request = urllib.request.Request(url)
    request.add_header('User-Agent', 'projection-scraper 0.1')
    with urllib.request.urlopen(request) as response:
        return response.read()


def scrape_projections():
    for week in range(1, 2):  # If your league uses week 17 you should quit
        position_map = {'rb': 2, 'wr': 4, 'te': 5, 'qb': 1}
        for position, position_id in position_map.items():
            time.sleep(5)
            html = fetch_projections_page(week, position_map[position])
            soup = BeautifulSoup(html, 'lxml')

            table = soup.find('table', id='toolData')
            header_row = table.find('tr')
            column_names = [th.text for th in header_row.find_all('th')]

            for row in table.find_all('tr'):
                column_entries = [tr.text for tr in row.find_all('td')]

                # exclude repeated header rows and the "Tier N" rows
                if len(column_entries) != len(column_names):
                    continue

                # extract Fantasy Shark's player id
                player_link = row.find('a')
                player_id = int(player_link['href'].split('=')[-1].strip())

                # yield a dictionary of this player's weekly projection
                player = {'id': player_id, 'week': week, 'position': position}
                for key, entry in zip(column_names, column_entries):
                    player[key.lower()] = entry
                yield player
