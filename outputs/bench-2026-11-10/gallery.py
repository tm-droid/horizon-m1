#!/usr/bin/env python3
"""Visual gallery of every living mob (+variants) and every resource-pack-modified item in Horizon.

  gallery.py VERSION_DIR_NAME [--no-shader] [--only mobs|items] [--filter substr] [--dry-run]
             [--budget SECONDS] [--settle SECONDS] [--side-yaw DEG]

Stages a disposable copy of the user's real game setup (verify3.stage_user), builds a neutral platform
at y=199 (backdrop wall, barrier roof so NoAI undead do not sunburn) far above terrain, then for each
lineup: summon (NoAI/Silent/Invulnerable/PersistenceRequired) -> screenshot front -> (optional) re-summon
rotated -> screenshot side -> kill.  Items: invisible fixed item frames on the backdrop wall in 8x4
batches, plus held-in-hand shots for the most notable overrides.

Output: bench.OUT/gallery-<ver>[-noshader]/  <idx>-<label>.png, index.json, latest.log, console.log.
Commands/NBT used (all verified present in the client source): summon with NBT (NoAI, Silent, Invulnerable,
PersistenceRequired, Rotation, Age, IsBaby, Color, Sheared, powered, variant, Type, Variant, RabbitType,
HasLeftHorn/HasRightHorn, IsScreamingGoat, MainGene/HiddenGene, VillagerData, PuffState, Size, equipment,
Invul, ShowArms, Small, carriedBlockState), item_frame NBT (Facing, Item, Fixed, Invisible, block_pos),
fill, setblock, kill, give, select, gamemode, time, weather, difficulty, gamerule (26.x names
advance_time / spawn_mobs; legacy names as fallback).  Not found in source: snow golem `Pumpkin` key
(sheared snow golem may render plain), no NBT-level tropical-fish/horse validation (values follow vanilla packing).
"""
import argparse, json, math, os, re, shlex, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench  # noqa: E402
import verify3  # noqa: E402

GAME = verify3.GAME
ZM = 24            # mob row, blocks in front of origin z
WALL_Z = 35        # backdrop wall z offset; frames sit at WALL_Z-1
PLAT_Y = 199       # platform top block y (standing y = 200)
AQUATIC = {"cod", "salmon", "pufferfish", "tropical_fish", "squid", "glow_squid", "dolphin", "guardian",
           "elder_guardian", "axolotl", "tadpole", "nautilus", "zombie_nautilus"}
BABY_KINDS = ("cow pig sheep chicken horse donkey mule llama trader_llama rabbit wolf cat ocelot fox panda polar_bear "
              "goat villager zombie husk drowned zombie_villager zombified_piglin piglin hoglin zoglin strider turtle "
              "camel camel_husk sniffer armadillo bee mooshroom happy_ghast nautilus zombie_nautilus axolotl "
              "skeleton_horse zombie_horse parched").split()
SHEEP = "white orange magenta light_blue yellow lime pink gray light_gray cyan purple blue brown green red black".split()
BIOMES = "desert jungle plains savanna snow swamp taiga".split()
PROFS = ("none farmer librarian cleric armorer butcher cartographer fisherman fletcher leatherworker mason nitwit "
         "shepherd toolsmith weaponsmith").split()
PROFS_SHOWN = ["farmer", "librarian", "cleric", "armorer"]
MATERIALS = "leather chainmail iron golden diamond netherite copper".split()
TF_COLORS = [(14, 0), (1, 11), (4, 3), (15, 6), (9, 10), (5, 2), (12, 7), (0, 14), (6, 13), (3, 8), (10, 1), (2, 12)]


# ---------------------------------------------------------------- data sources
def vdir(ver):
    return bench.VERS / ver / ".local/horizon-client/26.3"


def load_registry(ver):
    v = vdir(ver)
    types = json.loads((v / "entity-types.json").read_text())
    living = [k[10:] for k, d in types.items() if "attributes" in d and k != "minecraft:player"]
    size = {k[10:]: (d["width"], d["height"]) for k, d in types.items()}
    items = {k[10:] for k in json.loads((v / "items.json").read_text())}
    var = {}
    for d in ("cat_variant", "wolf_variant", "frog_variant", "pig_variant", "cow_variant", "chicken_variant",
              "zombie_nautilus_variant"):
        p = v / "data/minecraft" / d
        var[d] = sorted(f.stem for f in p.glob("*.json")) if p.exists() else []
    return living, size, items, var


def selected_packs():
    txt = (GAME / "options.txt").read_text()
    m = re.search(r"(?m)^resourcePacks:(.*)$", txt)
    sel = json.loads(m.group(1)) if m else []
    return [s.removeprefix("file/") for s in sel if s != "vanilla" and not s.startswith("vanilla")]


def scan_items(items):
    """item name -> {"kinds": set, "packs": set} for vanilla items touched by the staged resourcepacks."""
    found, missing = {}, []
    pats = [(re.compile(r"^assets/minecraft/items/([^/]+)\.json$"), "items-def"),
            (re.compile(r"^assets/minecraft/models/item/([^/]+)\.json$"), "model"),
            (re.compile(r"^assets/minecraft/textures/item/([^/]+)\.png$"), "texture")]
    cit = re.compile(r"^assets/minecraft/(?:optifine|mcpatcher)/cit/.+\.properties$")

    def note(name, kind, pack):
        if name in items:
            e = found.setdefault(name, {"kinds": set(), "packs": set()})
            e["kinds"].add(kind); e["packs"].add(pack)

    def cit_items(text):
        out = []
        for line in text.splitlines():
            k, _, val = line.partition("=")
            if k.strip() in ("items", "matchItems"):
                out += [t.split(":")[-1] for t in val.split() if t]
        return out

    for pk in selected_packs():
        p = GAME / "resourcepacks" / pk
        try:
            if p.is_file():
                with zipfile.ZipFile(p) as zf:
                    for n in zf.namelist():
                        for rx, kind in pats:
                            m = rx.match(n)
                            if m:
                                note(m.group(1), kind, pk)
                        if cit.match(n):
                            for it in cit_items(zf.read(n).decode("utf8", "replace")):
                                note(it, "cit", pk)
            elif p.is_dir():
                for root, _, files in os.walk(p):
                    for f in files:
                        n = str(Path(root, f).relative_to(p)).replace(os.sep, "/")
                        for rx, kind in pats:
                            m = rx.match(n)
                            if m:
                                note(m.group(1), kind, pk)
                        if cit.match(n):
                            for it in cit_items(Path(root, f).read_text("utf8", "replace")):
                                note(it, "cit", pk)
            else:
                missing.append(pk)
        except Exception as e:  # noqa: BLE001
            missing.append(f"{pk} ({e})")
    return found, missing


# ---------------------------------------------------------------- plan
def ent(kind, nbt="", label=None, side=False):
    return {"kind": kind, "nbt": nbt, "label": label or kind, "side": side}


def item_nbt(items, name, comps=""):
    return f'{{id:"minecraft:{name}",count:1{comps}}}' if name in items else None


def equip(items, **slots):
    parts = []
    for slot, name in slots.items():
        it = item_nbt(items, name) if not name.startswith("{") else name
        if it:
            parts.append(f"{slot}:{it}")
    return f"equipment:{{{','.join(parts)}}}" if parts else ""


def join(*xs):
    return ",".join(x for x in xs if x)


def plan_mobs(living, size, items, var):
    base = [ent(k, side=True) for k in living]
    V = []  # variants; (ent, ...) side only for shape-changing ones
    L = set(living)

    def add(e):
        if e["kind"] in L:
            V.append(e)

    for v in var["cat_variant"]:
        add(ent("cat", f'variant:"minecraft:{v}"', f"cat-{v}"))
    add(ent("cat", "Sitting:1b", "cat-sitting"))
    for v in var["wolf_variant"]:
        add(ent("wolf", f'variant:"minecraft:{v}"', f"wolf-{v}"))
    add(ent("wolf", "Tame:1b,CollarColor:14b,Sitting:1b", "wolf-tame-collar-sitting", True))
    add(ent("wolf", join("Tame:1b", equip(items, body="wolf_armor")), "wolf-armor", True))
    for d, kind in (("frog_variant", "frog"), ("pig_variant", "pig"), ("cow_variant", "cow"),
                    ("chicken_variant", "chicken"), ("zombie_nautilus_variant", "zombie_nautilus")):
        for v in var[d]:
            add(ent(kind, f'variant:"minecraft:{v}"', f"{kind}-{v}"))
    add(ent("pig", equip(items, saddle="saddle"), "pig-saddle", True))
    add(ent("mooshroom", 'Type:"red"', "mooshroom-red")); add(ent("mooshroom", 'Type:"brown"', "mooshroom-brown"))
    for i, c in enumerate(SHEEP):
        add(ent("sheep", f"Color:{i}b", f"sheep-{c}"))
    add(ent("sheep", "Sheared:1b", "sheep-sheared", True)); add(ent("sheep", "Sheared:1b,Color:14b", "sheep-sheared-red"))
    for b in BIOMES:
        for p in PROFS_SHOWN:
            add(ent("villager", f'VillagerData:{{type:"minecraft:{b}",profession:"minecraft:{p}",level:2}}', f"villager-{b}-{p}"))
    for p in PROFS:
        if p not in PROFS_SHOWN:
            add(ent("villager", f'VillagerData:{{type:"minecraft:plains",profession:"minecraft:{p}",level:3}}', f"villager-plains-{p}"))
    for b, p in (("plains", "farmer"), ("desert", "librarian"), ("snow", "cleric"), ("swamp", "armorer"), ("jungle", "none")):
        add(ent("zombie_villager", f'VillagerData:{{type:"minecraft:{b}",profession:"minecraft:{p}",level:2}}', f"zombie_villager-{b}-{p}"))
    for i in range(5):
        add(ent("parrot", f"Variant:{i}", f"parrot-{i}"))
        add(ent("axolotl", f"Variant:{i}", f"axolotl-{i}"))
    for i in (0, 1, 2, 3, 4, 5, 99):
        add(ent("rabbit", f"RabbitType:{i}", f"rabbit-{i}"))
    for col in range(7):
        add(ent("horse", f"Variant:{col}", f"horse-color{col}"))
    for col, mk in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 1), (6, 2)):
        add(ent("horse", f"Variant:{col | mk << 8}", f"horse-color{col}-marking{mk}"))
    add(ent("horse", join("Variant:0", equip(items, saddle="saddle", body="diamond_horse_armor")), "horse-saddle-armor", True))
    add(ent("skeleton_horse", equip(items, saddle="saddle"), "skeleton_horse-saddle", True))
    for i in range(4):
        add(ent("llama", f"Variant:{i}", f"llama-{i}")); add(ent("trader_llama", f"Variant:{i}", f"trader_llama-{i}"))
    add(ent("llama", equip(items, body="red_carpet"), "llama-carpet", True))
    add(ent("camel", equip(items, saddle="saddle"), "camel-saddle", True))
    add(ent("happy_ghast", equip(items, body="blue_harness"), "happy_ghast-harness", True))
    add(ent("fox", 'Type:"red"', "fox-red")); add(ent("fox", 'Type:"snow"', "fox-snow"))
    add(ent("fox", 'Type:"snow",Sleeping:1b', "fox-snow-sleeping", True))
    for g in "normal lazy worried playful brown weak aggressive".split():
        add(ent("panda", f'MainGene:"{g}",HiddenGene:"{g}"', f"panda-{g}"))
    add(ent("creeper", "powered:1b", "creeper-charged", True))
    add(ent("iron_golem", "Health:20f", "iron_golem-cracked", True)); add(ent("iron_golem", "Health:60f", "iron_golem-damaged"))
    add(ent("snow_golem", "Pumpkin:0b", "snow_golem-sheared", True))
    add(ent("goat", "HasLeftHorn:0b", "goat-no-left-horn")); add(ent("goat", "HasLeftHorn:0b,HasRightHorn:0b", "goat-no-horns", True))
    add(ent("goat", "IsScreamingGoat:1b", "goat-screaming", True))
    for i, s in enumerate(("small", "medium", "large")):
        add(ent("salmon", f'type:"{s}"', f"salmon-{s}", True))
    add(ent("slime", "Size:0", "slime-tiny")); add(ent("slime", "Size:3", "slime-big", True))
    add(ent("magma_cube", "Size:0", "magma_cube-tiny")); add(ent("magma_cube", "Size:3", "magma_cube-big", True))
    add(ent("pufferfish", "PuffState:1", "pufferfish-half")); add(ent("pufferfish", "PuffState:2", "pufferfish-full"))
    add(ent("wither", "Invul:0,Health:150f", "wither-half-health", True))
    add(ent("guardian", "", "guardian-2", True))
    for i, (kind, pat) in enumerate([("kob", 0), ("sunstreak", 1), ("snooper", 2), ("dasher", 3), ("brinely", 4), ("spotty", 5)]):
        body, pc = TF_COLORS[i]
        add(ent("tropical_fish", f"Variant:{pat << 8 | body << 16 | pc << 24}", f"tropical_fish-small-{kind}"))
    for i, (kind, pat) in enumerate([("flopper", 0), ("stripey", 1), ("glitter", 2), ("blockfish", 3), ("betty", 4), ("clayfish", 5)]):
        body, pc = TF_COLORS[6 + i]
        add(ent("tropical_fish", f"Variant:{1 | pat << 8 | body << 16 | pc << 24}", f"tropical_fish-large-{kind}"))
    # armor stands
    add(ent("armor_stand", "ShowArms:1b", "armor_stand-plain", True)); add(ent("armor_stand", "Small:1b,ShowArms:1b", "armor_stand-small"))
    for m in MATERIALS:
        if f"{m}_helmet" in items:
            add(ent("armor_stand", join("ShowArms:1b", equip(items, head=f"{m}_helmet", chest=f"{m}_chestplate", legs=f"{m}_leggings",
                                                              feet=f"{m}_boots", mainhand=f"{m}_sword", offhand="shield")),
                    f"armor_stand-{m}", m in ("netherite", "diamond")))
    trim = ',components:{"minecraft:trim":{material:"minecraft:gold",pattern:"minecraft:sentry"}}'
    add(ent("armor_stand", equip(items, head=item_nbt(items, "iron_helmet", trim) or "", chest=item_nbt(items, "iron_chestplate", trim) or "",
                                 legs=item_nbt(items, "iron_leggings", trim) or "", feet=item_nbt(items, "iron_boots", trim) or ""),
            "armor_stand-iron-trim-sentry-gold"))
    add(ent("armor_stand", equip(items, chest="elytra", head="turtle_helmet"), "armor_stand-elytra-turtle"))
    add(ent("armor_stand", equip(items, head="player_head", mainhand="trident", offhand="totem_of_undying"), "armor_stand-misc-held", True))
    # geared monsters
    gear = [("zombie", dict(head="netherite_helmet", chest="netherite_chestplate", legs="netherite_leggings", feet="netherite_boots", mainhand="netherite_sword")),
            ("zombie", dict(head="diamond_helmet", chest="iron_chestplate", mainhand="iron_shovel")),
            ("husk", dict(head="iron_helmet", chest="golden_chestplate", mainhand="stone_axe")),
            ("drowned", dict(mainhand="trident")), ("drowned", dict(head="diamond_helmet", offhand="nautilus_shell")),
            ("skeleton", dict(head="chainmail_helmet", chest="chainmail_chestplate", mainhand="bow")),
            ("stray", dict(head="leather_helmet", mainhand="bow")), ("bogged", dict(head="golden_helmet", mainhand="bow")),
            ("wither_skeleton", dict(mainhand="stone_sword")),
            ("piglin", dict(head="golden_helmet", chest="golden_chestplate", mainhand="golden_sword")),
            ("piglin", dict(mainhand="crossbow")), ("piglin_brute", dict(mainhand="golden_axe")),
            ("zombified_piglin", dict(head="golden_helmet", mainhand="golden_sword")),
            ("vindicator", dict(mainhand="iron_axe")), ("pillager", dict(mainhand="crossbow")),
            ("zombie", dict(head="carved_pumpkin")), ("skeleton", dict(head="player_head", mainhand="bow")),
            ("villager", dict(head="iron_helmet")), ("zombie", dict(mainhand="shield", offhand="totem_of_undying"))]
    for kind, slots in gear:
        lab = f"{kind}-geared-" + "-".join(sorted(slots.values()))[:40]
        add(ent(kind, equip(items, **slots), lab, True))
    add(ent("enderman", 'carriedBlockState:{Name:"minecraft:grass_block"}', "enderman-carrying", True))
    # babies
    for k in BABY_KINDS:
        add(ent(k, "Age:-24000,IsBaby:1b", f"baby-{k}", True))
    return base, V


def pack(entries, size):
    """Group consecutive same-family entries into lineups (<=5, <=13 blocks wide, big mobs alone)."""
    lineups, cur, w = [], [], 0.0

    def flush():
        nonlocal cur, w
        if cur:
            lineups.append(cur)
        cur, w = [], 0.0

    for e in entries:
        ww, hh = size.get(e["kind"], (1.0, 1.0))
        if e["nbt"].startswith("Age:-24000"):
            ww, hh = ww * 0.6, hh * 0.6
        solo = ww >= 2.4 or hh >= 3.0
        aq = e["kind"] in AQUATIC
        if solo:
            flush(); lineups.append([e]); continue
        if cur and (len(cur) >= 5 or w + ww + 1.0 > 13.0 or (cur[0]["kind"] in AQUATIC) != aq or cur[0]["label"].startswith("baby-") != e["label"].startswith("baby-")):
            flush()
        cur.append(e); w += ww + 1.0
    flush()
    return lineups


def plan_items(found):
    def key(n):
        k = found[n]["kinds"]
        return (-(("items-def" in k) + ("model" in k) + ("cit" in k)), -len(found[n]["packs"]), n)
    names = sorted(found, key=key)
    notable = [n for n in names if found[n]["kinds"] - {"texture"}]
    return names, notable


def lineup_geometry(line, size):
    ws = []
    for e in line:
        w, h = size.get(e["kind"], (1.0, 1.0))
        if e["nbt"].startswith("Age:-24000"):
            w, h = w * 0.6, h * 0.6
        ws.append((max(w, 0.7), h))
    total = sum(w for w, _ in ws) + 1.0 * (len(ws) - 1)
    xs, x = [], -total / 2
    for w, _ in ws:
        xs.append(x + w / 2); x += w + 1.0
    maxh = max(h for _, h in ws); maxw = max(w for w, _ in ws)
    d = max(5.0, total / 2.2, maxh * 1.7, maxw * 2.0)
    return xs, total, maxh, d


# ---------------------------------------------------------------- run
class Gallery:
    def __init__(self, g, out, profile, args):
        self.g, self.out, self.profile, self.args = g, out, profile, args
        self.idx, self.shots, self.fails = 0, [], []
        self.t0 = time.time()
        self.ox = self.oz = 0
        self.skipped = []
        self.logpos = 0
        self.pool = None

    # --- helpers
    def cmd(self, c):
        try:
            self.g.ctl("command", c)
            return True
        except Exception as e:  # noqa: BLE001
            self.fails.append({"cmd": c[:200], "err": str(e)[:200]})
            print(f"  ! {c[:80]} -> {str(e)[:100]}", flush=True)
            return False

    def batch(self, cmds):
        """Many commands in one horizon-ctl call (script --keep-going); falls back to one by one."""
        f = Path(tempfile.mkstemp(suffix=".txt", dir=str(self.profile))[1])
        f.write_text("".join(f"command {shlex.quote(c)}\n" for c in cmds))
        try:
            # `script` prints one JSON object per command line (NDJSON), not one document.
            g = self.g
            p = subprocess.run([str(g.rel / "horizon-ctl"), "--socket", g.sock, "--timeout", "60", "script", str(f), "--keep-going"],
                               env=g.env, capture_output=True, text=True, timeout=65)
            rs = [json.loads(ln) for ln in p.stdout.splitlines() if ln.strip()]
            bad = [r for r in rs if "error" in r or r.get("ok") is False]
            if bad:  # commands already ran once; report, don't re-run (re-running doubles summons)
                print(f"  script batch: {len(bad)}/{len(rs)} failed: {json.dumps(bad[0])[:160]}", flush=True)
            elif p.returncode or not rs:
                raise RuntimeError(f"rc {p.returncode} {p.stdout[-150:]} {p.stderr[-150:]}")
        except Exception as e:  # noqa: BLE001
            print(f"  script batch failed ({str(e)[:80]}), per-command fallback", flush=True)
            for c in cmds:
                self.cmd(c)
        finally:
            f.unlink(missing_ok=True)

    def logsize(self):
        p = self.profile / "logs/latest.log"
        return p.stat().st_size if p.exists() else 0

    def logdelta(self, pos):
        p = self.profile / "logs/latest.log"
        if not p.exists():
            return []
        with p.open("rb") as fh:
            fh.seek(pos)
            txt = fh.read().decode("utf8", "replace")
        keep, seen = [], set()
        rx = re.compile(r"WARN|ERROR|CEM|texture|model|missing|Failed|Exception", re.I)
        for ln in txt.splitlines():
            if rx.search(ln) and ln not in seen:
                seen.add(ln); keep.append(ln[:300])
        return keep[:40]

    def over_budget(self):
        return time.time() - self.t0 > self.args.budget

    def shoot(self, label, kind, ents, meta, pos):
        self.idx += 1
        name = f"{self.idx:03d}-{re.sub(r'[^A-Za-z0-9_.+-]+', '_', label)[:80]}.png"
        path = self.out / name
        try:
            self.g.ctl("screenshot", str(path), timeout=30)
        except Exception as e:  # noqa: BLE001
            self.fails.append({"shot": name, "err": str(e)[:200]})
            print(f"  ! screenshot {name}: {str(e)[:100]}", flush=True)
        rec = {"file": name, "label": label, "type": kind, "entities": ents, "t": round(time.time() - self.t0, 1),
               "log": self.logdelta(pos), **meta}
        self.shots.append(rec)
        print(f"[{self.idx:3d} {rec['t']:6.1f}s] {name} ({len(rec['log'])} log lines)", flush=True)
        self.write_index()

    def write_index(self, final=False):
        (self.out / "index.json").write_text(json.dumps(
            {"shots": self.shots, "command_failures": self.fails, "skipped": self.skipped, "final": final}, indent=1) + "\n")

    def cleanup(self):
        self.cmd("kill @e[type=!player]")
        if self.pool:
            x0, x1, z0, z1, cx, cz = self.pool
            self.batch([f"fill {x0} 200 {z0} {x1} 203 {z1} air", f"setblock {cx} 203 {cz} air"])
            self.pool = None
        time.sleep(0.8)

    # --- world
    def build_world(self):
        ox, oz = self.ox, self.oz
        c = []
        for y0 in range(200, 216, 4):
            c.append(f"fill {ox-22} {y0} {oz-8} {ox+22} {y0+3} {oz+36} air")
        c += [f"fill {ox-22} {PLAT_Y} {oz-8} {ox+22} {PLAT_Y} {oz+36} smooth_stone",
              f"fill {ox-22} {PLAT_Y} {oz+WALL_Z} {ox+22} 214 {oz+WALL_Z} light_gray_concrete",
              f"fill {ox-22} 216 {oz-8} {ox+22} 216 {oz+36} barrier"]
        for r in ("advance_time:doDaylightCycle", "spawn_mobs:doMobSpawning"):
            new, old = r.split(":")
            if not self.cmd(f"gamerule {new} false"):
                self.cmd(f"gamerule {old} false")
        c = ["gamemode creative", "difficulty normal", "time set 6000", "weather clear", "kill @e[type=!player]"] + c
        self.batch(c)
        time.sleep(2)

    def camera(self, cx, d, maxh, water, y_mob):
        cz = self.oz + ZM - d
        if water:
            self.cmd(f"setblock {cx} 203 {math.floor(cz)} smooth_stone")
            fy = 204
        else:
            fy = 200
        eye = fy + 1.62
        pitch = math.degrees(math.atan2(eye - (y_mob + maxh * 0.5), d))
        self.cmd(f"tp @s {cx} {fy} {cz}")
        try:
            self.g.ctl("tp", cx, fy, cz)
            self.g.ctl("look", 0, round(pitch, 1))
        except Exception as e:  # noqa: BLE001
            self.fails.append({"cam": str(e)[:200]})
        return [cx, fy, round(cz, 2)], round(pitch, 1)

    def spawn_line(self, line, xs, yaw, water):
        cmds = []
        y = 200.3 if water else 200
        for e, x in zip(line, xs):
            nbt = join("NoAI:1b", "Silent:1b", "Invulnerable:1b", "PersistenceRequired:1b", f"Rotation:[{yaw}f,0f]",
                       "Invul:0" if e["kind"] == "wither" else "", e["nbt"])
            ey = y + (2.5 if e["kind"] == "ghast" else 0)  # ghast tentacles hang below its feet; keep them out of the floor
            cmds.append(f"summon minecraft:{e['kind']} {self.ox + x:.2f} {ey} {self.oz + ZM + 0.5} {{{nbt}}}")
        self.batch(cmds)

    def do_lineup(self, line, size, phase, n, total):
        xs, span, maxh, d = lineup_geometry(line, size)
        water = line[0]["kind"] in AQUATIC
        label = "+".join(dict.fromkeys(e["label"] for e in line))[:70]
        cx = self.ox
        if water:
            hw = math.ceil(span / 2 + 2)
            x0, x1, z0, z1 = cx - hw, cx + hw, self.oz + ZM - 3, self.oz + ZM + 3
            cz = math.floor(self.oz + ZM - max(d, 7.0))
            self.pool = (x0, x1, z0, z1, cx, cz)
            d = max(d, 7.0)
            self.batch([f"fill {x0} 200 {z0} {x1} 201 {z0} glass", f"fill {x0} 200 {z1} {x1} 201 {z1} glass",
                        f"fill {x0} 200 {z0} {x0} 201 {z1} glass", f"fill {x1} 200 {z0} {x1} 201 {z1} glass",
                        f"fill {x0+1} 200 {z0+1} {x1-1} 201 {z1-1} water"])
        print(f"{phase} lineup {n}/{total}: {label}", flush=True)
        for side in ([False, True] if any(e["side"] for e in line) else [False]):
            yaw = self.args.side_yaw if side else 180
            pos = self.logsize()
            self.spawn_line(line, xs, yaw, water)
            cam, pitch = self.camera(cx, d, maxh, water, 200.3 if water else 200)
            time.sleep(self.args.settle)
            self.shoot(f"{label}{'-side' if side else ''}", "mobs",
                       [{"kind": e["kind"], "nbt": e["nbt"], "label": e["label"], "x": round(x, 2)} for e, x in zip(line, xs)],
                       {"yaw": yaw, "camera": cam, "pitch": pitch, "view": "side" if side else "front"}, pos)
            self.cmd("kill @e[type=!player]")
            time.sleep(0.8)
        self.cleanup()

    def item_shot(self, names, n, total, found):
        cols, rows = 8, 4
        ox, oz = self.ox, self.oz
        pos = self.logsize()
        cells, cmds = [], []
        for i, nm in enumerate(names):
            r, c = divmod(i, cols)
            x, y, z = ox - 4 + c, 203 - r, oz + WALL_Z - 1
            cells.append({"item": nm, "row": r, "col": c, "cell": [x, y, z], "kinds": sorted(found[nm]["kinds"]),
                          "packs": sorted(found[nm]["packs"])})
            cmds.append(f"summon minecraft:item_frame {x+0.5} {y+0.5} {z+0.5} {{Facing:2b,Fixed:1b,Invisible:1b,block_pos:[I;{x},{y},{z}],"
                        f'Item:{{id:"minecraft:{nm}",count:1}}}}')
        print(f"items shot {n}/{total}: {names[0]} .. {names[-1]}", flush=True)
        self.batch(cmds)
        self.cmd(f"tp @s {ox} 200 {oz + WALL_Z - 1 - 4.4}")
        try:
            self.g.ctl("tp", ox, 200, oz + WALL_Z - 1 - 4.4); self.g.ctl("look", 0, -6)
        except Exception as e:  # noqa: BLE001
            self.fails.append({"cam": str(e)[:200]})
        time.sleep(self.args.settle + 0.8)
        self.shoot(f"items-{n:02d}-{names[0]}", "items", cells, {"grid": f"{cols}x{rows} row0=top, col0=left (viewer's left)"}, pos)
        self.cmd("kill @e[type=!player]")
        time.sleep(0.8)

    def held_shots(self, notable):
        self.g.ctl("key", "f1", "tap")  # HUD (and hand, if F1 hides it) back on
        self.cmd("clear @s")
        self.cmd(f"tp @s {self.ox} 200 {self.oz + WALL_Z - 6}")
        try:
            self.g.ctl("tp", self.ox, 200, self.oz + WALL_Z - 6); self.g.ctl("look", 0, 0)
        except Exception:  # noqa: BLE001
            pass
        for i, nm in enumerate(notable, 1):
            if self.over_budget():
                self.skipped.append(f"held:{nm}..")
                break
            pos = self.logsize()
            try:
                self.g.ctl("give", nm, 1)
                try:
                    self.g.ctl("select", nm)
                except RuntimeError:  # armor from give lands outside the hotbar; put it in the hand directly
                    self.cmd(f"item replace entity @s weapon.mainhand with minecraft:{nm}")
            except Exception as e:  # noqa: BLE001
                self.fails.append({"held": nm, "err": str(e)[:200]}); continue
            time.sleep(0.9)
            self.shoot(f"held-{nm}", "held", [{"item": nm}], {"view": "first-person"}, pos)
            self.cmd("clear @s")
        self.g.ctl("key", "f1", "tap")


def build_plan(args):
    living, size, items, var = load_registry(args.version)
    base, variants = plan_mobs(living, size, items, var)
    found, missing = scan_items(items)
    names, notable = plan_items(found)
    f = args.filter
    if f:
        fs = f.split(",")  # comma-separated substrings, any match
        hit = lambda s: any(x in s for x in fs)  # noqa: E731
        base = [e for e in base if hit(e["label"])]; variants = [e for e in variants if hit(e["label"])]
        names = [n for n in names if hit(n)]; notable = [n for n in notable if hit(n)]
    return {"living": living, "size": size, "base": base, "variants": variants, "found": found, "missing": missing,
            "names": names, "notable": notable[:args.held],
            "base_lines": pack(base, size), "var_lines": pack(variants, size)}


def summary(plan, args):
    nb = sum(len(l) for l in plan["base_lines"]); nv = sum(len(l) for l in plan["var_lines"])
    sides = lambda ls: sum(2 if any(e["side"] for e in l) else 1 for l in ls)  # noqa: E731
    item_shots = math.ceil(len(plan["names"]) / 32) if plan["names"] else 0
    mob_shots = (sides(plan["base_lines"]) + sides(plan["var_lines"])) if args.only != "items" else 0
    item_total = (item_shots + len(plan["notable"])) if args.only != "mobs" else 0
    print(f"living entity types in registry: {len(plan['living'])}")
    print(f"mobs: base {nb} types in {len(plan['base_lines'])} lineups; variants {nv} in {len(plan['var_lines'])} lineups")
    print(f"items: {len(plan['names'])} vanilla items touched by packs ({len(plan['notable'])} held shots; "
          f"{sum(1 for n in plan['found'] if plan['found'][n]['kinds'] - {'texture'})} with model/definition/CIT overrides); "
          f"{item_shots} frame shots")
    print(f"total shots planned: {mob_shots + item_total} (mobs {mob_shots}, items {item_total})")
    if plan["missing"]:
        print("pack scan problems:", plan["missing"][:5])


def dry_run(args, plan):
    print("== base mob lineups")
    for l in plan["base_lines"]:
        print("  ", " | ".join(e["label"] for e in l))
    print("== variant lineups")
    for l in plan["var_lines"]:
        print("  ", " | ".join(e["label"] for e in l))
    print("== items (first 60 of", len(plan["names"]), ")")
    print("  ", " ".join(plan["names"][:60]))
    print("== held notable:", " ".join(plan["notable"]))
    summary(plan, args)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--no-shader", action="store_true")
    ap.add_argument("--only", choices=["mobs", "items"])
    ap.add_argument("--filter", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=780, help="seconds allowed for the shot loop (after world ready)")
    ap.add_argument("--settle", type=float, default=1.4)
    ap.add_argument("--side-yaw", type=int, default=90)
    ap.add_argument("--held", type=int, default=12)
    args = ap.parse_args()

    if not (vdir(args.version)).exists():
        sys.exit(f"no such version dir: {vdir(args.version)}")
    plan = build_plan(args)
    if args.dry_run:
        dry_run(args, plan)
        return

    out = bench.OUT / f"gallery-{args.version}{'-noshader' if args.no_shader else ''}"
    out.mkdir(parents=True, exist_ok=True)
    rec = {"version": args.version, "no_shader": args.no_shader, "gate": bench.gate()}
    profile = bench.PROFILES / f"gallery-{int(time.time())}"
    bench.PROFILES.mkdir(parents=True, exist_ok=True)
    rec["shader"] = verify3.stage_user(profile)
    if args.no_shader:
        for f in (profile / "shaderpacks").glob("*"):
            f.unlink()
        gfx = profile / "horizon-graphics.txt"
        gfx.write_text(re.sub(r"(?m)^pickedShaderPack:.*$", "pickedShaderPack:", gfx.read_text()))
        rec["shader"] = ""
    bench.BUILDS["T"] = args.version; bench.NAMES["T"] = "TEST"
    summary(plan, args)
    was = bench.get_mute(); bench.mute(True)
    g = bench.Game("T", profile, "gallery")
    gal = Gallery(g, out, profile, args)
    t0 = time.time()
    try:
        g.wait_socket(); g.ctl("wait-ready", "240", timeout=245)
        rec["startup_s"] = round(time.time() - t0, 1)
        try:
            rec["settle_s"] = g.settle()
        except Exception as e:  # noqa: BLE001
            rec["settle_warn"] = str(e)
        g.front()
        # origin: chunk-aligned player position
        gal.ox, gal.oz, oy = 0, 0, 80
        try:
            st = g.ctl("state")
            p = st.get("player", {})
            pos = p.get("pos") or p.get("position") or [p.get("x"), p.get("y"), p.get("z")]
            gal.ox, gal.oz = int(pos[0]) // 16 * 16, int(pos[2]) // 16 * 16
        except Exception as e:  # noqa: BLE001
            print("state parse failed, using bench FLY start:", e)
            gal.ox, gal.oz = int(float(bench.FLY[0])) // 16 * 16, int(float(bench.FLY[2])) // 16 * 16
        rec["origin"] = [gal.ox, gal.oz]
        print(f"origin {gal.ox},{gal.oz}", flush=True)
        gal.build_world()
        g.ctl("key", "f1", "tap")  # hide HUD
        gal.t0 = time.time()
        size = plan["size"]
        if args.only != "items":
            bl = plan["base_lines"]
            for n, line in enumerate(bl, 1):
                if gal.over_budget():
                    gal.skipped.append(f"mobs-base from lineup {n}"); break
                gal.do_lineup(line, size, "mobs-base", n, len(bl))
        if args.only != "mobs" and plan["names"]:
            names = plan["names"]
            chunks = [names[i:i + 32] for i in range(0, len(names), 32)]
            for n, ch in enumerate(chunks, 1):
                if gal.over_budget():
                    gal.skipped.append(f"items from shot {n}"); break
                gal.item_shot(ch, n, len(chunks), plan["found"])
            gal.held_shots(plan["notable"])  # toggles F1 on, then off again
        if args.only != "items":
            vl = plan["var_lines"]
            for n, line in enumerate(vl, 1):
                if gal.over_budget():
                    gal.skipped.append(f"mobs-variants from lineup {n}"); break
                gal.do_lineup(line, size, "mobs-variants", n, len(vl))
        rec["ok"] = True
    except Exception as e:  # noqa: BLE001
        rec["error"] = str(e)
        print("ERROR:", e, flush=True)
    finally:
        rec["peak_rss_MB"] = round(g.rss_peak / 1024, 1)
        g.quit(); bench.mute(was)
        rec["exit_code"] = g.p.returncode
    for f in ("console.log", "logs/latest.log"):
        if (profile / f).exists():
            (out / Path(f).name).write_bytes((profile / f).read_bytes())
    gal.write_index(final=True)
    (out / "run.json").write_text(json.dumps({**rec, "shots": len(gal.shots), "skipped": gal.skipped,
                                              "failures": len(gal.fails), "elapsed_s": round(time.time() - t0)}, indent=2) + "\n")
    bench.trash(profile)
    print(json.dumps({k: rec.get(k) for k in ("ok", "error", "startup_s", "peak_rss_MB", "exit_code")}),
          f"shots={len(gal.shots)} skipped={gal.skipped} failures={len(gal.fails)} out={out}")


if __name__ == "__main__":
    main()
