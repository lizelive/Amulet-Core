from __future__ import annotations

from .anvil_1908 import (
    Anvil1908Interface,
)
from amulet.api.chunk import StatusFormats


class Anvil1912Interface(Anvil1908Interface):
    def __init__(self):
        super().__init__()
        self._set_feature("status", StatusFormats.Java_14)

    @staticmethod
    def minor_is_valid(key: int):
        return 1912 <= key < 1934


export = Anvil1912Interface
