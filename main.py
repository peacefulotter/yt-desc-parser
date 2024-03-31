import re
import argparse
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from pytube import YouTube
from datetime import datetime
from urlextract import URLExtract
from datetime import datetime, timedelta, timezone

from googleapiclient.discovery import build

from utils import Record
from enums import LinkType, PublishedOptions


YT_ROOT_URL = "https://www.youtube.com/watch?v="

API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

with open("api_key.txt") as f:
    DEVELOPER_KEY = f.read().strip()


def with_youtube(func):
    def wrapper(*args, **kwargs):
        with build(API_SERVICE_NAME, API_VERSION, developerKey=DEVELOPER_KEY) as yt:
            return func(*args, **kwargs, yt=yt)

    return wrapper


def bypass_age_gate(self):
    """
    https://github.com/pytube/pytube/issues/1712
    """

    from pytube.innertube import InnerTube
    import pytube.exceptions as exceptions

    """Attempt to update the vid_info by bypassing the age gate."""
    innertube = InnerTube(
        client="ANDROID_CREATOR",
        use_oauth=self.use_oauth,
        allow_cache=self.allow_oauth_cache,
    )
    innertube_response = innertube.player(self.video_id)

    playability_status = innertube_response["playabilityStatus"].get("status", None)

    # If we still can't access the video, raise an exception
    # (tier 3 age restriction)
    if playability_status == "UNPLAYABLE":
        raise exceptions.AgeRestrictedError(self.video_id)

    self._vid_info = innertube_response


def get_description(id):
    video = YouTube(f"{YT_ROOT_URL}{id}")
    bypass_age_gate(video)
    return video.description


"""
https://stackoverflow.com/questions/17681670/extract-email-sub-strings-from-large-document
"""

valid_email_regex = re.compile(
    r"(?i)"  # Case-insensitive matching
    r"(?:[A-Z0-9!#$%&'*+/=?^_`{|}~-]+"  # Unquoted local part
    r"(?:\.[A-Z0-9!#$%&'*+/=?^_`{|}~-]+)*"  # Dot-separated atoms in local part
    r"|\"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]"  # Quoted strings
    r"|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*\")"  # Escaped characters in local part
    r"@"  # Separator
    r"[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?"  # Domain name
    r"\.(?:[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+"  # Top-level domain and subdomains
)


def isValid(email):
    """Check if the given email address is valid."""
    return True if re.fullmatch(valid_email_regex, email) else False


def get_emails(s: str):
    emails = re.findall(r"[\w.+-]+@[\w-]+\.[\w.-]+", s)
    return [(email, isValid(email)) for email in emails]


"""
https://stackoverflow.com/questions/9760588/how-do-you-extract-a-url-from-a-string-using-python
"""
extractor = URLExtract()


def get_url_type(url: str):
    return LinkType.INSTA.value if "instagram" in url else LinkType.OTHER.value


def get_urls(s: str, url_types):
    urls = extractor.find_urls(s)
    res = []
    for url in urls:
        if "http" not in url:
            continue
        url_type = get_url_type(url)
        if url_type in url_types:
            res.append((url, url_type))
    return res


def handle_search_result(videos, links, item, config):
    snippet = item["snippet"]

    channel = snippet["channelTitle"]
    title = snippet["title"]
    published = snippet["publishedAt"]
    kind = item["id"]["kind"].split("#")[-1]
    id = item["id"][
        {"video": "videoId", "channel": "channelId", "playlist": "playlistId"}[kind]
    ]

    if kind == "video":
        videos.loc[len(videos)] = [channel, title, published, id]

        desc = snippet["description"]
        try:
            desc = get_description(id)
        except Exception as e:
            print(f"Error: {e}")

        if "all" in config.type or "email" in config.type:
            emails = get_emails(desc)
            for email, valid in emails:
                links.loc[len(links)] = [
                    id,
                    email,
                    LinkType.EMAIL.value,
                    valid,
                ]

        if "all" in config.type or "insta" in config.type or "other" in config.type:
            urls = get_urls(desc, config.type)
            for url, link_type in urls:
                links.loc[len(links)] = [id, url, link_type, True]

    elif kind == "channel":
        pass

    elif kind == "playlist":
        pass


@with_youtube
def youtube_search(q, max_results, published_after, config, yt=None):

    query = q + " type beat"
    print(
        f"Searching for {query}, published after = {published_after}, # result = {max_results} ..."
    )

    search_max_results = min(max_results, 50)
    request = yt.search().list(
        q=query,
        part="id,snippet",
        type="video",
        maxResults=search_max_results,
        publishedAfter=published_after,
    )

    videos = pd.DataFrame(columns=["channel", "title", "published", "id"])
    links = pd.DataFrame(columns=["id", "link", "type", "valid"])

    remaining = max_results
    while remaining > 0:
        res = request.execute()
        for item in tqdm(res.get("items", [])):
            handle_search_result(videos, links, item, config)
        remaining -= search_max_results

    return videos, links


def get_published_time(config):
    mode = config.published_mode
    weeks, days, hours = 0, 0, 0

    match mode:
        case PublishedOptions.LAST_MONTH.value:
            weeks, days, hours = 4, 0, 0
        case PublishedOptions.LAST_WEEK.value:
            weeks, days, hours = 1, 0, 0
        case PublishedOptions.LAST_DAY.value:
            weeks, days, hours = 0, 1, 0
        case PublishedOptions.CUSTOM.value:
            weeks, days, hours = config.published_custom

    print(weeks, days, hours)

    return (
        datetime.now(timezone.utc) - timedelta(days=days, hours=hours, weeks=weeks)
    ).isoformat()[:-6] + "Z"


def main(config, cb=None):
    queries = config.queries
    max_results = config.max
    published_after = get_published_time(config)

    out_dir = Path(".") / "out"
    out_dir.mkdir(exist_ok=True)

    now = datetime.now()
    now = now.strftime("%d-%m-%Y_%H-%M-%S")

    for query in queries:
        videos, links = youtube_search(query, max_results, published_after, config)

        folder = out_dir / f'{now}_{"-".join(query.split(" "))}'
        folder.mkdir()

        videos.to_csv(folder / "videos.csv")
        links.to_csv(folder / "links.csv")

        table = pd.merge(videos, links, on="id")

        print(table)
        print("\n".join(list(set(table["link"]))))

        if cb:
            cb(table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--queries", help="Search artists separated by ,", default="ninho,booba"
    )
    parser.add_argument(
        "--type",
        default="email",
        choices=["email", "insta", "other", "all"],
    )
    parser.add_argument("--max", help="Max results", default=25, type=int)
    parser.add_argument(
        "--filter",
        help="Filter by published date",
        default=PublishedOptions.LAST_MONTH.value,
        choices=[e.value for e in PublishedOptions],
    )
    parser.add_argument(
        "--custom",
        help="Custom published date",
        default="0,0,0",
        type=lambda x: [int(i) for i in x.split(",")],
        choices=["weeks", "days", "hours"],
    )
    args = parser.parse_args()

    config = Record(
        queries=args.queries.split(","),
        type=set([t for t in args.type.split(",")]),
        max=args.max,
        published_mode=args.filter,
        published_custom=args.custom,
    )

    print(config)
    main(config)
