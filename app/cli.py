"""
CLI for Content Accessibility Suite.

Usage:
    python -m app.cli ingest <file_path>
    python -m app.cli process <file_id>
    python -m app.cli search "query" [--file-id <file_id>]
    python -m app.cli ask "question" [--file-id <file_id>]
    python -m app.cli compare <file_id>
"""

from __future__ import annotations

import sys
import textwrap

import click

from app.config.settings import settings
from app.utils.exceptions import format_user_error

settings.configure_logging()

# Make CLI output robust on Windows cp1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")

from app.controllers.file_controller import FileController  # noqa: E402

_SEP = "-" * 56


def _render_answer(answer_result) -> None:
    """Render answer text plus the exact supporting chunks used."""
    click.echo("")
    if answer_result.insufficient_evidence:
        click.echo(
            click.style(
                "WARNING: Insufficient evidence in the provided context.",
                fg="yellow",
                bold=True,
            )
        )
    else:
        click.echo(click.style("OK: Answer", fg="green", bold=True))
    click.echo(_SEP)
    click.echo(textwrap.fill(f"  {answer_result.answer}", width=72))

    if answer_result.confidence_notes:
        click.echo("")
        click.echo(click.style(f"  Note: {answer_result.confidence_notes}", fg="yellow"))

    if answer_result.supporting_chunks:
        click.echo("")
        click.echo(click.style("  Supporting chunks used:", bold=True))
        for i, chunk in enumerate(answer_result.supporting_chunks, 1):
            conf_color = "green" if chunk.confidence >= 0.7 else ("yellow" if chunk.confidence >= 0.4 else "red")
            preview = chunk.chunk_text[:260].replace("\n", " ")
            click.echo(
                f"    [{i}] Chunk #{chunk.chunk_index}  "
                f"score={chunk.score:.4f}  "
                f"confidence={click.style(f'{chunk.confidence:.2f}', fg=conf_color)}"
            )
            source_file = chunk.file_name or chunk.source_metadata.get("file_name", "")
            pages = chunk.source_metadata.get("pages") or chunk.source_metadata.get("page")
            if source_file:
                click.echo(f"        Source file: {source_file}")
            if pages:
                click.echo(f"        Source page(s): {pages}")
            click.echo(textwrap.fill(f"        {preview}...", width=72, subsequent_indent="        "))
    else:
        click.echo("")
        click.echo("  Supporting chunks used: none")
    click.echo(_SEP)
    click.echo("")


@click.group()
@click.version_option(version="0.3.0", prog_name="cas")
def cli() -> None:
    """Content Accessibility Suite - CLI interface."""


@cli.command("ingest")
@click.argument("file_path", type=click.Path(exists=True, readable=True))
def ingest_command(file_path: str) -> None:
    """Validate and ingest a single file."""
    controller = FileController()
    try:
        meta = controller.ingest_file(file_path)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Ingestion failed')}", fg="red"), err=True)
        sys.exit(1)

    click.echo("")
    click.echo(click.style("OK: File ingested successfully", fg="green", bold=True))
    click.echo(_SEP)
    click.echo(f"  File ID      : {meta.file_id}")
    click.echo(f"  Original name: {meta.original_name}")
    click.echo(f"  File type    : {meta.file_type.value}")
    click.echo(f"  MIME type    : {meta.mime_type}")
    click.echo(f"  Size         : {meta.size_bytes:,} bytes")
    click.echo(f"  Stored path  : {meta.stored_path}")
    click.echo(f"  Status       : {meta.status.value}")
    click.echo(f"  Created at   : {meta.created_at.isoformat()}")
    click.echo(_SEP)
    click.echo(f"\nNext step -> python -m app.cli process {meta.file_id}")
    click.echo("")


@cli.command("process")
@click.argument("file_id")
def process_command(file_id: str) -> None:
    """Run extraction and post-processing for an ingested file."""
    from app.controllers.processing_controller import ProcessingController

    controller = ProcessingController()
    click.echo(f"\nProcessing file: {file_id} ...")

    try:
        result = controller.process_file(file_id)
    except ValueError as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Processing failed')}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Processing failed')}", fg="red"), err=True)
        sys.exit(1)

    extraction = result.extraction
    conf = extraction.confidence if extraction else 0.0
    method = extraction.method.value if extraction else "unknown"
    warnings = extraction.warnings if extraction else []

    click.echo("")
    click.echo(click.style("OK: Processing complete", fg="green", bold=True))
    click.echo(_SEP)
    click.echo(f"  Extraction method : {method}")
    conf_color = "green" if conf >= 0.7 else ("yellow" if conf >= 0.4 else "red")
    click.echo(f"  Confidence        : {click.style(f'{conf:.2f}', fg=conf_color)}")
    click.echo(f"  Latency           : {result.latency_ms} ms")

    if warnings:
        click.echo("")
        click.echo(click.style("  Warnings:", fg="yellow"))
        for w in warnings:
            click.echo(f"    - {w}")

    click.echo("")
    click.echo(click.style("  Extracted text preview:", bold=True))
    preview = result.cleaned_text[:500].replace("\n", " ")
    click.echo(textwrap.fill(f"    {preview}...", width=72))

    click.echo("")
    click.echo(click.style("  Summary:", bold=True))
    click.echo(textwrap.fill(f"    {result.summary}", width=72))

    click.echo("")
    click.echo(click.style("  Key points:", bold=True))
    for i, point in enumerate(result.key_points, 1):
        click.echo(textwrap.fill(f"    {i}. {point}", width=72, subsequent_indent="       "))

    click.echo("")
    click.echo(click.style("  Topic tags:", bold=True))
    click.echo(f"    {', '.join(result.topic_tags)}")

    click.echo(_SEP)
    click.echo(f"\nNext step -> python -m app.cli query \"your question\"")
    click.echo("")


@cli.command("search")
@click.argument("query")
@click.option("--file-id", default=None, help="Optional: restrict search to one file ID.")
@click.option("--top-k", default=5, show_default=True, help="Number of results to return.")
def search_command(query: str, file_id: str | None, top_k: int) -> None:
    """Semantic search over all processed files (or one file when --file-id is set)."""
    from app.controllers.search_controller import SearchController

    controller = SearchController()
    scope = f"file {file_id}" if file_id else "all processed files"
    click.echo(f"\nSearching '{query}' in {scope} ...")

    try:
        results = controller.search(file_id=file_id, query=query, top_k=top_k)
    except ValueError as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Search failed')}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Search failed')}", fg="red"), err=True)
        sys.exit(1)

    if not results:
        click.echo(click.style("\n  No relevant chunks found.", fg="yellow"))
        sys.exit(0)

    click.echo("")
    click.echo(click.style(f"OK: Top {len(results)} result(s)", fg="green", bold=True))
    click.echo(_SEP)
    for i, r in enumerate(results, 1):
        conf_color = "green" if r.confidence >= 0.7 else ("yellow" if r.confidence >= 0.4 else "red")
        click.echo(
            f"  [{i}] Score: {r.score:.4f}  Chunk #{r.chunk_index}  "
            f"Confidence: {click.style(f'{r.confidence:.2f}', fg=conf_color)}"
        )
        preview = r.chunk_text[:300].replace("\n", " ")
        click.echo(textwrap.fill(f"      {preview}", width=72, subsequent_indent="      "))
        source_file = r.file_name or r.source_metadata.get("file_name", "")
        pages = r.source_metadata.get("pages") or r.source_metadata.get("page")
        if source_file:
            click.echo(f"      Source file: {source_file}")
        if pages:
            click.echo(f"      Source page(s): {pages}")
        click.echo(f"      Source metadata: {r.source_metadata}")
        click.echo("")

    click.echo(_SEP)
    if file_id:
        click.echo(f"\nNext step -> python -m app.cli query \"your question\" --file-id {file_id}")
    else:
        click.echo(f"\nNext step -> python -m app.cli query \"your question\"")
    click.echo("")


@cli.command("ask")
@click.argument("question")
@click.option("--file-id", default=None, help="Optional: restrict Q&A to one file ID.")
@click.option("--top-k", default=5, show_default=True, help="Context chunks to retrieve.")
def ask_command(question: str, file_id: str | None, top_k: int) -> None:
    """Grounded Q&A over all processed files (or one file when --file-id is set)."""
    from app.controllers.search_controller import SearchController

    controller = SearchController()
    scope = f"file {file_id}" if file_id else "all processed files"
    click.echo(f"\nAnswering from {scope}: '{question}' ...")

    try:
        answer_result = controller.answer(file_id=file_id, question=question, top_k=top_k)
    except ValueError as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Q&A failed')}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Q&A failed')}", fg="red"), err=True)
        sys.exit(1)

    _render_answer(answer_result)


@cli.command("query")
@click.argument("question")
@click.option("--file-id", default=None, help="Optional: restrict query to one file ID.")
@click.option("--top-k", default=5, show_default=True, help="Context chunks to retrieve.")
def query_command(question: str, file_id: str | None, top_k: int) -> None:
    """
    Alias for grounded Q&A over all processed files.

    This command exists to match the final app flow terminology: query documents -> answer with supporting chunks.
    """
    from app.controllers.search_controller import SearchController

    controller = SearchController()
    scope = f"file {file_id}" if file_id else "all processed files"
    click.echo(f"\nQuery on {scope}: '{question}' ...")

    try:
        answer_result = controller.answer(file_id=file_id, question=question, top_k=top_k)
    except ValueError as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Query failed')}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Query failed')}", fg="red"), err=True)
        sys.exit(1)

    _render_answer(answer_result)


@cli.command("compare")
@click.argument("file_id")
def compare_command(file_id: str) -> None:
    """Run model comparison for a processed file."""
    from app.controllers.comparison_controller import ComparisonController

    controller = ComparisonController()
    click.echo(f"\nRunning model comparison for file {file_id} ...")

    try:
        report = controller.compare(file_id)
    except ValueError as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Comparison failed')}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"\nERROR: {format_user_error(exc, prefix='Comparison failed')}", fg="red"), err=True)
        sys.exit(1)

    click.echo("")
    click.echo(click.style("OK: Model Comparison Report", fg="green", bold=True))
    click.echo(_SEP)

    for model_result in report.model_results:
        status_color = "green" if model_result.get("status") == "success" else "red"
        click.echo(
            f"  [{click.style(model_result.get('status', 'unknown'), fg=status_color)}] "
            f"{model_result.get('provider', '?')} / {model_result.get('model_name', '?')}"
        )
        click.echo(f"    Stage      : {model_result.get('stage', '?')}")
        click.echo(f"    Latency    : {model_result.get('latency_ms', 0)} ms")
        click.echo(f"    Est. cost  : ${model_result.get('estimated_cost', 0.0):.5f}")
        if model_result.get("quality_notes"):
            click.echo(f"    Quality    : {model_result['quality_notes']}")
        if model_result.get("error_message"):
            click.echo(click.style(f"    Error      : {model_result['error_message']}", fg="red"))
        click.echo("")

    if report.metric_summary:
        click.echo(click.style("  Summary:", bold=True))
        for k, v in report.metric_summary.items():
            click.echo(f"    {k}: {v}")
        click.echo("")

    if report.observations:
        click.echo(click.style("  Observations:", bold=True))
        click.echo(textwrap.fill(f"    {report.observations}", width=72))
        click.echo("")

    click.echo(_SEP)
    click.echo("")


if __name__ == "__main__":
    cli()
