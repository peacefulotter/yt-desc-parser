from enum import Enum

import re
import argparse
import pandas as pd
from tqdm import tqdm
from pathlib import Path
from pytube import YouTube
from datetime import datetime
from urlextract import URLExtract

from googleapiclient.discovery import build

DEVELOPER_KEY = "AIzaSyBqyzdb7oagxtoIQz08FimfidlbIi9awn0"
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


class LinkType(Enum):
    EMAIL = "email"
    INSTA = "insta"
    OTHER = "other"


def get_url_type(url: str):
    return LinkType.INSTA.value if "instagram" in url else LinkType.OTHER.value


def get_urls(s: str):
    urls = extractor.find_urls(s)
    return [(url, get_url_type(url)) for url in urls if url.startswith("http")]


@with_youtube
def youtube_search(q, max_results=5, yt=None):

    res = yt.search().list(q=q, part="id,snippet", maxResults=max_results).execute()

    videos = pd.DataFrame(columns=["title", "published", "id"])
    links = pd.DataFrame(columns=["title", "id", "link", "type", "valid"])

    for search_result in tqdm(res.get("items", [])):
        snippet = search_result["snippet"]
        title = snippet["title"]
        published = snippet["publishedAt"]
        kind = search_result["id"]["kind"].split("#")[-1]
        id = search_result["id"][
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

    return videos, links


def main(config):
    query = config.q
    videos, links = youtube_search(query)

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
    print("\n".join(table["link"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", help="Search term", default="ninho type beat")
    parser.add_argument(
        "--type",
        help="email | insta | other | all",
        default="email",
        choices=["email", "insta", "other", "all"],
    )
    parser.add_argument("--max", help="Max results", default=25)
    args = parser.parse_args()
    main(args)
