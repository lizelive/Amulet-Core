from __future__ import annotations

from .anvil_1467 import (
    Anvil1467Interface,
)


class Anvil1484Interface(Anvil1467Interface):
    def __init__(self):
        super().__init__()
        self._set_feature("height_map", "C|V2")

    @staticmethod
    def minor_is_valid(key: int):
        return 1484 <= key < 1503


export = Anvil1484Interface
