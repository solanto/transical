# transical

[![PyPI](https://img.shields.io/pypi/v/transical)](https://pypi.org/project/transical/)

transical converts publically-available [GTFS](https://gtfs.org/) transit schedules into calendar events, bundled into [iCalendar](https://en.wikipedia.org/wiki/ICalendar) (`.ics`) files.

It’s designed to automate putting public transit schedules in your calendar. iCalendar files can be imported into Google Calendar, Apple Calendar, Evolution, Thunderbird, or just about any other calendar application.

## installing

[pipx](https://pipx.pypa.io/) is the preferred way to install transical. Unlike [pip](https://pip.pypa.io/) alone: it automatically isolates the package from your other Python packages, puts the package in your [`PATH`](https://en.wikipedia.org/wiki/PATH_(variable)), and installs [manpages](https://en.wikipedia.org/wiki/Man_page).

On pipx systems:

```shell
pipx install transical
```

Install [shell autocompletions](https://en.wikipedia.org/wiki/Command-line_completion) with `transical --autocomplete`.

<details>
<summary>do you <em>really</em> want to use pip?</summary>

pip is not recommended. On pip systems, for global installation:

```shell
pip install transical
```
</details>

## usage

```bash
transical input.gtfs 2026-07-01/2026-08-01 output.ics
```

That's it! transical interactively walks you through picking a route, origin stop, and destination stop, before producing an output file with all the transit journeys that fall between the specified dates (1 July and 1 August 2026, in this example).

```console
$ transical https://feeds.mta.maryland.gov/gtfs/marc 2026-07-01/2026-08-01 output.ics
No route was provided. Use arrow keys to select a route from the menu below.
🔄› 11704 · MARC · BRUNSWICK - WASHINGTON                                       
    11705 · MARC · PENN - WASHINGTON                                            
    11706 · MARC · CAMDEN - WASHINGTON                                          
Selecting route. Hit </> to search.
```

You can directly import transical's `.ics` outputs in desktop applications (guides linked) like [Google Calendar](https://support.google.com/calendar/answer/37118?hl=en&co=GENIE.Platform%3DDesktop), [Apple Calendar](https://support.apple.com/guide/calendar/import-or-export-calendars-icl1023/mac), [Evolution](https://help.gnome.org/evolution/import-single-files.html), and [Thunderbird](https://support.mozilla.org/en-US/kb/thunderbird-import).

You can also send outputs to yourself to import events on another device, with a tool like [*xdg-email*](https://portland.freedesktop.org/doc/xdg-email.html):

```bash
xdg-email --attach output.ics recipient@example.com
```

### more features

transical supports adding event reminders, and it even has its own filtering language to let you granularly choose journeys based on time of day and day of week.

transical has a noninteractive, script mode, too; it won't output anything it doesn't need to when called with `--route` and `--termini` flags already provided to it.

Read more about [using transical](docs/general.md) or [writing filter expressions](docs/filter-expressions.md). You can also find this documentation in transical's manpages, or see an overview with `transical --help`.

## developing and building

This project uses [uv](https://docs.astral.sh/uv/).

Clone the repository with [Git](https://git-scm.com/) and use uv to install dependencies:

```bash
git clone git@github.com:solanto/transical.git
cd transical
uv sync
```

Run the program in development with `uv run`:

```bash
uv run transical
```

And build the package with `uv build`:

```bash
uv build
```

This not only packages the program itself, but also converts documentation in [`docs`](docs) to manpages—installable via pipx—by way of a custom Pandoc pipeline. You can check out this pipeline in [`tools`](tools).

## acknowledgements

[komoot](https://www.komoot.com/)'s free [photon API](https://photon.komoot.io/) for [OpenStreetMap](https://www.openstreetmap.org) lets this project make station names prettier in your calendar. Thanks, komoot!

## contributing

Feel free to ask questions or make suggestions here or at [person@dandelion.computer](mailto:person@dandelion.computer). I'll do my best to collaborate with those who'd like to!

If you fork transical, be sure to change [`meta:ORG_DOMAIN`](meta.py#L18) to your own domain (which could even be something like `your-username.github.io`). transical uses this identifier to tell remote servers exactly whose code is requesting information, as well as to document exactly whose code made the events in produced iCalendar files.

## license

[GNU General Public License v3.0 or later](https://spdx.org/licenses/GPL-3.0-or-later.html). See license in [`LICENSE.md`](LICENSE.md).
