import requests
import csv
import datetime

def download_map_info():
    API_KEY = open("api.key").read()
    tsvfile = open("data.tsv", 'w', encoding="utf-8")
    since_date_str = "2007-10-07"  # Date to start at
    API_MAX_RESULTS = 500


    header_seen = False
    header_keys = None
    mysql_timestamp_format = "%Y-%m-%d %H:%M:%S"
    seen_rows = set()
    tsvwriter = csv.writer(tsvfile, delimiter='\t', lineterminator='\n')


    while True:
        payload = {"k": API_KEY, "since": since_date_str}
        r = requests.get("https://osu.ppy.sh/api/get_beatmaps", params=payload)

        info_dicts = r.json()
        if not info_dicts: break  # Empty JSON, end of map search

        if not header_seen:  # Write header once
            first_map = info_dicts[0]
            header_keys = sorted(first_map.keys())
            print(header_keys)
            tsvwriter.writerow(header_keys)
            header_seen = True


        for info_dict in info_dicts:
            row = tuple(info_dict[key] for key in header_keys)
            if row not in seen_rows:  # Prevent duplicate rows being written
                tsvwriter.writerow(row)
                seen_rows.add(row)

            # Progress info, not actually used in written file
            print("{} {} {} - {} [{}]".format(
                info_dict["approved_date"],
                info_dict["beatmap_id"],
                info_dict["artist"],
                info_dict["title"],
                info_dict["version"]))


        # When the API returns 500 results, so last mapset may have diffs cut off.
        # Therefore, the whole mapset needs to be read again. The API's "since"
        # parameter appears to be exclusive, so subtract 1 second to include
        # the map again.

        end_date_str = info_dicts[-1]["approved_date"]
        end_date = datetime.datetime.strptime(end_date_str, mysql_timestamp_format)

        if len(info_dicts) == API_MAX_RESULTS:
            end_date -= datetime.timedelta(seconds=1)
        since_date_str = end_date.strftime(mysql_timestamp_format)

        print('-' * 40)


    tsvfile.close()


download_map_info()