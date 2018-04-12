import requests
import csv
import datetime


def scrape_page(set_id):
    """Scrape page and return submitted date.
    https://github.com/ppy/osu-api/issues/195
    old.ppy.sh may be faster but gives less info about dates.
    """
    from bs4 import BeautifulSoup
    import json

    r = requests.get("http://osu.ppy.sh/s/" + str(set_id))
    soup = BeautifulSoup(r.text, "html.parser")
    json_beatmapset = soup.find("script", id="json-beatmapset")
    submitted_date = json.loads(json_beatmapset.string)["submitted_date"]

    return submitted_date


def download_map_info(api_path="api.key", tsv_path="data.tsv",
                      scrape=True, verbose=False, testing=False):
    """Main function to download and write.
    Scraping mode adds what scrape_page returns.
    WARNING: Scraping is probably slow! 
    """

    API_KEY = open(api_path).read()
    tsvfile = open(tsv_path, 'w', encoding="utf-8")
    since_date_str = "2007-10-07"  # Date to start at
    API_MAX_RESULTS = 500


    header_seen = False
    header_keys = None
    mysql_timestamp_format = "%Y-%m-%d %H:%M:%S"
    scrape_headers = ["submitted_date"]

    seen_beatmap_ids = set()
    set_id_dict = dict()  # (set_id: submitted_date) pairs
    tsvwriter = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')


    while True:
        payload = {"k": API_KEY, "since": since_date_str}
        r = requests.get("https://osu.ppy.sh/api/get_beatmaps", params=payload)

        info_dicts = r.json()
        if "error" in info_dicts: print(info_dicts)

        if not info_dicts: break  # Empty JSON, end of map search

        if not header_seen:  # Write header once
            first_map = info_dicts[0]
            # First n cols of table
            # Alternative: Use bool list to indicate whether API or scraped
            header_keys = sorted(first_map.keys())
            full_header = header_keys.copy()
            if scrape: full_header.extend(scrape_headers)

            if verbose: print(full_header)
            tsvwriter.writerow(full_header)
            header_seen = True


        for info_dict in info_dicts:
            # Load info_dict value by header key
            row = [info_dict[key] for key in header_keys]

            # Get set id, prevent duplicates
            if scrape:
                set_id = info_dict["beatmapset_id"]
                if set_id not in set_id_dict:
                    set_id_dict[set_id] = scrape_page(set_id)
                    if verbose: print("Submitted date", set_id_dict[set_id])

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

                if verbose:
                    # Progress info, not actually used in written file
                    print("{} {} {} - {} [{}]".format(
                        info_dict["approved_date"],
                        info_dict["beatmap_id"],
                        info_dict["artist"],
                        info_dict["title"],
                        info_dict["version"]))

            else:
                if verbose: print("Skipped (seen already)")


        # When the API returns 500 results, last mapset may have diffs cut off.
        # Therefore, the whole mapset needs to be read again. The API's "since"
        # parameter appears to be exclusive, so subtract 1 second to include
        # the map again.

        end_date_str = info_dicts[-1]["approved_date"]
        end_date = datetime.datetime.strptime(end_date_str, mysql_timestamp_format)

        if len(info_dicts) == API_MAX_RESULTS:
            end_date -= datetime.timedelta(seconds=1)
        since_date_str = end_date.strftime(mysql_timestamp_format)

        if verbose:
            print('-' * 50)

        if testing: break


    tsvfile.close()

if __name__ == "__main__":
    #print(scrape_page(1))
    download_map_info(verbose=True, testing=True)