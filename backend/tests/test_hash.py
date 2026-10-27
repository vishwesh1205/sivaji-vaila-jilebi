from app.hash_chain import compute_hash


def test_hash_chain():
    h = compute_hash("0" * 64, {"action": "CREATED"})
    assert len(h) == 64
