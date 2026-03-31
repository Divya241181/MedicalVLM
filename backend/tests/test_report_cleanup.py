from backend.api.main import clean_report


def test_clean_report_sanitizes_gibberish():
    raw = "Findings :    patchy   opacities   ,,, ,  mild  effusion??   "
    cleaned = clean_report(raw)
    assert cleaned == "Findings : patchy opacities, mild effusion."


def test_clean_report_handles_empty_string():
    assert clean_report("") == ""
