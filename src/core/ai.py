"""OpenAI integration — STUB, deferred to a later release.

Per spec (Out of Scope for 0.1):
    - GPT reports (core/ai.py = stub with function signature only).

Signature locked in here so the rest of the app (and the assistant button
in the Analysis tab) can wire against it without changes later.

When implemented (planned for 0.2):
    - Use httpx.AsyncClient; model "gpt-4o-mini"; timeout=30s.
    - Send ONLY the structured summary dict (averages, trends, goal gaps,
      data quality). Never send raw database rows.
    - System prompt: max 400 tokens output; structure =
      "2 patterns + 2 practical suggestions + 1 warning"; no motivational
      phrases.
    - Save response into the `reports` table with a generated_at timestamp.
    - Error handling: timeout, 401, 429, network error. Never lose user
      data; on failure return a clear Persian error string.
"""
from __future__ import annotations

from typing import Any, Optional


OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT_S = 30
OPENAI_MAX_TOKENS = 400


async def request_report(report_type: str, summary: dict, api_key: str) -> str:
    """Request an AI report from OpenAI.

    Args:
        report_type: 'daily' | 'weekly' | 'monthly'
        summary: structured dict built by `core.analytics`. Only this dict
            is sent — never raw rows.
        api_key: OpenAI API key (read from the device Keystore at call time).

    Returns:
        The report text. On error, a short Persian message describing what
        went wrong (so the UI can show it without crashing).

    v0.1 behavior: NOT IMPLEMENTED. Returns a Persian message saying so.
    """
    # --- v0.1 stub --------------------------------------------------------
    return (
        "در این نسخه، تحلیل را از خلاصه بالا می‌خوانی. "
        "تحلیل هوشمند را در نسخه بعد می‌بینی."
    )
    # --- end stub ---------------------------------------------------------

    # Reference implementation (commented; lands in 0.2):
    #
    # import httpx
    # from core import models
    #
    # system_prompt = (
    #     "You are a study analyst. Output in Persian. "
    #     "Maximum 400 tokens. Structure: 2 patterns + 2 practical "
    #     "suggestions + 1 warning. No motivational phrases. "
    #     "Never judge the user; only describe where time went and the "
    #     "distance from their own goals."
    # )
    # user_prompt = _format_summary_for_openai(report_type, summary)
    #
    # try:
    #     async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_S) as client:
    #         resp = await client.post(
    #             OPENAI_ENDPOINT,
    #             headers={"Authorization": f"Bearer {api_key}"},
    #             json={
    #                 "model": OPENAI_MODEL,
    #                 "messages": [
    #                     {"role": "system", "content": system_prompt},
    #                     {"role": "user", "content": user_prompt},
    #                 ],
    #                 "max_tokens": OPENAI_MAX_TOKENS,
    #                 "temperature": 0.4,
    #             },
    #         )
    #         resp.raise_for_status()
    #         data = resp.json()
    #         content = data["choices"][0]["message"]["content"]
    #         models.save_report(report_type, summary.get("period_start", ""),
    #                            summary.get("period_end", ""), content)
    #         return content
    # except httpx.TimeoutException:
    #     return "پاسخ از سرور زمان‌بر بود؛ دوباره تلاش کن."
    # except httpx.HTTPStatusError as e:
    #     if e.response.status_code == 401:
    #         return "کلید API نامعتبر است."
    #     if e.response.status_code == 429:
    #         return "محدودیت درخواست؛ کمی بعد دوباره امتحان کن."
    #     return f"خطای سرور: {e.response.status_code}"
    # except httpx.HTTPError:
    #     return "اتصال اینترنت برقرار نیست."


def _format_summary_for_openai(report_type: str, summary: dict) -> str:
    """Build the user-prompt payload from the structured summary.

    Only sends aggregate numbers (averages, trends, goal gaps, data quality).
    Never includes raw rows, notes, or personal text.
    """
    lines = [f"نوع گزارش: {report_type}"]
    for k, v in summary.items():
        if isinstance(v, (str, int, float)):
            lines.append(f"{k}: {v}")
        elif isinstance(v, list):
            lines.append(f"{k}: {len(v)} مورد")
    return "\n".join(lines)
