import copy
from ledger import plan, adjudicate, quote, sim

P = plan.DEV_PLAN


def c(i, p, svc, dos, usd, arrive=None, known=True):
    a = int(usd * 100)
    return dict(id=i, person=p, svc=svc, dos=dos, allowed=a, first_allowed=a, arrive=arrive if arrive is not None else dos + 1,
                known=known, expected=a, range=(a, a), corr_at=None)


def test_deductible_then_coinsurance_then_oop_cap():
    out = adjudicate.replay(P, 1, [c(1, 0, "imaging", 1, 1000), c(2, 0, "imaging", 2, 1000), c(3, 0, "inpatient", 3, 50000)])
    assert out[1] == 100000                     # all to deductible
    assert out[2] == 70000 + 6000               # $700 finishes the $1,700 deductible, 20% of the other $300
    assert sum(out.values()) == 450000          # capped at $4,500 out-of-pocket


def test_preventive_and_telehealth_skip_the_deductible():
    out = adjudicate.replay(P, 1, [c(1, 0, "preventive", 1, 250), c(2, 0, "telehealth", 2, 60)])
    assert out == {1: 0, 2: 0}


def test_embedded_family_limits():
    fam = [c(i, i % 3, "inpatient", i, 20000) for i in range(1, 7)]
    out = adjudicate.replay(P, 3, fam)
    assert sum(out.values()) == 900000          # family OOP $9,000
    per = {}
    for x in fam:
        per[x["person"]] = per.get(x["person"], 0) + out[x["id"]]
    assert max(per.values()) == 450000          # nobody pays more than the embedded $4,500


def test_dos_order_not_arrival_order():
    late_er = c(1, 1, "er", 10, 2000, arrive=80)     # daughter's ER, claim lands months later
    mri = c(2, 0, "imaging", 20, 1450, arrive=30)
    fam = dict(size=2, claims=[late_er, mri])
    truth = adjudicate.replay(P, 2, fam["claims"])
    arr = quote.arrival_order(P, fam)
    assert truth[2] < arr[2]                    # arrival order charges the MRI the deductible the ER already used
    q = {r["id"]: r for r in quote.quotes(P, fam)}[2]
    assert q["posted"] == 145000 and q["this"] == truth[2] and q["lo"] == q["hi"]


def test_quote_never_uses_the_future():
    s = sim.make(4, dict(employees=20))
    f = s["families"][0]
    for own in f["claims"]:
        if own["known"]:
            g = copy.deepcopy(f)
            for x in g["claims"]:
                if x["arrive"] >= own["dos"] and not (x["known"] and x["dos"] < own["dos"]):
                    x["allowed"] = x["first_allowed"] = 99999999       # unknown at the visit: must not matter
            assert quote.price(P, f, own, own["dos"], "this") == quote.price(P, g, dict(own, expected=own["expected"]), own["dos"], "this")


def test_hdhp_lint():
    assert plan.lint_hdhp(P) == []
    bad = dict(P, year=2027, ded_self=0, ded_embedded=1750, oop_self=9000,
               services={**P["services"], "rx_glp1": dict(share="copay", value=0, pre_ded=True, cat="other"),
                         "insulin": dict(share="copay", value=0, pre_ded=True, cat="insulin")})
    rules = [r for r, _ in plan.lint_hdhp(bad)]
    assert rules.count("MIN_DEDUCTIBLE") == 2         # self $0 < $1,750 and family $3,400 < 2027 $3,500
    assert "EMBEDDED_DEDUCTIBLE" in rules and "MAX_OOP" in rules
    assert rules.count("PRE_DEDUCTIBLE") == 1     # GLP-1 flagged, insulin allowed
