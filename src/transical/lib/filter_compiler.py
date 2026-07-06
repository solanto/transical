import calendar
from typing import Callable

from more_itertools import collapse
from pyparsing import (
    CaselessKeyword,
    Group,
    Word,
    alphanums,
    alphas,
    infixNotation,
    opAssoc,
    quoted_string,
)

from transical.lib.utils import (
    DAY_INDEX,
    DAY_PREFIX_DICT,
    DAY_PREFIX_STRICT_SET,
    PrefixSet,
    normalize,
)

FIELD_PREFIXES = PrefixSet(["day", "time"])


def validate_field(tokens):
    try:
        return FIELD_PREFIXES[tokens[0]]
    except (ValueError, KeyError):
        raise ValueError(f"Unknown field: {tokens[0]}")


AND = CaselessKeyword("AND")
OR = CaselessKeyword("OR")
NOT = CaselessKeyword("NOT")
IS = CaselessKeyword("IS")

field_ident = Word(alphas).setParseAction(validate_field)
unquoted_word = ~(AND | OR | NOT | IS) + Word(alphanums + ":,/")

parser = infixNotation(
    Group(field_ident + (Group(IS + NOT) | IS) + (unquoted_word | quoted_string)),
    [(NOT, 1, opAssoc.RIGHT), (AND, 2, opAssoc.LEFT), (OR, 2, opAssoc.LEFT)],
)

type Expression = str | list[Expression]


def day_range(start_day: str, end_day: str) -> set[str]:
    start_idx = DAY_INDEX[start_day]
    end_idx = DAY_INDEX[end_day]
    all_days = [normalize(day) for day in calendar.day_name]
    return (
        set(all_days[start_idx : end_idx + 1])
        if start_idx <= end_idx
        else set(all_days[start_idx:] + all_days[: end_idx + 1])
    )


def day_condition(complement: str, negate: bool) -> str:
    match complement.split("/"):
        case [start, end] if (
            start in DAY_PREFIX_STRICT_SET and end in DAY_PREFIX_STRICT_SET
        ):
            days = day_range(
                next(iter(DAY_PREFIX_DICT[start])), next(iter(DAY_PREFIX_DICT[end]))
            )
        case [single]:
            days = DAY_PREFIX_DICT[single]
        case _:
            raise ValueError(f"Invalid day complement '{complement}'")
    return f"day {'not in' if negate else 'in'} {days}"


def time_condition(complement: str, negate: bool) -> str:
    match complement.split("/"):
        case [start, end]:
            return (
                f"(time > {s(end)}) or (time < {s(start)})"
                if negate
                else f"{s(start)} <= time <= {s(end)}"
            )
        case [single]:
            return f"time {'!=' if negate else '=='} {s(single)}"
        case _:
            raise ValueError(f"Invalid time complement '{complement}'")


def field_condition(field: str, complement: str, negate: bool = False) -> str:
    match field:
        case "day":
            return day_condition(complement, negate)
        case "time":
            return time_condition(complement, negate)
        case _:
            raise ValueError(f"Unsupported field '{field}'")


def e(expr: Expression) -> str:
    code: str | None = None

    match expr:
        case ["NOT", list(a)]:
            code = f"not {e(a)}"
        case [str(a), ["IS", "NOT"], str(b)]:
            code = field_condition(a, b, negate=True)
        case [str(a), "IS", str(b)]:
            code = field_condition(a, b)
        case [list(a), "AND", *b]:
            code = f"{e(a)} and {e(b)}"
        case [list(a), "OR", *b]:
            code = f"{e(a)} or {e(b)}"
        case [list(a)]:
            return e(a)

    if code is None:
        raise ValueError(f"Invalid expression '{collapse(expr)}'")

    return "(" + code + ")"


type EventFilter = Callable[[str, int], bool]

_compile = compile


def compile(expr_str: str) -> EventFilter:
    code = "lambda day, time: " + e(parser.parse_string(expr_str).as_list())
    return eval(_compile(code, "event_filter", "eval"))


trivial_filter: EventFilter = lambda _, __: True


def s(time_str: str):
    try:
        parts = list(map(int, time_str.strip().split(":")))
        match len(parts):
            case 2:
                return parts[0] * 3600 + parts[1] * 60
            case 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except (ValueError, IndexError, AttributeError):
        pass
    return None
