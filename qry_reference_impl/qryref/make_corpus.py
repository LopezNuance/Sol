from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path
from copy import deepcopy
from .engine import infer_all_bounds
from .certificate import generate_certificate

BASE_SOURCES = {
    "users": {
        "schema": [
            {"name": "id", "type": "i64", "nullable": False},
            {"name": "name", "type": "string", "nullable": False},
            {"name": "country", "type": "string", "nullable": True},
            {"name": "active", "type": "bool", "nullable": False}
        ],
        "rows": {"min": 0, "max": 1000},
        "unique_keys": [["id"]]
    },
    "orders": {
        "schema": [
            {"name": "order_id", "type": "i64", "nullable": False},
            {"name": "user_id", "type": "i64", "nullable": False},
            {"name": "amount", "type": "decimal", "nullable": False},
            {"name": "status", "type": "string", "nullable": False}
        ],
        "rows": {"min": 0, "max": 5000},
        "unique_keys": [["order_id"]]
    },
    "profiles": {
        "schema": [
            {"name": "user_id", "type": "i64", "nullable": False},
            {"name": "tier", "type": "string", "nullable": True}
        ],
        "rows": {"min": 0, "max": 1000},
        "unique_keys": [["user_id"]]
    },
    "countries": {
        "schema": [
            {"name": "country", "type": "string", "nullable": False},
            {"name": "region", "type": "string", "nullable": False}
        ],
        "rows": {"min": 0, "max": 250},
        "unique_keys": [["country"]]
    }
}


def q(case_id, nodes, root, sources=None, desc=""):
    return {"schema_version": "qry.query.v0.1", "query_id": case_id, "description": desc or case_id, "sources": deepcopy(sources or BASE_SOURCES), "nodes": nodes, "root": root}


def read(id, source): return {"id": id, "op": "read", "source": source}
def filt(id, inp, mn, mx, expr="pred"): return {"id": id, "op": "filter", "input": inp, "predicate": {"expr": expr, "min_selectivity": mn, "max_selectivity": mx}}
def proj(id, inp, fields): return {"id": id, "op": "project", "input": inp, "fields": fields}
def lim(id, inp, n): return {"id": id, "op": "limit", "input": inp, "limit": n}
def sort(id, inp, by): return {"id": id, "op": "sort", "input": inp, "by": by}
def dist(id, inp, keys): return {"id": id, "op": "distinct", "input": inp, "keys": keys}
def agg(id, inp, groups, aggs): return {"id": id, "op": "aggregate", "input": inp, "group_by": groups, "aggregates": aggs}
def join(id, l, r, jt="inner", rel="many_to_many"): return {"id": id, "op": "join", "left": l, "right": r, "join_type": jt, "relationship": rel, "on": [{"left": "id", "right": "user_id"}]}
def union(id, inputs, op="union_all"): return {"id": id, "op": op, "inputs": inputs}
def ren(id, inp, mapping): return {"id": id, "op": "rename", "input": inp, "mapping": mapping}

def user_fields(*names): return [{"name": n, "expr": n} for n in names]
def order_fields(*names): return [{"name": n, "expr": n} for n in names]


def valid_queries():
    qs=[]
    # 1-10 simple unary
    qs.append(q("QRY-001", [read("u", "users")], "u", desc="read users"))
    qs.append(q("QRY-002", [read("o", "orders")], "o", desc="read orders"))
    qs.append(q("QRY-003", [read("u", "users"), proj("p", "u", user_fields("id", "name"))], "p"))
    qs.append(q("QRY-004", [read("u", "users"), filt("f", "u", 0.0, 0.5, "active")], "f"))
    qs.append(q("QRY-005", [read("o", "orders"), filt("f", "o", 0.1, 0.2, "amount>100")], "f"))
    qs.append(q("QRY-006", [read("u", "users"), lim("l", "u", 10)], "l"))
    qs.append(q("QRY-007", [read("u", "users"), sort("s", "u", ["country", "id"])], "s"))
    qs.append(q("QRY-008", [read("u", "users"), dist("d", "u", ["country"])], "d"))
    qs.append(q("QRY-009", [read("u", "users"), agg("a", "u", [], [{"name":"n","fn":"count","type":"i64"}])], "a"))
    qs.append(q("QRY-010", [read("u", "users"), agg("a", "u", ["country"], [{"name":"n","fn":"count","type":"i64"}])], "a"))
    # 11-20 combinations and joins
    qs.append(q("QRY-011", [read("u", "users"), filt("f", "u", 0.0, 0.4), proj("p", "f", user_fields("id","country")), lim("l", "p", 25)], "l"))
    qs.append(q("QRY-012", [read("u", "users"), proj("p1","u",user_fields("id","country")), proj("p2","u",user_fields("id","country")), union("ua",["p1","p2"],"union_all")], "ua"))
    qs.append(q("QRY-013", [read("u", "users"), proj("p1","u",user_fields("id","country")), proj("p2","u",user_fields("id","country")), union("ud",["p1","p2"],"union_distinct")], "ud"))
    qs.append(q("QRY-014", [read("u","users"), read("o","orders"), join("j","u","o","inner","many_to_many")], "j"))
    qs.append(q("QRY-015", [read("o","orders"), read("u","users"), join("j","o","u","inner","many_to_one")], "j"))
    qs.append(q("QRY-016", [read("u","users"), read("o","orders"), join("j","u","o","inner","one_to_many")], "j"))
    qs.append(q("QRY-017", [read("u","users"), read("p","profiles"), join("j","u","p","inner","one_to_one")], "j"))
    qs.append(q("QRY-018", [read("u","users"), read("o","orders"), join("j","u","o","left","one_to_many")], "j"))
    qs.append(q("QRY-019", [read("u","users"), read("o","orders"), join("j","u","o","semi","many_to_many")], "j"))
    qs.append(q("QRY-020", [read("u","users"), read("o","orders"), join("j","u","o","anti","many_to_many")], "j"))
    # 21-35 nested variants
    for i, sel in enumerate([0.05,0.1,0.15,0.25,0.33,0.66,0.75,0.9], start=21):
        qs.append(q(f"QRY-{i:03d}", [read("o","orders"), filt("f","o",0,sel), agg("a","f",["status"],[{"name":"sum_amount","fn":"sum","type":"decimal"}])], "a"))
    qs.append(q("QRY-029", [read("c","countries"), sort("s","c",["region"]), lim("l","s",100)], "l"))
    qs.append(q("QRY-030", [read("u","users"), ren("r","u",{"id":"user_id"}), proj("p","r",[{"name":"user_id","expr":"user_id"},{"name":"country","expr":"country"}])], "p"))
    qs.append(q("QRY-031", [read("u","users"), proj("p","u",[{"name":"one","literal":1,"type":"i32","nullable":False},{"name":"id","expr":"id"}])], "p"))
    qs.append(q("QRY-032", [read("u","users"), read("c","countries"), join("j","u","c","inner","many_to_one"), agg("a","j",["right.region"],[{"name":"n","fn":"count","type":"i64"}])], "a"))
    qs.append(q("QRY-033", [read("o","orders"), dist("d","o",["user_id"]), lim("l","d",500)], "l"))
    qs.append(q("QRY-034", [read("u","users"), lim("l0","u",0)], "l0"))
    qs.append(q("QRY-035", [read("u","users"), filt("f","u",1.0,1.0), lim("l","f",1000)], "l"))
    # 36-45 more valid
    qs.append(q("QRY-036", [read("o","orders"), sort("s","o",["amount"]), filt("f","s",0.0,0.2), lim("l","f",100)], "l"))
    qs.append(q("QRY-037", [read("u","users"), read("p","profiles"), join("j","u","p","left","one_to_one"), filt("f","j",0,0.5)], "f"))
    qs.append(q("QRY-038", [read("o","orders"), agg("a","o",[],[{"name":"total","fn":"sum","type":"decimal"},{"name":"n","fn":"count","type":"i64"}])], "a"))
    qs.append(q("QRY-039", [read("u","users"), proj("p","u",user_fields("id","country")), dist("d","p",["country"]), sort("s","d",["country"])], "s"))
    qs.append(q("QRY-040", [read("u","users"), filt("f1","u",0,0.8), filt("f2","f1",0,0.5)], "f2"))
    qs.append(q("QRY-041", [read("u","users"), read("o","orders"), join("j","u","o","full","many_to_many")], "j"))
    qs.append(q("QRY-042", [read("u","users"), read("p","profiles"), join("j","u","p","right","one_to_one")], "j"))
    qs.append(q("QRY-043", [read("o","orders"), proj("p1","o",order_fields("order_id","status")), filt("f","o",0,0.2), proj("p2","f",order_fields("order_id","status")), union("ua",["p1","p2"],"union_all"), lim("l","ua",6000)], "l"))
    qs.append(q("QRY-044", [read("u","users"), filt("f","u",0,0.2), proj("p","f",user_fields("id","active")), sort("s","p",["id"])], "s"))
    qs.append(q("QRY-045", [read("o","orders"), filt("f","o",0,0.05), agg("a","f",[],[{"name":"n","fn":"count","type":"i64"}])], "a"))
    return qs


def invalid_queries(valids):
    cases=[]
    def add(cid, query, expected, desc): cases.append((cid, query, expected, desc, None))
    # schema missing query_id
    bad = deepcopy(valids[0]); bad.pop("query_id")
    add("QRY-046", bad, ["QRY-SCHEMA-001"], "schema missing query_id")
    bad = deepcopy(valids[0]); bad["query_id"]="QRY-047"; bad["nodes"].append(deepcopy(bad["nodes"][0]))
    add("QRY-047", bad, ["QRY-SEM-001"], "duplicate node")
    bad = deepcopy(valids[0]); bad["query_id"]="QRY-048"; bad["root"]="nope"
    add("QRY-048", bad, ["QRY-SEM-002"], "missing root")
    bad = q("QRY-049", [read("u","users"), filt("f","missing",0,1)], "f")
    add("QRY-049", bad, ["QRY-SEM-003"], "missing input")
    bad = {"schema_version":"qry.query.v0.1","query_id":"QRY-050","sources":deepcopy(BASE_SOURCES),"nodes":[{"id":"a","op":"filter","input":"b","predicate":{"min_selectivity":0,"max_selectivity":1}},{"id":"b","op":"filter","input":"a","predicate":{"min_selectivity":0,"max_selectivity":1}}],"root":"a"}
    add("QRY-050", bad, ["QRY-SEM-004"], "cycle")
    bad = q("QRY-051", [{"id":"x","op":"read","source":"ghost"}], "x")
    add("QRY-051", bad, ["QRY-SEM-005"], "unknown source")
    bad = q("QRY-052", [read("u","users"), proj("p","u",[{"name":"no","expr":"nope"}])], "p")
    add("QRY-052", bad, ["QRY-SEM-006"], "project missing field")
    bad = q("QRY-053", [read("u","users"), read("o","orders"), union("uall",["u","o"],"union_all")], "uall")
    add("QRY-053", bad, ["QRY-SEM-007"], "union mismatch")
    bad = q("QRY-054", [read("u","users"), filt("f","u",0.8,0.2)], "f")
    add("QRY-054", bad, ["QRY-SEM-008"], "bad selectivity")
    bad = q("QRY-055", [read("u","users"), lim("l","u",-1)], "l")
    add("QRY-055", bad, ["QRY-SEM-009"], "bad limit")
    bad = q("QRY-056", [{"id":"x","op":"explode","input":"u"}], "x")
    add("QRY-056", bad, ["QRY-SEM-010"], "unknown op")
    bad = q("QRY-057", [read("u","users"), proj("p","u",[{"name":"x","expr":"id"},{"name":"x","expr":"name"}])], "p")
    add("QRY-057", bad, ["QRY-SEM-011"], "duplicate output field")
    bad = q("QRY-058", [read("u","users"), read("o","orders"), join("j","u","o","weird","many_to_many")], "j")
    add("QRY-058", bad, ["QRY-SEM-012"], "invalid join type")
    # valid query but expected bounds wrong
    bad = deepcopy(valids[0]); bad["query_id"]="QRY-059"
    cases.append(("QRY-059", bad, ["QRY-BOUND-001"], "expected bounds wrong", "bad_bounds"))
    # cert failures
    for cid, mutation, exp, desc in [
        ("QRY-060", "missing_step", ["QRY-CERT-001"], "certificate missing step"),
        ("QRY-061", "step_bound", ["QRY-CERT-002"], "certificate bad step bound"),
        ("QRY-062", "final_bound", ["QRY-CERT-003"], "certificate bad final bound"),
        ("QRY-063", "order", ["QRY-CERT-004"], "certificate bad order"),
        ("QRY-064", "root", ["QRY-CERT-005"], "certificate bad root"),
    ]:
        base = deepcopy(valids[10]); base["query_id"] = cid
        cases.append((cid, base, exp, desc, mutation))
    # schema source missing schema
    bad = deepcopy(valids[0]); bad["query_id"]="QRY-065"; bad["sources"]["users"].pop("schema")
    add("QRY-065", bad, ["QRY-SCHEMA-001"], "source missing schema")
    # aggregate missing group field
    bad = q("QRY-066", [read("u","users"), agg("a","u",["missing"],[{"name":"n","fn":"count","type":"i64"}])], "a")
    add("QRY-066", bad, ["QRY-SEM-006"], "aggregate missing group field")
    # sort missing field
    bad = q("QRY-067", [read("u","users"), sort("s","u",["missing"])], "s")
    add("QRY-067", bad, ["QRY-SEM-006"], "sort missing field")
    # distinct missing key
    bad = q("QRY-068", [read("u","users"), dist("d","u",["missing"])], "d")
    add("QRY-068", bad, ["QRY-SEM-006"], "distinct missing field")
    # missing certificate
    base = deepcopy(valids[0]); base["query_id"]="QRY-069"
    cases.append(("QRY-069", base, ["QRY-CERT-000"], "missing certificate", "no_cert"))
    return cases


def write_case(out: Path, query: dict, expected_diags: list[str], desc: str, mutation=None, cid_override: str | None = None):
    cid = cid_override or query.get("query_id", out.name)
    d = out / "cases" / cid
    d.mkdir(parents=True, exist_ok=True)
    (d/"query.json").write_text(json.dumps(query, indent=2, sort_keys=True))
    manifest = {"case_id": cid, "description": desc, "expected_diagnostics": expected_diags}
    (d/"manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    if not expected_diags or mutation in {"bad_bounds","missing_step","step_bound","final_bound","order","root"}:
        try:
            bounds = infer_all_bounds(query)
            rootb = bounds[query["root"]].to_json()
            expected = {"schema_version":"qry.bounds.v0.1","query_id":cid,"root":query["root"],"node_bounds":{k:v.to_json() for k,v in bounds.items()},"root_bound":rootb}
            if mutation == "bad_bounds":
                expected["root_bound"]["rows"]["max"] = 999999
            (d/"expected_bounds.json").write_text(json.dumps(expected, indent=2, sort_keys=True))
            cert = generate_certificate(query, cid)
            if mutation == "missing_step":
                cert["steps"] = cert["steps"][:-1]
            elif mutation == "step_bound":
                cert["steps"][-1]["bound"]["rows"]["max"] = 123456
            elif mutation == "final_bound":
                cert["final_bound"]["rows"]["max"] = 123456
            elif mutation == "order":
                cert["steps"] = list(reversed(cert["steps"]))
            elif mutation == "root":
                cert["root"] = "not_the_root"
            if mutation != "no_cert":
                (d/"certificate.json").write_text(json.dumps(cert, indent=2, sort_keys=True))
                if not expected_diags:
                    cert_dir = out / "certificates"
                    cert_dir.mkdir(exist_ok=True)
                    (cert_dir/f"{cid}.cert.json").write_text(json.dumps(cert, indent=2, sort_keys=True))
        except Exception:
            pass
    (d/"README.md").write_text(f"# {cid}\n\n{desc}\n")


def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="corpus")
    args=ap.parse_args(argv)
    out=Path(args.out)
    if out.exists(): shutil.rmtree(out)
    (out/"cases").mkdir(parents=True)
    valids=valid_queries()
    all_cases = []
    for query in valids:
        all_cases.append((query["query_id"], query, [], query.get("description", query["query_id"]), None))
    all_cases.extend(invalid_queries(valids))
    assert len(all_cases) == 69, len(all_cases)
    for cid, query, exp, desc, mut in all_cases:
        write_case(out, query, exp, desc, mut, cid_override=cid)
    manifest = {"schema_version":"qry.corpus.v0.1", "case_count":69, "cases":[c[0] for c in all_cases]}
    (out/"manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"wrote {len(all_cases)} cases to {out}")

if __name__ == "__main__":
    main()
