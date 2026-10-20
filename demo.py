"""One family, one plan year: why the price at the visit changes later, and what the ledger does about it."""
from ledger import plan, quote, adjudicate

P = plan.DEV_PLAN
D = lambda m, d: (m - 1) * 30.4 + d                     # rough day-of-year


def c(i, who, svc, dos, usd, arrive, known=True, rng=None):
    a = int(usd * 100)
    return dict(id=i, person=who, svc=svc, dos=dos, allowed=a, first_allowed=a, arrive=arrive, known=known,
                expected=a if rng is None else 220000, range=(a, a) if rng is None else rng, corr_at=None)


NAMES = {0: "Dad", 1: "Son", 2: "Daughter"}
fam = dict(size=3, claims=[
    c(1, 1, "lab", D(1, 12), 600, D(1, 20)),                                   # posted in January
    c(2, 1, "imaging", D(2, 20), 1000, D(4, 10)),                             # son's MRI: booked in-network, claim lands in April
    c(3, 2, "er", D(3, 2), 2600, D(5, 18), rng=(88000, 660000)),              # daughter's ER: price unknown until the claim, May
    c(4, 0, "imaging", D(3, 20), 1450, D(3, 28)),                             # dad's MRI on March 20: the visit we price
])
print(f"Plan: {P['name']}, family deductible ${P['ded_fam']:,}, then 20% coinsurance.\n")
for x in fam["claims"]:
    print(f"  {NAMES[x['person']]:9s} {x['svc']:8s} visit day {x['dos']:5.0f}  claim arrives day {x['arrive']:5.0f}  allowed ${x['allowed'] / 100:,.0f}")
r = {x["id"]: x for x in quote.quotes(P, fam)}[4]
print(f"\nDad's MRI, priced at the visit (day {D(3, 20):.0f}):")
print(f"  running total of arrived claims     ${r['posted'] / 100:,.0f}   (only January's lab is posted)")
print(f"  + son's booked MRI, ER at its floor ${r['this'] / 100:,.0f}   (this; range ${r['lo'] / 100:,.0f}-${r['hi'] / 100:,.0f}, not FIRM: ER claim pending)")
print(f"  what Dad finally owes               ${r['final'] / 100:,.0f}   (date-of-service replay once every claim is in)")
arr = quote.arrival_order(P, fam)
print(f"\nAdjudicated once on arrival instead: Dad's MRI costs ${arr[4] / 100:,.0f}, because the son's and daughter's claims arrive after it.")
print(f"Just-in-time HSA funding at the visit: running total over-funds ${(r['posted'] - r['final']) / 100:,.0f}, this ${(r['this'] - r['final']) / 100:,.0f}, "
      f"and the member sees the range instead of a surprise.")
