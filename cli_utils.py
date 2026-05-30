import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from pathlib import Path
from urllib.parse import urlparse


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def make_parser(pos_name, pos_help, description=None):
    parser = ArgumentParser(description=description or "", formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(pos_name, help=pos_help)
    return parser


def safe_filename(url, max_len=50):
    parsed = urlparse(url)
    netloc = parsed.netloc or "unknown"
    return netloc.replace(".", "_")[:max_len]


def ensure_output_dir(name):
    dir_path = Path(name)
    dir_path.mkdir(exist_ok=True)
    return dir_path
