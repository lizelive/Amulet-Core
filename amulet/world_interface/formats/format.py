from __future__ import annotations

from typing import Tuple, Any

from ...api.block import BlockManager
from ...api.chunk import Chunk
from .. import interface_loader
from .. import translator_loader


class Format:
    def __init__(self, directory: str):
        self._directory = directory

    def load_chunk(
        self, cx: int, cz: int, palette: BlockManager, recurse: bool = True
    ) -> Chunk:
        """
        Loads and creates a universal amulet.api.chunk.Chunk object from chunk coordinates.

        :param cx: The x coordinate of the chunk.
        :param cz: The z coordinate of the chunk.
        :return: The chunk at the given coordinates.
        """

        # TODO: comment what is going on here. It is a bit abstract
        interface_key, interface_data = self._get_interface(cx, cz)
        interface_id = interface_loader.identify(interface_key)
        interface = interface_loader.get_interface(interface_id)

        chunk, chunk_palette = interface.decode(interface_data)
        translator_key = interface.get_translator(interface_data)
        translator_id = translator_loader.identify(translator_key)

        if recurse:
            def callback(x, z):
                palette = BlockManager()
                chunk = self.load_chunk(cx + x, cz + z, palette, False)
                return chunk, palette

        else:
            callback = None
        chunk, chunk_palette = translator_loader.get_translator(
            translator_id
        ).to_universal(chunk, chunk_palette, callback)

        for block, index in chunk_palette._block_to_index_map.items():
            chunk._blocks[chunk._blocks == index] = palette.get_add_block(block)
        return chunk

    def save_chunk(self, chunk: Chunk, palette: BlockManager, interface_id: str, translator_id: str):
        """
        Saves a universal amulet.api.chunk.Chunk object using the given interface and translator.

        TODO: This changes the chunk and palette to only include blocks used in the chunk, translates them with the translator,
        and then calls the interface passing in the translator. It then calls _put_encoded to store the data returned by the interface

        The passed ids will be send to interface_loader.get_interface, *not* .identify.
        """
        raise NotImplementedError()

    def _put_interface(self, cx: int, cz: int, data: Any):
        """
        Actually stores the data from the interface to disk.
        """
        raise NotImplementedError()

    def _get_interface(self, cx: int, cz: int) -> Tuple[Tuple, Any]:
        """
        Return the interface key and data to interface with given chunk coordinates.

        :param cx: The x coordinate of the chunk.
        :param cz: The z coordinate of the chunk.
        :return: The interface key for the identify method and the data to interface with.
        """
        raise NotImplementedError()

    @staticmethod
    def identify(directory: str) -> bool:
        """
        Returns whether this format is able to load a given world.

        :param directory: The path to the root of the world to load.
        :return: True if the world can be loaded by this format, False otherwise.
        """
        raise NotImplementedError()
