import pytest
from django.core.cache import cache

from apps.classes.views import InviteAccept, InviteAcceptThrottle

PASSWORD = "a-good-password-123"


def _login(api, email):
    res = api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD})
    assert res.status_code == 200


@pytest.fixture
def clear_cache():
    # The throttle counts requests in the cache. Clear it before and after each
    # test so the window counter is deterministic within a single test without
    # ever sleeping on wall-clock time.
    cache.clear()
    yield
    cache.clear()


def test_accept_throttle_is_wired():
    # Cheap structural assertion documenting intent: the accept view is throttled
    # per-IP via the dedicated throttle class, scoped to "invite-accept".
    assert InviteAcceptThrottle in InviteAccept.throttle_classes
    assert InviteAcceptThrottle.scope == "invite-accept"


# The configured default is 10/min. DRF binds SimpleRateThrottle.THROTTLE_RATES
# to the DEFAULT_THROTTLE_RATES dict at import time, so @override_settings of the
# rate does NOT reach an already-imported throttle class. Rather than fight that,
# these tests exercise the real default rate functionally and stay deterministic
# by clearing the cache (the throttle's counter store) at the start of each test,
# never by sleeping on wall-clock time.
RATE_LIMIT = 10


@pytest.mark.django_db
def test_accept_returns_429_after_limit(api, make_user, clear_cache):
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    # Token outcome itself does not matter: throttling triggers regardless of
    # whether the request would otherwise 404/409. Firing more than the limit
    # within the (freshly cleared) window must produce at least one 429, and the
    # first request must not be throttled.
    statuses = [
        api.post("/api/v1/invites/some-token-value/accept").status_code
        for _ in range(RATE_LIMIT + 2)
    ]
    assert statuses[0] != 429
    assert 429 in statuses[RATE_LIMIT:]


@pytest.mark.django_db
def test_single_accept_not_throttled(api, make_user, clear_cache):
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    # A single request under the limit must get its normal outcome, never 429.
    res = api.post("/api/v1/invites/some-token-value/accept")
    assert res.status_code != 429
    assert res.status_code in (200, 201, 404, 409, 410)
