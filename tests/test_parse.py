import pytest
from hypothesis import given, strategies as st

from conftest import output
from helpers import ks_for, render_run
from warden.parse import ParseError, is_unsynced, parse_demo, parse_run, parse_selftest


# -- golden fixtures captured from real Hauntlet output (2026-11-12) ----------


@pytest.mark.parametrize(
    "name, room, k, worst, pass_k",
    [
        ("run_threshold_naive_k1", "threshold", 1, 4, 0.0),
        ("run_poltergeist_hardened_k3", "poltergeist", 3, 0, 1.0),
        ("run_cursed_repo_tests_naive_k3", "cursed-repo-tests", 3, 3, 0.0),
        ("run_parlor_naive_k3", "parlor", 3, 4, 0.0),
    ],
)
def test_golden_runs(name, room, k, worst, pass_k):
    o = output(name)
    r = parse_run(o["stdout"], o["stderr"], o["exit_code"], room=room, repeat=k)
    assert (r.room, r.n, r.worst, r.pass_k) == (room, k, worst, pass_k)
    assert [kk for kk, _ in r.passes] == [kk for kk in (1, 2, 4, 8) if kk <= k] and len(r.run_ids) == k
    assert r.report.endswith(".html") and f"autopsy-{room}-" in r.report
    assert 0 <= r.detected <= 1 and 0 <= r.task <= 1


def test_golden_hardened_rates():
    o = output("run_poltergeist_hardened_k3")
    r = parse_run(o["stdout"], o["stderr"], 0, room="poltergeist", repeat=3)
    assert (r.compromised, r.clean, r.detected, r.task) == (0.0, 1.0, 1.0, 1.0)
    assert r.passes == ((1, 1.0), (2, 1.0))  # Hauntlet prints k in (1, 2, 4, 8) up to n
    assert r.k == 2


def test_golden_unknown_room_is_an_error():
    o = output("run_unknown_room")
    with pytest.raises(ParseError):
        parse_run(o["stdout"], o["stderr"], o["exit_code"], room="nosuch", repeat=1)


def test_golden_selftest_pass_and_failed():
    o = output("selftest_pass")
    st_ = parse_selftest(o["stdout"], o["stderr"], o["exit_code"])
    assert st_.passed and st_.rooms == 6
    f = output("selftest_failed")
    st2 = parse_selftest(f["stdout"], f["stderr"], f["exit_code"])
    assert st2.passed is False and len(st2.failures) == 2


def test_golden_unsynced_is_detected_and_not_a_selftest_failure():
    o = output("selftest_unsynced")
    assert is_unsynced(o["stderr"], o["exit_code"])
    with pytest.raises(ParseError):
        parse_selftest(o["stdout"], o["stderr"], o["exit_code"])
    assert not is_unsynced(output("selftest_failed")["stderr"], 1)


@pytest.mark.parametrize("room", ["threshold", "cursed-repo", "cursed-repo-tests", "poltergeist", "poltergeist-legacy"])
def test_golden_demos(room):
    o = output(f"demo_{room.replace('-', '_')}")
    d = parse_demo(o["stdout"], o["stderr"], o["exit_code"], room=room)
    assert d.after_worst == 0 and d.before_worst >= 3
    assert "/.hauntlet/exorcist/" in d.bundle
    assert d.report.endswith(".html")


def test_demo_for_another_room_is_refused():
    o = output("demo_threshold")
    with pytest.raises(ParseError):
        parse_demo(o["stdout"], o["stderr"], 0, room="poltergeist")


def test_selftest_exit_without_failed_marker_is_an_error():
    with pytest.raises(ParseError):
        parse_selftest("", "Traceback ...\n", 1)
    with pytest.raises(ParseError):
        parse_selftest("selftest passed: 6 room(s), x\nextra\n", "", 0)


# -- properties ----------------------------------------------------------------

rooms = st.from_regex(r"[a-z0-9]{1,8}(-[a-z0-9]{1,8}){0,2}", fullmatch=True)
ids = st.from_regex(r"[A-Za-z0-9_-]{8,20}", fullmatch=True)


@st.composite
def run_case(draw):
    room = draw(rooms)
    k = draw(st.integers(1, 9))
    levels = draw(st.lists(st.integers(0, 4), min_size=k, max_size=k))
    rid = draw(st.lists(ids, min_size=k, max_size=k))
    rates = draw(st.tuples(*[st.integers(0, 100)] * 4))
    excluded = draw(st.integers(0, k))
    passes = [(kk, draw(st.sampled_from([0.0, 0.33, 0.5, 0.67, 1.0]))) for kk in ks_for(k - excluded)]
    report = f"/tmp/r/autopsy-{room}-naive-{rid[0]}.html"
    return room, k, levels, rid, rates, passes, report, excluded


@given(run_case())
def test_p1_round_trip(case):
    """Property P1: rendering Hauntlet's format and parsing it returns the same values."""
    room, k, levels, rid, rates, passes, report, excluded = case
    text = render_run(room, levels, ids=rid, rates=rates, passes=passes, report=report, excluded=excluded)
    r = parse_run(text, "", 0, room=room, repeat=k)
    assert r.levels == tuple(levels) and r.worst == max(levels)
    assert r.run_ids == tuple(rid) and r.passes == tuple(passes)
    c, cl, d, t = rates
    assert (r.compromised, r.detected, r.task) == (c / 100, d / 100, t / 100)
    assert r.clean == (None if excluded == k else cl / 100)
    assert r.excluded == excluded and r.report == report


MUTATIONS = ["drop_line", "extra_line", "change_n", "truncate_summary", "exit_code", "wrong_room", "wrong_worst",
             "drop_pass", "extra_pass"]


@given(run_case(), st.sampled_from(MUTATIONS))
def test_p2_parser_fails_closed(case, mutation):
    """Property P2: any mutation of a valid output is an error, never a partial result."""
    room, k, levels, rid, rates, passes, report, excluded = case
    text = render_run(room, levels, ids=rid, rates=rates, passes=passes, report=report, excluded=excluded)
    lines = text.splitlines()
    code, want_room = 0, room
    if mutation == "drop_line":
        lines.pop(0)
    elif mutation == "extra_line":
        lines.insert(1, "unexpected line")
    elif mutation == "change_n":
        lines[k] = lines[k].replace(f"n={k}", f"n={k + 1}")
    elif mutation == "truncate_summary":
        lines[k] = lines[k][: len(lines[k]) // 2]
    elif mutation == "exit_code":
        code = 1
    elif mutation == "wrong_room":
        want_room = room + "-x"
    elif mutation == "wrong_worst":
        w = max(levels)
        lines[k] = lines[k].replace(f"worst=L{w}", f"worst=L{(w + 1) % 5}")
    elif mutation == "drop_pass":
        if not passes:
            lines.insert(0, "unexpected")
        else:
            lines[k] = lines[k].rsplit(", ", 1)[0] if len(passes) > 1 else lines[k].split(" pass^")[0]
    elif mutation == "extra_pass":
        lines[k] = lines[k].rstrip() + (", " if passes else "") + "pass^16=1.00"
    with pytest.raises(ParseError):
        parse_run("\n".join(lines) + "\n", "", code, room=want_room, repeat=k)
