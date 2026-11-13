from hypothesis import given, strategies as st

from warden.mask import MASKED, has_unmasked, mask, mask_obj


def test_masks_a_dummy_value():
    assert mask("key=HAUNTLET-DUMMY-run1-trap2-abc123 end") == f"key={MASKED} end"


def test_leaves_masked_and_other_text_alone():
    assert mask(f"{MASKED} and plain text") == f"{MASKED} and plain text"
    assert mask("HAUNTLET-other") == "HAUNTLET-other"


def test_stops_at_quotes_and_brackets():
    assert mask('"HAUNTLET-DUMMY-x1"') == f'"{MASKED}"'
    assert mask("<HAUNTLET-DUMMY-x1>") == f"<{MASKED}>"


def test_mask_obj_masks_keys_and_nested_values():
    obj = {"HAUNTLET-DUMMY-k1": ["HAUNTLET-DUMMY-v1", {"x": "HAUNTLET-DUMMY-v2"}], "n": 3}
    out = mask_obj(obj)
    assert not has_unmasked(str(out))
    assert out["n"] == 3


secretish = st.text(alphabet=st.characters(blacklist_categories=("Cs",)), max_size=30)


@given(st.lists(st.one_of(secretish, secretish.map(lambda s: "HAUNTLET-DUMMY-" + s)), max_size=8))
def test_p8_masking_leaves_no_dummy_and_is_idempotent(parts):
    """Property P8."""
    text = " ".join(parts) + " HAUNTLET-DUMMY-abc"
    m = mask(text)
    assert not has_unmasked(m)
    assert mask(m) == m
