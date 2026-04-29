"""Allows `python -m app` to be an alias for the CLI."""
from app.cli import cli

if __name__ == "__main__":
    cli()
