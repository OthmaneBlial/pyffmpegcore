"""
Module entrypoint for ``python -m pyffmpegcore``.
"""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
