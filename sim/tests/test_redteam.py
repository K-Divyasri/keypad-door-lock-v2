from doorlock_sim.redteam import run_redteam, summarize


def test_all_scenarios_pass():
    """The committed guarantee: every documented security edge case behaves
    the way `knowledge/05_the_lock_state_machine.md` says it should. If this
    test ever fails, the fix belongs in `lock_fsm.py`, not in this test --
    the scenarios describe deliberate security decisions, not incidental
    behaviour."""
    results = run_redteam()
    failures = [(r.scenario.id, r.detail) for r in results if not r.passed]
    assert not failures, f"red-team scenarios failed: {failures}"


def test_summary_matches_results():
    results = run_redteam()
    s = summarize(results)
    assert s["total"] == len(results)
    assert s["passed"] == sum(1 for r in results if r.passed)
