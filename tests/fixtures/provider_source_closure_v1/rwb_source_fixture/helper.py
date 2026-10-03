"""Pure imported helper used to expose alias-only drift."""

PREFIX = "fixture:"


def transform(value="synthetic"):
    return PREFIX + value
