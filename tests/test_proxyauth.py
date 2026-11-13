import hashlib
import hmac

from hypothesis import given, strategies as st

from warden import proxyauth as P

SECRET = "s3cret-for-tests"
NOW = 1_794_537_000.0


def headers(method="GET", target="/api/state", body=b"", now=NOW, **kw):
    return P.sign_headers(SECRET, method, target, body, now=now, **kw)


def ok(h, method="GET", target="/api/state", body=b"", now=NOW, cache=None, secret=SECRET):
    return P.verify(h, method, target, body, secret, cache or P.ReplayCache(), now=now)


def test_valid_request():
    assert ok(headers())


def test_query_is_part_of_the_target():
    h = headers(target="/api/history?room=parlor")
    assert ok(h, target="/api/history?room=parlor")
    assert not ok(headers(target="/api/history?room=parlor"), target="/api/history?room=threshold")


def test_stale_and_future_timestamps():
    assert not ok(headers(now=NOW - 61))
    assert not ok(headers(now=NOW + 61))
    assert ok(headers(now=NOW - 59))


def test_tampered_body_method_or_path():
    h = headers("PUT", "/api/settings", b'{"repeat": 3}')
    assert not ok(h, "PUT", "/api/settings", b'{"repeat": 9}')
    assert not ok(headers("GET"), "POST")
    assert not ok(headers(target="/api/state"), target="/api/drift")


def test_replay_is_refused():
    cache = P.ReplayCache()
    h = headers()
    assert ok(h, cache=cache)
    assert not ok(h, cache=cache)


def test_v1_only_and_docs_header_are_refused():
    ts = str(int(NOW))
    v1 = hmac.new(SECRET.encode(), f"{ts}:GET:/api/state:{hashlib.sha256(b'').hexdigest()}".encode(),
                  hashlib.sha256).hexdigest()
    assert not ok({"X-KiroCrew-Proxy": f"{ts}:{v1}"})
    assert not ok({"X-Crew-Proxy": f"{ts}:{v1}"})


def test_missing_secret_or_bad_nonce():
    assert not ok(headers(), secret=None)
    assert not ok(headers(), secret="other")
    h = headers()
    h[P.NONCE_HEADER] = "XYZ"
    assert not ok(h)


def test_headers_are_case_insensitive():
    h = {k.lower(): v for k, v in headers().items()}
    assert ok(h)


def test_load_secret(tmp_path):
    assert P.load_secret({"KIROCREW_PROXY_SECRET": " a "}, tmp_path) == "a"
    assert P.load_secret({}, tmp_path) is None
    (tmp_path / ".app_secret").write_text("b\n")
    assert P.load_secret({}, tmp_path) == "b"


def test_replay_cache_expires_and_is_bounded():
    c = P.ReplayCache(ttl=10, max_entries=3)
    assert c.check_and_add("a" * 32, 0)
    assert c.check_and_add("a" * 32, 11)  # expired, accepted again
    for i in range(5):
        c.check_and_add(f"{i:032d}", 12)
    assert len(c._seen) == 3


@given(st.binary(max_size=64), st.sampled_from(["GET", "POST", "PUT"]), st.from_regex(r"/api/[a-z/-]{1,20}", fullmatch=True))
def test_signed_requests_verify_and_one_bit_flips_fail(body, method, target):
    h = headers(method, target, body)
    assert ok(h, method, target, body)
    if body:
        flipped = bytes([body[0] ^ 1]) + body[1:]
        assert not ok(headers(method, target, body), method, target, flipped)
