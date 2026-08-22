import pytest


@pytest.fixture
def demo_csv() -> str:
    rows = ["date,sku_id,location_id,units,price,promo,stockout"]
    pattern = [8, 9, 10, 11, 12, 18, 15]
    from datetime import date, timedelta

    start = date(2026, 1, 1)
    for index in range(56):
        observed_on = start + timedelta(days=index)
        rows.append(f"{observed_on.isoformat()},SKU-1,NORTH,{pattern[index % 7]},12.5,false,false")
    return "\n".join(rows) + "\n"
