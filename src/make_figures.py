"""Regenerate primary figures from the packaged Go 1.23.2 source corpus."""
from __future__ import annotations
import json, os
import matplotlib as mpl
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
import matplotlib.pyplot as plt

ROOT=os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
with open(os.path.join(ROOT,"results","real_source_validation.json"),encoding="utf-8") as f:
    obj=json.load(f)
rows=obj["rows"]
order=["archive/zip","compress/flate","crypto/tls","encoding/json","net/http"]
labels=["archive/zip","compress/flate","crypto/tls","encoding/json","net/http"]

def group(field):
    return [[r[field] for r in rows if r["file"].startswith(pkg+"/")] for pkg in order]

outdir=os.path.join(ROOT,"figures"); os.makedirs(outdir,exist_ok=True)
for filename,field,ylabel in [
    ("fig1_boundary_jaccard","boundary_jaccard","Boundary Jaccard similarity"),
    ("fig2_migration_reuse","content_addressed_migration_reuse","Content-addressed migration reuse"),
]:
    fig,ax=plt.subplots(figsize=(7.0,3.7))
    ax.boxplot(group(field),tick_labels=labels,showmeans=True,showfliers=True)
    ax.set_ylabel(ylabel); ax.set_ylim(-0.05,1.05); ax.tick_params(axis="x",rotation=18)
    ax.grid(True,axis="y",alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir,filename+".pdf"),bbox_inches="tight")
    fig.savefig(os.path.join(outdir,filename+".png"),dpi=240,bbox_inches="tight")
    plt.close(fig)
print("wrote primary real-source figures")
