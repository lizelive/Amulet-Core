import json
import os

import re  # For command-line


class Prototype1:

    @staticmethod
    def properties_to_string(props: dict) -> str:
        result = []
        for key, value in props.items():
            result.append("{}={}".format(key, value))
        return ",".join(result)

    @staticmethod
    def string_to_properties(string: str) -> dict:
        result = {}
        split = string.split(",")
        for pair in split:
            key, value = pair.split("=")
            if not value.isdigit() and not value.isalpha():
                value = float(value)
            elif not value.isalpha():
                value = int(value)
            result[key] = value
        return result

    def __init__(self, definitions_to_build):
        self.blocks = {}
        self._definitions = {}

        fp = open(os.path.join(os.path.dirname(__file__), "internal", "blocks.json"))
        self.defs_internal = json.load(fp)
        fp.close()

        self._definitions["internal"] = {"minecraft": self.defs_internal["minecraft"]}

        if not os.path.exists(
            "{}.json".format(
                os.path.join(os.path.dirname(__file__), definitions_to_build, "blocks")
            )
        ):
            raise FileNotFoundError()

        fp = open(
            "{}.json".format(
                os.path.join(os.path.dirname(__file__), definitions_to_build, "blocks")
            ),
            "r",
        )
        defs = json.load(fp)
        fp.close()
        self._definitions[definitions_to_build] = {"minecraft": {}}
        for resource_location in defs:
            for base_block in defs[resource_location]:
                if base_block not in defs[resource_location]:
                    self._definitions[definitions_to_build]["minecraft"][
                        base_block
                    ] = {}

                if (
                    "map_to" in defs[resource_location][base_block]
                    and "id" in defs[resource_location][base_block]
                ):
                    map_to = defs[resource_location][base_block]["map_to"]
                    block_idenifier = defs[resource_location][base_block]["id"]
                    self.blocks[map_to[map_to.index(":") + 1:]] = block_idenifier
                else:
                    for blockstate in defs[resource_location][base_block]:
                        block_id = defs[resource_location][base_block][blockstate].get(
                            "id", [-1, -1]
                        )
                        map_to = defs[resource_location][base_block][blockstate].get(
                            "map_to", "internal:minecraft:unknown"
                        )
                        self.blocks[map_to[map_to.index(":") + 1:]] = block_id

    def get_internal_block(
        self, resource_location="minecraft", basename="air", properties=None
    ) -> dict:
        if properties:
            properties = self.properties_to_string(properties)

        if resource_location in self._definitions["internal"]:
            if basename in self._definitions["internal"][resource_location]:
                if (
                    properties
                    and properties in self._definitions["internal"][resource_location][
                        basename
                    ]
                ):
                    return self._definitions["internal"][resource_location][basename][
                        properties
                    ]

                elif properties:
                    raise KeyError(
                        "No blockstate definition found for '{}:{}[{}]'".format(
                            resource_location, basename, properties
                        )
                    )

                else:
                    return self._definitions["internal"][resource_location][basename]

        raise KeyError(
            "No blockstate definition found for '{}:{}'".format(
                resource_location, basename
            )
        )


if __name__ == "__main__":
    ver = input("Version definitions to build: ")
    proto = Prototype1(ver)
    matcher = re.compile(r"^(.)+:(.)+$")
    while True:
        user_input = input(">> ").lower()
        if user_input == "quit" or user_input == "q":
            break

        elif user_input.startswith("block"):
            print(
                "Result: {}".format(
                    proto.blocks.get(
                        user_input.replace("block ", ""), "minecraft:unknown"
                    )
                )
            )
        elif user_input.startswith("reverse"):
            user_input = user_input.replace("reverse ", "")
            result = None
            if matcher.match(user_input):
                for key, value in proto.blocks.items():
                    if user_input == value:
                        result = key
                        break

            else:
                numerical_ids = map(int, user_input.replace(" ", "")[1:-1].split(","))
                numerical_ids = [i for i in numerical_ids]
                result = None
                for key, value in proto.blocks.items():
                    if value == numerical_ids:
                        result = key
                        break

            if result:
                print("Result: {}".format(result))
            else:
                print("Block not found")
        elif user_input.startswith("load"):
            user_input = user_input.replace("load ", "")
            proto = Prototype1(user_input)
            print("Successfully loaded '{}' definitions".format(user_input))
        elif user_input == "list":
            print(proto.blocks)
        else:
            print("==== Help ====")
            print(
                "block <internal name>: Looks up a block from it's internal mapping name (internal -> version)"
            )
            print(
                "reverse <versioned name>: Looks up a block from it's internal mapping value (version -> internal)"
            )
            print("list: Lists all blocks in the current mapping")
            print("load <version>: Loads the specified version of block definitions")
