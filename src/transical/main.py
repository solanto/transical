import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from random import choice
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
from typing import Any, BinaryIO, Final, cast

import click as ck
import pandas as pd
import partridge as ptg
import requests
from auto_click_auto import enable_click_shell_completion_option
from icalendar import Alarm, Calendar, Event, vRecur
from isodate import duration_isoformat
from pandas import DataFrame

import transical.lib.filter_compiler as filter_compiler
from meta import (
    APP_DOMAIN,
    APP_ID,
    APP_NAME,
    ORG_DOMAIN,
    VERSION,
)
from transical.lib.cli_types import DateInterval, Duration, Termini
from transical.lib.filter_compiler import EventFilter
from transical.lib.utils import (
    GTFS_TO_ICAL_DAY,
    absorb,
    copy_signature,
    data_menu,
    find_flag_index,
    hash,
    singleton_table_get,
)

requests_session = requests.Session()

ROUTE_FLAG = ("--route", "-r")
TERMINI_FLAG = ("--termini", "-t")
FILTER_FLAG = ("--filter", "-f")

THIS_YEAR: Final = date.today().year

EXAMPLES: Final = "\n\n.\n\n".join(
    f"  {sys.argv[0]} {arguments}\n\n  ↳ {description}"
    for arguments, description in [
        (
            f"input.gtfs {THIS_YEAR}-07-01/{THIS_YEAR}-08-01 output.ics",
            f"Interactively pick a route, origin stop, and destination stop from input.gtfs; evaluate all journeys between the chosen stops between 1 July, {THIS_YEAR}, and 1 August, {THIS_YEAR}; and save those journeys as events in output.ics.",
        )
    ]
)


class Command(ck.Command):
    def format_epilog(self, ctx, formatter):
        if self.epilog:
            formatter.write_heading("Example")
            formatter.write_text(EXAMPLES)
            formatter.write_paragraph()

            formatter.write_text(self.epilog)
            formatter.write_paragraph()
            formatter.write_dl


@ck.command(
    cls=Command,
    epilog="Use a tool like sed (https://www.gnu.org/software/sed/) to replace parts of events' titles or descriptions, or mergecal (https://mergecal.readthedocs.io/en/latest/) to turn multiple outputs into a single iCalendar file.",
)
@ck.pass_context
@ck.help_option("--help", "-h", help="display this help and exit")
@ck.version_option(
    VERSION,
    "--version",
    "-v",
    prog_name=APP_NAME,
    message=f"%(prog)s ({ORG_DOMAIN}) %(version)s",
)
@ck.argument("input")
@ck.argument("interval", metavar="START_DATE/END_DATE", type=DateInterval())
@ck.argument("output", type=ck.File(mode="wb", lazy=True), required=False)
@ck.option(
    *ROUTE_FLAG,
    metavar="ROUTE_ID",
    help="evaluate journeys matching ROUTE_ID (default: interactive choice)",
)
@ck.option(
    *TERMINI_FLAG,
    metavar="ORIG_ID/DEST_ID",
    type=Termini(),
    help="evaluate journeys from ORIG_ID to DEST_ID (default: interactive choice)",
)
@ck.option(
    "--alarm",
    "-a",
    metavar="PERIOD",
    type=Duration(),
    multiple=True,
    help="add a reminder PERIOD (integer number of minutes or ISO 8601 period) before each event (pass multiple alarms with '-a PERIOD1 -a PERIOD2 …')",
)
@ck.option(
    *FILTER_FLAG, metavar="EXPRESSION", help="filter journeys based on EXPRESSION"
)
@ck.option(
    "--keep-origin-location",
    "-o",
    is_flag=True,
    help="don't attempt to canonicalize the origin stop's name and coordinates (default: canonicalize via OpenStreetMap)",
)
@enable_click_shell_completion_option(help="enable shell autocompletion and exit")
def cli(
    ctx: ck.Context,
    input: str,
    interval: tuple[date, date],
    output: BinaryIO | None,
    route: str,
    termini: tuple[str, str],
    alarm: tuple[timedelta, ...],
    filter: str | None,
    keep_origin_location: bool,
):
    """Turn a GTFS schedule into calendar events.

    Read INPUT as path to a local GTFS archive or a URL to one online. Evaluate journeys between START_DATE and END_DATE (YYYY-MM-dd format). Write an iCalendar file to OUTPUT path.
    """

    if (not route or not termini) and not output:
        raise ValueError(
            "An output must be specified in interactive mode, when route or temrini are not provided"
        )

    filter_callback = cast(
        EventFilter,
        filter_compiler.compile(filter) if filter else lambda _, __: True,
    )

    temp_file: _TemporaryFileWrapper | None = None

    try:
        requests_session.get_adapter(input)
        with requests_session.get(input, stream=True, timeout=30) as response:
            response.raise_for_status()

            temp_file = NamedTemporaryFile(mode="wb", suffix=".zip")
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)

            gtfs_path = temp_file.name
    except requests.exceptions.InvalidSchema:
        if Path(input).is_file():
            gtfs_path = input
        else:
            raise FileNotFoundError(input)

    start_date, end_date = interval
    full_feed = ptg.load_feed(gtfs_path)
    interactive = False

    def echo_selection_canceled():
        ck.echo("🚫 Selection was canceled.")

    if not route:
        interactive = True
        ck.echo(
            f"No route was provided. Use arrow keys to select a {ck.style('route', bold=True)} from the menu below."
        )

        route_icon = "🔄"
        match data_menu(
            full_feed.routes[
                ["route_id", "route_short_name", "route_long_name", "route_desc"]
            ],
            cursor=route_icon,
            cursor_color="cyan",
            category="route",
        ).show():
            case int(index):
                route = str(full_feed.routes.loc[index, "route_id"])
                absorb(2)
                ck.echo(f"{route_icon} Using route {route}.")
            case _:
                return echo_selection_canceled()

    if termini:
        origin_stop_id, destination_stop_id = termini
    else:
        interactive = True
        no_termini_message = "No termini were provided."
        ck.echo(
            f"{no_termini_message} Use arrow keys to select an {ck.style('origin', bold=True)} from the menu below."
        )

        all_route_trip_ids = full_feed.trips.query("route_id == @route")["trip_id"]
        forward_backward_route_stop_cols = [
            "direction_id",
            "stop_sequence",
            "stop_id",
            "stop_name",
        ]
        if not all_route_trip_ids.empty:
            spanning_trips = (
                full_feed.stop_times.query("trip_id in @all_route_trip_ids")
                .groupby("trip_id")
                .size()
                .reset_index(name="count")
                .merge(full_feed.trips[["trip_id", "direction_id"]], on="trip_id")
                .sort_values("count", ascending=False)
                .drop_duplicates(subset=["direction_id"])
            )
            all_route_stops_ordered = (
                full_feed.stop_times.merge(spanning_trips, on="trip_id")
                .sort_values(by=["direction_id", "stop_sequence"])
                .drop_duplicates(subset=["direction_id", "stop_id"], keep="first")
            )
            dir0_stops = all_route_stops_ordered.query("direction_id == 0")
            dir1_stops_reversed = all_route_stops_ordered.query("direction_id == 1")
            forward_backward_route_stops = (
                pd.concat([dir0_stops, dir1_stops_reversed])
                .merge(full_feed.stops, on="stop_id", how="left")
                .loc[lambda df: df["stop_id"] != df["stop_id"].shift()]
                .reset_index(drop=True)[forward_backward_route_stop_cols]
            )
        else:
            forward_backward_route_stops = DataFrame(
                columns=forward_backward_route_stop_cols
            )

        origin_icon = "📍"

        match data_menu(
            forward_backward_route_stops[["stop_id", "stop_name"]],
            cursor=origin_icon,
            cursor_color="red",
            category="origin",
        ).show():
            case int(index):
                origin_stop_index = index
                origin_stop_id = str(forward_backward_route_stops.loc[index, "stop_id"])
                origin_stop_direction = bool(
                    forward_backward_route_stops.loc[index, "direction_id"]
                )
                absorb()
                ck.echo(f"{origin_icon} Using origin {origin_stop_id}.")
            case _:
                return echo_selection_canceled()

        ck.echo(
            f"{no_termini_message} Use arrow keys to select a {ck.style('destination', bold=True)} from the menu below."
        )
        raw_destinations = forward_backward_route_stops.iloc[origin_stop_index + 1 :]
        same_direction_destinations, _ = (
            raw_destinations.query("direction_id == @origin_stop_direction"),
            origin_stop_direction,  # tell linter we use this variable
        )
        destination_options = cast(
            DataFrame,
            (
                raw_destinations
                if same_direction_destinations.empty
                else same_direction_destinations
            ),
        ).reset_index()

        destination_icon = "🏁"

        match data_menu(
            destination_options[["stop_id", "stop_name"]],
            cursor=destination_icon,
            cursor_color="yellow",
            category="destination",
        ).show():
            case int(index):
                destination_stop_id = str(destination_options.loc[index, "stop_id"])
                absorb()
                ck.echo(f"{destination_icon} Using destination {destination_stop_id}.")
            case _:
                return echo_selection_canceled()

    if interactive:
        filter_flag_index = find_flag_index(FILTER_FLAG)
        route_flag_index = find_flag_index(ROUTE_FLAG)
        termini_flag_index = find_flag_index(TERMINI_FLAG)

        excluded_indices = {
            index
            for flag_index in (route_flag_index, termini_flag_index, filter_flag_index)
            if flag_index is not None
            for index in (flag_index, flag_index + 1)
        }

        argv_without_tip_items = [
            argument
            for index, argument in enumerate(sys.argv)
            if index not in excluded_indices
        ]

        @copy_signature(ck.style)
        def tip_style(text: str, **kwargs):
            return ck.style(text, fg="yellow", **kwargs)

        ck.echo(
            tip_style(f"\n✨ Next time, you can run:\n")
            + tip_style(" ".join(argv_without_tip_items[:4]) + " ")
            + tip_style(f"-r {route} ", bold=route_flag_index is None)
            + tip_style(
                f"-t {origin_stop_id}/{destination_stop_id}",
                bold=termini_flag_index is None,
            )
            + tip_style(
                f"{f' -f "{filter}"' if filter else ""} {" ".join(argv_without_tip_items[4:])}\n",
            )
        )

    candidate_services = {
        id
        for d, ids in ptg.read_service_ids_by_date(gtfs_path).items()
        if start_date <= d <= end_date
        for id in ids
    }
    feed = ptg.load_feed(
        gtfs_path, {"trips.txt": {"route_id": route, "service_id": candidate_services}}
    )
    origin_stop_info = (
        feed.stops.query("stop_id == @origin_stop_id").iloc[0].astype(str)
    )

    event_location = origin_stop_info["stop_name"]
    event_geo = (origin_stop_info["stop_lat"], origin_stop_info["stop_lon"])

    if interactive:
        ck.echo("🤖 Working…")

    if not keep_origin_location:
        url = "https://photon.komoot.io/api/"
        params: dict[str, Any] = {
            "limit": 1,
            "lang": "en",
            "lat": origin_stop_info["stop_lat"],
            "lon": origin_stop_info["stop_lon"],
            "include": "osm.railway.station,osm.railway.halt,osm.railway.subway_entrance,osm.railway.tram_stop,osm.amenity.bus_station,osm.highway.bus_stop,osm.amenity.ferry_terminal,osm.public_transport.platform",
        }
        headers: dict[str, str] = {"User-Agent": f"transical 0.1 ({APP_DOMAIN})"}
        response = requests_session.get(url, params=params, headers=headers)
        origin_osm_info: dict[str, Any] | None = (
            response.json()["features"][0] if response.status_code == 200 else None
        )

        if origin_osm_info is not None:
            event_location = str(origin_osm_info["properties"]["name"])
            event_geo = (
                str(origin_osm_info["geometry"]["coordinates"][1]),
                str(origin_osm_info["geometry"]["coordinates"][0]),
            )

    origin_data = feed.stop_times.query("stop_id == @origin_stop_id")[
        ["trip_id", "stop_sequence", "departure_time"]
    ]
    dest_data = feed.stop_times.query("stop_id == @destination_stop_id")[
        ["trip_id", "stop_sequence", "arrival_time"]
    ]
    merged_stops = pd.merge(origin_data, dest_data, on="trip_id")
    ordered_merged_stops = merged_stops.query("stop_sequence_x < stop_sequence_y")
    relevant_trips = pd.merge(
        feed.trips.query("trip_id in @ordered_merged_stops.trip_id"),
        ordered_merged_stops,
        on="trip_id",
    )

    cal = Calendar()
    cal.add(
        "prodid",
        f"-//{ORG_DOMAIN}//transical//EN",
    )
    cal.add("version", "0.1")

    seen_events = set()

    route_row = feed.routes.query("route_id == @route").iloc[0]
    route_name = f"{route_row.get('route_short_name', '')} {route_row.get('route_long_name', '')}".strip()

    dest_stop_info = feed.stops.query("stop_id == @destination_stop_id").iloc[0]
    origin_name = origin_stop_info["stop_name"]
    dest_name = dest_stop_info["stop_name"]

    for _, trip in relevant_trips.iterrows():
        calendar_rows = feed.calendar.query("service_id == @trip.service_id")
        if calendar_rows.empty:
            continue
        calendar_row = calendar_rows.iloc[0]

        run_days = [day for day in GTFS_TO_ICAL_DAY.keys() if bool(calendar_row[day])]
        if not run_days:
            continue

        trip_time = int(trip["departure_time"])
        filtered_run_days = [day for day in run_days if filter_callback(day, trip_time)]
        if not filtered_run_days:
            continue

        event_signature = (
            str(trip.get("trip_short_name", trip["trip_headsign"])).title(),
            int(trip["departure_time"]),
            int(trip["arrival_time"]),
            tuple(sorted(filtered_run_days)),
        )

        if event_signature in seen_events:
            continue
        seen_events.add(event_signature)

        service_start = pd.to_datetime(calendar_row["start_date"]).date()
        service_end = pd.to_datetime(calendar_row["end_date"]).date()
        rrule_start = max(start_date, service_start)
        rrule_end = min(end_date, service_end)

        active_weekdays = [GTFS_TO_ICAL_DAY[day] for day in filtered_run_days]

        event = Event()
        dtstart = datetime.combine(rrule_start, time.min) + timedelta(
            seconds=int(trip["departure_time"])
        )
        dtend = datetime.combine(rrule_start, time.min) + timedelta(
            seconds=int(trip["arrival_time"])
        )
        event.add(
            "summary", str(trip.get("trip_short_name", trip["trip_headsign"])).title()
        )
        event.add(
            "description",
            (
                f"Route: {route_name}\n"
                f"Between: {origin_name} & {dest_name}\n"
                f"Heading: {str(trip['trip_headsign'])}"
            ),
        )
        event.add("dtstamp", datetime.now(UTC))
        event.add("dtstart", dtstart)
        event.add("dtend", dtend)

        agency_name = singleton_table_get(feed.agency, "agency_name")

        match singleton_table_get(feed.agency, "agency_id"):
            case None:
                if agency_name is None:
                    raise ValueError("agency.txt must include agency_name")
                else:
                    agency_id = hash(agency_name)
            case id:
                agency_id = str(id)

        feed_id = str(singleton_table_get(full_feed.feed_info, "feed_id", agency_id))

        event_id = f"{feed_id}_{agency_id}_{trip['trip_id']}"
        event.add("uid", f"{event_id}@{APP_ID}")

        event.add(
            "rrule",
            vRecur(
                {
                    "freq": "weekly",
                    "byday": active_weekdays,
                    "until": datetime.combine(rrule_end, datetime.min.time()),
                }
            ),
        )

        exceptions = feed.calendar_dates.query(
            "service_id == @trip.service_id and exception_type == 2"
        )
        exdts: list[date] = []
        for _, exception_row in exceptions.iterrows():
            exception_date = cast(date, exception_row["date"])
            if start_date <= exception_date <= end_date:
                exdts.append(
                    datetime.combine(exception_date, time.min)
                    + timedelta(seconds=int(trip["departure_time"]))
                )
        if exdts:
            event.add("exdate", exdts)

        event.add("location", event_location)
        event.add("geo", event_geo)

        for period in alarm:
            a = Alarm()
            a.add("action", "DISPLAY")
            a.add("trigger", -period)
            a.add("uid", f"{event_id}_{duration_isoformat(period)}@{APP_ID}")
            event.add_component(a)

        cal.add_component(event)

    ical = cal.to_ical()

    if output:
        output.write(ical)

        if interactive:
            ck.echo(
                choice(
                    [
                        "🚂",
                        "🚃",
                        "🚄",
                        "🚅",
                        "🚆",
                        "🚇",
                        "🚈",
                        "🚉",
                        "🚋",
                        "🚌",
                        "🚍",
                        "🚎",
                        "🚏",
                        "🚠",
                        "🚡",
                        "🚟",
                    ]
                )
                + " Done!"
            )
    else:
        print(ical.decode(sys.stdout.encoding))
