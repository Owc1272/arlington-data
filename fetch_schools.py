"""
Fetch Arlington, MA school data from MA DESE via Socrata API.
Source: https://educationtocareer.data.mass.gov

No authentication required. Filters for Arlington district (DIST_NAME='Arlington').
Output: website/data/schools.json
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

OUTPUT_PATH = Path(__file__).parent / "website" / "data" / "schools.json"
BASE = "https://educationtocareer.data.mass.gov/resource"
HEADERS = {"User-Agent": "Mozilla/5.0"}
DIST_FILTER = "DIST_NAME='Arlington'"
DIST_FILTER_ORG = "DIST_NAME='Arlington' AND ORG_TYPE='District'"


def fetch_socrata(dataset_id, where=None, limit=5000):
    """Fetch data from Socrata API."""
    url = f"{BASE}/{dataset_id}.json"
    params = {"$limit": limit}
    if where:
        params["$where"] = where
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    return []


def safe_int(v):
    if v is None: return None
    try: return int(float(v))
    except: return None


def safe_float(v):
    if v is None: return None
    try: return float(v)
    except: return None


def safe_pct(v):
    """Convert decimal like 0.645 to percentage like 64.5."""
    f = safe_float(v)
    if f is None: return None
    if f <= 1.0: return round(f * 100, 1)
    return round(f, 1)


def fetch_enrollment():
    """Enrollment by grade, race, gender, selected populations."""
    print("Fetching enrollment (t8td-gens)...")
    data = fetch_socrata("t8td-gens", DIST_FILTER_ORG)
    results = []
    for row in sorted(data, key=lambda r: r.get("sy", "")):
        year = safe_int(row.get("sy"))
        if not year: continue
        results.append({
            "year": year,
            "total": safe_int(row.get("total_cnt")),
            "by_grade": {
                "pk": safe_int(row.get("pk_cnt")),
                "k": safe_int(row.get("k_cnt")),
                **{f"g{i}": safe_int(row.get(f"g{i}_cnt")) for i in range(1, 13)},
            },
            "race_pct": {
                "white": safe_pct(row.get("wh_pct")),
                "asian": safe_pct(row.get("as_pct")),
                "hispanic": safe_pct(row.get("hl_pct")),
                "black": safe_pct(row.get("baa_pct")),
                "multiracial": safe_pct(row.get("mnhl_pct")),
            },
            "gender_pct": {
                "female": safe_pct(row.get("fe_pct")),
                "male": safe_pct(row.get("ma_pct")),
            },
            "el_pct": safe_pct(row.get("el_pct")),
            "low_income_pct": safe_pct(row.get("li_pct")),
            "swd_pct": safe_pct(row.get("swd_pct")),
            "high_needs_pct": safe_pct(row.get("hn_pct")),
        })
    print(f"  {len(results)} years")
    return results


def fetch_mcas():
    """MCAS legacy results — district-level, All Students, ELA + Math."""
    print("Fetching MCAS (ccsh-ajgw)...")
    data = fetch_socrata("ccsh-ajgw",
        f"{DIST_FILTER_ORG} AND STU_GRP='All Students' AND (SUBJ='ELA' OR SUBJ='MTH')")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        results.append({
            "year": year,
            "subject": row.get("subj"),
            "grade": row.get("grd"),
            "tested": safe_int(row.get("tot_stu_incl")),
            "proficient_advanced_pct": safe_pct(row.get("p_a_pct")),
            "advanced_pct": safe_pct(row.get("a_pct")),
            "proficient_pct": safe_pct(row.get("p_pct")),
            "needs_improvement_pct": safe_pct(row.get("ni_pct")),
            "warning_failing_pct": safe_pct(row.get("wf_pct")),
        })
    # Aggregate to district-level per year/subject (avg across grades)
    agg = {}
    for r in results:
        key = (r["year"], r["subject"])
        if key not in agg:
            agg[key] = {"year": r["year"], "subject": r["subject"], "pa_pcts": [], "tested_total": 0}
        if r["proficient_advanced_pct"] is not None:
            agg[key]["pa_pcts"].append(r["proficient_advanced_pct"])
            agg[key]["tested_total"] += r["tested"] or 0

    aggregated = []
    for key, v in sorted(agg.items()):
        if v["pa_pcts"]:
            aggregated.append({
                "year": v["year"],
                "subject": v["subject"],
                "proficient_advanced_pct": round(sum(v["pa_pcts"]) / len(v["pa_pcts"]), 1),
                "tested": v["tested_total"],
            })
    print(f"  {len(aggregated)} year/subject records")
    return aggregated


def fetch_graduation():
    """Graduation rates."""
    print("Fetching graduation rates (n2xa-p822)...")
    data = fetch_socrata("n2xa-p822",
        f"{DIST_FILTER} AND ORG_TYPE='District' AND STU_GRP='All Students' AND GRAD_RATE_TYPE like '%4-Year%'")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        rate = safe_pct(row.get("grad_pct"))
        dropout = safe_pct(row.get("drpout_pct"))
        if rate is not None:
            results.append({
                "year": year,
                "graduation_rate_4yr": rate,
                "dropout_pct": dropout,
            })
    results.sort(key=lambda r: r["year"])
    seen = {}
    for r in results:
        seen[r["year"]] = r
    results = sorted(seen.values(), key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def fetch_dropout():
    """Dropout rates."""
    print("Fetching dropout rates (cmm7-ttbg)...")
    data = fetch_socrata("cmm7-ttbg",
        f"{DIST_FILTER} AND ORG_TYPE='District' AND STU_GRP='All Students'")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        rate = safe_pct(row.get("drpout_pct_all"))
        if rate is not None:
            results.append({"year": year, "dropout_rate": rate})
    seen = {}
    for r in results:
        seen[r["year"]] = r
    results = sorted(seen.values(), key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def fetch_staff():
    """Staff/educator data by age group."""
    print("Fetching staff data (a4b4-k49f)...")
    data = fetch_socrata("a4b4-k49f",
        f"{DIST_FILTER_ORG} AND JOB_CAT='All'")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        results.append({
            "year": year,
            "fte_total": safe_float(row.get("fte_cnt")),
            "age_under_26": safe_float(row.get("und_26_cnt")),
            "age_26_32": safe_float(row.get("btwn_26_32_cnt")),
            "age_33_40": safe_float(row.get("btwn_33_40_cnt")),
            "age_41_48": safe_float(row.get("btwn_41_48_cnt")),
            "age_49_56": safe_float(row.get("btwn_49_56_cnt")),
            "age_57_64": safe_float(row.get("btwn_57_64_cnt")),
            "age_over_64": safe_float(row.get("ovr_64_cnt")),
        })
    results.sort(key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def fetch_teachers():
    """Teacher data."""
    print("Fetching teacher data (4684-cw3t)...")
    data = fetch_socrata("4684-cw3t",
        f"{DIST_FILTER} AND ORG_TYPE='District' AND SUBJECT='All Teachers'")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        ratio_str = row.get("stu_tchr_ratio", "")
        ratio = None
        if ratio_str and "to" in ratio_str:
            try:
                ratio = float(ratio_str.split("to")[0].strip())
            except:
                pass
        results.append({
            "year": year,
            "teacher_fte": safe_float(row.get("tchr_cnt")),
            "licensed_pct": safe_pct(row.get("tchr_lic_pct")),
            "student_teacher_ratio": ratio,
        })
    results.sort(key=lambda r: r["year"])
    seen = {}
    for r in results:
        seen[r["year"]] = r
    results = sorted(seen.values(), key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def fetch_class_size():
    """Class size data."""
    print("Fetching class size (35yv-uxv5)...")
    data = fetch_socrata("35yv-uxv5",
        f"{DIST_FILTER} AND ORG_TYPE='District' AND SUBJ='All'")
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        avg = safe_float(row.get("avg_clss_cnt"))
        if avg:
            results.append({
                "year": year,
                "avg_class_size": avg,
                "total_students": safe_int(row.get("tot_stu_cnt")),
                "total_classes": safe_int(row.get("tot_clss_cnt")),
            })
    results.sort(key=lambda r: r["year"])
    seen = {}
    for r in results:
        seen[r["year"]] = r
    results = sorted(seen.values(), key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def fetch_expenditures():
    """District expenditures by spending category."""
    print("Fetching expenditures (er3w-dyti)...")
    data = fetch_socrata("er3w-dyti", DIST_FILTER)
    results = {}
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        cat = row.get("spnd_cat", "")
        amount = safe_float(row.get("ttl_exp"))
        pp = safe_float(row.get("pp_ttl_exp"))
        if year not in results:
            results[year] = {"year": year, "categories": {}, "per_pupil": {}}
        if cat and amount:
            results[year]["categories"][cat] = amount
        if cat and pp:
            results[year]["per_pupil"][cat] = pp
    output = sorted(results.values(), key=lambda r: r["year"])
    print(f"  {len(output)} years")
    return output


def fetch_nss():
    """Chapter 70 / Net School Spending."""
    print("Fetching Chapter 70/NSS (5izv-jyrd)...")
    data = fetch_socrata("5izv-jyrd", DIST_FILTER)
    results = []
    for row in data:
        year = safe_int(row.get("sy"))
        if not year: continue
        results.append({
            "year": year,
            "foundation_budget": safe_float(row.get("fdn_bdgt_amt")),
            "required_nss": safe_float(row.get("req_nss_amt")),
            "actual_nss": safe_float(row.get("actl_nss_amt")),
        })
    results.sort(key=lambda r: r["year"])
    print(f"  {len(results)} years")
    return results


def build_summary(enrollment, graduation, staff, teachers):
    """Build summary from latest data."""
    latest_enr = enrollment[-1] if enrollment else {}
    latest_grad = graduation[-1] if graduation else {}
    latest_staff = staff[-1] if staff else {}
    latest_teach = teachers[-1] if teachers else {}

    teacher_fte = latest_teach.get("teacher_fte")
    ratio = latest_teach.get("student_teacher_ratio")
    total_students = latest_enr.get("total")

    return {
        "enrollment": total_students,
        "enrollment_year": latest_enr.get("year"),
        "graduation_rate": latest_grad.get("graduation_rate_4yr"),
        "graduation_year": latest_grad.get("year"),
        "staff_fte": latest_staff.get("fte_total"),
        "teacher_fte": teacher_fte,
        "student_teacher_ratio": ratio,
        "high_needs_pct": latest_enr.get("high_needs_pct"),
        "low_income_pct": latest_enr.get("low_income_pct"),
    }


def main():
    print("=" * 60)
    print("  Arlington, MA — School Data Fetcher")
    print("  Source: MA DESE via Socrata API")
    print("=" * 60)
    print()

    enrollment = fetch_enrollment()
    time.sleep(0.3)
    mcas = fetch_mcas()
    time.sleep(0.3)
    graduation = fetch_graduation()
    time.sleep(0.3)
    dropout = fetch_dropout()
    time.sleep(0.3)
    staff = fetch_staff()
    time.sleep(0.3)
    teachers = fetch_teachers()
    time.sleep(0.3)
    class_size = fetch_class_size()
    time.sleep(0.3)
    expenditures = fetch_expenditures()
    time.sleep(0.3)
    nss = fetch_nss()

    summary = build_summary(enrollment, graduation, staff, teachers)

    output = {
        "generated": datetime.now().isoformat(),
        "source": "Massachusetts Department of Elementary and Secondary Education (DESE)",
        "district": "Arlington",
        "district_code": "00100000",
        "enrollment": enrollment,
        "mcas": mcas,
        "graduation": graduation,
        "dropout": dropout,
        "staff": staff,
        "teachers": teachers,
        "class_size": class_size,
        "expenditures": expenditures,
        "nss": nss,
        "summary": summary,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
