import calendar
import sys
from hashlib import shake_128
from typing import Any, Callable, Final, Iterable, ParamSpec, TypeVar

import click
import pandas as pd
from pandas import DataFrame
from simple_term_menu import TerminalMenu

P = ParamSpec("P")
R = TypeVar("R")


def singleton_table_get(df: DataFrame, col: str, default: Any = None) -> Any:
    return df.at[0, col] if col in df.columns and pd.notna(df.at[0, col]) else default


def hash(string: str):
    hasher = shake_128()
    hasher.update(string.encode())
    return hasher.hexdigest(5)


def copy_signature(_: Callable[P, Any]):
    def decorator(target_func: Callable[..., R]) -> Callable[P, R]:
        return target_func

    return decorator


def absorb(lines=1):
    for _ in range(lines):
        click.echo("\033[A\033[2K", nl=False)


def normalize(s: str):
    return s.lower()


def normalize_day(s: str):
    return normalize(s).removesuffix("s")


class PrefixSet(Iterable[str]):
    def __init__(
        self, items: Iterable[str], normalize: Callable[[str], str] = normalize
    ):
        self._items = set(items)
        self._normalize = normalize

    def __iter__(self):
        return iter(self._items)

    def _match(self, prefix: str):
        normalized_prefix = self._normalize(prefix)
        return [
            item
            for item in self._items
            if self._normalize(item).startswith(normalized_prefix)
        ]

    def __getitem__(self, prefix: str):
        matches = self._match(prefix)
        match len(matches):
            case 0:
                raise ValueError(f"The key '{prefix}' is not in the set")
            case 1:
                return matches[0]
            case _:
                raise KeyError(
                    f"The key '{prefix}' is ambiguous. Possible matches: {', '.join(matches)}"
                )

    def __contains__(self, prefix: str):
        return len(self._match(prefix)) >= 1


class PrefixDict[T](Iterable[str]):
    def __init__(self, dict: dict[str, T], normalize: Callable[[str], str] = normalize):
        self._dict = dict
        self._prefix_set = PrefixSet(self._dict.keys(), normalize=normalize)

    def __iter__(self):
        return iter(self._dict)

    def __getitem__(self, prefix: str):
        return self._dict[self._prefix_set[prefix]]

    def __contains__(self, prefix: str):
        return prefix in self._prefix_set


GTFS_TO_ICAL_DAY: Final = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}


DAY_PREFIX_STRICT_SET = PrefixSet(
    (day for day in GTFS_TO_ICAL_DAY.keys()),
    normalize=normalize_day,
)
SPECIAL_DAY_TOKENS = {
    "weekday": GTFS_TO_ICAL_DAY.keys() - {"saturday", "sunday"},
    "weekend": {"saturday", "sunday"},
}
DAY_PREFIX_DICT = PrefixDict(
    {day: {day} for day in DAY_PREFIX_STRICT_SET} | SPECIAL_DAY_TOKENS,
    normalize=normalize_day,
)
DAY_INDEX = {normalize(name): index for index, name in enumerate(calendar.day_name)}


def find_flag_index(flags: Iterable[str]) -> int | None:
    return next((index for index, arg in enumerate(sys.argv) if arg in flags), None)


def format_table(df: DataFrame):
    return df.apply(
        lambda col: (
            col.str.ljust(int(col.str.len().max())) if col.str.len().max() >= 0 else col
        )
    ).apply(
        lambda row: " · ".join(str(val) for val in row if val and pd.notna(val)),
        axis=1,
    )


def data_menu(df: DataFrame, cursor: str, cursor_color: str, category: str):
    return TerminalMenu(
        format_table(df),
        menu_cursor=cursor + "› ",
        menu_cursor_style=("fg_" + cursor_color,),
        status_bar=(f"Selecting {category}. Hit </> to search."),
        status_bar_style=("fg_gray",),
    )
