"""Asks Claude for a part script, then checks and runs it, repairing failures."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from . import config
from .prompts import system_prompt
from .runner import RunError, RunResult, ScriptError, run_script


class PartDesign(BaseModel):
    status: Literal["ok", "need_info"]
    part_name: str
    script: str
    assumptions: list[str]
    questions: list[str]


@dataclass
class DesignResult:
    design: PartDesign
    run: RunResult | None = None
    errors: list[str] = field(default_factory=list)  # failures that were repaired along the way


class DesignError(RuntimeError):
    def __init__(self, message: str, design: PartDesign | None):
        super().__init__(message)
        self.design = design


def _assistant_content(response) -> list[dict]:
    """Echo a response back as an assistant turn, keeping thinking blocks unchanged."""
    blocks = []
    for block in response.content:
        if block.type == "text":
            blocks.append({"type": "text", "text": block.text})
        else:
            blocks.append(block.model_dump(exclude_none=True))
    return blocks


def _ask(client: anthropic.Anthropic, messages: list[dict]):
    response = client.messages.parse(
        model=config.MODEL,
        max_tokens=config.MAX_TOKENS,
        system=system_prompt(),
        thinking={"type": "adaptive"},
        output_config={"effort": config.EFFORT},
        output_format=PartDesign,
        messages=messages,
    )
    if response.stop_reason == "refusal":
        raise DesignError("Claude declined this request", None)
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise DesignError("Claude's answer was cut off or could not be parsed", None)
    return response


def design_part(
    description: str,
    out_dir: Path,
    client: anthropic.Anthropic | None = None,
) -> DesignResult:
    """Turn a text description into a checked, exported part.

    Returns early with status "need_info" when Claude needs answers first.
    Raises DesignError if the script still fails after the repair attempts.
    """
    client = client or anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": description}]
    errors: list[str] = []

    for attempt in range(config.MAX_REPAIR_ATTEMPTS + 1):
        response = _ask(client, messages)
        design: PartDesign = response.parsed_output
        if design.status == "need_info":
            return DesignResult(design=design, errors=errors)
        try:
            run = run_script(design.script, out_dir)
            return DesignResult(design=design, run=run, errors=errors)
        except (ScriptError, RunError) as e:
            errors.append(str(e))
            if attempt == config.MAX_REPAIR_ATTEMPTS:
                raise DesignError(f"script still failing after repairs: {e}", design) from e
            messages.append({"role": "assistant", "content": _assistant_content(response)})
            messages.append({
                "role": "user",
                "content": f"The script failed when the app checked or ran it:\n\n{e}\n\n"
                "Fix it and return the full corrected script.",
            })
    raise AssertionError("unreachable")
