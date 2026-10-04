"""Google Sheets API client wrapper for read-only timetable access."""

from django.conf import settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from core.google_client import normalize_user_scopes
from core.google_scopes import (
    GoogleScopeMissingError,
    SCOPE_SPREADSHEETS_READONLY,
    validate_scopes,
)


class SheetAccessError(Exception):
    """Base class for sheet access failures."""


class SheetPermissionError(SheetAccessError):
    """User does not have permission to access the spreadsheet."""


class SheetNotFoundError(SheetAccessError):
    """Spreadsheet or tab does not exist."""


class MissingSheetsScope(SheetAccessError):
    """User has not granted the Sheets read scope."""


class SheetsClient:
    """Thin wrapper around the Google Sheets v4 API."""

    def __init__(self, user):
        self.user = user
        self._verify_scope()

    def _verify_scope(self):
        result = validate_scopes(normalize_user_scopes(self.user), [SCOPE_SPREADSHEETS_READONLY])
        if not result.ok:
            raise GoogleScopeMissingError(
                feature="import_google_sheet_preview",
                missing_scopes=result.missing,
            )

    def _credentials(self) -> Credentials:
        return Credentials(
            token=self.user.access_token,
            refresh_token=self.user.get_refresh_token(),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=normalize_user_scopes(self.user),
        )

    def _service(self):
        return build("sheets", "v4", credentials=self._credentials(), cache_discovery=False)

    def get_spreadsheet_metadata(self, spreadsheet_id: str) -> dict:
        """Return spreadsheet title and list of sheet tabs."""
        try:
            return (
                self._service()
                .spreadsheets()
                .get(
                    spreadsheetId=spreadsheet_id,
                    fields="spreadsheetId,properties.title,sheets(properties(sheetId,title,index))",
                )
                .execute()
            )
        except HttpError as exc:
            if exc.resp.status == 403:
                raise SheetPermissionError(
                    "Cannot access this spreadsheet. "
                    "Make sure it is shared with your Google Workspace account."
                ) from exc
            if exc.resp.status == 404:
                raise SheetNotFoundError(
                    "Spreadsheet not found. Check the URL and sharing settings."
                ) from exc
            raise SheetAccessError(f"Google Sheets API error: {exc}") from exc

    def get_sheet_values(self, spreadsheet_id: str, sheet_name: str) -> list[list[str]]:
        """Return all cell values from a single sheet tab as a 2-D list of strings."""
        try:
            result = (
                self._service()
                .spreadsheets()
                .values()
                .get(
                    spreadsheetId=spreadsheet_id,
                    range=sheet_name,
                    valueRenderOption="FORMATTED_VALUE",
                    dateTimeRenderOption="FORMATTED_STRING",
                )
                .execute()
            )
            return result.get("values", [])
        except HttpError as exc:
            if exc.resp.status == 403:
                raise SheetPermissionError(
                    "Cannot read sheet data. Check sharing permissions."
                ) from exc
            raise SheetAccessError(f"Google Sheets API error: {exc}") from exc

    def resolve_sheet_name(
        self,
        metadata: dict,
        gid: str | None = None,
        sheet_name: str | None = None,
    ) -> str:
        """
        Determine which tab to read.
        Priority: explicit sheet_name > gid from URL > first sheet.
        """
        sheets = [s["properties"] for s in metadata.get("sheets", [])]
        if not sheets:
            raise SheetNotFoundError("Spreadsheet has no sheets.")

        if sheet_name:
            for s in sheets:
                if s["title"].strip().lower() == sheet_name.strip().lower():
                    return s["title"]
            available = [s["title"] for s in sheets]
            raise SheetNotFoundError(
                f"Sheet tab '{sheet_name}' not found. Available tabs: {available}"
            )

        if gid:
            for s in sheets:
                if str(s["sheetId"]) == str(gid):
                    return s["title"]
            # gid not matched — fall through to first sheet

        return sheets[0]["title"]

    def list_sheets(self, metadata: dict) -> list[dict]:
        """Return [{title, gid}, ...] for all tabs in the spreadsheet."""
        return [
            {"title": s["properties"]["title"], "gid": s["properties"]["sheetId"]}
            for s in metadata.get("sheets", [])
        ]
