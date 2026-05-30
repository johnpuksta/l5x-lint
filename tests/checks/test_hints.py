from l5x_lint.checks._hints import suggest_did_you_mean, syntax_habit_hints, _levenshtein


def test_levenshtein_identical():
    assert _levenshtein("hello", "hello") == 0


def test_levenshtein_one_substitution():
    assert _levenshtein("kitten", "sitten") == 1


def test_levenshtein_one_insertion():
    assert _levenshtein("kitten", "kittens") == 1


def test_levenshtein_emtpy():
    assert _levenshtein("", "abc") == 3
    assert _levenshtein("abc", "") == 3


def test_did_you_mean_exact_match_does_not_suggest_self():
    known = ["Motor_Run", "Motor_Stop"]
    result = suggest_did_you_mean("Motor_Run", known)
    assert result is not None
    assert "Motor_Run" not in result


def test_did_you_mean_close():
    known = ["Motor_Run", "Motor_Stop"]
    result = suggest_did_you_mean("Motor_Rn", known)
    assert result is not None
    assert "Motor_Run" in result


def test_did_you_mean_no_match():
    known = ["Motor_Run", "Motor_Stop"]
    result = suggest_did_you_mean("XyZQp", known)
    assert result is None


def test_syntax_habit_st_eq():
    assert syntax_habit_hints("IF x == 5 THEN") is not None


def test_syntax_habit_st_ne():
    assert syntax_habit_hints("IF x != 5 THEN") is not None


def test_syntax_habit_st_and():
    assert syntax_habit_hints("x && y") is not None


def test_syntax_habit_st_or():
    assert syntax_habit_hints("x || y") is not None


def test_syntax_habit_brackets():
    assert syntax_habit_hints("{ x := 1 }") is not None


def test_syntax_habit_no_match():
    assert syntax_habit_hints("x := y + z") is None
