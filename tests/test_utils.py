import sys
import os
import time
import shutil
from typing import Optional
from contextlib import contextmanager

TESTS_DIR = os.path.dirname(__file__)


def get_world_path(name: str) -> str:
    return os.path.join(TESTS_DIR, "worlds_src", name)


def get_temp_world_path(name: str) -> str:
    return os.path.join(TESTS_DIR, "worlds_temp", name)


def get_data_path(name: str) -> str:
    return os.path.join(TESTS_DIR, "data", name)


def clean_path(path: str):
    """Clean a given path removing all data at that path."""
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.isfile(path):
        os.remove(path)


def clean_temp_world(temp_world_name: str) -> str:
    """Remove the temporary world."""
    dst_path = get_temp_world_path(temp_world_name)
    clean_path(dst_path)
    return dst_path


def create_temp_world(
    src_world_name: str, temp_world_name: Optional[str] = None
) -> str:
    """Copy the world to a temporary location and return this path.

    :param src_world_name: The name of a world in ./worlds_src
    :param temp_world_name: Optional temporary name. Leave as None to auto to the same as src
    :return: The full path to a copy of the world
    """
    src_path = get_world_path(src_world_name)
    if temp_world_name is None:
        temp_world_name = src_world_name
    dst_path = clean_temp_world(temp_world_name)

    shutil.copytree(src_path, dst_path)
    return dst_path


@contextmanager
def timeout(test_instance, time_constraint: float, show_completion_time=False):
    start = time.time()
    yield

    end = time.time()
    delta = end - start
    if delta > time_constraint:
        test_instance.fail(
            f"Test execution didn't meet desired run time of {time_constraint}, ran in {delta} instead"
        )
    elif show_completion_time:
        print(
            f"Test ran in {delta} seconds, was required to run in {time_constraint} seconds",
            file=sys.stderr,
        )
