#!/usr/bin/env python3

import re

from panflute import (
    Code,
    CodeBlock,
    Doc,
    Element,
    Emph,
    Header,
    Link,
    RawBlock,
    RawInline,
    Str,
    Strong,
    run_filters,
    stringify,
)

FLAG_RE = re.compile(r"^--[\w\-_]+|^-[\w\-_]+")
WORD_RE = re.compile(r"\S+")


def escape(text: str) -> str:
    return text.replace("\\", r"\\")


def capitalize_headers(elem: Element, _: Doc):
    if not isinstance(elem, Header):
        return None

    first = True
    new_content = []

    for x in elem.content:
        if not isinstance(x, Str):
            new_content.append(x)
            continue

        if elem.level == 1:
            new_content.append(Str(x.text.upper()))
            continue

        if first:
            new_content.append(
                Str(re.sub(r"^[a-zA-Z]", lambda m: m.group(0).upper(), x.text, count=1))
            )
            first = False
        else:
            new_content.append(Str(x.text.lower()))

    elem.content = new_content
    return elem


def bold_flag(word: str) -> str:
    m = FLAG_RE.match(word)
    if not m:
        return word
    flag = m.group(0)
    return f"\\fB{flag}\\fR{word[len(flag):]}"


def code(elem: Element, _: Doc):
    if not isinstance(elem, Code):
        return None

    words = elem.text.split(" ")
    out = []

    for w in words:
        w = escape(w)
        if w.startswith("-"):
            w = bold_flag(w)
        out.append(w)

    return RawInline(" ".join(out), format="man")


def process_bnf_word(word: str) -> str:
    word = escape(word)
    out = []
    i = 0

    while i < len(word):
        c = word[i]

        if c == "<":
            j = word.find(">", i)
            if j != -1:
                out.append(word[i : j + 1])
                i = j + 1
                continue

        if c in ('"', "'"):
            j = word.find(c, i + 1)
            if j != -1:
                out.append(f"\\fB{word[i:j+1]}\\fR")
                i = j + 1
                continue

        if word.startswith("::=", i):
            out.append("\\fB::=\\fR")
            i += 3
            continue

        if c in ("|", "/"):
            out.append(f"\\fB{c}\\fR")
            i += 1
            continue

        out.append(c)
        i += 1

    return "".join(out)


def code_block(elem: Element, _: Doc):
    if not isinstance(elem, CodeBlock):
        return None

    def process_line(line: str) -> str:
        parts = line.split(" ")
        out = []
        first_word = True

        for w in parts:
            w = escape(w)

            if "bash" in elem.classes:
                if first_word and (w.endswith(":") or re.match(r"^[\w\-_]+$", w)):
                    w = f"\\fB{w}\\fR"
                elif w.startswith("-"):
                    w = bold_flag(w)

            elif "bnf" in elem.classes:
                w = process_bnf_word(w)

            first_word = w == "|"
            out.append(w)

        return " ".join(out)

    body = "\n".join(process_line(l) for l in elem.text.splitlines())

    return RawBlock(f".PP\n.nf\n{body}\n.fi", format="man")


def emph(elem: Element, _: Doc):
    if isinstance(elem, Emph):
        return RawInline(f"\\fB{stringify(elem)}\\fR", format="man")


def strong(elem: Element, _: Doc):
    if isinstance(elem, Strong):
        return RawInline(f"\\fB\\ul{stringify(elem)}\\ul0\\fR", format="man")


def link(elem: Element, _: Doc):
    if not isinstance(elem, Link):
        return None

    text = stringify(elem)
    url = elem.url

    return RawInline(
        rf"\X'tty: link {url}'{text}\X'tty: link'",
        format="man",
    )


def main(doc=None):
    return run_filters(
        [
            capitalize_headers,
            code,
            code_block,
            emph,
            strong,
            link,
        ],
        doc=doc,
    )


if __name__ == "__main__":
    main()
