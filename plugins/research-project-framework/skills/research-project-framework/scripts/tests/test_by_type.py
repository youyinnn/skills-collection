"""A paper folder whose name has no underscore must not crash the label matching."""
import by_type as b


def test_match_tolerates_a_folder_name_without_underscore():
    assert b.match("Paper", ["ICSE2025_Paper_X", "nounderscore"]) == "ICSE2025_Paper_X"
    assert b.match("nounderscore", ["ICSE2025_Paper_X", "nounderscore"]) == "nounderscore"
