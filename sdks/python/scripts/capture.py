"""Contract test capture utilities for evaluator notebooks.

Three-step workflow for notebook authors
-----------------------------------------
1. Wrap every model in your chain with ``capture_llm()``:

       chain = prompt | capture_llm("step_name", my_model) | JsonOutputParser()

   The prefix (``"step_name"``) becomes the step key in ``prompt_steps`` in
   the TOML output.  Use a short, stable name per step (e.g. ``"main"``,
   ``"bk"``, ``"vocab"``).

2. Immediately after each test-case evaluation, call ``capture_case()`` to save a
   point-in-time copy of what was captured.  Pass the evaluator's input dict
   and output dict directly — no manual field extraction needed::

       case_input  = {"text": my_text, "grade": 4}
       case_output = run_evaluator(**case_input)

       _cap = capture_case(
           name="my_case",
           input=case_input,
           llm_call_captures=["step_name"],  # prefixes, in call order
           expected_result=case_output,
           description="…",                 # optional human-readable label
       )

3. Print the TOML block and paste it into ``contracts.toml`` (for example,
   ``sdks/settings/<evaluator>/contracts.toml``):

       print(build_contract_toml(_cap_one, _cap_two))

Resetting between runs
-----------------------
Call ``reset_captures()`` at the start of each evaluation to avoid stale data from a
previous run leaking into the next capture_case::

    reset_captures()
    output = run_evaluator(text, grade)
    _cap = capture_case(
        name="my_case",
        input={"text": text, "grade": grade},
        llm_call_captures=["main"],
        expected_result=output,
    )

Async chains
-------------
``capture_llm()`` works in both sync (``invoke``) and async (``ainvoke``)
chains with no extra configuration.
"""

from __future__ import annotations

import json as _json
from typing import Any

from langchain_core.runnables import RunnableLambda

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

# Flat dict populated by capture_llm() on every chain invocation.
# Keys follow the pattern "{prefix}_{field}" (e.g. "bk_user_prompt").
_captures: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def reset_captures() -> None:
    """Clear all captured data. Call at the start of each evaluation run."""
    _captures.clear()


def capture_llm(prefix: str, model: Any) -> RunnableLambda:
    """Return a wrapped model that records the formatted prompt and raw response.

    Drop it into a LangChain chain wherever you have a bare model::

        # single-step evaluator
        chain = prompt | capture_llm("main", llm) | JsonOutputParser()

        # multi-step evaluator
        bk_chain    = bk_prompt    | capture_llm("bk",    bk_model)
        vocab_chain = vocab_prompt | capture_llm("vocab", vocab_model) | JsonOutputParser()

    After the chain runs, ``_captures`` contains:

    * ``"{prefix}_system_prompt"`` — system message content (``""`` if none)
    * ``"{prefix}_user_prompt"``   — human message content
    * ``"{prefix}_raw_response"``  — text content of the LLM response.
                                     Most providers return a plain string.
                                     Some (e.g. Google Gemini via
                                     langchain_google_genai) return a list of
                                     content blocks; the first ``"text"`` block
                                     is extracted so the stored value is always
                                     a plain string suitable for JsonOutputParser.
    * ``"{prefix}_model"``         — model identifier
    * ``"{prefix}_temperature"``   — temperature used

    Supports both ``invoke`` (sync) and ``ainvoke`` (async) chains.
    """
    model_name = getattr(model, "model", None) or getattr(model, "model_name", None) or ""
    temperature = float(getattr(model, "temperature", 0))

    def _record(prompt_value: Any, ai_message: Any) -> None:
        if isinstance(prompt_value, str):
            # Plain string passed directly to the model — treat it as a lone
            # human message with no system prompt.  This happens when the
            # caller formats a prompt template themselves and passes the result
            # as a string rather than going through a ChatPromptTemplate chain.
            system = ""
            human = prompt_value
        else:
            messages = (
                prompt_value.to_messages()
                if hasattr(prompt_value, "to_messages")
                else list(prompt_value)
            )
            system = next(
                (str(m.content) for m in messages if getattr(m, "type", None) == "system"), ""
            )
            human = next(
                (str(m.content) for m in messages if getattr(m, "type", None) == "human"), ""
            )
        _captures[f"{prefix}_system_prompt"] = system
        _captures[f"{prefix}_user_prompt"] = human
        _captures[f"{prefix}_model"] = model_name
        _captures[f"{prefix}_temperature"] = temperature
        _captures[f"{prefix}_raw_response"] = _extract_text_content(ai_message.content)

    def _invoke(prompt_value: Any) -> Any:
        ai_message = model.invoke(prompt_value)
        _record(prompt_value, ai_message)
        return ai_message

    async def _ainvoke(prompt_value: Any) -> Any:
        ai_message = await model.ainvoke(prompt_value)
        _record(prompt_value, ai_message)
        return ai_message

    return RunnableLambda(_invoke, afunc=_ainvoke)


def capture_case(
    *,
    name: str,
    input: dict[str, Any],
    llm_call_captures: list[str],
    expected_result: dict[str, Any] | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Return a point-in-time copy of ``_captures`` merged with structured context.

    Args:
        name:              Case identifier used as the TOML key (e.g. ``"marco_polo_grade3"``).
        input:             The evaluator's input dict (e.g. ``{"text": ..., "grade": 4}``).
                           Keys are written as-is to the ``[input]`` TOML section.
        llm_call_captures: Ordered list of capture prefixes to include as
                           ``prompt_steps`` in the TOML.  Must match the prefixes
                           passed to ``capture_llm()`` during this run, in call order.
        expected_result:   The evaluator's output.  Pass the whole output — no
                           need to extract individual fields.  Plain dicts, Pydantic
                           v1/v2 models, and anything dict-like are all accepted;
                           ``capture_case()`` normalises to a plain dict.  Written to
                           the ``[expected_result]`` TOML section.
        description:       Optional human-readable label for this test case.

    Example::

        case_input  = {"text": text, "grade": 3}
        case_output = run_evaluator(**case_input)

        _cap = capture_case(
            name="marco_polo_grade3",
            input=case_input,
            llm_call_captures=["bk", "vocab"],
            expected_result=case_output,
            description="Marco Polo passage, grade 3",
        )
    """
    data: dict[str, Any] = dict(_captures)
    data["name"] = name
    data["input"] = dict(input)
    data["llm_call_captures"] = llm_call_captures
    if expected_result is not None:
        # Normalise to a plain dict so capture_case() is always fully serializable.
        # Handles Pydantic v2 models (.model_dump()), v1 models (.dict()), and
        # anything else that is already a dict or dict-like.
        if hasattr(expected_result, "model_dump"):
            expected_result = expected_result.model_dump()
        elif hasattr(expected_result, "dict"):
            expected_result = expected_result.dict()
        data["expected_result"] = dict(expected_result)
    if description is not None:
        data["description"] = description
    return data


def build_contract_toml(*cases: dict[str, Any]) -> str:
    """Build the contract TOML block for one or more test cases.

    Args:
        *cases: One or more dicts as returned by :func:`capture_case`.

    Returns:
        TOML string ready to paste into ``contracts.toml`` (for example,
        ``sdks/settings/<evaluator>/contracts.toml``).

    Example::

        print(build_contract_toml(_cap_grade3, _cap_grade7))
    """
    return "\n".join(_build_case(c) for c in cases)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_text_content(content: Any) -> str:
    """Extract a plain-text string from an AIMessage content value.

    Most LLM providers via LangChain return a plain ``str``.  Some
    (e.g. Google Gemini via ``langchain_google_genai``) return a list of
    content blocks such as::

        [{"type": "text", "text": "...the model's reply...", "extras": {...}}]

    This helper normalises both shapes to a plain string so that
    ``_raw_response`` is always something ``JsonOutputParser`` can parse
    directly — not a Python-repr of a list.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                return str(block["text"])
    return str(content)


def _toml_value(v: Any) -> str:
    """Serialize *v* to a TOML literal."""
    if isinstance(v, str):
        if v == "":
            return '""'
        # Prefer multiline LITERAL strings ('''...''') — they are verbatim so
        # backslashes, double-quotes, and \' sequences are all safe.  The only
        # restriction is the content cannot contain '''.
        #
        # IMPORTANT: no "\n" before the closing ''' — that would add a spurious
        # trailing newline to every parsed value (TOML only trims the *first*
        # newline after the opening delimiter, not the last one before closing).
        if "'''" not in v:
            return "'''\n" + v + "'''"
        # Fallback: content contains ''' so literal multiline cannot be used.
        # json.dumps produces a TOML-safe basic string (all backslashes/quotes
        # escaped); tomllib accepts it as a single-line value.
        return _json.dumps(v)
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_json.dumps(item) for item in v) + "]"
    # Fallback: JSON-encode whatever it is.
    return _json.dumps(str(v))


def _build_case(c: dict[str, Any]) -> str:
    name = c["name"]
    lines: list[str] = []

    # ── optional top-level description ───────────────────────────────────────
    description = c.get("description")
    if description:
        lines += [
            f"[cases.{name}]",
            f"description = {_json.dumps(description)}",
            "",
        ]

    # ── input section ────────────────────────────────────────────────────────
    lines.append(f"[cases.{name}.input]")
    for field, val in c.get("input", {}).items():
        # Do NOT strip text — stripping would make input.text differ from the
        # text that capture_llm used when formatting the user_prompt, causing
        # the contract test's prompt-fidelity assertion to fail.
        lines.append(f"{field} = {_toml_value(val)}")
    lines.append("")

    # ── prompt_steps sections ─────────────────────────────────────────────────
    prefixes = c["llm_call_captures"]
    for prefix in prefixes:
        lines += [
            f"[cases.{name}.prompt_steps.{prefix}]",
            f"model = {_json.dumps(c.get(prefix + '_model', ''))}",
            f"temperature = {c.get(prefix + '_temperature', 0)}",
            f"system_prompt = {_toml_value(c.get(prefix + '_system_prompt', ''))}",
            f"user_prompt = {_toml_value(c.get(prefix + '_user_prompt', ''))}",
            f"llm_response = {_toml_value(c.get(prefix + '_raw_response', ''))}",
            "",
        ]

    # ── expected_result section ───────────────────────────────────────────────
    expected = c.get("expected_result")
    if expected:
        lines.append(f"[cases.{name}.expected_result]")
        for field, value in expected.items():
            lines.append(f"{field} = {_toml_value(value)}")
        lines.append("")

    return "\n".join(lines)
