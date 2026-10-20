"""Upfront price vs what the member finally owes.  python evaluate.py [dev|heldout] [out.json]"""
import json, sys
from ledger import sim, quote, plan, adjudicate

UNCERTAIN = {"er", "surgery", "inpatient"}            # price not known at the visit (range only)


def run(which):
    if which == "heldout":
        h = json.load(open("heldout/config.json"))
        seeds, cfg, P = h["seeds"], h["cfg"], h["plan"]
        P["services"] = {**plan.SERVICES, **P.get("services", {})}
    else:
        seeds, cfg, P = [1, 2, 3], None, plan.DEV_PLAN
    R = dict(plan=P["name"], lint=plan.lint_hdhp(P), known=0, uncertain=0, firm=0, firm_right=0, in_range=0,
             families=0, families_arrival_diff=0, arrival_diff_usd=0.0)
    for m in ("posted", "replay", "this"):
        R[m] = dict(exact=0, bills=0, bill_usd=0.0, refund_usd=0.0)
    for s in seeds:
        for f in sim.make(s, cfg)["families"]:
            R["families"] += 1
            a, t = quote.arrival_order(P, f), adjudicate.replay(P, f["size"], f["claims"])
            if sum(a.values()) != sum(t.values()):
                R["families_arrival_diff"] += 1; R["arrival_diff_usd"] += abs(sum(a.values()) - sum(t.values())) / 100
            for r in quote.quotes(P, f):
                if r["svc"] in UNCERTAIN:
                    R["uncertain"] += 1
                    R["in_range"] += r["lo"] - 100 <= r["final"] <= r["hi"] + 100
                    continue
                R["known"] += 1
                firm = r["lo"] == r["hi"]
                R["firm"] += firm; R["firm_right"] += firm and abs(r["final"] - r["this"]) <= 100
                for m in ("posted", "replay", "this"):
                    d = r["final"] - r[m]
                    x = R[m]
                    x["exact"] += abs(d) <= 100; x["bills"] += d > 100
                    x["bill_usd"] += max(0, d) / 100; x["refund_usd"] += max(0, -d) / 100
    return R


NAMES = {"posted": "running total (arrival order)", "replay": "date-of-service replay", "this": "replay + known pending visits (this)"}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "dev"
    R = run(which)
    print(f"{which}: {R['plan']} - {R['families']} families, {R['known']} visits with a known price, {R['uncertain']} ER/surgery/inpatient")
    for m, n in NAMES.items():
        x = R[m]
        print(f"  {n:38s} upfront price exact {100 * x['exact'] / R['known']:5.1f}%   later bills {x['bills']:4d} (${x['bill_usd']:,.0f})"
              f"   later refunds ${x['refund_usd']:,.0f}")
    print(f"  FIRM quotes {R['firm']}/{R['known']}, right {R['firm_right']}   ER/surgery/inpatient: final inside range {R['in_range']}/{R['uncertain']}")
    print(f"  adjudicating once on arrival: {R['families_arrival_diff']}/{R['families']} families owe a different yearly total (${R['arrival_diff_usd']:,.0f})")
    print(f"  plan check: {R['lint'] or 'HDHP OK'}")
    if len(sys.argv) > 2:
        json.dump(R, open(sys.argv[2], "w"), indent=1)
