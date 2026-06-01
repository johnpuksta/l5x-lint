from __future__ import annotations


def suggest_did_you_mean(name: str, known_names: list[str]) -> str | None:
    candidates = [
        (n, _levenshtein(name.lower(), n.lower())) for n in known_names if n != name
    ]
    candidates.sort(key=lambda x: x[1])
    if not candidates:
        return None
    best_dist = candidates[0][1]
    if best_dist <= 4:
        return f"Did you mean '{candidates[0][0]}'?"
    return None


def syntax_habit_hints(text: str) -> str | None:
    hints = {
        "==": "Use '=' in ST",
        "!=": "Use '<>' in ST",
        "&&": "Use 'AND'",
        "||": "Use 'OR'",
        "&&": "Use 'AND'",
        "{": "Use '(* *)'",
    }
    for pattern, hint in hints.items():
        if pattern in text:
            return hint
    return None


def _levenshtein(a: str, b: str) -> int:
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            temp = dp[j]
            if a[i - 1] == b[j - 1]:
                dp[j] = prev
            else:
                dp[j] = 1 + min(prev, dp[j], dp[j - 1])
            prev = temp
    return dp[n]
