import json
from collections import Counter
r=json.load(open("_tr_inventory.json"))
ext=Counter(); newext=Counter()
multi=[]
for fld in r:
    if fld["n_docfiles"]>1: multi.append((fld["folder"],fld["n_docfiles"],fld["new"],fld["dup"]))
    for f in fld["files"]:
        if "file" in f and "." in f["file"]:
            e=f["file"].lower().rsplit(".",1)[-1]; ext[e]+=1
            if f.get("new"): newext[e]+=1
print("all file extensions:",dict(ext))
print("NEW file extensions:",dict(newext))
print("\nfolders with >1 file:")
for x in multi: print("  ",x)
