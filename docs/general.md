---
title: transical
section: 1
title_prefix: "User Commands"
header: "transical Manual"
footer: "transical 0.3"
date: July 2026
---

# name

*transical* – manual page for transical 0.3

# synopsis

```bash
transical [OPTIONS] INPUT START_DATE/END_DATE [OUTPUT]
```

# description

*transical* turns GTFS schedules into calendar events.

*transical* reads `INPUT` as a path to a local GTFS archive or a URL to one online, evaluates journeys between `START_DATE` and `END_DATE` (`YYYY-MM-dd` format), and writes an iCalendar file to the `OUTPUT` path.

# options

`-h`, `--help`

: display help and exit

`-v`, `--version`

: show the version and exit

`-r`, `--route` `ROUTE_ID`

: evaluate journeys matching `ROUTE_ID` (default: interactive choice)

`-t`, `--termini` `ORIG_ID/DEST_ID`

: evaluate journeys from `ORIG_ID` to `DEST_ID` (default: interactive choice)

`-a`, `--alarm` `PERIOD`

: add a reminder `PERIOD` (integer number of minutes or [ISO 8601 period](https://en.wikipedia.org/wiki/ISO_8601#Durations)) before each event (pass multiple alarms with `-a PERIOD1 -a PERIOD2 ...`)

`-f`, `--filter` `EXPRESSION`

: filter journeys based on `EXPRESSION`

`-o`, `--keep-origin-location`

: don't attempt to canonicalize the origin stop's name and coordinates (default: canonicalize via OpenStreetMap)

`--autocomplete`

: enable shell autocompletion and exit

# examples

## routes, stops, & interactive mode

Interactively pick a route, origin stop, and destination stop from `input.gtfs`; evaluate all journeys between the chosen stops between 1 July, 2026, and 1 August, 2026; and save those journeys as events in `output.ics`:

```bash
transical input.gtfs 2026-07-01/2026-08-01 output.ics
```

Do the same as before, but with route ID `RED` preselected—leaving only the origin and destination stop to be chosen interactively.

```bash
transical input.gtfs 2026-07-01/2026-08-01 output.ics -r RED
```

Finally, do the same with origin and destination stop IDs `STN_B03` and `STN_A14` on route ID `RED` preselected, leaving the program to run noninteractively.

```bash
transical input.gtfs 2026-07-01/2026-08-01 output.ics -r RED -t STN_B03/STN_A14
```

## remote feeds

Use the GTFS feed for the Maryland Transit Administration's MARC, available [online](https://www.mta.maryland.gov/developer-resources):

```bash
transical https://feeds.mta.maryland.gov/gtfs/marc 2026-07-01/2026-08-01 output.ics
```

## alarms

Add reminders thirty and ninety minutes before each journey—using an integer number of minutes and an ISO 8601 period expression, respectively:

```bash
transical input.gtfs 2026-07-01/2026-07-31 output.ics -a 30 -a PT1H30M
```

## filtering

Export only weekday journeys departing between eight and ten o'clock:

```bash
transical input.gtfs 2026-07-01/2026-07-31 output.ics \
    -f 'day is weekday and time is 8:00/10:00' 
```

See a full specification of filter expressions' grammar, alongside more examples, in [filter expressions](filter-expressions.md).

## standard output

Write an iCalendar file of journeys to standard output (`stdout`; requires route and termini):

```bash
transical input.gtfs 2026-07-01/2026-08-01 -r RED -t STN_B03/STN_A14
```

# further processing

Use a tool like [*sed*](https://www.gnu.org/software/sed/) to replace parts of events\' titles or descriptions, or [*MergeCal*](https://mergecal.readthedocs.io/en/latest/) to turn multiple outputs into a single iCalendar file.

Email an output to yourself for easy import on another device, with a tool like [*xdg-email*](https://portland.freedesktop.org/doc/xdg-email.html):

```bash
transical input.gtfs 2026-07-01/2026-08-01 output.ics
xdg-email --attach output.ics recipient@example.com
```

# see also

[Filter expressions](filter-expressions.md)
