from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import requests

from src.ingestion.loaders.loader_factory import LoaderFactory
from src.ingestion.loaders.pdf_loader import PDFLoader
from src.ingestion.loaders.url_loader import URLLoader


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"


class LoaderTests(unittest.TestCase):
    def test_loader_factory_detects_pdf_and_url_sources(self) -> None:
        self.assertEqual(LoaderFactory.detect_source_type("https://example.com/post"), "url")
        self.assertEqual(LoaderFactory.detect_source_type("report.pdf"), "pdf")

    def test_pdf_loader_normalizes_pages_into_document(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
            fake_reader = SimpleNamespace(
                pages=[
                    SimpleNamespace(extract_text=lambda: "First page text"),
                    SimpleNamespace(extract_text=lambda: "Second page text"),
                ],
                metadata=SimpleNamespace(title="Fixture PDF"),
            )
            with patch("src.ingestion.loaders.pdf_loader.PdfReader", return_value=fake_reader):
                document = PDFLoader().load(handle.name)

        self.assertEqual(document.source_type, "pdf")
        self.assertEqual(document.title, "Fixture PDF")
        self.assertIn("First page text", document.content)
        self.assertEqual(document.metadata["pages"][0]["page_number"], 1)
        self.assertEqual(len(document.metadata["sections"]), 2)

    def test_url_loader_extracts_readable_article_sections(self) -> None:
        html = (FIXTURE_DIR / "sample_blog.html").read_text(encoding="utf-8")
        response = Mock()
        response.text = html
        response.raise_for_status = Mock()

        with patch("src.ingestion.loaders.url_loader.requests.get", return_value=response):
            document = URLLoader().load("example.com/blog-post")

        self.assertEqual(document.source, "https://example.com/blog-post")
        self.assertEqual(document.title, "Sample Blog Post")
        self.assertIn("Hybrid retrieval combines semantic similarity", document.content)
        self.assertGreaterEqual(len(document.metadata["sections"]), 2)

    def test_url_loader_extracts_infobox_summary_facts(self) -> None:
        html = """
        <html>
          <head><title>Spider-Man</title></head>
          <body>
            <main>
              <table class="infobox">
                <tr><th>Publisher</th><td>Marvel Comics</td></tr>
                <tr><th>First appearance</th><td>Amazing Fantasy #15 (August 1962)</td></tr>
              </table>
              <h1>Spider-Man</h1>
              <p>Spider-Man is a superhero appearing in Marvel Comics.</p>
            </main>
          </body>
        </html>
        """
        response = Mock()
        response.text = html
        response.raise_for_status = Mock()

        with patch("src.ingestion.loaders.url_loader.requests.get", return_value=response):
            document = URLLoader().load("https://example.com/spider-man")

        self.assertIn("Publisher: Marvel Comics", document.content)
        self.assertIn("First appearance: Amazing Fantasy #15 (August 1962)", document.content)
        self.assertEqual(document.metadata["sections"][0]["title"], "Summary facts")

    def test_url_loader_prefers_content_rich_parser_output_block(self) -> None:
        html = """
        <html>
          <head><title>Spider-Man</title></head>
          <body>
            <main>
              <div class="mw-parser-output"><span><img src="poster.jpg" /></span></div>
              <div class="mw-parser-output"><div></div></div>
              <div class="mw-parser-output">
                <table class="infobox">
                  <tr><th>First appearance</th><td>Amazing Fantasy #15 (August 1962)</td></tr>
                </table>
                <div>
                  <p>Spider-Man is a superhero appearing in American comic books published by Marvel Comics.</p>
                  <h2>Publication history</h2>
                  <p>The character first appeared in Amazing Fantasy #15.</p>
                </div>
              </div>
            </main>
          </body>
        </html>
        """
        response = Mock()
        response.text = html
        response.raise_for_status = Mock()

        with patch("src.ingestion.loaders.url_loader.requests.get", return_value=response):
            document = URLLoader().load("https://example.com/spider-man")

        self.assertIn("Amazing Fantasy #15", document.content)
        self.assertIn("Marvel Comics", document.content)
        self.assertGreaterEqual(len(document.metadata["sections"]), 2)

    def test_url_loader_excludes_reference_style_sections(self) -> None:
        html = """
        <html>
          <head><title>Spider-Man</title></head>
          <body>
            <main>
              <div class="mw-parser-output">
                <p>Spider-Man is published by Marvel Comics.</p>
                <h2>Bibliography</h2>
                <p>Long publication lists that should not be indexed for factual QA.</p>
                <h2>References</h2>
                <p>[1] Reference content should not be indexed.</p>
              </div>
            </main>
          </body>
        </html>
        """
        response = Mock()
        response.text = html
        response.raise_for_status = Mock()

        with patch("src.ingestion.loaders.url_loader.requests.get", return_value=response):
            document = URLLoader().load("https://example.com/spider-man")

        titles = [section["title"] for section in document.metadata["sections"]]
        self.assertNotIn("Bibliography", titles)
        self.assertNotIn("References", titles)

    def test_url_loader_wraps_request_failures_with_user_readable_message(self) -> None:
        with patch("src.ingestion.loaders.url_loader.requests.get", side_effect=requests.RequestException("dns failure")):
            with self.assertRaisesRegex(ValueError, "Failed to fetch URL"):
                URLLoader().load("https://example.com/unreachable")


if __name__ == "__main__":
    unittest.main()
