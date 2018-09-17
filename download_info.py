import gevent.monkey; gevent.monkey.patch_all()
import requests
import csv
import datetime
import os.path
import pickle
import grequests
from bs4 import BeautifulSoup
import json


def scrape_map_pages(set_ids):
    """Scrape pages given by set_ids and return submitted dates.
    Makes requests asynchronously with grequests.
    https://github.com/ppy/osu-api/issues/195
    old.ppy.sh may be faster but gives less info about dates.
    """

    submitted_dates = []
    urls = ["http://osu.ppy.sh/beatmapsets/"+str(set_id) for set_id in set_ids]
    rs = (grequests.get(u) for u in urls)
    for r in grequests.map(rs):
        assert(r.status_code == 200)  # set exists

        soup = BeautifulSoup(r.text, "html.parser")
        json_beatmapset = soup.find("script", id="json-beatmapset")
        submitted_date = json.loads(json_beatmapset.string)["submitted_date"]
        print(r.url, submitted_date)
        submitted_dates.append(submitted_date)

    assert(len(submitted_dates) == len(set_ids))
    return submitted_dates


class Seen:
    '''Organize seen information to be dumped.'''
    def __init__(self):
        self.header_seen = False
        self.header_keys = None
        self.seen_beatmap_ids = set()
        self.set_id_dict = dict()  # (set_id: submitted_date) pairs
   
    

def download_map_info(api_key, tsv_path="data.tsv",
                      seen_path="seen.pkl", scrape=True, break_early=False):
    """Main function to download and write data table from API (and scraping).
    Makes requests sequentially.
    Scraping mode adds what scrape_map_pages returns.
    If seen_path exists, tries to restart based on seen file (pickle)
    WARNING: Scraping is probably slow!
    Also resume functionality is EXPERIMENTAL.
    TODO: May write duplicate rows or headers again. Check.
    """


    API_URL = "https://osu.ppy.sh/api/get_beatmaps"
    tsvfile = open(tsv_path, 'a', encoding="utf-8")
    since_date_str = "2007-10-07"  # Date to start at
    API_MAX_RESULTS = 500
    
    
    seen = Seen()

    MYSQL_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"
    scrape_headers = ["submitted_date"]


    # Load or init seen structures
    if os.path.isfile(seen_path):
        print("Loading seen files", seen_path)
        with open(seen_path, 'rb') as f:
            seen = pickle.load(f)


    tsvwriter = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')

    # Requests session
    session = requests.Session()

    while True:
        payload = {"k": api_key, "since": since_date_str}
        r = session.get(API_URL, params=payload)

        info_dicts = r.json()
        if "error" in info_dicts:
            print(info_dicts)
            raise Exception("info_dict error")

        if not info_dicts: break  # Empty JSON, end of map search

        if not seen.header_seen:  # Write header once
            first_map = info_dicts[0]
            # First n cols of table
            # Alternative: Use bool list to indicate whether API or scraped
            seen.header_keys = sorted(first_map.keys())
            full_header = seen.header_keys.copy()
            if scrape: full_header.extend(scrape_headers)

            print("Full header", full_header)
            tsvwriter.writerow(full_header)
            seen.header_seen = True

        if scrape:
            # Gather set_ids in info_dicts to batch request
            set_ids_to_request = set()
            for info_dict in info_dicts:
                set_id = info_dict["beatmapset_id"]
                if set_id not in seen.set_id_dict:
                    set_ids_to_request.add(set_id)

            set_ids_to_request = list(set_ids_to_request)  # Fix order
            submitted_dates = scrape_map_pages(set_ids_to_request)

            # Add responses to seen.set_id_dict
            for (set_id, submitted_date) in \
                    zip(set_ids_to_request, submitted_dates):
                seen.set_id_dict[set_id] = submitted_date



        for info_dict in info_dicts:
            # Load info_dict value by header key
            row = [info_dict[key] for key in seen.header_keys]

            # Read from set_id_dict
            if scrape:
                set_id = info_dict["beatmapset_id"]
                # Append submitted_date
                row.append(seen.set_id_dict[set_id])


            # Clean strings
            # https://osu.ppy.sh/b/1468670?m=0 has a TAB in the tags
            # https://osu.ppy.sh/b/707380 has a newline in the tags
            for i in range(len(row)):
                if type(row[i]) == str and ('\t' in row[i] or '\n' in row[i]):
                    print("Bad whitespace detected!")
                    row[i] = row[i].replace('\t', ' ').replace('\n', ' ')


            # Write row, prevent duplicate rows being written
            beatmap_id = info_dict["beatmap_id"]
            if beatmap_id not in seen.seen_beatmap_ids:
                tsvwriter.writerow(row)
                seen.seen_beatmap_ids.add(beatmap_id)

                # Progress info, not actually used in written file
                print("{} {} {} - {} [{}]".format(
                    info_dict["approved_date"],
                    info_dict["beatmap_id"],
                    info_dict["artist"],
                    info_dict["title"],
                    info_dict["version"]))

            else:
                print("Skipped (seen {} already)".format(beatmap_id))


        # Write seen values
        # Should only run AFTER API call succeeds
        with open(seen_path, 'wb') as f:
            pickle.dump(seen, f)
        print("Wrote id pickle files")


        # When the API returns 500 results, last mapset may have diffs cut off.
        # Therefore, the whole mapset needs to be read again. The API's "since"
        # parameter appears to be exclusive, so subtract 1 second to include
        # the map again.

        end_date_str = info_dicts[-1]["approved_date"]
        end_date = datetime.datetime.strptime(
            end_date_str, MYSQL_TIMESTAMP_FMT)

        if len(info_dicts) == API_MAX_RESULTS:
            end_date -= datetime.timedelta(seconds=1)
        since_date_str = end_date.strftime(MYSQL_TIMESTAMP_FMT)

        print('-' * 50)

        if break_early: break


    tsvfile.close()
    session.close()


def scrape_rankings(gamemode, country, max_page):
    '''Scrape a rankings page for user IDs.
    https://github.com/ppy/osu-api/issues/132 '''
    RANKINGS_URL = "https://old.ppy.sh/p/pp"

    user_ids = []

    session = requests.Session()

    for page in range(1, max_page+1):
        payload = {'m': gamemode, "page": page}
        if country:
            payload['c'] = country

        r = session.get(RANKINGS_URL, params=payload)


        soup = BeautifulSoup(r.text, "html.parser")
        for href_tag in soup.find_all(href=True):
            link = href_tag['href']
            if link.startswith("/u"):
                user_ids.append(int(link.split("/u/")[1]))


    session.close()
    return user_ids


def exception_handler(request, exception):
    print(request, exception)


def download_rankings(api_key, gamemode=0, country=None, max_page=200,
                      top_scores=100):
    API_URL = "https://osu.ppy.sh/api/get_user_best"

    BATCH_REQUESTS = 10  # Don't exceed 1200 requests/min and make peppy angry
    user_ids = scrape_rankings(gamemode=gamemode, country=country,
                               max_page=max_page)

    print(user_ids)

    for i in range(0, len(user_ids), BATCH_REQUESTS):
        rs = []
        for user_id in user_ids[i:i+BATCH_REQUESTS]:
            payload = {'k': api_key, 'u': user_id, 'm': gamemode,
                       "limit": top_scores}
            rs.append(grequests.get(API_URL, params=payload))

        for r in grequests.map(rs, exception_handler=exception_handler):
            print(r.json())



if __name__ == "__main__":
    api_path = "api.key"
    API_KEY = open(api_path).read().strip()

    download_rankings(api_key=API_KEY, gamemode=3, max_page=2)