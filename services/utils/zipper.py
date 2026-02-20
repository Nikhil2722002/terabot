"""
ZIP Archive Creator
- Compresses a list of files into a single ZIP
- Deletes originals after they are added
"""

import zipfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_zip(files: list[Path], output_path: Path) -> Path:
    """
    Create a ZIP archive from *files* at *output_path*.
    Original files are deleted after being added to the archive.
    Returns the output path.
    """
    logger.info(f"Creating ZIP with {len(files)} file(s) → {output_path.name}")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in files:
            if fp.exists():
                zf.write(fp, fp.name)
                logger.debug(f"  Added: {fp.name}")
            else:
                logger.warning(f"  Missing, skipped: {fp}")

    # Remove originals
    for fp in files:
        try:
            fp.unlink(missing_ok=True)
        except Exception as exc:
            logger.error(f"Could not delete {fp}: {exc}")

    size = output_path.stat().st_size
    logger.info(f"ZIP created: {output_path.name} ({size:,} bytes)")
    return output_path
