#!/usr/bin/env python3
"""Check the pack and native model inputs for a scoped R11 cart CEM pilot."""

from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile
import json
import struct


OUTPUTS = Path(__file__).resolve().parents[2]
RUNTIME = OUTPUTS / "horizon-runtime"
GAME = RUNTIME / "game"
VERSION = RUNTIME / "launcher-data/versions/native-f42-m1-r11-ef12b7f4368d"
WINNER = "Minecarts with Wheels.zip"
LOWER = "FA+All_Extensions-v1.9.2.zip"
CARTS = ("minecart", "chest_minecart", "furnace_minecart", "hopper_minecart",
         "tnt_minecart", "command_block_minecart", "spawner_minecart")
JEMS = {f"assets/minecraft/optifine/cem/{cart}.jem": cart for cart in CARTS}


def check(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    options = (GAME / "options.txt").read_text()
    order = json.loads(next(line.split(":", 1)[1] for line in options.splitlines()
                            if line.startswith("resourcePacks:")))
    owners = {cart: [] for cart in CARTS}
    for entry in order:
        if not entry.startswith("file/"):
            continue
        name = entry.removeprefix("file/")
        with ZipFile(GAME / "resourcepacks" / name) as pack:
            for path in pack.namelist():
                if path in JEMS:
                    owners[JEMS[path]].append(name)
                elif path.endswith(tuple(f"/{cart}.jem" for cart in CARTS)):
                    raise SystemExit(f"Alternate cart CEM path requires review: {name}:{path}")
    for cart, layers in owners.items():
        check(layers == [LOWER, WINNER], f"Unexpected selected CEM layers for {cart}: {layers}")

    source = GAME / "resourcepacks" / WINNER
    digest = sha256(source.read_bytes()).hexdigest()
    check(digest == "fcea5d5a0ef671285a2f7c4f1f4d5661397d35f7aeefa93202bec0194652864e",
          "Wheel pack bytes changed")
    with ZipFile(source) as pack:
        png = pack.read("assets/minecraft/textures/entity/wheel.png")
        check(png[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", png[16:24]) == (8, 6),
              "Unexpected wheel sprite")
        canonical = json.loads(pack.read(next(iter(JEMS))))
        check(all(json.loads(pack.read(path)) == canonical for path in JEMS),
              "Cart JEMs no longer describe identical wheel geometry")
        body, = canonical["models"]
        check(body["part"] == "front" and body["attach"] is True and
              body["texture"] == "textures/entity/wheel.png" and body["textureSize"] == [8, 6] and
              [len(axle["boxes"]) for axle in body["submodels"]] == [2, 2] and
              body["animations"] == [{"front_wheels.rx": "limb_swing*4",
                                      "back_wheels.rx": "limb_swing*4"}],
              "Wheel attachment or rotation changed")

    document = VERSION / ".local/horizon-client/26.3/entity-models.json"
    vanilla = json.loads(document.read_text())
    for cart in CARTS:
        front = vanilla[f"minecraft:{cart}#main"]["children"]["front"]
        check(front["pose"] == [-9.0, 4.0, 0.0, 0.0, 4.712389, 0.0, 1.0, 1.0, 1.0]
              and len(front["polygons"]) == 6, f"Unexpected front anchor for {cart}")
    # CemLayer::build nests the new bone under front. The baked XY inversion
    # precedes front's 270-degree Y rotation (x,z -> -z,x).
    tx, ty, tz = body["translate"]
    centers = []
    for axle in body["submodels"]:
        ax, ay, az = axle["translate"]
        check(axle["invertAxis"] == body["invertAxis"] == "xy", "Unexpected axis convention")
        for box in axle["boxes"]:
            x, y, z, width, height, depth = box["coordinates"]
            bone_center = (-tx - ax - x - width / 2,
                           -ty - ay - y - height / 2,
                           tz + az + z + depth / 2)
            px, py, pz = bone_center
            centers.append((-9 - pz, 4 + py, px))
    check(set(centers) == {(x, 4.5, z) for x in (-5, 5) for z in (-8.5, 8.5)},
          f"Unexpected wheel center coordinates: {centers}")
    print(json.dumps({"wheel_archive_sha256": digest, "selected_layers": len(order),
                      "checked_variants": list(CARTS), "wheel_size": [8, 6],
                      "custom_cuboids_per_cart": 4, "vanilla_front_pivot": [-9.0, 4.0, 0.0],
                      "vanilla_front_yaw_rad": 4.712389, "rest_centers": centers}, indent=2))


if __name__ == "__main__":
    main()
