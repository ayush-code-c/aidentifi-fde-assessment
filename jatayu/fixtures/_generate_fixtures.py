"""Generate deterministic, realistic SYNTHETIC profiles for offline runs.

These are fictional people at fictional firms. They exist so the pipeline runs
end-to-end with zero credits and produces every deliverable, and so filter +
ranking behaviour is demonstrable without a live Coresignal account. The shape
(field names, nesting) mirrors the Coresignal clean Employee schema so swapping
in `JATAYU_MODE=live` requires no code change.

Run:  python fixtures/_generate_fixtures.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).parent
random.seed(42)

# Fictional firms (NOT the real firms the brief says to study).
BOUTIQUE_AM = ["Maplewell Capital", "Tanglin Asset Management", "Keppel Straits Partners",
               "Lioncross Investment Management", "Serangoon Capital Partners",
               "Pinnacle Meridian Asset Mgmt", "Orchard Bridge Capital"]
BIG_BANK = ["DBS Bank", "OCBC Bank", "UOB", "Standard Chartered", "Citi", "HSBC"]
BIG4 = ["Deloitte", "PwC", "KPMG", "Ernst & Young"]
INSURERS = ["Great Eastern", "Prudential Singapore", "AIA Singapore"]
SFO = ["Tan Family Office", "Evergreen Family Office", "Banyan Tree SFO"]

FIRST = ["Wei", "Mei", "Arjun", "Priya", "Daniel", "Sarah", "Jun", "Li", "Rajesh",
         "Aisha", "Marcus", "Grace", "Kumar", "Hui", "Benjamin", "Natalie", "Ravi",
         "Joanne", "Terence", "Shanti", "Cheryl", "Vikram", "Faizal", "Yong"]
LAST = ["Tan", "Lim", "Nair", "Sharma", "Wong", "Ng", "Goh", "Chua", "Menon", "Koh",
        "Pillai", "Teo", "Reddy", "Ong", "Iyer", "Lee", "Rao", "Sim", "Das", "Chan"]


def _name(i):
    return f"{FIRST[i % len(FIRST)]} {LAST[(i * 7) % len(LAST)]}"


def _exp(title, company, industry, size, y0, y1, loc="Singapore", desc=""):
    return {
        "title": title, "company_name": company, "company_industry": industry,
        "company_size": size, "date_from": f"{y0}-01", "date_to": (f"{y1}-12" if y1 else None),
        "location": loc, "company_location": loc, "description": desc,
    }


def _profile(i, **kw):
    base = {
        "id": 100000 + i,
        "name": _name(i),
        "linkedin_url": f"https://www.linkedin.com/in/synthetic-{100000 + i}",
        "location_country": "Singapore",
        "active_experience": True,
        "skills": [],
        "education": [{"title": "National University of Singapore", "subtitle": "Law"}],
    }
    base.update(kw)
    # derive current title/company from first experience
    if base.get("experience"):
        base.setdefault("title", base["experience"][0]["title"])
        base.setdefault("headline", base["experience"][0]["title"])
        base.setdefault("current_title", base["experience"][0]["title"])
        base.setdefault("current_company", base["experience"][0]["company_name"])
        base.setdefault("active_experience_company_name", base["experience"][0]["company_name"])
    return base


def make_mandate_a() -> list[dict]:
    P = []
    i = 0

    # --- STRONG fits: sole CCO at boutique SG AM, CMS/AI/VCC language (~12) ---
    strong_summaries = [
        "Sole compliance officer and CMS licence holder at a boutique independent "
        "asset manager. Built the compliance function from scratch. Own AI client "
        "onboarding under our own Capital Markets Services licence, MAS regulatory "
        "management, fund governance and Board reporting. Open-architecture "
        "third-party fund distribution (private credit, private equity, hedge funds) "
        "to Accredited Investors. VCC structures. Commercial business partner to the "
        "front office in a growth-mode firm.",
        "Chief Compliance Officer at an independent Singapore fund manager. Sole "
        "compliance ownership: MAS CMS licensing, Accredited Investor onboarding, "
        "trade and risk oversight, VCC fund governance. Partner with investment team "
        "to enable growth. Open-architecture distribution of alternatives.",
    ]
    for n in range(12):
        yrs = random.choice([9, 10, 11, 12, 13])
        comp = BOUTIQUE_AM[n % len(BOUTIQUE_AM)]
        summ = strong_summaries[n % len(strong_summaries)]
        exp = [
            _exp("Chief Compliance Officer" if n % 2 else "Head of Compliance (Sole)",
                 comp, "Investment Management", random.choice([35, 60, 90, 120]),
                 2026 - yrs + 6, None, desc=summ),
            _exp("Compliance Manager", BOUTIQUE_AM[(n + 2) % len(BOUTIQUE_AM)],
                 "Asset Management", 80, 2026 - yrs, 2026 - yrs + 6,
                 desc="Compliance manager covering CMS licensing and AI onboarding."),
        ]
        P.append(_profile(i, experience=exp, summary=summ,
                          skills=["MAS", "CMS Licensing", "AML/CFT", "Fund Governance", "VCC"]))
        i += 1

    # --- MEDIUM: compliance but at a bank / retail-IFA flavour (~14) ---
    for n in range(14):
        yrs = random.choice([8, 9, 10, 12, 15])
        if n % 2 == 0:
            comp = BIG_BANK[n % len(BIG_BANK)]
            ind = "Banking"
            summ = ("Compliance officer within the private banking division. Wealth "
                    "management compliance, suitability, KYC/AML. Part of a compliance "
                    "team of 25.")
            title = "Compliance Officer"
            skills = ["KYC", "AML", "Suitability"]
        else:
            comp = "iWealth Advisers"
            ind = "Financial Services"
            summ = ("Head of compliance at a retail IFA distribution platform. Retail "
                    "and IFA distribution only. MAS FAA licensing.")
            title = "Head of Compliance"
            skills = ["FAA", "Retail Distribution"]
        exp = [
            _exp(title, comp, ind, random.choice([1500, 8000, 20000]),
                 2026 - yrs, None, desc=summ),
        ]
        P.append(_profile(i, experience=exp, summary=summ, skills=skills))
        i += 1

    # --- WEAK / wrong pools the brief names (~12) ---
    # Big-4 advisory-only
    for n in range(4):
        comp = BIG4[n % len(BIG4)]
        summ = ("Regulatory compliance advisory consultant. Advise asset managers on "
                "MAS licensing applications. Big 4 advisory only, no in-house seat.")
        exp = [_exp("Compliance Advisory Manager", comp, "Management Consulting",
                    25000, 2014, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=["Advisory"]))
        i += 1
    # MAS regulator, current (should be filtered OUT by must_not_current_company)
    for n in range(2):
        summ = "Assistant Director, Capital Markets Intermediaries Department."
        exp = [_exp("Assistant Director", "Monetary Authority of Singapore",
                    "Government Administration", 4000, 2012, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=["Supervision"]))
        i += 1
    # ex-MAS who MOVED industry-side (should SURVIVE and score well)
    for n in range(2):
        summ = ("Ex-MAS supervisor now Head of Compliance at an independent asset "
                "manager. CMS licence, Accredited Investor onboarding, VCC governance.")
        exp = [
            _exp("Head of Compliance", BOUTIQUE_AM[n], "Investment Management", 70,
                 2020, None, desc=summ),
            _exp("Deputy Director", "Monetary Authority of Singapore",
                 "Government Administration", 4000, 2010, 2020,
                 desc="Supervised CMS licensees."),
        ]
        P.append(_profile(i, experience=exp, summary=summ,
                          skills=["MAS", "CMS Licensing", "VCC"]))
        i += 1
    # junior analysts (filtered by must_not_title / min years)
    for n in range(2):
        summ = "Compliance analyst supporting the AML team."
        exp = [_exp("Compliance Analyst", BOUTIQUE_AM[n], "Asset Management", 60,
                    2023, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=["AML"]))
        i += 1
    # insurer compliance (industry gate should drop)
    for n in range(2):
        summ = "Compliance manager, life insurance product governance."
        exp = [_exp("Compliance Manager", INSURERS[n], "Insurance", 6000, 2015,
                    None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=["Insurance"]))
        i += 1

    # --- SPARSE strong fits (thin data, high fit, must score high-fit/low-conf) (~4) ---
    for n in range(4):
        comp = BOUTIQUE_AM[(n + 3) % len(BOUTIQUE_AM)]
        exp = [_exp("Chief Compliance Officer", comp, "Investment Management", 50,
                    2016, None, desc="")]
        P.append(_profile(
            i, experience=exp, summary="",  # no summary => low confidence
            skills=[], education=[]))
        i += 1

    # --- NON-SG (filtered by geography) (~2) ---
    for n in range(2):
        exp = [_exp("Head of Compliance", "Hong Kong Asset Mgmt", "Investment Management",
                    80, 2014, None, loc="Hong Kong",
                    desc="CMS-equivalent compliance, SFC licensed.")]
        P.append(_profile(i, location_country="Hong Kong", experience=exp,
                          summary="SFC compliance.", skills=["SFC"]))
        i += 1

    return P


def make_mandate_b() -> list[dict]:
    """Smaller fixture set for Mandate B (Investment Director / SFO)."""
    P = []
    i = 500
    # strong multi-asset PMs at SFOs
    for n in range(8):
        yrs = random.choice([16, 18, 20, 22])
        comp = SFO[n % len(SFO)]
        summ = ("Investment Director at a single family office. Multi-asset portfolio "
                "construction across global public equities, fixed income, REITs, "
                "private equity, venture capital and hedge funds. Discretionary "
                "mandate reporting to the principal. Strong private bank and GP "
                "relationships driving co-investment deal flow. CFA charterholder.")
        exp = [
            _exp("Investment Director", comp, "Investment Management", 15,
                 2026 - yrs + 8, None, desc=summ),
            _exp("Portfolio Manager", "Lioncross Investment Management",
                 "Investment Management", 120, 2026 - yrs, 2026 - yrs + 8,
                 desc="Multi-asset discretionary portfolio management."),
        ]
        P.append(_profile(i, experience=exp, summary=summ,
                          skills=["Multi-Asset", "Private Equity", "CFA", "Asset Allocation"]))
        i += 1
    # private bankers with PM book (medium)
    for n in range(6):
        yrs = random.choice([15, 17, 19])
        summ = ("Senior private banker with discretionary PM book for HNW/family "
                "office clients. Multi-asset allocation, public and private markets.")
        exp = [_exp("Executive Director, Private Wealth", BIG_BANK[n % len(BIG_BANK)],
                    "Banking", 20000, 2026 - yrs, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ,
                          skills=["Private Banking", "Discretionary"]))
        i += 1
    # single-asset specialists (weak)
    for n in range(4):
        summ = "Equities-only portfolio manager. Asian public equities long-only."
        exp = [_exp("Portfolio Manager", "Lioncross Investment Management",
                    "Investment Management", 120, 2008, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=["Equities"]))
        i += 1
    # sparse SFO PMs
    for n in range(3):
        exp = [_exp("Head of Investments", SFO[n % len(SFO)], "Investment Management",
                    12, 2014, None, desc="")]
        P.append(_profile(i, experience=exp, summary="", skills=[], education=[]))
        i += 1
    # junior step-up (weak)
    for n in range(2):
        summ = "Investment associate, two years buy-side."
        exp = [_exp("Investment Associate", "Serangoon Capital Partners",
                    "Investment Management", 40, 2022, None, desc=summ)]
        P.append(_profile(i, experience=exp, summary=summ, skills=[]))
        i += 1
    return P


if __name__ == "__main__":
    a = make_mandate_a()
    b = make_mandate_b()
    (HERE / "mandate_a_raw_profiles.json").write_text(json.dumps(a, indent=2))
    (HERE / "mandate_b_raw_profiles.json").write_text(json.dumps(b, indent=2))
    print(f"wrote {len(a)} Mandate A profiles, {len(b)} Mandate B profiles")
