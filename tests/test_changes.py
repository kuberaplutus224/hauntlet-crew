import copy
import json
import random

from hypothesis import given, strategies as st

from warden.changes import MAX_LEN, PREFIX, Change, detect, render

ROOMS = ["threshold", "poltergeist", "parlor"]
LEVELS = ["L0", "L1", "L2", "L3", "L4"]


def rec(levels=None, *, passed=True, status=None, errors=None, drift=None):
    levels = levels or {}
    rooms = {r: {a: {"worst": levels.get((r, a), "L4" if a == "naive" else "L0"), "error": None}
                 for a in ("naive", "hardened")} for r in ROOMS}
    errors = errors or []
    st_ = status or ("error" if errors else "failed" if passed is False else "ok")
    return {"status": st_, "selftest": {"passed": passed}, "rooms": rooms, "errors": errors, "drift": drift}


def drift(items, ws="/ws", status=None):
    files = {}
    for item, s in items.items():
        files.setdefault(item.split("#")[0], {"status": s, "items": []})["items"].append({"item": item, "status": s})
    return {"workspace": ws, "status": status or "x", "files": files}


def kinds(changes):
    return [c.kind for c in changes]


def test_baseline_notifies_only_selftest_and_run_error():
    assert detect(None, rec()) == []
    assert kinds(detect(None, rec(passed=False))) == ["selftest"]
    assert kinds(detect(None, rec(errors=[{"command": "run parlor naive", "kind": "timeout"}]))) == ["run_error"]


def test_level_change():
    ch = detect(rec(), rec({("poltergeist", "hardened"): "L2"}))
    assert ch == [Change("level", "poltergeist/hardened", "L0", "L2")]


def test_selftest_failing_and_recovering():
    assert kinds(detect(rec(), rec(passed=False))) == ["selftest"]
    assert detect(rec(passed=False), rec(passed=False)) == []
    assert kinds(detect(rec(passed=False), rec())) == ["selftest_recovered"]


def test_run_error_notifies_once_per_failure_shape():
    e1 = [{"command": "selftest", "kind": "unsynced"}]
    e2 = [{"command": "demo threshold", "kind": "timeout"}]
    assert kinds(detect(rec(), rec(errors=e1))) == ["run_error"]
    assert detect(rec(errors=e1), rec(errors=e1)) == []
    assert kinds(detect(rec(errors=e1), rec(errors=e2))) == ["run_error"]
    assert detect(rec(errors=e1), rec()) == []  # recovery from an error does not notify by itself


def test_errored_room_yields_no_level_change():
    a, b = rec(), rec({("threshold", "naive"): "L0"})
    b["rooms"]["threshold"]["naive"]["error"] = "timeout: killed"
    assert detect(a, b) == []


def test_drift_changes():
    a = rec(drift=drift({"f#A": "present", "f#B": "weaker"}))
    b = rec(drift=drift({"f#A": "missing", "f#B": "weaker", "f#C": "weaker", "f#D": "present"}))
    ch = detect(a, b)
    assert ch == [Change("drift", "f#A", "present", "missing"), Change("drift", "f#C", None, "weaker")]
    assert detect(b, rec(drift=drift({"f#A": "present"}))) == []  # improvements alone


def test_drift_baseline_on_workspace_change_or_special_status():
    a = rec(drift=drift({"f#A": "present"}, ws="/one"))
    b = rec(drift=drift({"f#A": "missing"}, ws="/two"))
    assert detect(a, b) == []
    c = rec(drift=drift({}, ws="/one", status="no reference yet"))
    d = rec(drift=drift({"f#A": "missing"}, ws="/one"))
    assert detect(c, d) == []


def test_not_comparable_records():
    assert detect(rec(), rec(status="skipped")) == []
    assert detect(rec(), rec(status="not_configured")) == []
    assert kinds(detect(rec(status="skipped"), rec(passed=False))) == ["selftest"]


def test_render_is_one_short_line():
    ch = [Change("level", f"room{i}/naive", "L0", "L4") for i in range(40)]
    line = render(ch)
    assert line.startswith(PREFIX) and len(line) <= MAX_LEN and "\n" not in line and line.endswith("more")
    assert render([Change("selftest", "selftest", None, "failing")]) == "Hauntlet Warden: selftest failing"
    one = render([Change("drift", "x" * 400, None, "missing")])
    assert len(one) <= MAX_LEN
    assert "uv sync" in render([Change("run_error", "selftest", None, "unsynced")])


def test_render_masks():
    assert "HAUNTLET-DUMMY-…" in render([Change("drift", "HAUNTLET-DUMMY-abc#x", None, "missing")])


# -- property P5 -----------------------------------------------------------------

level_maps = st.dictionaries(st.tuples(st.sampled_from(ROOMS), st.sampled_from(["naive", "hardened"])),
                             st.sampled_from(LEVELS), max_size=6)
drift_maps = st.dictionaries(st.sampled_from([f"f#{c}" for c in "ABCDE"]),
                             st.sampled_from(["present", "missing", "weaker", "review", "n/a"]), max_size=5)
records = st.builds(lambda lv, p, d: rec(lv, passed=p, drift=drift(d)), level_maps, st.booleans(), drift_maps)


def _reorder(r, seed):
    rnd = random.Random(seed)

    def shuffle(o):
        if isinstance(o, dict):
            items = list(o.items())
            rnd.shuffle(items)
            return {k: shuffle(v) for k, v in items}
        if isinstance(o, list):
            return [shuffle(v) for v in o]
        return o

    return shuffle(copy.deepcopy(r))


@given(records, st.integers(0, 1000))
def test_p5_self_and_reordered_yield_nothing(r, seed):
    assert detect(r, r) == []
    assert detect(r, _reorder(r, seed)) == []
    assert detect(_reorder(r, seed), r) == []


@given(records, records)
def test_p5_fires_only_on_real_changes(a, b):
    ch = detect(a, b)
    level = {c.key for c in ch if c.kind == "level"}
    want_level = {f"{r}/{ag}" for r in ROOMS for ag in ("naive", "hardened")
                  if a["rooms"][r][ag]["worst"] != b["rooms"][r][ag]["worst"]}
    assert level == want_level
    assert ("selftest" in kinds(ch)) == (b["selftest"]["passed"] is False and a["selftest"]["passed"] is not False)
    assert ("selftest_recovered" in kinds(ch)) == (b["selftest"]["passed"] is True and a["selftest"]["passed"] is False)
    old = {r["item"]: r["status"] for f in a["drift"]["files"].values() for r in f["items"]}
    new = {r["item"]: r["status"] for f in b["drift"]["files"].values() for r in f["items"]}
    want_drift = {i for i, s in new.items() if s in ("missing", "weaker") and old.get(i) != s}
    assert {c.key for c in ch if c.kind == "drift"} == want_drift
    assert ch == sorted(ch, key=Change.sort_key)
    json.dumps([c.to_dict() for c in ch])
