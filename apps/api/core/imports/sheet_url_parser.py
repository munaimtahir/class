"""Parse a Google Sheets URL and extract the spreadsheet ID and optional gid."""

import re
from dataclasses import dataclass, field
from typing import Optional


class SheetUrlParseError(ValueError):
    pass


@dataclass
class ParsedSheetUrl:
    spreadsheet_id: str
    gid: Optional[str] = None
    original_url: str = ""


def parse_sheet_url(url: str) -> ParsedSheetUrl:
    """
    Extract spreadsheet ID and optional gid from a Google Sheets URL.

    Supports formats:
    - https://docs.google.com/spreadsheets/d/{id}/edit
    - https://docs.google.com/spreadsheets/d/{id}/edit#gid={gid}
    - https://docs.google.com/spreadsheets/d/{id}/pub?gid={gid}
    - https://docs.google.com/spreadsheets/d/{id}  (bare)
    """
    url = (url or "").strip()
    if not url:
        raise SheetUrlParseError("Sheet URL is required.")

    if "docs.google.com" not in url and "spreadsheets" not in url:
        raise SheetUrlParseError(
            "Invalid Google Sheet URL. Expected a link from docs.google.com/spreadsheets/."
        )

    id_match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not id_match:
        raise SheetUrlParseError(
            "Could not extract spreadsheet ID from the URL. "
            "Expected format: https://docs.google.com/spreadsheets/d/{ID}/..."
        )

    spreadsheet_id = id_match.group(1)

    # gid can appear as #gid= or &gid= or ?gid=
    gid_match = re.search(r"[#&?]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else None

    return ParsedSheetUrl(
        spreadsheet_id=spreadsheet_id,
        gid=gid,
        original_url=url,
    )
