import requests
import csv
import datetime


def scrape_page(set_id):
    """Scrape page and return submitted date.
    https://github.com/ppy/osu-api/issues/195
    TODO: Is there a faster site?
    """
    from bs4 import BeautifulSoup
    import json

    r = requests.get("http://osu.ppy.sh/s/" + str(set_id))
    soup = BeautifulSoup(r.text, "html.parser")
    json_beatmapset = soup.find("script", id="json-beatmapset")
    submitted_date = json.loads(json_beatmapset.string)["submitted_date"]

    return submitted_date


def download_map_info(api_path="api.key", tsv_path="data.tsv",
                      scrape=True):
    """Main function to download and write."""

    API_KEY = open(api_path).read()
    tsvfile = open(tsv_path, 'w', encoding="utf-8")
    since_date_str = "2007-10-07"  # Date to start at
    API_MAX_RESULTS = 500


    header_seen = False
    header_keys = None
    mysql_timestamp_format = "%Y-%m-%d %H:%M:%S"

    seen_beatmap_ids = set()
    tsvwriter = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')


    while True:
        payload = {"k": API_KEY, "since": since_date_str}
        r = requests.get("https://osu.ppy.sh/api/get_beatmaps", params=payload)

        info_dicts = r.json()
        if "error" in info_dicts: print(info_dicts)

        if not info_dicts: break  # Empty JSON, end of map search

        if not header_seen:  # Write header once
            first_map = info_dicts[0]
            header_keys = sorted(first_map.keys())
            print(header_keys)
            tsvwriter.writerow(header_keys)
            header_seen = True


        for info_dict in info_dicts:
            row = [info_dict[key] for key in header_keys]

            # Prevent duplicate rows being written
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

            else: print("Skipped")


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

        #break  # for testing loop


    tsvfile.close()

if __name__ == "__main__":
    download_map_info()