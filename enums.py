from enum import Enum


class LinkType(Enum):
    EMAIL = "email"
    INSTA = "insta"
    OTHER = "other"


class PublishedOptions(Enum):
    LAST_MONTH = "last_month"
    LAST_WEEK = "last_week"
    LAST_DAY = "last_day"
    CUSTOM = "custom"


class PublishedCustomOptions(Enum):
    WEEKS = "weeks"
    DAYS = "days"
    HOURS = "hours"
