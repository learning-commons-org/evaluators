"""Contract tests: verify SDK fidelity to the evaluation notebooks.

Each evaluator has a ``contracts.toml`` in its settings folder that records:
  - ``input``:           the evaluator inputs used for the test case
  - ``prompt_steps``:    the exact LLM request (formatted messages, model, temperature)
                         and raw response captured from a real notebook run
  - ``expected_result``: the structured LLM output (notebook format)

Tests load these artifacts, run the evaluator with the LLM mocked to return the
captured response, and assert that:
  1. The SDK sends the same prompt as the notebook (same formatted messages,
     model, and temperature).
  2. The SDK produces the same result from that response as the notebook.
"""
