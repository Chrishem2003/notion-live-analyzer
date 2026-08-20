"""
classification.py — Real access-control levels for Drive (and, later, Docs/
Chat/Meet content). This is the actual "classified system" building block.

Four levels, lowest to highest sensitivity. A user's clearance is just a
string from this same list — compare positions, nothing fancier, nothing
fake. `clearance_for_user()` gives a sane default mapping from your
existing auth (is_admin()) to a clearance level; swap it out once you have
a real per-user role column, this is intentionally a single, obvious
function to replace.
"""

from dataclasses import dataclass

LEVELS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]


def _level_index(level: str) -> int:
    try:
        return LEVELS.index(level.upper())
    except ValueError:
        raise ValueError(f"Unknown classification level {level!r}. Must be one of {LEVELS}.")


def can_access(user_clearance: str, file_classification: str) -> bool:
    """True if a user with `user_clearance` may view a file classified at
    `file_classification`. Higher clearance sees everything at or below it."""
    return _level_index(user_clearance) >= _level_index(file_classification)


def can_delete(user_clearance: str, file_classification: str, is_owner: bool) -> bool:
    """Owners can always delete their own files. Non-owners need RESTRICTED
    clearance (the top tier) regardless of the file's own level — deletion
    is a more sensitive action than viewing."""
    if is_owner:
        return True
    return user_clearance.upper() == "RESTRICTED"


def clearance_for_user(is_admin: bool) -> str:
    """
    Default mapping until you wire in a real per-user role column:
    admins get RESTRICTED (see everything), everyone else gets INTERNAL
    (sees PUBLIC and INTERNAL files, not CONFIDENTIAL/RESTRICTED).

    This is a real, if coarse, policy — not a placeholder that always
    grants access. Replace this one function when you add real roles;
    everything else in this module stays the same.
    """
    return "RESTRICTED" if is_admin else "INTERNAL"


@dataclass
class ClassificationCheck:
    allowed: bool
    reason: str


def check_access(user_clearance: str, file_classification: str, is_owner: bool = False) -> ClassificationCheck:
    """Verbose version for UI code that wants to explain a denial rather
    than just branch on a bool."""
    if is_owner or can_access(user_clearance, file_classification):
        return ClassificationCheck(True, "authorized")
    return ClassificationCheck(
        False,
        f"Requires {file_classification} clearance or higher (you have {user_clearance}).",
    )