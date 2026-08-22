from demand_workbench.ingest import CsvIngestor


def test_ingest_rejects_invalid_rows_and_merges_duplicates() -> None:
    text = """date,sku_id,location_id,units,promo
2026-01-01,SKU-1,NORTH,3,true
2026-01-01,SKU-1,NORTH,2,false
2026-01-03,SKU-1,NORTH,4,
2026-01-04,SKU-1,NORTH,-1,
"""

    result = CsvIngestor().parse(text)

    assert result.accepted_rows == 3
    assert len(result.rejected_rows) == 1
    assert result.series[0].observations[0].units == 5
    assert result.series[0].observations[1].imputed is True
    assert result.series[0].observations[1].units == 0
    assert "duplicate" in result.warnings[0]


def test_ingest_requires_contract_headers() -> None:
    try:
        CsvIngestor().parse("date,units\n2026-01-01,1\n")
    except ValueError as exc:
        assert "location_id" in str(exc)
        assert "sku_id" in str(exc)
    else:
        raise AssertionError("Missing headers must fail ingestion")


def test_ingest_reports_stockout_boundary() -> None:
    text = "date,sku_id,location_id,units,stockout\n2026-01-01,A,L,0,yes\n"
    result = CsvIngestor().parse(text)
    assert "latent demand" in result.series[0].warnings[0]
