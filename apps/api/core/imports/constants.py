# Column keyword sets for auto-detecting sheet structure.
# Matching is case-insensitive; a cell is matched if any keyword appears in the normalised
# header value or vice-versa.

DAY_KEYWORDS = {"day", "weekday", "week_day"}
DATE_KEYWORDS = {"date", "datum", "session_date"}
START_TIME_KEYWORDS = {"start", "start_time", "from", "begin", "begins", "time_from"}
END_TIME_KEYWORDS = {"end", "end_time", "to", "until", "finish", "time_to"}
COMBINED_TIME_KEYWORDS = {"time", "period", "slot", "timing", "hours", "schedule"}
SUBJECT_KEYWORDS = {"subject", "course", "paper", "module", "dept", "department"}
TITLE_KEYWORDS = {"title", "lecture", "session", "lec", "topic_title", "class", "name"}
TOPIC_KEYWORDS = {"topic", "subtopic", "content", "chapter", "description"}
GROUP_KEYWORDS = {"group", "batch", "section", "subgroup", "class_group"}
FACULTY_KEYWORDS = {"faculty", "teacher", "lecturer", "instructor", "prof", "dr"}
ROOM_KEYWORDS = {"room", "venue", "hall", "lab", "theatre"}
NOTES_KEYWORDS = {"notes", "remarks", "comment", "comments"}

WEEKDAY_NAMES: dict[str, int] = {
    "monday": 0,
    "mon": 0,
    "tuesday": 1,
    "tue": 1,
    "tues": 1,
    "wednesday": 2,
    "wed": 2,
    "thursday": 3,
    "thu": 3,
    "thur": 3,
    "thurs": 3,
    "friday": 4,
    "fri": 4,
    "saturday": 5,
    "sat": 5,
    "sunday": 6,
    "sun": 6,
}

# Defaults applied to every imported session unless the sheet provides explicit values.
DEFAULT_REQUIRES_MEET: bool = True
DEFAULT_PUBLISH_MODE: str = "scheduled"
# Minutes offset from session start time for the default scheduled_for value.
# Negative means before the session starts.
DEFAULT_SCHEDULED_FOR_OFFSET_MINUTES: int = -10
