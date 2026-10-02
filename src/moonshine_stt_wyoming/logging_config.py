import logging


def configure(level):
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s", force=True)
    for name in ("moonshine_voice", "urllib3", "requests", "wyoming"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
