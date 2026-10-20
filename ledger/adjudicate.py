"""Member cost share for a family's claims, replayed in date-of-service order (the plan's accumulator rule)."""


def limits(plan, family_size):
    if family_size == 1:
        return dict(ded_ind=plan["ded_self"] * 100, ded_fam=plan["ded_self"] * 100,
                    oop_ind=plan["oop_self"] * 100, oop_fam=plan["oop_self"] * 100)
    return dict(ded_ind=plan["ded_embedded"] * 100, ded_fam=plan["ded_fam"] * 100,
                oop_ind=plan["oop_embedded"] * 100, oop_fam=plan["oop_fam"] * 100)


class Acc:
    def __init__(self, lim):
        self.lim, self.ded, self.oop, self.dF, self.oF = lim, {}, {}, 0, 0

    def cost(self, plan, c, commit=True):
        """Member cents for one claim; updates the accumulators when commit."""
        L, p, s = self.lim, c["person"], plan["services"][c["svc"]]
        allowed = c["allowed"]
        rem_ded = max(0, min(L["ded_ind"] - self.ded.get(p, 0), L["ded_fam"] - self.dF))
        rem_oop = max(0, min(L["oop_ind"] - self.oop.get(p, 0), L["oop_fam"] - self.oF))
        ded_part = 0 if s["pre_ded"] else min(allowed, rem_ded)
        rest = allowed - ded_part
        share = 0 if s["share"] == "none" else min(int(s["value"] * 100), rest) if s["share"] == "copay" else round(s["value"] * rest)
        member = min(ded_part + share, rem_oop)
        if commit:
            dc = min(ded_part, member)
            self.ded[p] = self.ded.get(p, 0) + dc; self.dF += dc
            self.oop[p] = self.oop.get(p, 0) + member; self.oF += member
        return member


def order(c):
    return (c["dos"], c["id"])


def replay(plan, family_size, claims):
    """{claim id: member cents} for claims adjudicated in date-of-service order."""
    acc, out = Acc(limits(plan, family_size)), {}
    for c in sorted(claims, key=order):
        out[c["id"]] = acc.cost(plan, c)
    return out
