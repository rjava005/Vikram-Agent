from __future__ import annotations

import io
import re

from pypdf import PdfReader

from vikram_api.domain.models import ParsedEvidence, UnprocessableSourceError

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


class MarkdownParser:
    parser_id = "markdown-sections-v1"

    def parse(self, content: bytes) -> list[ParsedEvidence]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise UnprocessableSourceError("Markdown must be valid UTF-8.") from error
        lines = text.splitlines()
        sections: list[ParsedEvidence] = []
        heading = "Document"
        section_start = 1
        buffer: list[str] = []

        def flush(line_end: int) -> None:
            body = "\n".join(buffer).strip()
            if body:
                sections.append(
                    ParsedEvidence(
                        ordinal=len(sections),
                        content=body,
                        locator_kind="markdown_section",
                        locator={
                            "kind": "markdown_section",
                            "heading": heading,
                            "line_start": section_start,
                            "line_end": max(line_end, section_start),
                        },
                    )
                )

        for line_number, line in enumerate(lines, start=1):
            match = HEADING_RE.match(line)
            if match:
                flush(line_number - 1)
                heading = match.group(2).strip()
                section_start = line_number
                buffer = []
            else:
                buffer.append(line)
        flush(len(lines))
        if not sections:
            raise UnprocessableSourceError("The Markdown source contains no extractable text.")
        return sections


class PdfParser:
    parser_id = "pypdf-pages-v1"

    def parse(self, content: bytes) -> list[ParsedEvidence]:
        try:
            reader = PdfReader(io.BytesIO(content))
            pages: list[ParsedEvidence] = []
            for page_number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append(
                        ParsedEvidence(
                            ordinal=len(pages),
                            content=text,
                            locator_kind="pdf_page",
                            locator={"kind": "pdf_page", "page": page_number},
                        )
                    )
        except Exception as error:
            raise UnprocessableSourceError("The PDF could not be parsed safely.") from error
        if not pages:
            raise UnprocessableSourceError(
                "The PDF contains no extractable text. Scanned-PDF OCR is not available yet."
            )
        return pages
