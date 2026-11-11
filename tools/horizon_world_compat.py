"""Inspect world and item resource-pack models in Horizon-Test."""


def probe_build_surfaces(ctl, profile, record, *, beds_only=False):
    """Identical, state-checked panels for the enabled and excluded pack arms."""
    cases = record["world_compat"] = {}

    def command(text):
        reply = ctl("command", text)
        if not reply.get("ok"):
            raise RuntimeError(f"Build surface fixture command failed: {text}: {reply}")

    ctl("time", 1000)
    command("fill -535 68 54 -519 68 71 minecraft:stone")
    command("fill -535 69 54 -519 76 71 minecraft:air")

    panels = {
        "plants": [
            (0, 69, "mycelium"), (1, 69, "crimson_nylium"), (2, 69, "dirt"),
            (3, 69, "farmland[moisture=7]"), (4, 69, "farmland[moisture=7]"),
            (0, 70, "red_mushroom"), (1, 70, "crimson_fungus"), (2, 70, "potted_warped_fungus"),
            (3, 70, "wheat[age=7]"), (4, 70, "carrots[age=7]"),
        ],
        "doors_ladders_torches": [
            (0, 69, "oak_door[facing=north,half=lower,hinge=left,open=false]"),
            (0, 70, "oak_door[facing=north,half=upper,hinge=left,open=false]"),
            (1, 69, "oak_door[facing=north,half=lower,hinge=left,open=true]"),
            (1, 70, "oak_door[facing=north,half=upper,hinge=left,open=true]"),
            (4, 69, "torch"),
        ],
        "lanterns": [
            (0, 69, "lantern[hanging=false]"), (1, 69, "soul_lantern[hanging=false]"),
            (2, 71, "iron_chain[axis=y]"), (2, 70, "lantern[hanging=true]"),
            (3, 71, "copper_chain[axis=y]"), (3, 70, "copper_lantern[hanging=true]"),
        ],
        "beds": [
            (0, 69, "red_bed[facing=east,part=foot]"), (1, 69, "red_bed[facing=east,part=head]"),
            (3, 69, "cyan_bed[facing=east,part=foot]"), (4, 69, "cyan_bed[facing=east,part=head]"),
        ],
    }
    if beds_only:
        panels = {
            "beds_east_west": panels["beds"][:2] + [
                (3, 69, "cyan_bed[facing=west,part=head]"), (4, 69, "cyan_bed[facing=west,part=foot]"),
            ],
            "beds_north_south": [
                (0, 69, "white_bed[facing=north,part=head]"), (3, 69, "blue_bed[facing=south,part=foot]"),
            ],
        }
    for i, (name, cells) in enumerate(panels.items()):
        x = -533 + (i % 2) * 7
        z = 60 + (i // 2) * 9
        blocks = [(x + dx, y, z, spec) for dx, y, spec in cells]
        if name == "beds_north_south":
            blocks.extend(((x, 69, z + 1, "white_bed[facing=north,part=foot]"),
                           (x + 3, 69, z + 1, "blue_bed[facing=south,part=head]")))
        if name == "plants":
            command(f"setblock {x + 4} 68 {z + 1} minecraft:water")
        if name == "doors_ladders_torches":
            command(f"fill {x + 2} 69 {z + 1} {x + 3} 71 {z + 1} minecraft:stone")
            blocks.extend(((x + 2, 69, z, "ladder[facing=north]"),
                           (x + 2, 70, z, "ladder[facing=north]"),
                           (x + 3, 70, z, "wall_torch[facing=north]")))
        if name == "lanterns":
            command(f"fill {x + 2} 72 {z} {x + 3} 72 {z} minecraft:stone")
        for bx, y, bz, spec in blocks:
            command(f"setblock {bx} {y} {bz} minecraft:{spec}")
        ctl("wait", 18)
        readback = []
        for bx, y, bz, spec in blocks:
            expected, _, properties = spec.partition("[")
            actual = ctl("block", bx, y, bz)
            observed = actual["state"].partition("[")[2].rstrip("]").split(",")
            if (not actual["loaded"] or actual["block"] != f"minecraft:{expected}" or
                    properties and not set(properties.rstrip("]").split(",")).issubset(observed)):
                raise RuntimeError(f"Expected {spec} at {(bx, y, bz)}, got {actual}")
            readback.append(actual)
        views = []
        for side in (False, True):
            ctl("tp", x + (0 if side else 2.5), 69.5, z - 4.5)
            ctl("look-at", x + 2.5, 70, z + 0.5)
            ctl("wait", 12)
            path = profile / f"world-build-{name}-{'oblique' if side else 'front'}.png"
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing {name} build surface capture")
            views.append(str(path))
        cases[name] = {"complete": True, "readback": readback, "views": views}
    if beds_only:
        command("gamemode survival")
        command("clear @s")
        command("give @s minecraft:red_bed")
        ctl("wait", 12)
        item = "minecraft:red_bed"
        slot = next(s["slot"] for s in ctl("inventory")["hotbar"] if s and s["item"] == item)
        ctl("hotbar", slot + 1)
        ctl("wait", 12)
        held = ctl("status")["held"]
        if not held or held["item"] != item:
            raise RuntimeError(f"Expected red bed in hand, got {held}")
        views = {}
        for view in ("held", "inventory"):
            if view == "inventory":
                ctl("key", "e", "tap")
                ctl("wait-for", "screen", "inventory", "--timeout", "8", timeout=12)
                if not any(s["slot"] == slot and s["item"] == item for s in ctl("screen")["slots"]):
                    raise RuntimeError("Red bed missing from the inventory view")
            ctl("wait", 8)
            path = profile / f"world-build-bed-item-{view}.png"
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing bed item {view} capture")
            views[view] = str(path)
        ctl("key", "esc", "tap")
        cases["bed_item"] = {"complete": True, "held": held, "views": views}


def probe_subtitles(ctl, profile, record):
    cases = record["world_compat"] = {}
    settings = ctl("options-set", "showSubtitles", "true")
    if ctl("options-get", "showSubtitles")["options"]["showSubtitles"]["value"] is not True:
        raise RuntimeError(f"Subtitles could not be enabled: {settings}")
    ctl("tp", -527.5, 69, 57.5)
    ctl("look", 0, 0)
    for name, event, category in (
        ("villager", "entity.villager.ambient", "neutral"),
        ("rain", "weather.rain", "weather"),
        ("thunder", "entity.lightning_bolt.thunder", "weather"),
    ):
        result = ctl("command", f"playsound minecraft:{event} {category} @s ~ ~ ~ 0.2 1 0")
        if not result.get("ok"):
            raise RuntimeError(f"Sound event failed: {event}: {result}")
        ctl("wait", 6)
        path = profile / f"sound-{name}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing {name} subtitle capture")
        cases[name] = {"complete": True, "view": str(path), "event": event}
        ctl("wait", 70)


def probe(ctl, profile, record):
    cases = record["world_compat"] = {}

    def command(text):
        result = ctl("command", text)
        if not result.get("ok"):
            raise RuntimeError(f"Fixture command failed: {text}: {result}")

    def shot(case, stage):
        path = profile / f"world-{case}-{stage}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing screenshot for {case} {stage}")
        cases[case]["views"][stage] = str(path)

    def place_and_verify(blocks):
        for (x, y, z), spec in blocks:
            command(f"setblock {x} {y} {z} minecraft:{spec}")
        ctl("wait", 25)
        readback = []
        for pos, spec in blocks:
            name, _, suffix = spec.partition("[")
            actual = ctl("block", *pos)
            properties = actual["state"].partition("[")[2].rstrip("]").split(",")
            wanted = suffix.rstrip("]").split(",") if suffix else []
            if (not actual["loaded"] or actual["block"] != f"minecraft:{name}"
                    or not all(property_ in properties for property_ in wanted)):
                raise RuntimeError(f"Expected {spec} at {pos}, got {actual}")
            readback.append(actual)
        return readback

    def connected_blocks():
        case = "connected_blocks"
        z = 61
        blocks = [((-532, 69, z), "bricks"), ((-527, 69, z), "cobblestone")]
        for start_x, name in ((-530, "bricks"), (-525, "cobblestone")):
            blocks.extend(((x, y, z), name) for x in range(start_x, start_x + 2) for y in (69, 70))
        cases[case]["readback"] = place_and_verify(blocks)
        ctl("tp", -527, 69, 55)
        ctl("look", 0, 8)
        ctl("wait", 15)
        shot(case, "isolated-and-connected")
        ctl("tp", -533, 69, 56)
        ctl("look", -50, 7)
        ctl("wait", 15)
        shot(case, "oblique")

        # These packs' overlay rules paint stone next to a different material.
        mixed = []
        for x, neighbor in ((-531, "bricks"), (-525, "cobblestone")):
            for y in (69, 70):
                mixed.extend((((x, y, 58), "stone"), ((x + 1, y, 58), neighbor)))
        cases[case]["mixed_readback"] = place_and_verify(mixed)
        ctl("tp", -527.5, 69, 54.5)
        ctl("look", 0, 6)
        ctl("wait", 12)
        shot(case, "mixed-stone-neighbors")

    def rails():
        case = "rails"
        # Adjacent arms hold the curve under normal server neighbor updates.
        blocks = [
            ((-527, 73, 62), "stone"),
            ((-532, 69, 67), "rail[shape=north_south]"),
            ((-532, 69, 68), "rail[shape=north_south]"),
            ((-532, 69, 69), "rail[shape=north_south]"),
            ((-527, 69, 69), "rail[shape=north_south]"),
            ((-526, 69, 68), "rail[shape=east_west]"),
            ((-527, 69, 68), "rail[shape=south_east]"),
            ((-522, 68, 68), "redstone_block"),
            ((-522, 69, 68), "powered_rail[shape=north_south,powered=true]"),
        ]
        cases[case]["readback"] = place_and_verify(blocks)
        ctl("tp", -526.5, 74, 62.5)
        ctl("look", 0, 46)
        ctl("wait", 15)
        shot(case, "flat-curved-powered")
        ctl("tp", -526.5, 69, 65)
        ctl("look", 0, 28)
        ctl("wait", 15)
        shot(case, "curve-close")

    def tropical_fish_bucket():
        case = "tropical_fish_bucket"
        command("gamemode survival")
        command("clear @s")
        command("give @s minecraft:tropical_fish_bucket")
        ctl("tp", -527.5, 69, 74)
        ctl("look", 0, 8)
        ctl("wait", 10)
        item = "minecraft:tropical_fish_bucket"
        slot = next(s["slot"] for s in ctl("inventory")["hotbar"] if s and s["item"] == item)
        ctl("hotbar", slot + 1)
        ctl("wait", 12)
        held = ctl("status")["held"]
        if not held or held["item"] != item:
            raise RuntimeError(f"Expected the tropical fish bucket in hand, got {held}")
        shot(case, "held")
        ctl("wait", 8)
        shot(case, "held-later")
        ctl("key", "e", "tap")
        ctl("wait-for", "screen", "inventory", "--timeout", "8", timeout=12)
        ctl("wait", 8)
        slots = ctl("screen")["slots"]
        if not any(s["slot"] == slot and s["item"] == item for s in slots):
            raise RuntimeError("Tropical fish bucket missing from inventory view")
        shot(case, "inventory")
        cases[case]["held"] = held

    ctl("time", 1000)
    command("fill -535 68 54 -519 68 79 minecraft:stone")
    command("fill -535 69 54 -519 77 79 minecraft:air")
    ctl("wait", 20)

    for run in (connected_blocks, rails, tropical_fish_bucket):
        case = cases[run.__name__] = {"complete": False, "views": {}}
        try:
            run()
            case["complete"] = True
        except (RuntimeError, KeyError, StopIteration, ValueError) as error:
            case["error"] = f"{type(error).__name__}: {error}"
        finally:
            if ctl("screen")["screen"] == "inventory":
                ctl("key", "esc", "tap")
                ctl("wait-for", "screen", "playing", "--timeout", "8", timeout=12)
