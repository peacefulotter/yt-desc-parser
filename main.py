import re
import argparse
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from pytube import YouTube
from datetime import datetime
from urlextract import URLExtract
from datetime import datetime, timedelta

from googleapiclient.discovery import build

from enums import LinkType, PublishedOptions, PublishedCustomOptions


with open("api_key.txt") as f:
    DEVELOPER_KEY = f.read().strip()
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

YT_ROOT_URL = "https://www.youtube.com/watch?v="


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


def get_urls(s: str):
    urls = extractor.find_urls(s)
    return [(url, get_url_type(url)) for url in urls if url.startswith("http")]


def handle_search_result(videos, links, item):
    snippet = item["snippet"]
    title = snippet["title"]
    published = snippet["publishedAt"]
    kind = item["id"]["kind"].split("#")[-1]
    id = item["id"][
        {"video": "videoId", "channel": "channelId", "playlist": "playlistId"}[kind]
    ]

    if kind == "video":
        videos.loc[len(videos)] = [title, published, id]

        desc = get_description(id)
        emails = get_emails(desc)
        urls = get_urls(desc)

        for email, valid in emails:
            links.loc[len(links)] = [title, id, email, LinkType.EMAIL.value, valid]

        for url, link_type in urls:
            links.loc[len(links)] = [title, id, url, link_type, True]

    elif kind == "channel":
        pass

    elif kind == "playlist":
        pass


@with_youtube
def youtube_search(q, max_results, published_after, yt=None):

    search_max_results = min(max_results, 50)
    request = yt.search().list(
        q=q,
        part="id,snippet",
        type="video",
        maxResults=search_max_results,
        publishedAfter=published_after,
    )

    videos = pd.DataFrame(columns=["title", "published", "id"])
    links = pd.DataFrame(columns=["title", "id", "link", "type", "valid"])

    remaining = max_results
    while remaining > 0:
        res = request.execute()
        for item in tqdm(res.get("items", [])):
            handle_search_result(videos, links, item)
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

    return (datetime.now() - timedelta(days=days, hours=hours, weeks=weeks)).isoformat()


def main(config):
    query = config.q
    max_results = config.max
    published_after = get_published_time(config)
    videos, links = youtube_search(query, max_results, published_after)

    out_dir = Path(".") / "out"
    out_dir.mkdir(exist_ok=True)

    now = datetime.now()
    now = now.strftime("%d-%m-%Y_%H-%M-%S")
    folder = out_dir / f'{now}_{"-".join(query.split(" "))}'
    folder.mkdir()

    videos.to_csv(folder / "videos.csv")
    links.to_csv(folder / "links.csv")

    l = links.drop(["title"], axis=1)
    if config.type and config.type != "all":
        l = l.loc[links.type == config.type]
    table = pd.merge(videos, l, on="id")

    print(table)
    print("\n".join(list(set(table["link"]))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", help="Search term", default="ninho type beat")
    parser.add_argument(
        "--type",
        help="email | insta | other | all",
        default="email",
        choices=["email", "insta", "other", "all"],
    )
    parser.add_argument("--max", help="Max results", default=25, type=int)
    parser.add_argument(
        "--month",
        help="Look for videos of at most a month old",
        default=False,
        type=bool,
    )
    parser.add_argument(
        "--week", help="Look for videos of at most a week old", default=False, type=bool
    )
    parser.add_argument(
        "--day", help="Look for videos of at most a day old", default=False, type=bool
    )
    parser.add_argument(
        "--weeks", help="Look for videos of at most # weeks old", default=1, type=int
    )
    parser.add_argument(
        "--days", help="Look for videos of at most # days old", default=0, type=int
    )
    parser.add_argument(
        "--hours", help="Look for videos of at most # days old", default=0, type=int
    )
    args = parser.parse_args()
    main(args)
