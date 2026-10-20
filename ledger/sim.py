"""Synthetic employer: families, encounters over one plan year, claims that arrive late and get corrected."""
import math
import random

# service: (encounters per person-year, median allowed $, lognormal sigma, lag days (lo, hi), price known at visit)
SVC = {
    "preventive": (0.9, 250, 0.3, (3, 30), True),
    "telehealth": (1.2, 60, 0.2, (0, 2), True),
    "office": (2.4, 160, 0.3, (3, 30), True),
    "lab": (1.4, 90, 0.6, (5, 25), True),
    "imaging": (0.25, 900, 0.6, (7, 40), True),
    "er": (0.15, 2200, 0.6, (20, 90), False),
    "surgery": (0.05, 6000, 0.5, (30, 100), False),
    "inpatient": (0.02, 18000, 0.6, (40, 120), False),
    "oon_specialist": (0.2, 350, 0.5, (30, 150), None),        # None: not known to the plan until the claim arrives
}
DEV = dict(employees=150, family_mix=[0.55, 0.2, 0.13, 0.12], rx_generic=0.3, rx_glp1=0.08, correct_rate=0.06,
           lag_scale=1.0, util=1.0)


def make(seed, cfg=None):
    c = {**DEV, **(cfg or {})}
    r = random.Random(seed)
    fams, cid = [], 0
    for f in range(c["employees"]):
        size = r.choices([1, 2, 3, 4], c["family_mix"])[0]
        claims = []
        for p in range(size):
            for svc, (rate, med, sig, (lo, hi), known) in SVC.items():
                n = poisson(r, rate * c["util"])
                for _ in range(n):
                    cid += 1
                    claims.append(claim(r, cid, p, svc, r.uniform(0, 365), med, sig, lo, hi, known, c))
            for svc, share, med in (("rx_generic", c["rx_generic"], 25), ("rx_glp1", c["rx_glp1"], 1000)):
                if r.random() < share:
                    d = r.uniform(0, 30)
                    while d < 365:
                        cid += 1
                        claims.append(claim(r, cid, p, svc, d, med, 0.0, 0, 0, True, c))
                        d += 30
        fams.append(dict(id=f, size=size, claims=claims))
    return dict(families=fams, cfg=c)


def claim(r, cid, p, svc, dos, med, sig, lo, hi, known, c):
    allowed = max(500, int(round(med * math.exp(r.gauss(0, sig)) * 100)))
    arrive = dos + r.uniform(lo, hi) * c["lag_scale"] + 0.01
    x = dict(id=cid, person=p, svc=svc, dos=dos, allowed=allowed, first_allowed=allowed, arrive=arrive,
             known=known is not None, expected=allowed if known else (med * 100 if known is False else None),
             range=(allowed, allowed) if known else (int(med * 40), int(med * 300)) if known is False else None,
             corr_at=None)
    if svc in ("imaging", "er", "surgery", "inpatient") and r.random() < c["correct_rate"]:
        x["corr_at"] = arrive + r.uniform(20, 80)
        x["allowed"] = max(500, int(allowed * r.uniform(0.6, 1.4)))
    return x


def poisson(r, lam):
    k, t = 0, r.expovariate(1.0)
    while t < lam:
        k += 1
        t += r.expovariate(1.0)
    return k
