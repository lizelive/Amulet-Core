from __future__ import annotations

import glob
import importlib
import json
import os
import numpy
from typing import Tuple, AbstractSet, Dict, Any

from amulet.api.errors import InterfaceLoaderNoneMatched
from ...api.chunk import Chunk
import amulet_nbt as nbt

_loaded_interfaces: Dict[str, Interface] = {}
_has_loaded_interfaces = False

SUPPORTED_INTERFACE_VERSION = 0
SUPPORTED_META_VERSION = 0

INTERFACES_DIRECTORY = os.path.dirname(__file__)


def _find_interfaces():
    """Load all interfaces from the interfaces directory"""
    global _has_loaded_interfaces

    directories = glob.iglob(os.path.join(INTERFACES_DIRECTORY, "*", ""))
    for d in directories:
        meta_path = os.path.join(d, "interface.meta")
        if not os.path.exists(meta_path):
            continue

        with open(meta_path) as fp:
            interface_info = json.load(fp)

        if interface_info["meta_version"] != SUPPORTED_META_VERSION:
            print(
                f'[Error] Couldn\'t enable interface located in "{d}" due to unsupported meta version'
            )
            continue

        if interface_info["interface"]["interface_version"] != SUPPORTED_INTERFACE_VERSION:
            print(
                f"[Error] Couldn't enable interface \"{interface_info['interface']['id']}\" due to unsupported interface version"
            )
            continue

        spec = importlib.util.spec_from_file_location(
            interface_info["interface"]["entry_point"],
            os.path.join(d, interface_info["interface"]["entry_point"] + ".py"),
        )
        modu = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modu)

        if not hasattr(modu, "INTERFACE_CLASS"):
            print(
                f"[Error] Interface \"{interface_info['interface']['id']}\" is missing the INTERFACE_CLASS attribute"
            )
            continue

        _loaded_interfaces[interface_info["interface"]["id"]] = modu.INTERFACE_CLASS()

        if __debug__:
            print(
                f"[Debug] Enabled interface \"{interface_info['interface']['id']}\", version {interface_info['interface']['wrapper_version']}"
            )

    _has_loaded_interfaces = True


def reload():
    """Reloads all interfaces"""
    _loaded_interfaces.clear()
    _find_interfaces()


def get_all_loaded_interfaces() -> AbstractSet[str]:
    """
    :return: The identifiers of all loaded interfaces
    """
    if not _has_loaded_interfaces:
        _find_interfaces()
    return _loaded_interfaces.keys()


def get_interface(identifier: Tuple) -> Interface:
    """
    Given an ``identifier`` will find a valid interface class and return it
    ("anvil", 1519)

    :param identifier: The identifier for the desired loaded interface
    :return: The class for the interface
    """
    interface_id = _identify(identifier)
    return _loaded_interfaces[interface_id]


def _identify(identifier: Tuple) -> str:

    if not _has_loaded_interfaces:
        _find_interfaces()

    for interface_name, interface_instance in _loaded_interfaces.items():
        if interface_instance.is_valid(identifier):
            return interface_name

    raise InterfaceLoaderNoneMatched("Could not find a matching interface")


class Interface:
    def decode(self, data: Any) -> Tuple[Chunk, numpy.ndarray]:
        """
        Create an amulet.api.chunk.Chunk object from raw data given by the format.

        :param data: Raw chunk data provided by the format.
        :return: Chunk object that matches the data, along with the palette for that chunk.
        """
        raise NotImplementedError()

    def encode(self, chunk: Chunk, palette: numpy.ndarray) -> nbt.NBTFile:
        """
        Create raw data for the format to store given a translated chunk.

        :param chunk: The version-specific chunk to encode.
        :param palette: The palette the ids in the chunk correspond to.
        :return: Raw data to be stored by the format.
        """
        raise NotImplementedError()

    def get_translator(self, data: Any) -> Tuple:
        """
        Return the translator key given chunk coordinates.

        :param data: The data passed in to translate.
        :return: The translator key for the identify method.
        """
        raise NotImplementedError()

    @staticmethod
    def is_valid(key: Tuple) -> bool:
        """
        Returns whether this interface is able to interface with the chunk type with a given identifier key,
        generated by the format.

        :param key: The key who's decodability needs to be checked.
        :return: True if this interface can interface with the chunk version associated with the key, False otherwise.
        """
        raise NotImplementedError()


if __name__ == "__main__":
    import time

    _find_interfaces()
    print(_loaded_interfaces)
    time.sleep(1)
    reload()
    print(_loaded_interfaces)
