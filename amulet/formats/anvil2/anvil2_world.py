from __future__ import annotations

import struct
import zlib
from io import BytesIO
from typing import List, Tuple, Union
from collections import defaultdict

import numpy

from amulet.api import WorldFormat
from math import log, ceil
from nbt import nbt
from os import path

from amulet.api.world import World
from amulet.api.block import Block
from amulet.api import nbt_template
from amulet.utils.world_utils import get_smallest_dtype

from amulet.utils import world_utils


class _Anvil2RegionManager:
    def __init__(self, directory: str):
        self._directory = directory
        self._loaded_regions = {}

    def load_chunk(
        self, cx: int, cz: int
    ) -> Tuple[nbt.TAG_List, nbt.TAG_List, nbt.TAG_List]:
        rx, rz = world_utils.chunk_coords_to_region_coords(cx, cz)
        key = (rx, rz)

        if not self.load_region(rx, rz):
            raise Exception()

        cx &= 0x1F
        cz &= 0x1F

        chunk_offset = self._loaded_regions[key]["offsets"][
            (cx & 0x1F) + (cz & 0x1F) * 32
        ]
        if chunk_offset == 0:
            raise Exception()

        sector_start = chunk_offset >> 8
        number_of_sectors = chunk_offset & 0xFF

        if number_of_sectors == 0:
            raise Exception()

        if sector_start + number_of_sectors > len(
            self._loaded_regions[key]["free_sectors"]
        ):
            raise Exception()

        with open(
            path.join(self._directory, "region", "r.{}.{}.mca".format(rx, rz)), "rb"
        ) as fp:
            fp.seek(sector_start * world_utils.SECTOR_BYTES)
            data = fp.read(number_of_sectors * world_utils.SECTOR_BYTES)

        if len(data) < 5:
            raise Exception("Malformed sector/chunk")

        length = struct.unpack_from(">I", data)[0]
        _format = struct.unpack_from("B", data, 4)[0]
        data = data[5 : length + 5]

        if _format == world_utils.VERSION_GZIP:
            data = world_utils.gunzip(data)
        elif _format == world_utils.VERSION_DEFLATE:
            data = zlib.decompress(data)

        nbt_data = nbt.NBTFile(buffer=BytesIO(data))

        return (
            nbt_data["Level"]["Sections"],
            nbt_data["Level"]["TileEntities"],
            nbt_data["Level"]["Entities"],
        )

    def load_region(self, rx: int, rz: int) -> bool:
        key = (rx, rz)
        if key in self._loaded_regions:
            return True

        filename = path.join(self._directory, "region", "r.{}.{}.mca".format(rx, rz))
        if not path.exists(filename):
            raise FileNotFoundError()

        fp = open(filename, "rb")
        self._loaded_regions[key] = {}

        file_size = path.getsize(filename)
        if file_size & 0xFFF:
            file_size = (file_size | 0xFFF) + 1
            fp.truncate(file_size)

        if not file_size:
            file_size = world_utils.SECTOR_BYTES * 2
            fp.truncate(file_size)

        self._loaded_regions[key]["file_size"] = file_size

        fp.seek(0)

        offsets = fp.read(world_utils.SECTOR_BYTES)
        mod_times = fp.read(world_utils.SECTOR_BYTES)

        self._loaded_regions[key]["free_sectors"] = free_sectors = numpy.full(
            file_size // world_utils.SECTOR_BYTES, True, bool
        )
        self._loaded_regions[key]["free_sectors"][0:2] = False, False

        self._loaded_regions[key]["offsets"] = offsets = numpy.frombuffer(
            offsets, dtype=">u4"
        )
        self._loaded_regions[key]["mod_times"] = numpy.frombuffer(
            mod_times, dtype=">u4"
        )

        for offset in offsets:
            sector = offset >> 8
            count = offset & 0xFF

            for i in range(sector, sector + count):
                if i >= len(free_sectors):
                    return False

                free_sectors[i] = False

        fp.close()

        return True


def _decode_long_array(long_array: array_like, size: int) -> numpy.ndarray:
    """
    Decode an long array (from BlockStates or Heightmaps)
    :param long_array: Encoded long array
    :size uint: The expected size of the returned array
    :return: Decoded array as numpy array
    """
    long_array = numpy.array(long_array, dtype=">q")
    bits_per_block = (len(long_array) * 64) // size
    binary_blocks = numpy.unpackbits(
        long_array[::-1].astype(">i8").view("uint8")
    ).reshape(-1, bits_per_block)
    return binary_blocks.dot(2 ** numpy.arange(binary_blocks.shape[1] - 1, -1, -1))[
        ::-1  # Undo the bit-shifting that Minecraft does with the palette indices
    ][:size]


def _encode_long_array(data_array: array_like, palette_size: int) -> numpy.ndarray:
    """
    Encode an array of data to a long array (from BlockStates or Heightmaps).
    :param data_array: Data to encode
    :palette_size uint: Must be at least 4
    :return: Encoded array as numpy array
    """
    data_array = numpy.array(data_array, dtype=">i2")
    bits_per_block = max(4, int(ceil(log(palette_size, 2))))
    binary_blocks = (
        numpy.unpackbits(data_array.astype(">i2").view("uint8"))
        .reshape(-1, 16)[:, (16 - bits_per_block) :][::-1]
        .reshape(-1)
    )
    binary_blocks = numpy.pad(
        binary_blocks, ((64 - (len(data_array) * bits_per_block)) % 64, 0), "constant"
    ).reshape(-1, 64)
    return binary_blocks.dot(
        2 ** numpy.arange(binary_blocks.shape[1] - 1, -1, -1, dtype=">q")
    )[::-1]


class Anvil2World(WorldFormat):
    def __init__(
        self,
        directory: str,
        definitions: str,
        get_blockstate_adapter=None,
        entity_handlers=None,
    ):
        super(Anvil2World, self).__init__(
            directory, definitions, get_blockstate_adapter=get_blockstate_adapter
        )
        self._region_manager = _Anvil2RegionManager(directory)
        self._entity_handlers = (
            entity_handlers
            if entity_handlers
            else defaultdict(nbt_template.EntityHandler)
        )

    @classmethod
    def load(
        cls, directory: str, definitions: str, get_blockstate_adapter=None
    ) -> World:
        wrapper = cls(
            directory, definitions, get_blockstate_adapter=get_blockstate_adapter
        )
        fp = open(path.join(directory, "level.dat"), "rb")
        root_tag = nbt.NBTFile(fileobj=fp)
        fp.close()

        return World(directory, root_tag, wrapper)

    def _read_palette(self, palette: nbt.TAG_List) -> list:
        blockstates = []
        for entry in palette:
            name = entry["Name"].value
            properties = self._materials.properties_to_string(
                entry.get("Properties", {})
            )
            if properties:
                blockstates.append(f"{name}[{properties}]")
            else:
                blockstates.append(name)
        return blockstates

    def translate_entities(self, entities: list) -> List[nbt_template.NBTCompoundEntry]:
        entity_list = []
        for entity in entities:
            entity = nbt_template.create_entry_from_nbt(entity)
            entity = self._entity_handlers[entity["id"].value].load_entity(entity)
            entity_list.append(entity)

        return entity_list

    def translate_blocks(
        self, chunk_sections
    ) -> Union[numpy.ndarray, NotImplementedError]:
        if len(chunk_sections) == 0:
            return NotImplementedError(
                "We don't support reading chunks that never been edited in Minecraft before"
            )

        blocks = numpy.zeros((256, 16, 16), dtype=int)
        palette = ["minecraft:air"]

        for section in chunk_sections:
            height = section["Y"].value << 4

            blocks[height : height + 16, :, :] = _decode_long_array(
                section["BlockStates"].value, 4096
            ).reshape((16, 16, 16)) + len(palette)

            palette += self._read_palette(section["Palette"])

        blocks = numpy.swapaxes(blocks.swapaxes(0, 1), 0, 2)
        palette, inverse = numpy.unique(palette, return_inverse=True)
        palette_internal_ids = numpy.array(
            [
                self.block_manager.get_add_block(
                    self.get_blockstate(
                        self._materials.get_block_from_definition(
                            unique, default=unique
                        )
                    )
                )
                for unique in palette
            ],
            dtype=int,
        )

        blocks = palette_internal_ids[inverse[blocks]]

        return blocks.astype(f"uint{get_smallest_dtype(blocks)}")

    @classmethod
    def from_unified_format(cls, unified: World) -> WorldFormat:
        pass

    def save(self) -> None:
        pass


LEVEL_CLASS = Anvil2World
