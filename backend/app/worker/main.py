import logging
import sys

from arq import run_worker

from app.worker.settings import WorkerSettings


def main() -> None:
    logging.basicConfig(level="INFO", stream=sys.stdout)
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
