"""Disposition enum (no ``pass``)."""

from __future__ import annotations

from enum import Enum


class Disposition(str, Enum):
    STANDARD_REVIEW = "standard_review"
    ESCALATE = "escalate"
    AUTO_CONTAIN = "auto_contain"
