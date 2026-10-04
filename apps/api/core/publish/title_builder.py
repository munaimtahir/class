"""Utility for building clean display titles for sessions."""


class SessionDisplayTitleBuilder:
    """Build a human-readable display title for a session.

    Mode A — direct title: if the session already has a non-empty ``title``
    field it is used as-is.

    Mode B — generated title: composed from ``subject`` + ``group``
    (e.g. ``Anatomy-A,B,C``) or ``subject`` + ``session_type``
    (e.g. ``Embryology Lecture``).
    """

    @staticmethod
    def build(session) -> str:
        title = (getattr(session, "title", "") or "").strip()
        if title:
            return title
        return SessionDisplayTitleBuilder.compose(
            subject=getattr(session, "subject", "") or "",
            group=getattr(session, "group", "") or "",
        )

    @staticmethod
    def compose(subject: str, group: str = "", session_type: str = "") -> str:
        """Compose a title from its parts.

        >>> SessionDisplayTitleBuilder.compose("Anatomy", "A,B,C")
        'Anatomy-A,B,C'
        >>> SessionDisplayTitleBuilder.compose("Embryology", session_type="Lecture")
        'Embryology Lecture'
        """
        subject = subject.strip()
        group = group.strip()
        session_type = session_type.strip()

        if subject and group:
            return f"{subject}-{group}"
        if subject and session_type:
            return f"{subject} {session_type}"
        return subject
