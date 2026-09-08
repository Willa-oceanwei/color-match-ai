from ui.design import format_quantity


def test_format_quantity_hides_zero_decimal_places():
    assert format_quantity(5.0) == "5"
    assert format_quantity("12.500") == "12.5"
    assert format_quantity(0.25) == "0.25"
    assert format_quantity("依現場調整") == "依現場調整"
