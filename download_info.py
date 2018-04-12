import requests
import csv
import datetime
import os.path
import pickle


def scrape_pages(set_ids):
    """Scrape pages given by set_ids and return submitted dates.
    Makes requests asynchronously with grequests.
    https://github.com/ppy/osu-api/issues/195
    old.ppy.sh may be faster but gives less info about dates.
    """
    import grequests
    from bs4 import BeautifulSoup
    import json

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


def download_map_info(api_path="api.key", tsv_path="data.tsv",
                      seen_path="seen.pkl", scrape=True, _testing=False,
                      resume=False):
    """Main function to download and write data table from API (and scraping).
    Scraping mode adds what scrape_pages returns.
    If resume flag, tries to restart based on seen file (pickle)
    WARNING: Scraping is probably slow!
    Also resume functionality is EXPERIMENTAL.
    """

    API_KEY = open(api_path).read()
    tsvfile = open(tsv_path, 'a', encoding="utf-8")
    since_date_str = "2007-10-07"  # Date to start at
    API_MAX_RESULTS = 500


    header_seen = False
    header_keys = None
    mysql_timestamp_format = "%Y-%m-%d %H:%M:%S"
    scrape_headers = ["submitted_date"]


    seen_beatmap_ids = set()
    set_id_dict = dict()  # (set_id: submitted_date) pairs

    # Load or init seen structures
    if os.path.isfile(seen_path):
        print("Loading seen files", seen_path)
        with open(seen_path, 'rb') as f:
            header_seen, header_keys, seen_beatmap_ids, set_id_dict = pickle.load(f)


    tsvwriter = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')

    # Requests session
    session = requests.Session()

    while True:
        payload = {"k": API_KEY, "since": since_date_str}
        r = session.get("https://osu.ppy.sh/api/get_beatmaps", params=payload)

        info_dicts = r.json()
        if "error" in info_dicts:
            print(info_dicts)
            raise Exception("info_dict error")

        if not info_dicts: break  # Empty JSON, end of map search

        if not header_seen:  # Write header once
            first_map = info_dicts[0]
            # First n cols of table
            # Alternative: Use bool list to indicate whether API or scraped
            header_keys = sorted(first_map.keys())
            full_header = header_keys.copy()
            if scrape: full_header.extend(scrape_headers)

            print("Full header", full_header)
            tsvwriter.writerow(full_header)
            header_seen = True

        if scrape:
            # Gather set_ids in info_dicts to batch request
            set_ids_to_request = set()
            for info_dict in info_dicts:
                set_id = info_dict["beatmapset_id"]
                if set_id not in set_id_dict:
                    set_ids_to_request.add(set_id)

            set_ids_to_request = list(set_ids_to_request)  # Fix order
            submitted_dates = scrape_pages(set_ids_to_request)

            # Add responses to set_id_dict
            for (set_id, submitted_date) in zip(set_ids_to_request, submitted_dates):
                set_id_dict[set_id] = submitted_date



        for info_dict in info_dicts:
            # Load info_dict value by header key
            row = [info_dict[key] for key in header_keys]

            # Read from set_id_dict
            if scrape:
                set_id = info_dict["beatmapset_id"]
                # Append submitted_date
                row.append(set_id_dict[set_id])


            # Clean strings
            # https://osu.ppy.sh/b/1468670?m=0 has a TAB in the tags
            # https://osu.ppy.sh/b/707380 has a newline in the tags
            for i in range(len(row)):
                if type(row[i]) == str and ('\t' in row[i] or '\n' in row[i]):
                    print("Bad whitespace detected!")
                    row[i] = row[i].replace('\t', ' ').replace('\n', ' ')


            # Write row, prevent duplicate rows being written
            beatmap_id = info_dict["beatmap_id"]
            if beatmap_id not in seen_beatmap_ids:
                tsvwriter.writerow(row)
                seen_beatmap_ids.add(beatmap_id)

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
        with open(seen_path, 'wb') as f:
            pickle.dump((header_seen, header_keys, seen_beatmap_ids, set_id_dict), f)
        print("Wrote id pickle files")


        # When the API returns 500 results, last mapset may have diffs cut off.
        # Therefore, the whole mapset needs to be read again. The API's "since"
        # parameter appears to be exclusive, so subtract 1 second to include
        # the map again.

        end_date_str = info_dicts[-1]["approved_date"]
        end_date = datetime.datetime.strptime(end_date_str, mysql_timestamp_format)

        if len(info_dicts) == API_MAX_RESULTS:
            end_date -= datetime.timedelta(seconds=1)
        since_date_str = end_date.strftime(mysql_timestamp_format)

        print('-' * 50)

        if _testing: break


    tsvfile.close()

if __name__ == "__main__":
    download_map_info(scrape=True, _testing=False, resume=True)