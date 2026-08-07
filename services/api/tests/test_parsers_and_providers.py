from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vikram_api.providers.fake import DeterministicEmbeddingProvider
from vikram_api.providers.interfaces import LocalBlobStorage
from vikram_api.providers.parsers import MarkdownParser, PdfParser


def minimal_text_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode() + item + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(document)


def test_markdown_parser_preserves_heading_and_lines() -> None:
    parsed = MarkdownParser().parse(
        b"# Control loop\nPhase margin improves stability.\n\n## Check\nMeasure crossover."
    )
    assert [item.locator["heading"] for item in parsed] == ["Control loop", "Check"]
    assert parsed[0].locator["line_start"] == 1
    assert parsed[1].locator["line_end"] == 5


def test_pdf_parser_preserves_one_based_page() -> None:
    parsed = PdfParser().parse(minimal_text_pdf("Phase margin improves stability."))
    assert len(parsed) == 1
    assert parsed[0].locator == {"kind": "pdf_page", "page": 1}
    assert "Phase margin" in parsed[0].content


def test_fake_embeddings_are_deterministic() -> None:
    provider = DeterministicEmbeddingProvider()
    first = provider.embed("phase margin", 1)
    second = provider.embed("phase margin", 1)
    assert first == second
    assert len(first) == provider.dimensions


def test_content_addressed_storage_handles_parallel_identical_writes(tmp_path: Path) -> None:
    storage = LocalBlobStorage(tmp_path / "blobs")
    content = b"private engineering evidence"
    with ThreadPoolExecutor(max_workers=4) as executor:
        keys = list(executor.map(lambda _: storage.put(content, 1), range(8)))
    assert len(set(keys)) == 1
    assert storage.read(keys[0], 1) == content
    assert list((tmp_path / "blobs").rglob("*.tmp")) == []
