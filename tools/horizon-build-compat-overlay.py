#!/usr/bin/env python3
"""Build a pinned, reversible compatibility overlay for the current Horizon packs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "outputs/horizon-runtime"
LAB = ROOT / "outputs/horizon-compatibility/daily-20261107"
PACKS = LAB / "snapshot/resourcepacks"
ASSETS = RUNTIME / "launcher-data/versions/native-f42-m1-r3-6b039bd4b49f/.local/horizon-client/26.3/assets"
CEM = "assets/minecraft/optifine/cem/"
SMITH = "Recolourful Containers DARK 3.1.4 (1.19.4+).zip"
EXTENSIONS = "FA+All_Extensions-v1.9.2.zip"
ANIMATIONS = "FreshAnimations_v1.11.1_26.1+.zip"
PINNED = {
    SMITH: "19d1999d0194ff2a3c944c3d52459825adc5a4683751c390d7cbfc95e9b21071",
    EXTENSIONS: "027acba5f64c9d1bf5ccb8daecb7fc756961bfeee866434a0ee5f7809a48d326",
    ANIMATIONS: "a2f56bbc465eae5a3141458d8924e51bc66ac4e8f542d17b1b4f922193858a17",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def omit_mushroom_boxes(model):
    removed = {}
    def walk(node):
        name = node.get("id")
        if name in {"mushroom1", "mushroom2", "mushroom3"}:
            if name in removed or node.get("submodels") or len(node.get("boxes", [])) != 2:
                raise ValueError(f"Unexpected mushroom model bone {name}")
            removed[name] = len(node.pop("boxes"))
        for child in node.get("submodels", []):
            walk(child)
    for part in model["models"]:
        walk(part)
    if set(removed) != {"mushroom1", "mushroom2", "mushroom3"}:
        raise ValueError("Three expected authored mushroom bones were not found")
    return removed


def write_overlay(name, files):
    target = LAB / name
    temporary = target.with_suffix(".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, data in sorted(files.items()):
            entry = zipfile.ZipInfo(path)
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() or any(archive.read(path) != data for path, data in files.items()):
            raise ValueError("Overlay archive failed byte verification")
    temporary.replace(target)
    print(f"Verified {len(files)} overlay members in {target}")
    return target


def animation_followup(*, more=False, bogged=False):
    models = {
        "wandering_trader": ("villager", {"varb.baby_model": False, "varb.is_wanderer": True},
            "9e05010eeafa9c0c8ad3051cc04e4bbae9c4da11299b5dde1a96e3a078195cf6",
            "f764c0d26cebed7dc40ca72e8e005204ece5a351abb9a7018d10b169c27271de"),
        "elder_guardian": ("guardian", {"varb.is_elder": True},
            "a1c2a4da1771f61321a3b45d2bfc3cd8e51f4c5208b404cbe0954e64028b109a",
            "5bc6a1ff7d9a45929871ac0fe9bfb9398fa90e2ea06482dff944c7a44778741e"),
    }
    sources = {}
    name = "Horizon-Animation-Compatibility.zip"
    if more or bogged:
        skeleton = "47cd852b99b2d063adace631df5e0ad916ebb902f988daba3183815a9718d48c"
        physics = "Fresh Skeleton Physics.zip"
        models = {
            "parched": ("skeleton", {"varb.21_2_plus": True, "varb.is_stray": False,
                        "varb.is_bogged": False, "varb.is_parched": True},
                        "99c1c3337359773766a10f79a20d70d99795392692e048386badb47f7aef3997", skeleton),
            "stray": ("skeleton", {"varb.21_2_plus": True, "varb.is_stray": True,
                      "varb.is_bogged": False, "varb.is_parched": False},
                      "431a7860aa62e15bd3848b8bb2c789c894fda47fb06003ad016af9edb18f5d3c", skeleton),
            "mule": ("donkey", {"varb.21_2_plus": True},
                     "616802e095fe0f529eb8fb5f479c4226595a4c6362c8bc90c2c9c4859828e809",
                     "2153d87956e9103b9fc954a9c14f3e94b9fe4e91de9ba659cc7ab97580937ca2"),
            "cave_spider": ("spider", {"varb.is_cave": False},
                            "4fbe8b3fe36cf7e01014710f7200d759490581c36a44192ae2c5a415426922d9",
                            "359c1857222ba49ef5c74bae2d589fb1ca87a93230b5e4f1dba5686aaac7d763"),
        }
        sources = {"parched": physics, "stray": physics}
        name = "Horizon-Mob-Compatibility.zip"
        if bogged:
            models = {"bogged": ("skeleton", {"varb.21_2_plus": True, "varb.is_stray": False,
                                             "varb.is_bogged": True, "varb.is_parched": False},
                                "7c7998fd0560cf7d7e10ed0a954b200407f453694ae6f058d19640e0b9e20794", skeleton)}
            sources = {"bogged": physics}
            name = "Horizon-Bogged-Compatibility.zip"
    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                             "description": "Local Horizon mob animation compatibility"}})}
    with zipfile.ZipFile(PACKS / ANIMATIONS) as base:
        for entity, (carrier, variables, model_hash, carrier_hash) in models.items():
            path = f"{CEM}{entity}.jem"
            with zipfile.ZipFile(PACKS / sources.get(entity, EXTENSIONS)) as addon:
                source = addon.read(path)
            shared = f"{carrier}_animations.jpm"
            if sha(source) != model_hash or sha(base.read(CEM + shared)) != carrier_hash:
                raise ValueError(f"Unexpected model or animation carrier for {entity}")
            model = json.loads(source)
            root = model["models"][0]
            if root["model"] != f"{entity}_animations.jpm":
                raise ValueError(f"Expected absent animation import for {entity}")
            root["model"] = shared
            model["models"].insert(0, {"part": "root", "id": "codex_" + entity + "_vars",
                                       "attach": True, "animations": [variables]})
            files[path] = encode(model)
    write_overlay(name, files)


def gui_followup():
    from PIL import Image

    def tile_png(data, size, marker, crop, output_size):
        with Image.open(io.BytesIO(data)) as image:
            if image.size != size or image.convert("RGBA").getpixel((0, 0)) != marker:
                raise ValueError(f"Unexpected shader tile layout {size}, {marker}")
            tile = image.crop(crop).convert("RGBA")
            tile.putpixel((0, 0), (0, 0, 0, 0))
            result = io.BytesIO()
            tile.resize(output_size, Image.Resampling.NEAREST).save(result, format="PNG")
            return result.getvalue()

    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                             "description": "Local Horizon container GUI compatibility"}})}
    titles = {"container.enchant": "\uec01", "container.cartography_table": "\uec02",
              "container.enderchest": "\uec03", "container.dropper": "\uec04\uec05\uec06",
              "container.dispenser": "\uec07\uec08", "container.repair": "\uec09",
              "container.stonecutter": "\uec11"}
    replacements = {
        **{f"container/beacon/button{suffix}": ((84, 84), (1, 1, 2, 2))
           for suffix in ("", "_disabled", "_highlighted", "_selected")},
        "container/crafter/powered_redstone": ((174, 174), (1, 3, 0, 2)),
        "container/villager/trade_arrow": ((88, 20), (1, 5, 0, 2)),
        "container/villager/trade_arrow_out_of_stock": ((88, 20), (1, 5, 0, 2)),
    }
    sprite = "assets/minecraft/textures/gui/sprites/"
    vanilla = json.loads((ASSETS / "minecraft/lang/en_us.json").read_text())
    with zipfile.ZipFile(PACKS / SMITH) as source, zipfile.ZipFile(LAB / "Horizon-Daily-Compatibility.zip") as previous:
        for name in ("en_us", "en_us_vanilla"):
            path = f"assets/minecraft/lang/{name}.json"
            locale = json.loads(previous.read(path))
            for key, glyphs in titles.items():
                if name == "en_us_vanilla" and key == "container.enderchest":
                    glyphs = "\ueb01\uea0c\ueb03" + glyphs
                if locale[key] != glyphs:
                    raise ValueError(f"Unexpected legacy glyph for {key}")
                locale[key] = "§f" + vanilla[key]
            files[path] = encode(locale)
        for name, (size, marker) in replacements.items():
            path = sprite + name + ".png"
            with Image.open(io.BytesIO(source.read(path))) as image:
                if image.size != size or image.convert("RGBA").getpixel((0, 0)) != marker:
                    raise ValueError(f"Unexpected shader sprite {name}")
            files[path] = (ASSETS / path.removeprefix("assets/")).read_bytes()
        for name in ("button", "button_highlighted"):
            path = f"{sprite}recipe_book/{name}.png"
            # The native HUD draws one sprite at the 20×18 hitbox in either state.
            files[path] = tile_png(source.read(path), (42, 21), (1, 6, 0, 2), (0, 0, 21, 21), (20, 18))
        for name in ("speed", "haste", "resistance", "jump_boost", "strength", "regeneration"):
            path = f"assets/minecraft/textures/mob_effect/{name}.png"
            files[path] = tile_png(source.read("-1.21.2_assets/" + path), (36, 18), (1, 1, 1, 2),
                                   (0, 0, 18, 18), (18, 18))
        for name in ("confirm", "cancel"):
            path = f"{sprite}container/beacon/{name}.png"
            with Image.open(io.BytesIO(source.read(path))) as image:
                if image.convert("RGBA").getchannel("A").getbbox() is not None:
                    raise ValueError(f"Expected transparent beacon {name}")
            files[path] = (ASSETS / path.removeprefix("assets/")).read_bytes()
    write_overlay("Horizon-GUI-Compatibility.zip", files)


def charged_creeper():
    path = CEM + "creeper_charge.jem"
    with zipfile.ZipFile(PACKS / EXTENSIONS) as addon, zipfile.ZipFile(PACKS / ANIMATIONS) as base:
        model_bytes = addon.read(path)
        carrier_bytes = base.read(CEM + "creeper_animations.jpm")
    if (sha(model_bytes) != "747bdcef3ad6d90f8f8c9f5ad3b017c7f496f98d019bdb4e6e51ce6e9cc6ed9d"
            or sha(carrier_bytes) != "b9983194e871246cc1a7369b8dfb1cddd217c34cf75cfe0f94fe8b8b19f54b06"):
        raise ValueError("Unexpected charged creeper source model or animation carrier")
    model = json.loads(model_bytes)
    carrier = json.loads(carrier_bytes)
    root = model["models"][0]
    if root["model"] != "creeper_charge_animations.jpm" or [len(x) for x in carrier["animations"]] != [15, 18, 52, 22]:
        raise ValueError("Unexpected charged creeper animation layout")
    # The last block animates eyes and pupils, which the shell model lacks.
    carrier["animations"] = carrier["animations"][:3]
    root["model"] = "horizon_creeper_shell.jpm"
    model["models"].insert(0, {"part": "root", "id": "codex_creeper_shell_vars", "attach": True,
                               "animations": [{"varb.is_charge": True}]})
    write_overlay("Horizon-Charged-Creeper.zip", {
        "pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                       "description": "Local Horizon charged creeper shell"}}),
        path: encode(model),
        CEM + root["model"]: encode(carrier),
    })


def charged_creeper_stock():
    texture = "minecraft/textures/entity/creeper/creeper_armor.png"
    write_overlay("Horizon-Charge-Texture-Control.zip", {
        "pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                       "description": "Local Horizon vanilla charge texture control"}}),
        "assets/" + texture: (ASSETS / texture).read_bytes(),
    })


def armor_trim_followup():
    source = PACKS / "Fine Armoury v1.8.zip"
    if sha(source.read_bytes()) != "d0e1cfe3d93378571baf52f6b51c65f667d687677a39b3c91f7d9abe25fc9bd9":
        raise ValueError("Unexpected Fine Armoury source archive")
    prefix = "assets/minecraft/textures/trims/entity/humanoid/"
    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                             "description": "Local Horizon armour trim palettes"}})}
    with zipfile.ZipFile(source) as pack:
        members = set(pack.namelist())
        for path in sorted(members):
            if not path.startswith(prefix) or not path.endswith(".png"):
                continue
            metadata = path + ".mcmeta"
            if metadata in members:
                raise ValueError(f"Fine Armoury already declares {metadata}")
            original = (ASSETS / metadata.removeprefix("assets/")).read_bytes()
            if json.loads(original) != {"palette": {"base_palette": "trim_base"}}:
                raise ValueError(f"Unexpected vanilla palette metadata {metadata}")
            files[metadata] = original
    if len(files) != 18:
        raise ValueError("Expected 17 trim textures")
    write_overlay("Horizon-Trim-Compatibility.zip", files)


def skeleton_horse_followup():
    model_path = CEM + "skeleton_horse.jem"
    with zipfile.ZipFile(PACKS / "Fresh Skeleton Physics.zip") as addon:
        source = addon.read(model_path)
    with zipfile.ZipFile(PACKS / ANIMATIONS) as base:
        shared = base.read(CEM + "horse_animations.jpm")
    if (sha(source) != "01e1b2382a6439c1c75b8eb0b225e017a2e8e780d41a5d3ff2b3fa166895fbe4"
            or sha(shared) != "2375e9db68959c94cda7ece8f74582f6221ea7cd05b5fb2152ae37c9a710c054"):
        raise ValueError("Unexpected skeleton horse model or shared carrier")
    model, carrier = json.loads(source), json.loads(shared)
    missing = {"headpiece_snout", "l_eye_white", "l_pupil", "left_ear2", "left_eye",
               "left_rein2", "left_rein3", "left_saddle", "mane2", "mane3", "neck3",
               "r_eye_white", "r_pupil", "right_ear2", "right_eye", "right_rein2",
               "right_rein3", "right_saddle", "snout2"}
    before = carrier["animations"]
    after = [{key: value for key, value in group.items() if key.partition(".")[0] not in missing}
             for group in before]
    removed = {key.partition(".")[0] for group in before for key in group if key.partition(".")[0] in missing}
    reference = re.compile(r"(?<![\w.])(?:[A-Za-z_]\w*(?::[A-Za-z_]\w*)*)\.[A-Za-z0-9_]\w*")
    used = {token.split(".")[0] for group in after for value in group.values()
            for token in reference.findall(str(value))}
    if (sum(map(len, before)), sum(map(len, after))) != (144, 94) or removed != missing or used & missing:
        raise ValueError("Skeleton horse carrier pruning has a dependent expression")
    carrier["animations"] = after
    root = model["models"][0]
    if root["model"] != "skeleton_horse_animations.jpm":
        raise ValueError("Unexpected skeleton horse import")
    root["model"] = "horizon_skeleton_horse_body.jpm"
    model["models"].insert(0, {"part": "root", "id": "codex_skeleton_horse_vars", "attach": True,
                               "animations": [{"varb.21_2_plus": True, "varb.is_zombie": False,
                                               "varb.is_skeleton": True}]})
    write_overlay("Horizon-Skeleton-Horse-Compatibility.zip", {
        "pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                       "description": "Local Horizon skeleton horse body animation"}}),
        model_path: encode(model),
        CEM + root["model"]: encode(carrier),
    })


def ghast_harness_assets(*, align_body=False):
    model_path = CEM + "happy_ghast_harness.jem"
    with zipfile.ZipFile(PACKS / "3D Harness x Fresh Animations.zip") as addon:
        source = addon.read(model_path)
    with zipfile.ZipFile(PACKS / ANIMATIONS) as base:
        shared = base.read(CEM + "happy_ghast_animations.jpm")
    if (sha(source) != "3fccbb506071d01ef91a641c17c9230098c471bccacc5790273a75273fc0fc1c"
            or sha(shared) != "733d44b7825915c41c5f3a74a79af1fb21693a066f69c9fee857400c4a243fa7"):
        raise ValueError("Unexpected happy ghast harness model or carrier")
    model, carrier = json.loads(source), json.loads(shared)
    keys = {"varb.pfc", "var.Aequip", "var.equip", "goggles2.rx", "goggles2.ty",
            "goggles2.tz", "var.pre_frame_counter"}
    reduced = [{key: value for key, value in group.items() if key in keys} for group in carrier["animations"]]
    if [i for i, group in enumerate(reduced) if group] != [0, 9, 10] or sum(map(len, reduced)) != len(keys):
        raise ValueError("Unexpected harness dependency layout")
    if align_body:
        shared_groups = carrier["animations"]
        # Keep the shared body pose ahead of the harness-local goggles.
        # Face and tentacle writes address geometry absent from this layer.
        carrier["animations"] = [shared_groups[i] for i in (0, 1, 9, 10)]
        # Lowering the addon lenses puts their center below its custom eyes.
        # Raise them progressively with the existing equip interpolation.
        goggles = shared_groups[9]
        goggles["goggles2.ty"] = f"({goggles['goggles2.ty']}) - 3.5*var.equip"
        harness = next(p for p in model["models"] if p.get("part") == p.get("id") == "harness")
        harness["id"] = "body2"
    else:
        carrier["animations"] = [group for group in reduced if group]
    root = model["models"][0]
    if root["model"] != "happy_ghast_harness_animations.jpm":
        raise ValueError("Unexpected happy ghast harness import")
    root["model"] = "horizon_happy_ghast_harness.jpm"
    model["models"].insert(0, {"part": "root", "id": "codex_harness_vars", "attach": True,
                               "animations": [{"varb.is_harness": True}]})
    return {
        model_path: encode(model),
        CEM + root["model"]: encode(carrier),
    }


def ghast_harness_followup():
    write_overlay("Horizon-Ghast-Harness-Compatibility.zip", {
        "pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                       "description": "Local Horizon happy ghast harness goggles"}}),
        **ghast_harness_assets(),
    })


def ghast_body_followup(*, align_harness=False):
    models = {
        "happy_ghast.jem": "04ba9955dfa7fbad155b6092800e7b49d30451b2899ad877935ec6de6f2ff4f1",
        "happy_ghast_ropes.jem": "b9849a5e000a56a257b09699f60cd70969bd9651d5fb38d3ae4240a56fe36342",
    }
    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                             "description": "Local Horizon happy ghast body and rope anchors"}})}
    with zipfile.ZipFile(PACKS / "3D Harness x Fresh Animations.zip") as addon:
        for name, expected in models.items():
            path = CEM + name
            source = addon.read(path)
            if sha(source) != expected:
                raise ValueError(f"Unexpected ghast model {name}")
            model = json.loads(source)
            body = next(p for p in model["models"] if p.get("part") == "body" and p.get("id") == "body")
            # The native body stays the parent. The shared carrier targets its
            # custom geometry child separately for pitch, roll and scale.
            body["id"] = "body2"
            files[path] = encode(model)
    name = "Horizon-Ghast-Body-Compatibility.zip"
    if align_harness:
        files.update(ghast_harness_assets(align_body=True))
        name = "Horizon-Ghast-Alignment-Compatibility.zip"
    write_overlay(name, files)


def bed_geometry_followup():
    """Bake the two authored raised bed details into the native terrain model."""
    pack = (PACKS / "§lBetter Beds.zip").read_bytes()
    if sha(pack) != "5a19393245e1a622d45c15ac27245d2b445f60dc8272dee9c8e64b715b48d0b8":
        raise ValueError("Unexpected Better Beds pack")
    assets = ASSETS / "minecraft/models/block"
    template = (assets / "template_bed_head.json").read_bytes()
    if sha(template) != "7f6c3f1cb10e1ecdf1ee483433badd30dde4e73a429ff1022ff91b80f22d9fd1":
        raise ValueError("Unexpected terrain bed head template")
    terrain = json.loads(template)
    terrain_path = "assets/minecraft/models/block/"
    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
                                             "description": "Local Horizon Better Beds terrain geometry"}})}
    colors = ("black", "blue", "brown", "cyan", "gray", "green", "light_blue", "light_gray",
              "lime", "magenta", "orange", "pink", "purple", "red", "white", "yellow")
    with zipfile.ZipFile(io.BytesIO(pack)) as archive:
        authored = json.loads(archive.read(CEM + "bed.jem"))
        head = next(m for m in authored["models"] if m["part"] == "head")
        # The two mattresses share the same bounds in the neutral pose. Map
        # the inverted CEM child's basis to block x, up and south.
        if (authored["textureSize"] != [64, 64] or head["boxes"][0]["coordinates"] != [-8, -7, 16, 16, 16, 6]
                or terrain["elements"][0]["from"] != [0, 3, 0] or terrain["elements"][0]["to"] != [16, 9, 16]):
            raise ValueError("Beds no longer share the pinned neutral bounds")
        for child in head["submodels"]:
            tx, ty, tz = child["translate"]
            rx, ry, rz = child["rotate"]
            if child["invertAxis"] != "xy" or ry or rz or len(child["boxes"]) != 1:
                raise ValueError("Unsupported bed detail transform")
            box = child["boxes"][0]
            x, y, z, w, h, d = box["coordinates"]
            u, v = box["textureOffset"]
            # ModelPart.Cube strip, remapped to the terrain cube's face
            # corners. The atlas tile is 64x64, and block UVs use 0..16.
            u1, u2, u3, u4, u5 = (u+d, u+d+w, u+d+2*w, u+2*d+w, u+2*d+2*w)
            v1, v2 = v+d, v+d+h
            face_uvs = {
                "up": ((u1, v1, u2, v2), 0),
                "down": ((u4, v1, u5, v2), 180),
                "east": ((u2, v1, u4, v2), 90),
                "west": ((u, v1, u1, v2), 270),
                "north": ((u1, v, u2, v1), 180),
                "south": ((u2, v1, u3, v), 0),
            }
            px, py, pz = 8-tx, 25-tz, 9-ty
            terrain["elements"].append({
                "from": [px-x-w, py-z-d, pz-y-h], "to": [px-x, py-z, pz-y],
                "rotation": {"origin": [px, py, pz], "axis": "x", "angle": -rx},
                "faces": {face: {"uv": [c/4 for c in uv], "texture": "#horizon_bed", "rotation": rotation}
                          for face, (uv, rotation) in face_uvs.items()},
            })
        files[terrain_path + "horizon_better_bed_head.json"] = encode(terrain)
        for color in colors:
            texture = archive.read(f"assets/minecraft/textures/entity/bed/{color}.png")
            if struct.unpack(">II", texture[16:24]) != (64, 64):
                raise ValueError(f"Unexpected {color} Better Beds texture size")
            model = json.loads((assets / f"{color}_bed_head.json").read_bytes())
            if model.get("parent") != "minecraft:block/template_bed_head":
                raise ValueError(f"Unexpected native {color} bed inheritance")
            model["parent"] = "minecraft:block/horizon_better_bed_head"
            model["textures"]["horizon_bed"] = f"minecraft:block/horizon_better_bed/{color}"
            files[terrain_path + f"{color}_bed_head.json"] = encode(model)
            files[f"assets/minecraft/textures/block/horizon_better_bed/{color}.png"] = texture
    write_overlay("Horizon-Better-Beds-Compatibility.zip", files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--animation-followup", action="store_true")
    mode.add_argument("--mob-followup", action="store_true")
    mode.add_argument("--bogged-followup", action="store_true")
    mode.add_argument("--gui-followup", action="store_true")
    mode.add_argument("--charged-creeper", action="store_true")
    mode.add_argument("--charged-creeper-stock", action="store_true")
    mode.add_argument("--trim-followup", action="store_true")
    mode.add_argument("--skeleton-horse-followup", action="store_true")
    mode.add_argument("--ghast-harness-followup", action="store_true")
    mode.add_argument("--ghast-body-followup", action="store_true")
    mode.add_argument("--ghast-alignment-followup", action="store_true")
    mode.add_argument("--bed-geometry-followup", action="store_true")
    args = parser.parse_args()
    for name, expected in PINNED.items():
        if sha((PACKS / name).read_bytes()) != expected:
            raise ValueError(f"Unexpected source bytes for {name}")
    if args.animation_followup or args.mob_followup or args.bogged_followup:
        animation_followup(more=args.mob_followup, bogged=args.bogged_followup)
        return
    if args.gui_followup:
        gui_followup()
        return
    if args.charged_creeper:
        charged_creeper()
        return
    if args.charged_creeper_stock:
        charged_creeper_stock()
        return
    if args.trim_followup:
        armor_trim_followup()
        return
    if args.skeleton_horse_followup:
        skeleton_horse_followup()
        return
    if args.ghast_harness_followup:
        ghast_harness_followup()
        return
    if args.ghast_body_followup or args.ghast_alignment_followup:
        ghast_body_followup(align_harness=args.ghast_alignment_followup)
        return
    if args.bed_geometry_followup:
        bed_geometry_followup()
        return

    files = {"pack.mcmeta": encode({"pack": {"pack_format": 97, "min_format": 97, "max_format": 97,
             "description": "Local Horizon mooshroom and smithing compatibility"}})}
    model_path = CEM + "mooshroom.jem"
    with zipfile.ZipFile(PACKS / EXTENSIONS) as archive:
        source = archive.read(model_path)
    if sha(source) != "f0fb34ef12bc7f000b6cdacb294aea3f0924114a654c6b9c712027f4bc7148d6":
        raise ValueError("Unexpected adult mooshroom model")
    model = json.loads(source)
    if model["models"][0]["model"] != "mooshroom_animations.jpm":
        raise ValueError("Expected missing animation carrier")
    model["models"][0]["model"] = "cow_animations.jpm"
    model["models"].insert(0, {"part": "root", "id": "codex_mooshroom_vars", "attach": True,
        "animations": [{"varb.21_2_plus": True, "varb.baby_model": False,
                        "varb.index_eat": "rule_index==2", "varb.is_mooshroom": True}]})
    removed = omit_mushroom_boxes(model)
    files[model_path] = encode(model)
    with zipfile.ZipFile(PACKS / ANIMATIONS) as archive:
        carrier_hash = sha(archive.read(CEM + "cow_animations.jpm"))

    vanilla = json.loads((ASSETS / "minecraft/lang/en_us.json").read_text())
    keys = ["container.upgrade", "container.upgrade.missing_template_tooltip", "container.upgrade.error_tooltip"]
    keys += [f"item.minecraft.smithing_template.{kind}.{slot}_slot_description"
             for kind in ("armor_trim", "netherite_upgrade") for slot in ("base", "additions")]
    with zipfile.ZipFile(PACKS / SMITH) as archive:
        for locale in ("en_us", "en_us_vanilla"):
            name = f"assets/minecraft/lang/{locale}.json"
            lang = json.loads(archive.read(name))
            if lang["container.upgrade"] != "\uec10" or any(lang[k] != "" for k in keys[1:]):
                raise ValueError(f"Unexpected smithing language entries in {locale}")
            for key in keys:
                lang[key] = vanilla[key]
            lang["container.upgrade"] = "§f" + lang["container.upgrade"]
            files[name] = encode(lang)
        for icon in ("helmet", "chestplate", "leggings", "boots"):
            path = f"minecraft/textures/gui/sprites/container/slot/{icon}.png"
            name = "assets/" + path
            old = archive.read(name)
            icon_bytes = (ASSETS / path).read_bytes()
            if struct.unpack(">II", old[16:24]) != (32, 16) or struct.unpack(">II", icon_bytes[16:24]) != (16, 16):
                raise ValueError(f"Unexpected sprite sheet geometry for {name}")
            files[name] = icon_bytes

    target = write_overlay("Horizon-Daily-Compatibility.zip", files)
    (LAB / "overlay-provenance.json").write_bytes(encode({"source_packs": PINNED,
        "cow_animation_carrier_sha256": carrier_hash, "mushroom_boxes_removed": removed,
        "smithing_translation_keys": keys, "members": {name: sha(data) for name, data in files.items()},
        "overlay_sha256": sha(target.read_bytes())}))


if __name__ == "__main__":
    main()
