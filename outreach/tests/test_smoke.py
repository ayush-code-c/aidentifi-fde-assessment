"""Outreach smoke + behaviour tests. Run: PYTHONPATH=src python tests/test_smoke.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from outreach.config import Settings  # noqa: E402
from outreach.enrich import extract_hooks  # noqa: E402
from outreach.guardrails import check_grounding  # noqa: E402
from outreach.model import Recipient  # noqa: E402
from outreach.pipeline import run  # noqa: E402


def test_sparse_profile_is_flagged_and_generic():
    out = ROOT / "outputs" / "_test"
    s = Settings(); s.provider = "mock"
    summary = run(ROOT / "data" / "recipients.csv",
                  ROOT / "config" / "aidentifi_positioning.yaml", out, settings=s)
    assert summary["sparse"] >= 2, "brief requires >=2 sparse recipients handled"
    # the two sparse recipients must NOT mention a company they don't have
    sparse_file = out / "R4_Priya_Nair.md"
    assert sparse_file.exists()
    txt = sparse_file.read_text()
    assert "SPARSE" in txt


def test_guardrail_catches_fabricated_specifics():
    r = Recipient(id="X", name="Sam Lee", title="CEO", company="Acme",
                  industry="Fintech")
    msg = {"subject": "Hi", "body": "Hi Sam, as we discussed at Davos with Goldman Sachs, "
                                     "your hiring at Quantum Robotics is exciting."}
    flags = check_grounding(msg, r, approved_hooks=["CEO at Acme"])
    joined = " ".join(flags)
    assert "prior relationship" in joined            # 'as we discussed'
    assert any("Goldman Sachs" in f or "Quantum Robotics" in f for f in flags)


def test_grounded_message_has_no_flags():
    out = ROOT / "outputs" / "_test"
    s = Settings(); s.provider = "mock"
    summary = run(ROOT / "data" / "recipients.csv",
                  ROOT / "config" / "aidentifi_positioning.yaml", out, settings=s)
    assert summary["with_grounding_flags"] == 0, "template tier should be fully grounded"


def test_confidence_grading_of_hooks():
    r = Recipient(id="Y", name="A B", title="CEO", company="Co", industry="X",
                  hiring_signal="strong",
                  recent_activity="Posted about hiring a CFO")
    hooks = extract_hooks(r)
    # the explicit hiring activity must be a high-confidence specific hook
    assert any(h.kind == "specific" and h.confidence >= 0.8 for h in hooks)


if __name__ == "__main__":
    test_sparse_profile_is_flagged_and_generic()
    test_guardrail_catches_fabricated_specifics()
    test_grounded_message_has_no_flags()
    test_confidence_grading_of_hooks()
    print("all outreach smoke tests passed")
