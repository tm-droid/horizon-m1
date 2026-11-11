"""Inspect vanilla menus in the disposable Horizon-Test world."""


def probe(ctl, profile, record):
    cases = record["gui_compat"] = {}
    block_pos = (-528, 69, 60)

    def command(text):
        result = ctl("command", text)
        if not result.get("ok"):
            raise RuntimeError(f"Fixture command failed: {text}: {result}")

    def shot(case, stage):
        path = profile / f"gui-{case}-{stage}.png"
        if not ctl("screenshot", path).get("ok") or not path.is_file():
            raise RuntimeError(f"Missing screenshot for {case} {stage}")
        cases[case]["views"][stage] = str(path)

    def screen(expected):
        ctl("wait-for", "screen", expected, "--timeout", "8", timeout=12)
        ctl("wait", 5)
        return ctl("screen")

    def open_block(block, expected, station=None):
        x, y, z = block_pos
        command(f"setblock {x} {y} {z} minecraft:{block}")
        ctl("wait", 10)
        ctl("interact", *block_pos)
        state = screen(expected)
        if station and state.get("station") != station:
            raise RuntimeError(f"{block} opened unexpected station {state.get('station')}")
        # The integrated client's ender chest uses the remote virtual-container key.
        container_key = [-(2 ** 31), 0, 0] if block == "ender_chest" else list(block_pos)
        if expected == "container" and state.get("container") != container_key:
            raise RuntimeError(f"{block} opened unexpected container {state.get('container')}")
        return state

    def book_state(wanted_open):
        book = ctl("screen")["recipe_book"]
        if book["open"] != wanted_open:
            # The control API lists the toggle before other book targets in GUI pixels.
            x, y, width, height = book["targets"][0]
            ctl("click-at", x + width / 2, y + height / 2)
            ctl("wait", 8)
            book = ctl("screen")["recipe_book"]
        if book["open"] != wanted_open:
            raise RuntimeError(f"Recipe-book toggle did not reach open={wanted_open}")
        if not wanted_open and len(book["targets"]) != 1:
            raise RuntimeError("Closed recipe book did not expose exactly one toggle")
        return book

    def book_views(case):
        closed = book_state(False)
        shot(case, "book-closed")
        opened = book_state(True)
        shot(case, "book-open")
        book_state(False)
        cases[case]["recipe_book"] = {
            "closed_targets": closed["targets"],
            "open_targets": opened["targets"],
            "known_recipes": opened["known"],
        }

    def survival_inventory():
        case = "inventory"
        ctl("key", "e", "tap")
        state = screen("inventory")
        armor_ids = {500, 501, 502, 503}
        armor = {slot["slot"]: slot["item"] for slot in state["slots"] if slot["slot"] in armor_ids}
        if set(armor) != armor_ids or any(armor.values()):
            raise RuntimeError(f"Expected four empty armor slots, got {armor}")
        book_views(case)
        for part, item in (("head", "helmet"), ("chest", "chestplate"),
                           ("legs", "leggings"), ("feet", "boots")):
            command(f"item replace entity @s armor.{part} with minecraft:iron_{item}")
        ctl("wait", 10)
        armor = {slot["slot"]: slot["item"] for slot in ctl("screen")["slots"] if slot["slot"] in armor_ids}
        if set(armor.values()) != {f"minecraft:iron_{piece}" for piece in ("helmet", "chestplate", "leggings", "boots")}:
            raise RuntimeError(f"Expected four equipped armor pieces, got {armor}")
        shot(case, "equipped")
        cases[case]["equipped"] = armor

    def crafting_table():
        case = "crafting_table"
        command("clear @s")
        command("give @s minecraft:oak_planks 2")
        state = open_block(case, "inventory")
        if state["craft_size"] != 3:
            raise RuntimeError(f"Expected a 3×3 crafting grid, got {state['craft_size']}")
        book_views(case)
        hotbar = ctl("inventory")["hotbar"]
        slot = next(s["slot"] for s in hotbar if s and s["item"] == "minecraft:oak_planks")
        ctl("click-slot", slot)
        ctl("click-slot", 100, "right")
        ctl("click-slot", 103, "right")
        ctl("wait", 5)
        result = next(s for s in ctl("screen")["slots"] if s["slot"] == 200)
        if result["item"] != "minecraft:stick" or result["count"] != 4:
            raise RuntimeError(f"Expected four sticks in crafting output, got {result}")
        shot(case, "result")
        ctl("click-slot", 200, "shift")
        ctl("wait", 5)
        counts = ctl("inventory")["counts"]
        if counts.get("minecraft:stick") != 4 or counts.get("minecraft:oak_planks", 0):
            raise RuntimeError(f"Crafted sticks did not transfer or planks remained: {counts}")
        cases[case]["crafted_and_transferred"] = 4

    def container(block):
        open_block(block, "container")
        if block in ("furnace", "blast_furnace", "smoker"):
            book_views(block)
            if block == "furnace":
                command("give @s minecraft:raw_iron")
                command("give @s minecraft:coal")
                for item in ("raw_iron", "coal"):
                    slot = next(s["slot"] for s in ctl("inventory")["hotbar"]
                                if s and s["item"] == f"minecraft:{item}")
                    ctl("click-slot", slot, "shift")
                    ctl("wait", 8)
                shot(block, "burning")
        else:
            shot(block, "open")

    def workstation(block, station):
        if block == "beacon":
            command("fill -529 68 59 -527 68 61 minecraft:iron_block")
        open_block(block, "station", station)
        shot(block, "open")
        if block == "beacon":
            command("give @s minecraft:iron_ingot")
            ctl("wait", 100)
            slot = next(s["slot"] for s in ctl("inventory")["hotbar"]
                        if s and s["item"] == "minecraft:iron_ingot")
            ctl("click-slot", slot, "shift")
            ctl("wait", 10)
            ctl("click-gui", 61, 33)
            ctl("wait", 5)
            shot(block, "haste-selected")
            ctl("click-gui", 148, 118)
            screen("playing")
            for _ in range(5):
                ctl("wait", 20)
                if any(e["id"].removeprefix("minecraft:") == "haste"
                       for e in ctl("effects")["effects"]["active"]):
                    cases[block]["haste_applied"] = True
                    break
            else:
                raise RuntimeError("Haste did not apply after confirming the beacon")

    def powered_crafter():
        command("setblock -528 69 60 minecraft:crafter")
        command("setblock -529 69 60 minecraft:redstone_block")
        ctl("wait", 10)
        ctl("interact", *block_pos)
        screen("container")
        if "triggered=true" not in ctl("block", *block_pos)["state"]:
            raise RuntimeError("Crafter was not powered")
        shot("crafter", "powered")

    def trade():
        command('summon minecraft:villager -524.5 69 58.5 {NoAI:1b,PersistenceRequired:1b,'
                'Xp:1,VillagerData:{type:"minecraft:plains",profession:"minecraft:farmer",level:1},'
                'Offers:{Recipes:[{buy:{id:"minecraft:wheat",count:20},sell:{id:"minecraft:emerald",'
                'count:1},maxUses:16,uses:0,xp:0,priceMultiplier:0f,demand:0},'
                '{buy:{id:"minecraft:carrot",count:20},sell:{id:"minecraft:emerald",count:1},'
                'maxUses:16,uses:16,xp:0,priceMultiplier:0f,demand:0}]}}')
        ctl("wait", 20)
        entity = next(e for e in ctl("entities", 8, "minecraft:villager")["entities"]
                      if abs(e["pos"][0] + 524.5) < 0.5)
        ctl("interact-entity", entity["id"])
        if screen("station").get("station") != "Merchant":
            raise RuntimeError("Villager did not open trading")
        shot("villager", "trade")

    def creative():
        command("gamemode creative")
        ctl("key", "e", "tap")
        screen("creative")
        shot("creative", "open")

    ctl("tp", -527.5, 69, 57.5)
    ctl("look", 0, 10)
    ctl("time", 1000)
    command("fill -532 68 54 -523 68 64 minecraft:stone")
    command("fill -532 69 54 -523 74 64 minecraft:air")
    command("gamemode survival")
    command("clear @s")
    ctl("wait", 15)

    targets = [("inventory", survival_inventory, ()), ("crafting_table", crafting_table, ())]
    for block in ("chest", "barrel", "hopper", "dispenser", "dropper", "furnace", "blast_furnace",
                  "smoker", "brewing_stand", "shulker_box", "ender_chest"):
        targets.append((block, container, (block,)))
    for block, kind in (("anvil", "Anvil"), ("grindstone", "Grindstone"),
                        ("enchanting_table", "Enchanting"), ("loom", "Loom"),
                        ("stonecutter", "Stonecutter"), ("cartography_table", "Cartography"),
                        ("smithing_table", "Smithing"), ("beacon", "Beacon")):
        targets.append((block, workstation, (block, kind)))
    targets.extend([("crafter", powered_crafter, ()), ("villager", trade, ()), ("creative", creative, ())])

    for name, run, args in targets:
        case = cases[name] = {"complete": False, "views": {}}
        try:
            run(*args)
            case["complete"] = True
        except (RuntimeError, KeyError, IndexError, StopIteration, ValueError) as error:
            case["error"] = f"{type(error).__name__}: {error}"
        finally:
            if ctl("screen")["screen"] in ("inventory", "station", "container", "creative"):
                ctl("key", "esc", "tap")
                screen("playing")
