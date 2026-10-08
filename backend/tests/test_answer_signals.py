from app.services.answer_signals import analyze_answer


def test_word_count_and_metric() -> None:
    signals = analyze_answer("Reduced latency 40 percent")
    assert signals.word_count == 4
    assert signals.has_metric is True


def test_no_metric() -> None:
    signals = analyze_answer("I talked about the project a while ago")
    assert signals.has_metric is False


def test_star_coverage_detects_all_parts() -> None:
    text = (
        "The situation was a legacy system. My task was to migrate it. "
        "I built a new pipeline. As a result we reduced errors."
    )
    assert analyze_answer(text).star_coverage == {
        "situation": True,
        "task": True,
        "action": True,
        "result": True,
    }


def test_star_coverage_reports_missing_parts() -> None:
    coverage = analyze_answer("I built a thing.").star_coverage
    assert coverage["action"] is True
    assert coverage["situation"] is False
    assert coverage["result"] is False
