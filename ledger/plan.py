"""Plans as data, plus an HDHP (HSA-qualified) design check with cites.

Amounts in whole dollars here; adjudication works in cents.
"""

# IRS HDHP limits. 2026: Rev. Proc. 2025-19. 2027: Rev. Proc. 2026-24.
HDHP = {2026: dict(min_ded_self=1700, min_ded_fam=3400, max_oop_self=8500, max_oop_fam=17000, cite="Rev. Proc. 2025-19"),
        2027: dict(min_ded_self=1750, min_ded_fam=3500, max_oop_self=8700, max_oop_fam=17400, cite="Rev. Proc. 2026-24")}

# What an HDHP may pay before the deductible without breaking HSA eligibility.
PRE_DED_OK = {
    "preventive": "IRC 223(c)(2)(C) preventive care safe harbor",
    "telehealth": "IRC 223(c)(2)(E) telehealth safe harbor, made permanent by P.L. 119-21 (OBBBA)",
    "insulin": "Notice 2024-75 (insulin products regardless of diagnosis)",
    "chronic:diabetes": "Notice 2019-45 (glucose-lowering agents for diabetes)",
    "chronic:statin": "Notice 2019-45 (statins for heart disease / diabetes)",
}

S = lambda share, value=0, pre_ded=False, cat="other": dict(share=share, value=value, pre_ded=pre_ded, cat=cat)

SERVICES = {
    "preventive": S("none", pre_ded=True, cat="preventive"),
    "telehealth": S("copay", 0, pre_ded=True, cat="telehealth"),
    "office": S("copay", 40),
    "lab": S("coins", 0.2),
    "imaging": S("coins", 0.2),
    "er": S("coins", 0.2),
    "surgery": S("coins", 0.2),
    "inpatient": S("coins", 0.2),
    "rx_generic": S("copay", 10),
    "rx_glp1": S("coins", 0.2),
    "oon_specialist": S("coins", 0.4),
}

DEV_PLAN = dict(name="HDHP 2026 (dev)", year=2026, hsa=True, ded_self=1700, oop_self=4500,
                ded_fam=3400, ded_embedded=3400, oop_fam=9000, oop_embedded=4500, services=SERVICES)


def lint_hdhp(plan):
    """Return a list of (rule, detail) problems that would make an 'HSA-qualified' plan not an HDHP."""
    if not plan.get("hsa"):
        return []
    lim, out = HDHP[plan["year"]], []
    c = lim["cite"]
    if plan["ded_self"] < lim["min_ded_self"]:
        out.append(("MIN_DEDUCTIBLE", f"self-only deductible ${plan['ded_self']:,} < ${lim['min_ded_self']:,} ({c})"))
    if plan["ded_fam"] < lim["min_ded_fam"]:
        out.append(("MIN_DEDUCTIBLE", f"family deductible ${plan['ded_fam']:,} < ${lim['min_ded_fam']:,} ({c})"))
    if plan["ded_embedded"] < lim["min_ded_fam"]:
        out.append(("EMBEDDED_DEDUCTIBLE", f"per-person deductible in family coverage ${plan['ded_embedded']:,} < family minimum "
                                           f"${lim['min_ded_fam']:,}: one person could get benefits below the HDHP floor ({c} family minimum)"))
    if plan["oop_self"] > lim["max_oop_self"]:
        out.append(("MAX_OOP", f"self-only out-of-pocket max ${plan['oop_self']:,} > ${lim['max_oop_self']:,} ({c})"))
    if plan["oop_fam"] > lim["max_oop_fam"]:
        out.append(("MAX_OOP", f"family out-of-pocket max ${plan['oop_fam']:,} > ${lim['max_oop_fam']:,} ({c})"))
    for name, s in plan["services"].items():
        if s["pre_ded"] and s["cat"] not in PRE_DED_OK:
            out.append(("PRE_DEDUCTIBLE", f"'{name}' is paid before the deductible but is not preventive, telehealth or on the "
                                          f"chronic-care list (Notice 2019-45 / 2024-75)"))
    return out
