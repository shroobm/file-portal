"""WHAT THIS FILE DOES: the command-line entry of the indexer. main() reads --root, --config and
--rebuild; run() creates the working directories, sets up logging to <logs>/indexer.log and to
the console, loads the settings file and calls reconcile(). Its return value becomes the
process exit code. Run by the systemd unit, the vault hook and the daily timer.

Entry point of the oneshot unit (file-portal-indexer.service, fired by the vault's
post-update hook and by the daily timer): parse arguments, configure logging the way the
converter's run() does, reconcile once, exit with the reconcile's code -- 0 done, 1 the work
failed or a bundle was refused (receipt written first), 2 the vault is missing (receipt
written first). `--rebuild` is the ONLY way the index is ever emptied and re-embedded."""

import argparse
import logging
import sys
from pathlib import Path

from indexer.config import DEFAULT_ROOT, Paths, Settings
from indexer.reconcile import reconcile


# -- one reconcile run --
def run(root: Path, config: Path, rebuild: bool = False) -> int:
    """Prepare directories and logging under `root`, load settings from `config`, and run one
    reconcile (emptying the index first when `rebuild`). Returns reconcile's exit code.
    Side effects: creates directories, configures global logging, writes indexer.log."""
    paths = Paths.from_root(root)
    paths.ensure_exist()
    # Log to a file and, via the extra handler, to the console as well.
    logging.basicConfig(
        filename=paths.logs / "indexer.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    return reconcile(root, Settings.load(config), rebuild=rebuild)


# -- command-line entry --
def main() -> None:
    """CLI entry: parse --root, --config, --rebuild, call run() and exit with its code."""
    parser = argparse.ArgumentParser(description="File Portal indexer (reconcile once)")
    parser.add_argument(
        "--root", type=Path, default=DEFAULT_ROOT, help="file-portal root directory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config" / "indexer.toml",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="empty the index first and re-embed every bundle from the vault",
    )
    args = parser.parse_args()
    sys.exit(run(args.root, args.config, rebuild=args.rebuild))


if __name__ == "__main__":
    main()
