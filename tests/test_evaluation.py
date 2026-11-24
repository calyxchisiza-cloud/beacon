from beacon_core.eval import bucket, evaluate_flag


def flag(rollout=500, rules=None, enabled=True):
    return {
        "key": "payment",
        "enabled": enabled,
        "off": "old",
        "fallthrough": "new",
        "salt": "demo",
        "rollout": rollout,
        "rules": rules or [],
        "variations": {"old": False, "new": True},
    }


def test_the_same_user_stays_in_the_same_bucket():
    assert bucket("payment", "demo", "user-4") == bucket("payment", "demo", "user-4")


def test_a_disabled_flag_serves_the_off_variation():
    result = evaluate_flag(flag(enabled=False), {"key": "user-1", "attributes": {}})
    assert result["variation"] == "old"
    assert result["reason"] == "off"
    assert result["value"] is False


def test_five_percent_is_stable_and_near_five_percent():
    inside = 0
    for index in range(4000):
        result = evaluate_flag(flag(), {"key": f"user-{index}", "attributes": {}})
        again = evaluate_flag(flag(), {"key": f"user-{index}", "attributes": {}})
        assert result == again
        inside += result["variation"] == "new"
    assert 140 <= inside <= 260


def test_a_matching_rule_beats_the_rollout():
    rules = [
        {
            "id": "staff",
            "clauses": [{"attribute": "email", "op": "ends_with", "values": ["@acme.com"]}],
            "variation": "new",
            "rollout": None,
        }
    ]
    staff = evaluate_flag(flag(rollout=0, rules=rules), {"key": "a", "attributes": {"email": "a@acme.com"}})
    guest = evaluate_flag(flag(rollout=0, rules=rules), {"key": "b", "attributes": {"email": "b@other.com"}})
    assert staff["reason"] == "rule" and staff["value"] is True
    assert guest["reason"] == "rollout" and guest["value"] is False


def test_a_segment_can_target_a_group():
    segments = {"beta": {"clauses": [{"attribute": "plan", "op": "eq", "values": ["beta"]}]}}
    rules = [{"id": "beta", "clauses": [{"attribute": "segment", "op": "in", "values": ["beta"]}], "variation": "new", "rollout": None}]
    member = evaluate_flag(flag(rollout=0, rules=rules), {"key": "a", "attributes": {"plan": "beta"}}, segments)
    other = evaluate_flag(flag(rollout=0, rules=rules), {"key": "b", "attributes": {"plan": "free"}}, segments)
    assert member["reason"] == "rule"
    assert other["reason"] == "rollout"
