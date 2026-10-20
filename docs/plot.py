"""docs/result.png from the frozen held-out first run."""
import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = json.load(open("out/heldout_first_run.json"))
names = {"posted": "running total\n(arrival order)", "replay": "date-of-service\nreplay", "this": "replay + known\npending (this)"}
col = ["#bbb", "#999", "#1f6feb"]
fig, ax = plt.subplots(1, 3, figsize=(13, 4))
vals = [[100 * R[m]["exact"] / R["known"] for m in names], [R[m]["refund_usd"] / 1000 for m in names], [R[m]["bill_usd"] / 1000 for m in names]]
titles = ["Upfront price exactly right (%)", "Over-charged at the visit, refunded later ($k)", "Under-charged, billed later ($k)"]
for a, v, t in zip(ax, vals, titles):
    a.bar(list(names.values()), v, color=col)
    for i, x in enumerate(v):
        a.text(i, x, f"{x:.1f}", ha="center", va="bottom", fontsize=9)
    a.set_title(t, fontsize=10)
ax[0].set_ylim(85, 100)
fig.suptitle(f"Held-out, frozen first run: {R['families']} families, {R['known']:,} visits with a known price ({R['plan']})", fontsize=11)
plt.tight_layout(); plt.savefig("docs/result.png", dpi=110)
