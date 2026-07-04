#!/usr/bin/env python3

import re
from functools import reduce
from pathlib import Path
from typing import Callable

import frontmatter
import pypandoc

from meta import APP_NAME

LINK_RE = re.compile(r"\[.*?\]\(([^/]*?\.md)\)")

input_directory = Path("docs")
output_directory = Path("build/man")

output_directory.mkdir(parents=True, exist_ok=True)


def get_section(path: Path):
    front_matter = frontmatter.load(path)

    match front_matter.get("section", None):
        case str(section) | int(section) | float(section):
            return str(section)
        case None:
            raise KeyError(f"The front matter of {path} must have key 'section'")
        case _:
            raise ValueError(
                f"The front matter key 'section' of {path} must be a literal"
            )


def replace_doc_links(content: str):
    return LINK_RE.sub(
        lambda m: f"*{APP_NAME}*({get_section(input_directory / Path(m[1]))})",
        content,
    )


preprocessing_filters: list[Callable[[str], str]] = [replace_doc_links]


def main():
    for path in input_directory.iterdir():
        if path.is_file() and path.suffix == ".md":
            section = get_section(path)

            output_path = output_directory / f"man{section}" / f"{APP_NAME}.{section}"

            with open(path, "r", encoding="utf-8") as file:
                pypandoc.convert_text(
                    reduce(
                        lambda content, filter: filter(content),
                        preprocessing_filters,
                        file.read(),
                    ),
                    "man",
                    "markdown",
                    filters=["tools/lib/pandoc_filter.py"],
                    outputfile=output_path,
                    extra_args=["--standalone"],
                )

            print(path, "→", output_path)


if __name__ == "__main__":
    main()
