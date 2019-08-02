import datetime
import os.path
import pickle
import grequests
from bs4 import BeautifulSoup
import json
import time
import math
import argparse
import requests

class Progress:
    '''Organize seen information used in the process of making many API calls
    to be saved and reloaded.

    Attributes:
        json_list: list of info to be JSON dumped
    '''

    def __init__(self):
        self.json_list = []

    @staticmethod
    def load(progress_file):
        print("Loading progress file from", progress_file)
        with open(progress_file, 'rb') as f:
            return pickle.load(f)

    def save(self, progress_file):
        print("Saving progress to", progress_file)
        with open(progress_file, 'wb') as f:
            pickle.dump(self, f)

    def json_write(self, outfile):
        # Currently, per API, all values in JSON are strings
        print("Final write to", outfile)
        with open(outfile, 'w') as f:
            json.dump(self.json_list, f, indent=2)


def download_map_info(api_key,
                      outfile,
                      progress_file,
                      since_date_str="2001-01-01"):
    """Main function to download and write data table from API (and scraping).
    Makes requests sequentially.

    progress_file is always created.
    If progress_file exists, tries to restart based on seen file (pickle)

    Resume functionality appears stable, but no warranty(TM)
    TODO: add gamemode
    """

    assert outfile is not None, "outfile required"
    assert progress_file is not None, "progress_file required"

    API_URL = "https://osu.ppy.sh/api/get_beatmaps"
    API_MAX_RESULTS = 500
    MYSQL_TIMESTAMP_FMT = "%Y-%m-%d %H:%M:%S"

    # Load or init progress structures
    # maybe move this to Progress class
    if os.path.isfile(progress_file):
        print("Loading progress file", progress_file)
        progress = Progress.load(progress_file)

        since_date_str = progress.since  # Load since date
        print("Loaded since date", since_date_str)


    else:
        print("Creating new Progress instance")
        progress = Progress()

    session = requests.Session()

    while True:
        # Make API call
        payload = {"k": api_key, "since": since_date_str}
        r = session.get(API_URL, params=payload)
        assert r.status_code == 200

        # Read JSON response
        info_dicts = r.json()
        assert type(info_dicts) == list

        if "error" in info_dicts:
            print(info_dicts)
            raise Exception("info_dict error")

        if not info_dicts: break  # Empty JSON, end of map search

        # Add info dict to progress
        progress.json_list.extend(info_dicts)

        for info_dict in info_dicts:
            # General info for logging
            print("{} {} {} - {} [{}]".format(
                  info_dict["approved_date"],
                  info_dict["beatmap_id"],
                  info_dict["artist"],
                  info_dict["title"],
                  info_dict["version"]))


        # Write out progress
        progress.since = since_date_str
        print("Writing progress to", progress_file)
        print("Maps:", len(progress.json_list))
        progress.save(progress_file)


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


    session.close()

    # Final write
    print("Writing final JSON", outfile)
    progress.json_write(outfile)


def scrape_rankings(gamemode=0, country=None, min_page=1, max_page=200):
    '''Scrape rankings pages (one request at a time) for user IDs.
    https://github.com/ppy/osu-api/issues/102
    '''
    RANKINGS_URL = "https://old.ppy.sh/p/pp"
    user_ids = []

    session = requests.Session()

    for page in range(min_page, max_page+1):
        print("Scraping rankings page", page)

        # Prepare payload
        payload = {'m': gamemode, "page": page}
        if country:
            payload['c'] = country

        r = session.get(RANKINGS_URL, params=payload)

        # Parse user_id
        soup = BeautifulSoup(r.text, "html.parser")
        for href_tag in soup.find_all(href=True):
            link = href_tag['href']
            if link.startswith("/u"):
                user_ids.append(int(link.split("/u/")[1]))


    session.close()
    return user_ids


def exception_handler(request, exception):
    print(request, exception)


def download_rankings(api_key,
                      outfile,
                      progress_file,
                      gamemode=0,
                      country=None,
                      top_scores=100,
                      start_rank=0,
                      end_rank=10000):
    '''WIP Download top (100) scores of top (10k) users.
     Due to API rate limit, progress is stored.
     TODO: needs more testing.
     '''
    API_URL = "https://osu.ppy.sh/api/get_user_best"
    BATCH_REQUESTS = 100
    BATCH_INTERVAL = 5   # seconds
    PROGRESS_FREQ  = 10  # How often to save progress

    # Load progress if exists
    if os.path.isfile(progress_file):
        progress = Progress.load(progress_file)
        start_rank = progress.start_rank
        print("Loaded start rank", start_rank)
        print("JSON list length", len(progress.json_list))

    # Start new progress
    else:
        progress = Progress()
        assert 0 <= start_rank < end_rank <= 10000
        RANKS_PER_PAGE = 50
        max_page = math.ceil(end_rank / RANKS_PER_PAGE)
        progress.user_ids = \
            scrape_rankings(gamemode=gamemode, country=country,
                            max_page=max_page)


    progress_counter = 0
    for i in range(start_rank, end_rank, BATCH_REQUESTS):
        # Could move API calling to own function
        progress.start_rank = i  # Save start rank
        rs = []
        user_ids_range = progress.user_ids[i:i+BATCH_REQUESTS]
        print(i, "User IDs", user_ids_range)
        for user_id in user_ids_range:
            payload = {'k': api_key, 'u': user_id, 'm': gamemode,
                       "limit": top_scores}
            rs.append(grequests.get(API_URL, params=payload))

        start_time = time.process_time()

        # Store downloaded JSON
        for r in grequests.map(rs, exception_handler=exception_handler):
            json_response = r.json()
            progress.json_list.extend(json_response)

        # Save progress every PROGRESS_FREQ iters
        if progress_counter % PROGRESS_FREQ == 0:
            progress.save(progress_file)

        progress_counter += 1

        # Don't exceed 1200 requests/min and make peppy angry
        # Dumb throttling
        wait_time = max(0, start_time + BATCH_INTERVAL - time.process_time())
        print("Waiting", round(wait_time, 2), "s")
        time.sleep(wait_time)


    # Final write
    progress.json_write(outfile)


def main():
    parser = argparse.ArgumentParser(description="osu! bulk API downloader")

    # TODO: add since date str
    parser.add_argument("command", help="One of: map-info, rankings")
    parser.add_argument("outfile", help="JSON file to write to")
    parser.add_argument("-p", dest="progress_file",
                        help="File to store downloading progress")
    parser.add_argument("-k", dest="keyfile", default="api.key",
                        help="File to read API key. Defaults to api.key")
    parser.add_argument("-m", dest="gamemode", type=int,
                        help="Game mode " +
                             "(0 = osu!, 1 = Taiko, 2 = CtB, 3 = osu!mania)\n"+
                             "Defaults to all gamemodes")


    args = parser.parse_args()
    print(args)

    API_KEY = open(args.keyfile).read().strip()

    # for now, require progress file
    assert args.progress_file is not None, "progress file required"

    if args.command == "map-info":
        download_map_info(API_KEY,
                          outfile=args.outfile,
                          progress_file=args.progress_file)

    elif args.command == "rankings":
        # treat blank gamemode as 0
        if args.gamemode is not None:
            args.gamemode = 0

        download_rankings(API_KEY,
                          outfile=args.outfile,
                          gamemode=args.gamemode,
                          progress_file=args.progress_file)

    else:
        raise ValueError("Bad command")


if __name__ == "__main__":
    main()