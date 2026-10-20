"""Point-of-care prices and what the member finally owes.

  posted   accumulators as claims arrived (arrival order), visit at its expected price - a running total
  replay   arrived claims replayed in date-of-service order, visit at its expected price
  this     replay + encounters the plan already knows about but has no claim for yet (booked / checked-in
           in-network visits) at their expected price; plus a range: the member price is lowest when the
           pending encounters come in high and this visit low, highest the other way. FIRM when they meet.
"""
from .adjudicate import Acc, limits, order, replay


def _allowed_at(c, t):
    return c["allowed"] if c["corr_at"] is not None and c["corr_at"] < t else c["first_allowed"]


def price(plan, fam, own, t, method, pending_at="expected", own_at="expected"):
    acc = Acc(limits(plan, fam["size"]))
    arrived = [c for c in fam["claims"] if c["arrive"] < t]
    rows = [dict(c, allowed=_allowed_at(c, t)) for c in arrived]
    if method == "posted":
        rows.sort(key=lambda c: c["arrive"])
    else:
        if method == "this":
            for c in fam["claims"]:
                if c["known"] and c["dos"] < t <= c["arrive"]:
                    rows.append(dict(c, allowed=pick(c, pending_at)))
        rows.sort(key=order)
    for c in rows:
        acc.cost(plan, c)
    return acc.cost(plan, dict(own, allowed=pick(own, own_at)), commit=False)


def pick(c, at):
    return c["expected"] if at == "expected" else c["range"][0] if at == "lo" else c["range"][1]


def quotes(plan, fam):
    """One row per encounter known at the visit: quote by method, range, and the final amount owed."""
    truth = replay(plan, fam["size"], fam["claims"])
    out = []
    for own in fam["claims"]:
        if not own["known"]:
            continue
        t = own["dos"]
        row = dict(id=own["id"], svc=own["svc"], final=truth[own["id"]],
                   posted=price(plan, fam, own, t, "posted"), replay=price(plan, fam, own, t, "replay"),
                   this=price(plan, fam, own, t, "this", pending_at="lo"),   # never count more than we know: no later bill from a pending visit
                   lo=price(plan, fam, own, t, "this", pending_at="hi", own_at="lo"),
                   hi=price(plan, fam, own, t, "this", pending_at="lo", own_at="hi"))
        out.append(row)
    return out


def arrival_order(plan, fam):
    """Member cents per claim if each claim is adjudicated once, when it arrives (final allowed, no reprocessing)."""
    acc, out = Acc(limits(plan, fam["size"])), {}
    for c in sorted(fam["claims"], key=lambda c: c["arrive"]):
        out[c["id"]] = acc.cost(plan, c)
    return out
