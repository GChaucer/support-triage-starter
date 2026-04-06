from __future__ import annotations

import re

from src.schemas import IssueType, RecommendedTeam


HUMAN_REQUEST_PATTERNS = (
    re.compile(r"\bhuman\b"),
    re.compile(r"\brepresentative\b"),
    re.compile(r"\bagent\b"),
    re.compile(r"\bsomeone from support\b"),
)

THREAT_OR_FRUSTRATION_PATTERNS = (
    re.compile(r"\blawyer\b"),
    re.compile(r"\blegal\b"),
    re.compile(r"\battorney\b"),
    re.compile(r"\bsue\b"),
    re.compile(r"\bfurious\b"),
    re.compile(r"\bfrustrated\b"),
    re.compile(r"\bangry\b"),
)


def detect_language_escalation(message: str) -> tuple[str | None, str | None, RecommendedTeam | None]:
    normalized = message.lower()

    if any(pattern.search(normalized) for pattern in THREAT_OR_FRUSTRATION_PATTERNS):
        return ("Threat / legal / frustration language", "high", RecommendedTeam.GENERAL)
    if any(pattern.search(normalized) for pattern in HUMAN_REQUEST_PATTERNS):
        return ("Human requested", "normal", RecommendedTeam.GENERAL)
    return (None, None, None)


def team_for_issue(issue_type: IssueType) -> RecommendedTeam:
    if issue_type == IssueType.DUPLICATE_CHARGE:
        return RecommendedTeam.BILLING
    if issue_type == IssueType.ORDER_NOT_RECEIVED:
        return RecommendedTeam.FULFILLMENT
    return RecommendedTeam.GENERAL
