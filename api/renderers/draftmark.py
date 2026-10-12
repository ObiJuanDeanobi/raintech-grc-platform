"""DRAFT watermarking for generated DOCX and XLSX files (GitHub issue #145).

A draft is never stored and never issued, so every file it contains must say so
wherever it is opened: a header on every Word section, a header on every Excel
sheet plus a banner in the first row, and a first line in every CSV. Nothing
here needs a new dependency; both formats are plain zipped XML.
"""

import re
import zipfile
from io import BytesIO
from xml.sax.saxutils import escape

DRAFT_BANNER = "DRAFT — NOT ISSUED"
UNDECIDED = "Not yet decided"
DRAFT_PREFIX = "DRAFT_"

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_HEADER_PART = "word/header_draft.xml"
_HEADER_REL_ID = "rIdDraftHeader"
_HEADER_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header"
_HEADER_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
_RELS_PART = "word/_rels/document.xml.rels"


def _header_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:hdr xmlns:w="{_W}" xmlns:r="{_R}"><w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:b/><w:color w:val="C00000"/><w:sz w:val="28"/></w:rPr>'
        f"<w:t>{escape(DRAFT_BANNER)}</w:t></w:r></w:p></w:hdr>"
    )


def _rewrite_zip(data: bytes, changes: dict[str, bytes], new_files: dict[str, bytes]) -> bytes:
    out = BytesIO()
    with (
        zipfile.ZipFile(BytesIO(data)) as source,
        zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        stamp = source.infolist()[0].date_time
        for item in source.infolist():
            target.writestr(item, changes.get(item.filename, source.read(item.filename)))
        for name, content in new_files.items():
            target.writestr(zipfile.ZipInfo(name, date_time=stamp), content)
    return out.getvalue()


def mark_docx(data: bytes) -> bytes:
    """Put the draft header on every section and prefix the title."""
    with zipfile.ZipFile(BytesIO(data)) as archive:
        document = archive.read("word/document.xml").decode("utf-8")
        types = archive.read("[Content_Types].xml").decode("utf-8")
        rels = (
            archive.read(_RELS_PART).decode("utf-8")
            if _RELS_PART in archive.namelist()
            else (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                'relationships"></Relationships>'
            )
        )
    if "xmlns:r=" not in document[: document.find("<w:body")]:
        document = re.sub(r"<w:document\b", f'<w:document xmlns:r="{_R}"', document, count=1)
    references = "".join(
        f'<w:headerReference w:type="{kind}" r:id="{_HEADER_REL_ID}"/>'
        for kind in ("default", "first", "even")
    )

    def section(match: re.Match[str]) -> str:
        return match.group(0) + references

    document = re.sub(
        r'<w:headerReference\b[^>]*w:type="(?:default|first|even)"[^>]*/>', "", document
    )
    document = re.sub(r"<w:sectPr\b[^>]*(?<!/)>", section, document)
    if "<w:sectPr" not in document:
        # A document with no section properties still has one implicit section.
        document = document.replace("</w:body>", f"<w:sectPr>{references}</w:sectPr></w:body>")
    document = re.sub(
        r'(<w:pStyle w:val="Title"\s*/>.*?<w:t(?: [^>]*)?>)',
        lambda m: m.group(1) + escape(DRAFT_BANNER) + " — ",
        document,
        count=1,
        flags=re.S,
    )
    if _HEADER_REL_ID not in rels:
        rels = rels.replace(
            "</Relationships>",
            f'<Relationship Id="{_HEADER_REL_ID}" Type="{_HEADER_TYPE}" '
            f'Target="header_draft.xml"/></Relationships>',
        )
    if "/word/header_draft.xml" not in types:
        types = types.replace(
            "</Types>",
            f'<Override PartName="/word/header_draft.xml" ContentType="{_HEADER_CONTENT_TYPE}"/>'
            "</Types>",
        )
    return _rewrite_zip(
        data,
        {
            "word/document.xml": document.encode("utf-8"),
            "[Content_Types].xml": types.encode("utf-8"),
        }
        | ({_RELS_PART: rels.encode("utf-8")} if _RELS_PART in _names(data) else {}),
        {_HEADER_PART: _header_xml().encode("utf-8")}
        | ({} if _RELS_PART in _names(data) else {_RELS_PART: rels.encode("utf-8")}),
    )


def _names(data: bytes) -> set[str]:
    with zipfile.ZipFile(BytesIO(data)) as archive:
        return set(archive.namelist())


def _banner_cell(sheet_xml: str, prefix: str) -> str:
    """Prefix the first-row title cell with the banner (or add one if A1 is empty)."""
    text = escape(DRAFT_BANNER)
    cell = re.search(rf'<{prefix}c r="A1"([^>]*?)(?:/>|>(.*?)</{prefix}c>)', sheet_xml, flags=re.S)
    if cell is None:
        row = re.search(rf'<{prefix}row r="1"[^>]*?(/>|>)', sheet_xml)
        banner = (
            f'<{prefix}c r="A1" t="inlineStr"><{prefix}is><{prefix}t>{text}</{prefix}t>'
            f"</{prefix}is></{prefix}c>"
        )
        if row is None:
            return sheet_xml.replace(
                f"<{prefix}sheetData>",
                f'<{prefix}sheetData><{prefix}row r="1">{banner}</{prefix}row>',
                1,
            )
        if row.group(1) == "/>":
            return sheet_xml.replace(
                row.group(0), row.group(0)[:-2] + f">{banner}</{prefix}row>", 1
            )
        return sheet_xml.replace(row.group(0), row.group(0) + banner, 1)
    attributes, inner = cell.group(1), cell.group(2) or ""
    style = re.search(r'\ss="\d+"', attributes)
    keep = style.group(0) if style else ""
    existing = re.search(rf"<{prefix}(?:v|t)(?: [^>]*)?>(.*?)</{prefix}(?:v|t)>", inner, flags=re.S)
    original = existing.group(1) if existing else ""
    joined = f"{text} | {original}" if original else text
    replacement = (
        f'<{prefix}c r="A1"{keep} t="inlineStr"><{prefix}is>'
        f'<{prefix}t xml:space="preserve">{joined}</{prefix}t></{prefix}is></{prefix}c>'
    )
    return sheet_xml.replace(cell.group(0), replacement, 1)


def mark_xlsx(data: bytes) -> bytes:
    """Header on every sheet (``&CDRAFT``) and a banner in each sheet's first row."""
    changes: dict[str, bytes] = {}
    with zipfile.ZipFile(BytesIO(data)) as archive:
        for name in archive.namelist():
            if not re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name):
                continue
            xml = archive.read(name).decode("utf-8")
            prefix = "x:" if "<x:worksheet" in xml else ""
            header = (
                f"<{prefix}headerFooter><{prefix}oddHeader>"
                f"&amp;C{escape('DRAFT — NOT ISSUED')}"
                f"</{prefix}oddHeader></{prefix}headerFooter>"
            )
            margins = re.search(rf"<{prefix}pageMargins\b[^>]*/>", xml)
            setup = re.search(rf"<{prefix}pageSetup\b[^>]*/>", xml)
            anchor = setup or margins
            if anchor is not None:
                xml = xml.replace(anchor.group(0), anchor.group(0) + header, 1)
            else:
                xml = xml.replace(f"</{prefix}sheetData>", f"</{prefix}sheetData>" + header, 1)
            xml = _banner_cell(xml, prefix)
            changes[name] = xml.encode("utf-8")
    return _rewrite_zip(data, changes, {})
