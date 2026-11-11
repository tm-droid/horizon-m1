"""Targeted controls for the disposable daily compatibility scene."""


def probe_more_mobs(ctl, profile, record):
    cases = record["daily_compat"] = {}
    ctl("time", "1000")
    ctl("command", "fill -535 68 54 -510 68 74 minecraft:stone")
    ctl("command", "fill -535 69 54 -510 74 74 minecraft:air")
    fixtures = [
        ("wandering_trader", "wandering_trader", -531.5, 69.05, ""),
        ("elder_guardian_dry", "elder_guardian", -523.5, 69.05, ""),
        ("elder_guardian_water", "elder_guardian", -515.5, 69.5, "NoGravity:1b,"),
    ]
    for name, entity, x, y, nbt in fixtures:
        if name == "elder_guardian_water":
            ctl("command", "fill -518 69 55 -512 73 68 minecraft:water")
        ctl("command", f'summon minecraft:{entity} {x} {y} 62.5 '
            f'{{NoAI:1b,Silent:1b,PersistenceRequired:1b,Rotation:[180.0f,0.0f],{nbt}Invulnerable:1b}}')
        ctl("tp", x, 69, 57.5)
        ctl("look", 0, 6)
        ctl("wait", 22)
        found = [m for m in ctl("entities", 12, entity)["entities"] if abs(m["pos"][0] - x) < 0.2]
        if len(found) != 1:
            raise RuntimeError(f"Expected one {name} fixture, found {len(found)}")
        views = []
        for index in range(3):
            path = profile / f"{name}-{index}.png"
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing screenshot for {name}")
            views.append(str(path))
            ctl("wait", 7)
        cases[name] = {"complete": True, "entity": found[0], "views": views}


def probe_mob_family(ctl, profile, record):
    cases = record["daily_compat"] = {}

    def command(text):
        result = ctl("command", text)
        if not result.get("ok"):
            raise RuntimeError(f"Fixture command failed: {text}: {result}")

    ctl("time", 1000)
    command("fill -535 68 54 -510 68 74 minecraft:stone")
    command("fill -535 69 54 -510 74 74 minecraft:air")
    command("fill -530 73 61 -527 73 64 minecraft:stone")
    fixtures = [
        ("parched", "parched", -532.5, ""),
        ("stray", "stray", -528.5, ""),
        ("mule_bare", "mule", -524.5, "Tame:1b,"),
        ("mule_equipped", "mule", -520.5, 'Tame:1b,ChestedHorse:1b,equipment:{saddle:{id:"minecraft:saddle",count:1}},'),
        ("cave_spider", "cave_spider", -515.5, ""),
    ]
    for name, kind, x, data in fixtures:
        command(f'summon minecraft:{kind} {x} 69.05 62.5 '
                f'{{NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[180f,0f],{data}Tags:["qa_{name}"]}}')
        ctl("tp", x, 69, 58.5)
        ctl("look-at", x, 69.8, 62.5)
        ctl("wait", 12)
        nearby = [m for m in ctl("mobs", 12)["near"]
                  if m["kind"] == f"minecraft:{kind}" and abs(m["pos"][0] - x) < 0.2]
        if len(nearby) != 1:
            raise RuntimeError(f"Expected one {name} near the fixture position")
        mob = nearby[0]
        if kind == "mule" and any(mob.get(flag) != (name == "mule_equipped") for flag in ("chested", "saddled")):
            raise RuntimeError(f"Unexpected mule equipment state: {mob}")
        views = []
        for view, dx in (("front", 0), ("side", -2.5)):
            ctl("tp", x + dx, 69, 58.5)
            ctl("look-at", x, 69.8, 62.5)
            ctl("wait", 5)
            path = profile / f"{name}-{view}.png"
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing screenshot for {name}")
            views.append(str(path))
        cases[name] = {"complete": True, "mob": mob, "views": views}


def probe_armor_trim(ctl, profile, record):
    case = record["world_compat"]["armor_trim"] = {"complete": False, "views": []}

    def command(text):
        result = ctl("command", text)
        if not result.get("ok"):
            raise RuntimeError(f"Fixture command failed: {text}: {result}")

    def shot(stage):
        path = profile / f"trim-{stage}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing trim screenshot {stage}")
        case["views"].append(str(path))

    def slot_for(item):
        return next(s["slot"] for s in ctl("inventory")["hotbar"]
                    if s and s["item"] == f"minecraft:{item}")

    command("gamemode survival")
    command("clear @s")
    ctl("tp", -527.5, 69, 57.5)
    ctl("look", 0, 10)
    command("fill -532 68 54 -523 68 64 minecraft:stone")
    command("fill -532 69 54 -523 74 64 minecraft:air")
    command("setblock -528 69 60 minecraft:smithing_table")
    items = ("sentry_armor_trim_smithing_template", "diamond_chestplate", "redstone")
    for item in items:
        command(f"give @s minecraft:{item}")
    ctl("wait", 10)
    ctl("interact", -528, 69, 60)
    ctl("wait-for", "screen", "station", "--timeout", "10")
    if ctl("menu").get("station") != "Smithing":
        raise RuntimeError("Trim fixture did not open smithing")
    for item in items:
        ctl("click-slot", slot_for(item), "shift")
        ctl("wait", 5)
    result = next((s["stack"] for s in ctl("menu")["slots"] if s["slot"] == 650), {})
    if result.get("item") != "minecraft:diamond_chestplate" or result.get("trim") != ["minecraft:redstone", "minecraft:sentry"]:
        raise RuntimeError(f"Unexpected armor trim output {result}")
    shot("result")
    ctl("click-slot", 650, "shift")
    ctl("wait", 8)
    ctl("key", "esc", "tap")
    ctl("key", "e", "tap")
    ctl("wait-for", "screen", "inventory", "--timeout", "10")
    ctl("click-slot", slot_for("diamond_chestplate"), "shift")
    ctl("wait", 8)
    equipped = next(s["stack"] for s in ctl("menu")["slots"] if s["slot"] == 501)
    if equipped.get("trim") != result["trim"]:
        raise RuntimeError(f"Trim changed while equipping {equipped}")
    shot("equipped")
    ctl("key", "esc", "tap")
    ctl("key", "f5", "tap")
    ctl("key", "f5", "tap")
    ctl("key", "f1", "tap")
    ctl("wait", 8)
    shot("third-person")
    ctl("key", "f1", "tap")
    ctl("key", "f5", "tap")
    case.update(complete=True, trim=result["trim"])


def probe_charged_creeper(ctl, profile, record):
    cases = record["daily_compat"] = {}
    ctl("time", 1000)
    ctl("command", "fill -533 68 54 -522 68 70 minecraft:stone")
    ctl("command", "fill -533 69 54 -522 75 70 minecraft:air")
    for name, x, powered in (("regular", -530.5, 0), ("charged", -524.5, 1)):
        tag = f"qa_creeper_{name}"
        result = ctl("command", f'summon minecraft:creeper {x} 69.05 62.5 '
                     f'{{NoAI:1b,Silent:1b,PersistenceRequired:1b,Rotation:[180f,0f],'
                     f'powered:{powered}b,ignited:0b,Tags:["{tag}"]}}')
        if not result.get("ok"):
            raise RuntimeError(f"Failed to summon {name}: {result}")
        ctl("tp", x, 69, 58)
        ctl("look-at", x, 69.85, 62.5)
        ctl("wait", 15)
        nearby = [m for m in ctl("entities", 12, "creeper")["entities"] if abs(m["pos"][0] - x) < 0.2]
        power = ctl("command", f"data get entity @e[tag={tag},limit=1] powered")
        if len(nearby) != 1 or (powered and not any(line.rstrip().endswith("1b") for line in power.get("chat", []))):
            raise RuntimeError(f"Failed to verify {name} creeper: {power}")
        views = []
        for index in range(4):
            if index == 3:
                ctl("tp", x - 2.6, 69, 58)
                ctl("look-at", x, 69.85, 62.5)
            path = profile / f"creeper-{name}-{index}.png"
            ctl("wait", 4)
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing {name} creeper capture")
            views.append(str(path))
        cases[name] = {"complete": True, "entity": nearby[0], "powered_readback": power, "views": views}


def probe_dynamic_light(ctl, profile, record, *, extended=False):
    cases = record["daily_compat"] = {}
    # Keep the whole enclosure in the spawn chunk so it is loaded server-side.
    ctl("command", "fill -533 66 53 -523 75 65 minecraft:stone hollow")
    ctl("command", "gamemode survival")
    ctl("command", "clear @s")
    ctl("command", "give @s minecraft:stick")
    ctl("command", "give @s minecraft:torch")
    ctl("command", "tp @s -528.5 67 55.5 0 0")
    ctl("look", 0, 0)
    ctl("wait", 40)
    position = ctl("status")["player"]["position"]
    if max(abs(value - expected) for value, expected in zip(position, (-528.5, 67, 55.5))) > 0.2:
        raise RuntimeError(f"Player did not arrive inside the sealed cave: {position}")
    for point, expected in [((-529, 67, 55), "air"), ((-529, 66, 55), "stone"), ((-529, 75, 55), "stone")]:
        state = ctl("block", *point)
        if not state["loaded"] or state["block"] != f"minecraft:{expected}":
            raise RuntimeError(f"Invalid cave fixture block at {point}: {state}")
    for name, item in (("unlit", "stick"), ("held", "torch"), ("dropped", None)):
        if item:
            held_slot = next(s["slot"] for s in ctl("inventory")["hotbar"]
                             if s and s["item"] == "minecraft:" + item)
            ctl("hotbar", held_slot + 1)
        else:
            ctl("key", "q", "tap")
        ctl("wait", 16)
        state = ctl("status")
        held = state.get("held")
        if (held and held["item"]) != ("minecraft:" + item if item else None):
            raise RuntimeError(f"Unexpected held item in {name}: {held}")
        drops = ctl("entities", 8, "item")["entities"] if not item else []
        if not item and not any(entity["item"]["item"] == "minecraft:torch" for entity in drops):
            raise RuntimeError("Dropped torch was not observed")
        path = profile / f"dynamic-light-{name}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing {name} light capture")
        cases[name] = {"complete": True, "view": str(path), "held": held, "drops": drops}

    if not extended:
        return

    torch_id = "minecraft:torch"
    camera = ctl("status")
    camera_position = camera["player"]["position"]
    camera_angles = [camera["yaw"], camera["pitch"]]

    def distance(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5

    def torch_drops():
        return [drop for drop in ctl("entities", 8, "item")["entities"]
                if drop["item"]["item"] == torch_id]

    def capture(name, expected_held, drops, **details):
        state = ctl("status")
        position = state["player"]["position"]
        angles = [state["yaw"], state["pitch"]]
        held = state.get("held")
        if (distance(position, camera_position) > 0.05 or distance(angles, camera_angles) > 0.1
                or (held and held["item"]) != expected_held):
            raise RuntimeError(f"Unexpected {name} cave camera or held item: {position}, {angles}, {held}")
        path = profile / f"dynamic-light-{name}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing {name} light capture")
        cases[name] = {"complete": True, "view": str(path), "held": held, "drops": drops,
                       "camera": {"position": position, "yaw": angles[0], "pitch": angles[1]}, **details}

    # Settle the original toss first so teleporting it cannot carry residual throw velocity.
    ctl("wait", 24)
    original = torch_drops()
    first_ids = [drop["id"] for drop in cases["dropped"]["drops"] if drop["item"]["item"] == torch_id]
    if len(original) != 1 or first_ids != [original[0]["id"]]:
        raise RuntimeError(f"Expected the original dropped torch before relocation: {original}")
    target = (-525.5, 67.0, 60.5)
    ctl("command", 'tp @e[type=minecraft:item,distance=..8,limit=1,nbt={Item:{id:"minecraft:torch"}}] '
                   + " ".join(map(str, target)))
    ctl("wait", 24)
    moved = torch_drops()
    if (len(moved) != 1 or moved[0]["id"] != original[0]["id"]
            or distance(moved[0]["pos"], target) > 0.4
            or distance(moved[0]["pos"], original[0]["pos"]) < 2):
        raise RuntimeError(f"The original torch did not reach the relocation target: {moved}")
    capture("moved_dropped", None, moved, original_position=original[0]["pos"])

    before_pickup = ctl("inventory")["counts"].get(torch_id, 0)
    if before_pickup != 0:
        raise RuntimeError(f"Expected an empty torch inventory before pickup: {before_pickup}")
    pickup_position = " ".join(f"{value:.6f}" for value in moved[0]["pos"])
    ctl("command", f"tp @s {pickup_position} 0 0")
    ctl("wait", 24)
    after_pickup = ctl("inventory")["counts"].get(torch_id, 0)
    if after_pickup != moved[0]["item"]["count"] or torch_drops():
        raise RuntimeError(f"The player did not pick up the relocated torch: {after_pickup}")

    ctl("command", "tp @s -528.5 67 55.5 0 0")
    ctl("look", 0, 0)
    stick = next(s for s in ctl("inventory")["hotbar"] if s and s["item"] == "minecraft:stick")
    ctl("hotbar", stick["slot"] + 1)
    ctl("wait", 16)
    remaining = torch_drops()
    if remaining:
        raise RuntimeError(f"A dropped torch is still visible from the cave camera: {remaining}")
    capture("picked_up", "minecraft:stick", remaining, picked_up_count=after_pickup)


def probe_part_textures(ctl, profile, record, *, variants=False):
    cases = record["daily_compat"] = {}
    fixtures = [
        ("wandering_trader", ""), ("iron_golem", ""), ("pillager", ""), ("vindicator", ""),
        ("mule", "Tame:1b,ChestedHorse:1b,"), ("donkey", "Tame:1b,ChestedHorse:1b,"),
        ("llama", "Tame:1b,ChestedHorse:1b,"), ("trader_llama", "Tame:1b,ChestedHorse:1b,"),
        ("stray", ""), ("bogged", ""), ("sheep", "Color:14b,"),
    ]
    ctl("time", 1000)
    for text in ("fill -536 68 53 -476 68 70 minecraft:stone",
                 "fill -536 69 53 -476 75 70 minecraft:air",
                 "fill -499 73 61 -490 73 64 minecraft:stone"):
        ctl("command", text)
    subjects = [(kind, kind, data) for kind, data in fixtures]
    if variants:
        subjects.append(("iron_golem_named", "iron_golem", 'CustomName:"Cletus",Tags:["qa_cletus"],'))
    for index, (name, kind, data) in enumerate(subjects):
        x = -532.5 + index * 4.5
        result = ctl("command", f'summon minecraft:{kind} {x} 69.05 62.5 '
                     f'{{NoAI:1b,PersistenceRequired:1b,Silent:1b,Rotation:[180f,0f],{data}Invulnerable:1b}}')
        if not result.get("ok"):
            raise RuntimeError(f"Failed to summon {kind}: {result}")
        ctl("tp", x - 2.6, 69, 59)
        ctl("look-at", x, 69.9, 62.5)
        ctl("wait", 10)
        found = [m for m in ctl("entities", 12, kind)["entities"] if abs(m["pos"][0] - x) < 0.2]
        if len(found) != 1:
            raise RuntimeError(f"Expected one {kind} texture fixture")
        if name == "iron_golem_named":
            named = ctl("command", "data get entity @e[tag=qa_cletus,limit=1] CustomName")
            if not named.get("ok") or not any("Cletus" in line for line in named.get("chat", [])):
                raise RuntimeError(f"Named golem variant was not verified: {named}")
        views = []
        for suffix, dx, z in (("front-oblique", -2.6, 59), ("rear-oblique", 2.6, 66)):
            ctl("tp", x + dx, 69, z)
            ctl("look-at", x, 69.9, 62.5)
            ctl("wait", 4)
            path = profile / f"part-{name}-{suffix}.png"
            if not ctl("screenshot", path).get("ok") or not path.is_file():
                raise RuntimeError(f"Missing {kind} texture capture")
            views.append(str(path))
        cases[name] = {"complete": True, "entity": found[0], "views": views}


def probe_bogged_shearing(ctl, profile, record):
    cases = record["daily_compat"]
    ctl("time", 1000)
    ctl("command", "fill -532 68 55 -523 68 65 minecraft:stone")
    ctl("command", "fill -532 69 55 -523 74 65 minecraft:air")
    ctl("command", "fill -529 73 61 -526 73 64 minecraft:stone")
    ctl("command", "gamemode survival")
    ctl("command", "item replace entity @s weapon.mainhand with minecraft:shears")
    ctl("command", "tp @s -527.5 69 60.1 0 0")
    result = ctl("command", 'summon minecraft:bogged -527.5 69.05 62.5 '
                 '{NoAI:1b,Silent:1b,PersistenceRequired:1b,Rotation:[180f,0f]}')
    if not result.get("ok"):
        raise RuntimeError(f"Could not summon bogged: {result}")
    ctl("look-at", -527.5, 70, 62.5)
    ctl("wait", 14)
    held = ctl("status").get("held") or {}
    if held.get("item") != "minecraft:shears":
        raise RuntimeError(f"Shears are not held: {held}")
    for name, expected in (("unshorn", False), ("sheared", True)):
        found = [m for m in ctl("mobs", 8)["near"]
                 if m["kind"] == "minecraft:bogged" and abs(m["pos"][0] + 527.5) < 0.2]
        if len(found) != 1 or found[0].get("sheared") is not expected:
            raise RuntimeError(f"Unexpected bogged {name} state: {found}")
        path = profile / f"bogged-{name}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing bogged {name} capture")
        cases[name] = {"complete": True, "mob": found[0], "view": str(path)}
        if not expected:
            ctl("interact-entity", found[0]["id"])
            ctl("wait", 12)


def probe_skeleton_horse(ctl, profile, record):
    cases = record["daily_compat"]
    ctl("time", 1000)
    ctl("command", "fill -522 68 55 -513 68 65 minecraft:stone")
    ctl("command", "fill -522 69 55 -513 75 65 minecraft:air")
    ctl("command", "tp @s -518.5 69 58.5 0 0")
    summoned = ctl("command", 'summon minecraft:skeleton_horse -518.5 69.05 62.5 '
                   '{NoAI:1b,Tame:1b,Silent:1b,PersistenceRequired:1b,Rotation:[180f,0f],Tags:["qa_skeleton_horse"]}')
    if not summoned.get("ok"):
        raise RuntimeError(f"Could not summon skeleton horse: {summoned}")
    ctl("look-at", -518.5, 70.1, 62.5)
    ctl("wait", 14)
    found = [m for m in ctl("mobs", 10)["near"]
             if m["kind"] == "minecraft:skeleton_horse" and abs(m["pos"][0] + 518.5) < 0.2]
    if len(found) != 1 or found[0].get("saddled") is not False:
        raise RuntimeError(f"Unexpected bare skeleton horse fixture: {found}")
    views = []
    for name, wait in (("idle", 0), ("death-early", 3), ("death-late", 5)):
        if name == "death-early":
            result = ctl("command", "damage @e[type=minecraft:skeleton_horse,tag=qa_skeleton_horse,limit=1] 100 minecraft:generic")
            if not result.get("ok"):
                raise RuntimeError(f"Could not exercise horse death physics: {result}")
        if wait:
            ctl("wait", wait)
        path = profile / f"skeleton-horse-{name}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing skeleton horse {name} capture")
        views.append(str(path))
    cases["skeleton_horse"] = {"complete": True, "mob": found[0], "views": views}


def probe_ghast_harness(ctl, profile, record, *, ropes=False):
    cases = record["daily_compat"]
    ctl("time", 1000)
    ctl("command", "gamemode creative")
    ctl("command", "fill -519 70 55 -506 82 76 minecraft:air")
    if ropes:
        ctl("command", "fill -519 70 55 -506 70 76 minecraft:stone")
    ctl("tp", -512.5, 71, 60.5)
    for command in (
        'summon minecraft:happy_ghast -512.5 72 69.5 {NoAI:1b,NoGravity:1b,Silent:1b,'
        'PersistenceRequired:1b,Rotation:[180f,0f],Tags:["qa_ghast"],UUID:[I;28211,0,0,1],'
        'equipment:{body:{id:"minecraft:red_harness",count:1}}}',
        'summon minecraft:chicken -507.5 71 68.5 {NoAI:1b,Silent:1b,Tags:["qa_rider"]}',
    ):
        reply = ctl("command", command)
        if not reply.get("ok"):
            raise RuntimeError(f"Harness fixture command failed: {reply}")
    if ropes:
        reply = ctl("command", 'summon minecraft:horse -508.5 71 65.5 {NoAI:1b,Silent:1b,'
                    'PersistenceRequired:1b,leash:{UUID:[I;28211,0,0,1]}}')
        if not reply.get("ok"):
            raise RuntimeError(f"Leashed horse fixture failed: {reply}")
    ctl("look-at", -512.5, 74.5, 69.5)
    ctl("wait", 15)
    target = "@e[type=minecraft:happy_ghast,tag=qa_ghast,limit=1]"
    rider = "@e[type=minecraft:chicken,tag=qa_rider,limit=1]"
    def capture(label, side=False):
        path = profile / f"ghast-harness-{label}{'-side' if side else ''}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing ghast harness {label} capture")
        return str(path)

    def angle(side):
        ctl("tp", *(-505.5, 73, 63.5) if side else (-512.5, 71, 60.5))
        ctl("look-at", -512.5, 74.5, 69.5)
        ctl("wait", 12)

    for label, occupied in (("unridden", False), ("ridden", True), ("dismounted", False)):
        if label != "unridden":
            operation = f"mount {target}" if occupied else "dismount"
            reply = ctl("command", f"ride {rider} {operation}")
            if not reply.get("ok"):
                raise RuntimeError(f"Could not set harness rider state: {reply}")
        ctl("wait", 22)
        nearby = ctl("mobs", 20)["near"]
        ghast = next(m for m in nearby if m["kind"] == "minecraft:happy_ghast" and abs(m["pos"][0] + 512.5) < 0.4)
        chicken = next(m for m in nearby if m["kind"] == "minecraft:chicken" and
                       (m.get("mount") == ghast["id"] or abs(m["pos"][0] + 507.5) < 0.4
                        or label == "dismounted" and abs(m["pos"][0] + 512.5) < 1))
        if ghast.get("body") != "minecraft:red_harness" or (chicken.get("mount") == ghast["id"]) != occupied:
            raise RuntimeError(f"Unexpected harness and rider state: {ghast}, {chicken}")
        if ropes:
            horse = next(m for m in nearby if m["kind"] == "minecraft:horse" and abs(m["pos"][0] + 508.5) < 1)
            if horse.get("leash") != f"Mob({ghast['id']})":
                raise RuntimeError(f"Horse is not leashed to the fixture ghast: {horse}")
        case = {"complete": True, "view": capture(label), "ghast": ghast, "rider": chicken}
        if ropes:
            angle(True)
            case["side_view"] = capture(label, side=True)
            angle(False)
        cases["harness_" + label] = case


def probe(ctl, profile, record):
    cases = record["daily_compat"] = {}

    def command(text):
        result = ctl("command", text)
        if not result.get("ok"):
            raise RuntimeError(f"Fixture command failed: {text}: {result}")
        return result

    def shot(name):
        path = profile / f"{name}.png"
        result = ctl("screenshot", path)
        if not result.get("ok") or not path.is_file():
            raise RuntimeError(f"Missing screenshot for {name}")
        return str(path)

    def start():
        ctl("tp", -527.5, 69, 57.5)
        ctl("look", 0, 10)
        ctl("time", 1000)
        ctl("wait", 10)

    def mooshrooms():
        for x, color in [(-529.3, "brown"), (-525.7, "red")]:
            command(f'summon minecraft:mooshroom {x} 69.05 61.5 '
                    f'{{NoAI:1b,Type:"{color}",Rotation:[180.0f,0.0f],PersistenceRequired:1b,Silent:1b}}')
        ctl("wait", 15)
        entities = ctl("entities", 12, "mooshroom")["entities"]
        if len(entities) < 2:
            raise RuntimeError("Both mooshroom variants must be present")
        front = shot("mooshrooms-front")
        ctl("tp", -532.5, 70, 59.5)
        ctl("look", -64, 12)
        ctl("wait", 10)
        return {"entities": entities, "views": [front, shot("mooshrooms-oblique")]}

    def player_walk():
        start()
        ctl("key", "f5", "tap")
        ctl("key", "f5", "tap")
        ctl("wait", 8)
        before = ctl("status")["player"]
        views = [shot("player-idle")]
        try:
            ctl("key", "w", "down")
            for tick in (3, 6, 9):
                ctl("wait", 3)
                views.append(shot(f"player-walk-{tick}"))
            after = ctl("status")["player"]
            ctl("key", "space", "tap")
            ctl("wait", 3)
            views.append(shot("player-jump"))
        finally:
            ctl("release")
            ctl("key", "f5", "tap")
        if abs(after["position"][2] - before["position"][2]) < 0.3:
            raise RuntimeError("Walking fixture did not move the player")
        return {"before": before, "after": after, "views": views}

    def smithing():
        start()
        command("gamemode survival")
        command("clear @s")
        items = ["netherite_upgrade_smithing_template", "diamond_sword", "netherite_ingot"]
        for item in items:
            command(f"give @s minecraft:{item}")
        at = (-528, 69, 60)
        command(f"setblock {' '.join(map(str, at))} minecraft:smithing_table")
        ctl("wait", 10)
        ctl("interact", *at)
        ctl("wait-for", "screen", "station", "--timeout", "10")
        if ctl("menu").get("station") != "Smithing":
            raise RuntimeError("Smithing station did not open")
        views = [shot("smithing-empty")]
        try:
            ctl("key", "j", "tap")
            for index, item in enumerate(items):
                hotbar = ctl("inventory")["hotbar"]
                slot = next(s["slot"] for s in hotbar if s and s["item"] == f"minecraft:{item}")
                ctl("click-slot", slot, "shift")
                ctl("wait", 5)
                if index == 0:
                    views.append(shot("smithing-template-only"))
            menu = ctl("menu")
            result = next((s["stack"] for s in menu["slots"] if s["slot"] == 650), None)
            if result is None or result["item"] != "minecraft:netherite_sword":
                slots = {s["slot"]: s["stack"]["item"] for s in menu["slots"] if s["slot"] >= 600}
                raise RuntimeError(f"Expected a netherite sword in result slot, got {slots}")
            views.append(shot("smithing-result"))
            ctl("click-slot", 650, "shift")
            ctl("wait", 10)
            if any(s["slot"] >= 600 for s in ctl("menu")["slots"]):
                raise RuntimeError("Smithing input/result slots did not clear after transfer")
            hotbar = ctl("inventory")["hotbar"]
            if not any(s and s["item"] == "minecraft:netherite_sword" for s in hotbar):
                raise RuntimeError("The upgraded sword was not transferred to the player")
        finally:
            ctl("key", "esc", "tap")
            command("gamemode creative")
        return {"result": result, "views": views, "recipe_transfer": True}

    def cave():
        command("fill -550 66 53 -538 75 65 minecraft:stone hollow")
        ctl("tp", -544.5, 67, 55.5)
        ctl("look", 0, 0)
        ctl("wait", 40)
        effects_before = ctl("effects")["effects"]
        views = [shot("cave-default-off")]
        ctl("key", "j", "tap")
        try:
            ctl("wait", 12)
            views.append(shot("cave-after-first-j"))
        finally:
            ctl("key", "j", "tap")
        ctl("wait", 12)
        views.append(shot("cave-after-second-j"))
        if ctl("effects")["effects"] != effects_before:
            raise RuntimeError("Cave toggle altered gameplay effects")
        return {"views": views, "effects_unchanged": True}

    start()
    command("fill -535 68 54 -514 68 76 minecraft:stone")
    command("fill -535 69 54 -514 74 76 minecraft:air")
    ctl("wait", 20)
    for name, run in [("mooshrooms", mooshrooms), ("player_walk", player_walk),
                      ("smithing", smithing), ("cave", cave)]:
        try:
            cases[name] = {"complete": True, **run()}
        except (RuntimeError, KeyError, StopIteration, ValueError) as error:
            cases[name] = {"complete": False, "error": f"{type(error).__name__}: {error}"}
            ctl("release")
            if ctl("status")["screen"] in ("inventory", "station"):
                ctl("key", "esc", "tap")
    start()
