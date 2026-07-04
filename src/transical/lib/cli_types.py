import datetime

import click
from click import ParamType
from isodate import ISO8601Error, parse_duration


class DateInterval(ParamType):
    name = "date_interval"

    def convert(self, value: str, param, ctx):
        if not value:
            return None

        dates = value.split("/")

        if len(dates) != 2:
            self.fail(
                "Interval must contain exactly two dates delimited by `/`: `YYYY-mm-dd/YYYY-mm-dd`.",
                param,
                ctx,
            )
        try:
            start_date = click.DateTime(formats=["%Y-%m-%d"]).convert(
                dates[0], param, ctx
            )
            end_date = click.DateTime(formats=["%Y-%m-%d"]).convert(
                dates[1], param, ctx
            )
        except click.BadParameter:
            self.fail("Ensure both dates match the format `YYYY-mm-dd`.", param, ctx)
        return start_date.date(), end_date.date()


class Termini(ParamType):
    name = "termini"

    def convert(self, value: str, param, ctx):
        if not value:
            return None

        match value.split("/"):
            case [start, end]:
                return start, end
            case _:
                self.fail(
                    "Termini must contain exactly two stop IDs delimited by `/`: `ID/ID`.",
                    param,
                    ctx,
                )


class Duration(ParamType):
    name = "duration"

    def convert(self, value: str, param, ctx) -> datetime.timedelta | None:
        if isinstance(value, datetime.timedelta):
            return value
        try:
            return datetime.timedelta(minutes=float(value))
        except ValueError:
            pass

        try:
            return parse_duration(value)
        except ISO8601Error:
            self.fail(
                f"`{value}` is not a valid ISO 8601 duration (e.g. PT1H30M) or number of minutes (e.g. 90).",
                param,
                ctx,
            )
