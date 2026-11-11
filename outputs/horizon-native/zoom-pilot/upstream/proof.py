"""Zoom in a running modded game: the WebAssembly Zoom's settings files are read and written as they
were, the player's key choice holds, the wheel zooms instead of moving the hotbar, and the view zooms."""
import json
import time
from game import Game, difference

DATA = "horizon-mods/.horizon-mod-data/zoom"
# A player's settings from the WebAssembly Zoom: 8x, no smoothing, the key moved to C.
FILES = {f"{DATA}/level": "8", f"{DATA}/smooth": "false", "horizon-mods.txt": "key.zoom.zoom:key.keyboard.c\n"}


def run(ctl, resources, out):
    with Game(ctl, resources, out, FILES) as g:
        results = {}
        g.run("options", "mods")
        assert "Zoom 2.0.0: ON" in g.labels(), g.labels()
        g.run("click", g.ids()["Settings"])
        page = g.labels()
        assert page[:5] == ["Zoom key", "C", "Starting zoom: 8x", "Smooth zoom: OFF", "Slower turning: ON"], page
        g.shot("settings-page")
        g.play()
        g.run("command", "tp @s ~ ~ ~ 0 10")
        time.sleep(2)
        base = g.shot("1-normal")
        g.run("key", "z", "down")
        time.sleep(1)
        unbound = g.shot("2-z-not-bound")
        g.run("key", "z", "up")
        g.run("key", "c", "down")
        time.sleep(1)
        zoomed = g.shot("3-c-held-8x")
        slot = g.run("state")["selected"]
        g.run("scroll-at", "640", "360", "-3")
        time.sleep(1)
        results["wheel_kept_slot_while_held"] = g.run("state")["selected"] == slot
        g.run("key", "c", "up")
        time.sleep(1)
        released = g.shot("4-released")
        g.run("scroll-at", "640", "360", "-1")
        results["wheel_moves_slot_after"] = g.run("state")["selected"] != slot
        results["diff_unbound_key"] = round(difference(base, unbound), 1)
        results["diff_zoomed"] = round(difference(base, zoomed), 1)
        results["diff_released"] = round(difference(base, released), 1)
        assert results["wheel_kept_slot_while_held"] and results["wheel_moves_slot_after"], results
        assert results["diff_zoomed"] > 3 * max(results["diff_unbound_key"], results["diff_released"], 1), results
        # The page writes the WebAssembly Zoom's files.
        g.run("options", "mods")
        g.run("click", g.ids()["Settings"])
        ids = g.ids()
        g.run("click", ids["Starting zoom: 8x"])
        g.run("click", ids["Smooth zoom: OFF"])
        g.run("click", ids["C"])
        g.run("key", "x", "tap")
        stored = {k: (g.home / DATA / k).read_text() for k in ("level", "smooth", "sensitivity")}
        keys = (g.home / "horizon-mods.txt").read_text()
        results["stored"] = stored
        assert stored == {"level": "10", "smooth": "true", "sensitivity": "true"}, stored
        assert "key.zoom.zoom:key.keyboard.x" in keys, keys
        print(json.dumps({"proof": "zoom", "ok": True, **results}, indent=2))
