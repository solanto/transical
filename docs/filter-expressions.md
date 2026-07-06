---
title: transical
section: 7
title_prefix: "Filter Expressions"
header: "transical Manual"
footer: "transical 0.3"
date: July 2026
---

# name

*transical* – manual page for transical 0.3 filtering expressions

# synopsis

```bnf
<expression> ::= <field> is [ not ] <complement>
                 [ and <expression> | or <expression> ]

<field>      ::= day | time

<complement> ::= <day_literal> | <day_group> | <time_literal> | <range>
```

# description

A `--filter` expression allows users to isolate specific journeys by departure day-of-week and time-of-day when converting GTFS schedules to calendar events.

transical reads `INPUT` as a path to a local GTFS archive or a URL to one online., evaluates journeys between `START_DATE` and `END_DATE` (`YYYY-MM-dd` format) matching the filter expression, and writes an iCalendar file to the `OUTPUT` path.

All text in expressions is case-insensitive; `DAY IS WED`, `day IS wed`, and `day is wed` are equivalent.

# grammar

```bnf
<expression>     ::= <and_expression> [ or <expression> ]

<and_expression> ::= <condition> [ and <and_expression> ]

<condition>      ::= <base_condition>
                   | not "(" <expression> ")"

<base_condition> ::= <field> is [ not ] <complement>
                   | "(" <expression> ")"

<field>          ::= day | time

<complement>     ::= <day_literal> | <day_group> | <time_literal> | <range>

<day_literal>    ::= mondays
                   | tuesdays
                   | wednesdays
                   | thursdays
                   | fridays
                   | saturdays
                   | sundays

<day_group>      ::= weekdays | weekends

<time_literal>   ::= H:mm | H:mm:ss

<range>          ::= <day_literal>"/"<day_literal>
                   | <time_literal>"/"<time_literal>

```

## shorthand

For `<field>`s, `<day_literal>`s, and `<day_group>`s: any unambiguous suffix is accepted. For example, `day` can be written `d`; `Wednesdays` must meanwhile be at least `wed` to disambiguate from `weekdays` and `weekends`.

## time formatting

Times are in 24-hour format, and their hour portions can omit leading zeroes; 1pm is written `13:00`, and 8am is `08:00` or `8:00`.

## range inclusivity

Ranges are inclusive of their bounds; `8:00/13:00` is from the clock striking eight—not only up through 12:59:59—but also through the exact, singular second at 13:00:00. Likewise, `tue/thurs` includes all of Tuesday, Wednesday, and Thursday.

# examples

## basic fields & literals

Journeys on Mondays:

    day is monday

Journeys on Saturdays or Sundays:

    day is weekend

Journeys that depart at exactly 12:30:

    time is 12:30

## ranges

Journeys on Fridays, Saturdays, Sundays, or Mondays:

    day is fri/mon

Journeys that depart between seven-thirty and nine in the morning:

    time is 7:30/9:00

## condition negation

Journeys that depart outside of the hours between nine and five:

    time is not 9:00/17:00

## operator precedence

Journeys that depart 1. at exactly nine on Tuesdays, or 2. any time on Thursdays; equivalent to `(d is tue and t is 09:00) or day is thu`:

    d is tue and t is 09:00 or day is thu

## expression negation

Journeys that depart 1. anytime on weekdays, or 2. weekends outside of 10am to 4pm; equivalent to `d is weekday or t is not 10:00/16:00`.

    not (d is weekend and t is 10:00/16:00)

# see also

[General info on transical](general.md)