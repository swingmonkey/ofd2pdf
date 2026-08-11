"""Allow `python -m ofd2pdf`."""

import sys

from ofd2pdf.cli import main

if __name__ == "__main__":
    sys.exit(main())
