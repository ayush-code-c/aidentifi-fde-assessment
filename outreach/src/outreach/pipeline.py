"""Outreach pipeline: per recipient -> hooks -> angle -> brief -> compose -> verify.

Emits one outreach file per recipient plus a run summary. Every output carries a
transparent footer: the angle chosen, the personalization basis (which hooks),
whether the profile was treated as sparse, and any grounding flags - so a
reviewer sees the reasoning, not just the prose.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .angles import select_angle
from .config import Settings, load_positioning
from .enrich import Hook, extract_hooks
from .guardrails import check_grounding
from .llm import Brief, Composer
from .model import Recipient, load_recipients


@dataclass
class OutreachResult:
    recipient_id: str
    name: str
    channel: str
    is_sparse: bool
    angle: str
    angle_reason: str
    personalization_basis: list[str]
    approved_hooks: list[str]
    dropped_low_conf_hooks: list[str]
    subject: str
    body: str
    grounding_flags: list[str]
    confidence_note: str


def _clause(h: Hook) -> str:
    """Turn a specific hook into an inline-ready clause for the template tier."""
    t = h.text.strip().rstrip(".")
    if h.basis == "recent_activity":
        # Most activity strings start with a past-tense verb (Posted/Spoke/Closed);
        # "I saw you {verb}…" reads naturally across them.
        return "I saw you " + t[0].lower() + t[1:]
    if h.basis == "hiring_signal":
        if t.startswith("is "):
            return "You're " + t[3:]
        if t.startswith("appears"):
            return "You appear" + t[len("appears"):]
        return t[0].upper() + t[1:]
    return t[0].upper() + t[1:]  # bio sentence as-is


def _category(h: Hook, r: Hook) -> str:
    """Turn a category hook into an inline-ready phrase (no fabrication)."""
    t = h.text.strip()
    if t.startswith("a "):
        return "your role as " + t[2:]
    if " at " in t:
        return "your role as " + t
    if t.startswith("works in "):
        return "your work in " + t[len("works in "):]
    return t


def _approve_hooks(hooks: list[Hook], policy: dict) -> tuple[list[Hook], list[Hook], bool]:
    min_conf = policy["personalization"]["min_hook_confidence"]
    sparse_below = policy["personalization"]["sparse_if_top_hook_below"]
    max_specific = policy["personalization"]["max_specific_hooks"]

    approved, dropped = [], []
    specifics_used = 0
    for h in hooks:
        if h.confidence < min_conf:
            dropped.append(h)
            continue
        if h.kind == "specific":
            if specifics_used >= max_specific:
                dropped.append(h)
                continue
            specifics_used += 1
        approved.append(h)

    top_specific = max(
        [h.confidence for h in hooks if h.kind == "specific"], default=0.0
    )
    is_sparse = top_specific < sparse_below
    return approved, dropped, is_sparse


def run(recipients_path, positioning_path, out_dir, settings: Settings | None = None) -> dict:
    settings = settings or Settings()
    cfg = load_positioning(positioning_path)
    policy = cfg["policy"]
    recipients = load_recipients(recipients_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    composer = Composer(settings.provider, settings.model,
                        settings.anthropic_api_key, settings.openai_api_key)

    results: list[OutreachResult] = []
    for r in recipients:
        hooks = extract_hooks(r)
        approved, dropped, is_sparse = _approve_hooks(hooks, policy)
        angle_key, angle_reason = select_angle(r, approved, cfg)
        angle = cfg["angles"][angle_key]

        channel = r.channel if r.channel in policy["registers"] else policy["channel_default"]
        reg = policy["registers"][channel]
        specific_clauses = [_clause(h) for h in approved if h.kind == "specific"]
        category_phrases = [_category(h, r) for h in approved if h.kind == "category"]
        brief = Brief(
            first_name=r.first_name,
            register=channel,
            greeting=reg["greeting"].format(first_name=r.first_name),
            signoff=reg["signoff"],
            max_words=reg["max_words"],
            angle_thesis=angle["thesis"],
            cta=angle["cta"],
            company_one_liner=cfg["company"]["one_liner"].strip(),
            approved_hooks=[h.text for h in approved],
            is_sparse=is_sparse,
            specific_clauses=specific_clauses,
            category_phrases=category_phrases,
        )
        msg = composer.compose(brief)
        flags = check_grounding(msg, r, brief.approved_hooks)

        confidence_note = (
            "SPARSE profile - message kept category-level; specifics intentionally "
            "omitted. Verify before sending." if is_sparse
            else "Personalised from confirmed hooks."
        )
        res = OutreachResult(
            recipient_id=r.id, name=r.name, channel=channel, is_sparse=is_sparse,
            angle=angle_key, angle_reason=angle_reason,
            personalization_basis=[f"{h.basis} (conf {h.confidence:.2f})" for h in approved],
            approved_hooks=[h.text for h in approved],
            dropped_low_conf_hooks=[f"{h.text} (conf {h.confidence:.2f})" for h in dropped],
            subject=msg.get("subject", ""), body=msg.get("body", ""),
            grounding_flags=flags, confidence_note=confidence_note,
        )
        results.append(res)
        _write_md(out_dir, r, res, channel)

    summary = {
        "provider": settings.provider,
        "recipients": len(results),
        "sparse": sum(1 for x in results if x.is_sparse),
        "with_grounding_flags": sum(1 for x in results if x.grounding_flags),
        "outputs": [str(out_dir / f"{r.id}_{r.name.replace(' ', '_')}.md")
                    for r in recipients],
    }
    (out_dir / "_run_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _write_md(out_dir: Path, r: Recipient, res: OutreachResult, channel: str) -> None:
    path = out_dir / f"{r.id}_{r.name.replace(' ', '_')}.md"
    flags = "\n".join(f"  - ⚠️ {f}" for f in res.grounding_flags) or "  - none"
    basis = "\n".join(f"  - {b}" for b in res.personalization_basis) or "  - (none - sparse)"
    dropped = "\n".join(f"  - {d}" for d in res.dropped_low_conf_hooks) or "  - none"
    md = f"""# Outreach - {r.name} ({r.title}{', ' + r.company if r.has_company else ''})

**Channel:** {channel}  |  **Angle:** `{res.angle}` - {res.angle_reason}
**Profile:** {'SPARSE ⚠️' if res.is_sparse else 'rich'}  |  {res.confidence_note}

---

**Subject:** {res.subject}

{res.body}

---

### Reviewer panel (why this message looks the way it does)

- **Personalization basis (hooks used):**
{basis}
- **Hooks dropped (below confidence threshold):**
{dropped}
- **Grounding check (anti-hallucination):**
{flags}
"""
    path.write_text(md, encoding="utf-8")
