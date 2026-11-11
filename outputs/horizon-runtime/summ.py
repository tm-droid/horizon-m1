import json,subprocess,sys
out=subprocess.run(["/Library/Frameworks/Python.framework/Versions/3.13/bin/python3","analyze-overrides.py",*sys.argv[1:]],capture_output=True,text=True).stdout
d=json.loads(out)
for case,arms in d.items():
    print("==",case,"base med",arms.get("_base_medians"),"base-base scene%",arms.get("_base_vs_base_scene_diff_pct"))
    for arm,row in arms.items():
        if arm.startswith("_"): continue
        print(" ",arm,"n",row["n_pairs"],"scene%",row["scene_diff_pct_vs_base"])
        for k,v in row.items():
            if isinstance(v,dict): print("    %-34s %+.2f d=%s"%(k,v["med"],v["d"]))
