"""Nonsecret synthetic Provider source with closed defaults and wrappers."""

import time
from enum import StrEnum
from functools import lru_cache
from typing import TypeVar

from . import helper
from .helper import transform as source_alias

DEFAULT = "synthetic"
T = TypeVar("T")


class Flavor(StrEnum):
    TEXT = "text"


class Provider:
    provider_name = "fixture"
    capabilities = frozenset({Flavor.TEXT})

    def __init__(self, *, clock=time.monotonic, capabilities=frozenset({Flavor.TEXT})):
        self.clock = clock
        self.selected = frozenset(capabilities)

    @staticmethod
    def request(value=DEFAULT):
        return source_alias(value)


@lru_cache(maxsize=4, typed=False)
def cached(value=DEFAULT):
    return helper.transform(value)


def typed(value: T) -> T:
    return value


def lazy():
    from .lazy_helper import render
    return render()
