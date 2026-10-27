from app.services.resolution import InstitutionResolver, normalize_name


def test_normalize_name():
    assert "institute" in normalize_name("ABC Inst. of Tech")
    assert "saint" in normalize_name("St. Xavier")
