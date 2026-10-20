from portfolio_os.storage import list_opportunities, save_opportunity, seed_examples_if_empty


def test_store_round_trips_and_updates_without_duplicate(tmp_path):
    db = tmp_path / "portfolio.db"
    record = {"opportunity_id": "op-1", "title": "Test", "status": "Hypothesis"}
    save_opportunity(record, db)
    save_opportunity({**record, "status": "Validation"}, db)
    rows = list_opportunities(db)
    assert len(rows) == 1
    assert rows[0]["status"] == "Validation"


def test_seed_only_runs_on_empty_store_and_preserves_user_rows(tmp_path):
    db = tmp_path / "portfolio.db"
    seed_examples_if_empty(db)
    first = list_opportunities(db)
    assert len(first) == 4
    seed_examples_if_empty(db)
    assert len(list_opportunities(db)) == 4
    save_opportunity({"opportunity_id": "custom", "title": "My own idea"}, db)
    seed_examples_if_empty(db)
    assert len(list_opportunities(db)) == 5
