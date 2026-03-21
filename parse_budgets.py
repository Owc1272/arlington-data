"""
Parse Arlington budget PDFs and extract financial data.
Searches for the "Overall General Fund Budget Summary" table in each PDF,
extracts revenue and expenditure line items.
Output: website/data/finances.json
"""

import pdfplumber
import json
import re
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path(__file__).parent / "input" / "budgets"
OUTPUT_PATH = Path(__file__).parent / "website" / "data" / "finances.json"


def parse_dollar(s):
    """Parse a dollar string like '$ 149,169,849' or '$ (3,200,418)' to int."""
    if not s:
        return None
    s = s.strip()
    s = s.replace("$", "").replace(",", "").replace(" ", "").strip()
    if s == "-" or s == "":
        return 0
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    try:
        val = int(float(s))
        return -val if negative else val
    except ValueError:
        return None


def find_budget_summary_text(pdf):
    """Find the page(s) with the Overall General Fund Budget Summary."""
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "Overall General Fund Budget Summary" in text and "TOTAL REVENUES" in text:
            return text
    # Try a looser match
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if "TOTAL REVENUES" in text and "Property Tax" in text:
            return text
    return None


def extract_fy_columns(text):
    """Extract the fiscal year column headers from the summary table.
    Returns list of (year, column_type) tuples like [(2023, 'Actual'), (2024, 'Budget')]."""
    # Look for patterns like "FY2023 FY2024 FY2025 FY2026"
    fy_pattern = re.findall(r'FY\s*(\d{2,4})', text[:500])
    years = []
    for fy in fy_pattern:
        y = int(fy)
        if y < 100:
            y += 2000
        if 2000 <= y <= 2030 and y not in years:
            years.append(y)
    return years[:4]  # Usually 4 columns


def clean_budget_line(line):
    """Fix common PDF extraction artifacts like '$ 1 11,926,606' -> '$ 111,926,606'."""
    # Fix pattern where a digit gets separated: '$ 1 11,926' or '$ 5 ,000,000' or '$ ( 3,200'
    # Pattern: $ followed by 1-2 digits, then space, then more digits/commas
    line = re.sub(r'\$\s*(\d{1,2})\s+([\d,])', lambda m: '$ ' + m.group(1) + m.group(2), line)
    # Fix '$ ( 3,200,418)' -> '$ (3,200,418)'
    line = re.sub(r'\$\s*\(\s+', '$ (', line)
    return line


def extract_line_values(text, line_label, num_values=4):
    """Extract dollar values from a specific line in the budget summary.
    Returns list of parsed dollar amounts."""
    lines = text.split("\n")
    for line in lines:
        if line_label.lower() in line.lower():
            line = clean_budget_line(line)
            # Find all dollar amounts on this line
            amounts = re.findall(r'\$\s*[\(\-]?[\d,]+(?:\.\d+)?[\)]?', line)
            if not amounts:
                # Try without $ sign — just numbers after the label
                remainder = line.split(line_label, 1)[-1] if line_label in line else line
                amounts = re.findall(r'[\(\-]?[\d,]{3,}[\)]?', remainder)
            parsed = [parse_dollar(a) for a in amounts[:num_values]]
            return parsed
    return []


def parse_budget_pdf(filepath):
    """Parse a single budget PDF and return extracted data."""
    try:
        pdf = pdfplumber.open(filepath)
    except Exception as e:
        print(f"  Cannot open: {e}")
        return None

    text = find_budget_summary_text(pdf)
    if not text:
        # Try combining a few pages
        for i, page in enumerate(pdf.pages):
            t = page.extract_text() or ""
            if "Overall General Fund" in t or "TOTAL REVENUES" in t:
                text = t
                # Check next page too
                if i + 1 < len(pdf.pages):
                    text += "\n" + (pdf.pages[i + 1].extract_text() or "")
                break

    pdf.close()

    if not text:
        print(f"  No budget summary found")
        return None

    years = extract_fy_columns(text)
    if not years:
        print(f"  No FY columns found")
        return None

    print(f"  FY columns: {years}")

    # Revenue lines
    revenue_labels = {
        "property_tax": "Property Tax",
        "local_receipts": "Local Receipts",
        "state_aid": "State Aid",
        "free_cash": "Free Cash",
        "other_funds": "Other Funds",
        "total_revenue": "TOTAL REVENUES",
    }

    # Expenditure lines
    expenditure_labels = {
        "municipal_departments": "Municipal Departments Appropriations",
        "municipal_net": "Municipal Departments (Taxation",
        "school_department": "School Department",
        "minuteman_school": "Minuteman School",
        "healthcare_pensions": "Non-Departmental",
        "capital_debt": "Capital",
        "total_expenditures": "TOTAL EXPENDITURES",
        "non_appropriated": "Non-Appropriated",
    }

    results = {}
    for year in years:
        results[year] = {"revenue": {}, "expenditures": {}}

    col_count = len(years)

    for key, label in revenue_labels.items():
        values = extract_line_values(text, label, col_count)
        for i, year in enumerate(years):
            if i < len(values) and values[i] is not None:
                results[year]["revenue"][key] = values[i]

    for key, label in expenditure_labels.items():
        values = extract_line_values(text, label, col_count)
        for i, year in enumerate(years):
            if i < len(values) and values[i] is not None:
                results[year]["expenditures"][key] = values[i]

    return results


def get_fy_from_filename(filename):
    """Extract fiscal year from filename."""
    match = re.search(r'(?:FY|fy)\s*(\d{2,4})', filename)
    if match:
        y = int(match.group(1))
        if y < 100:
            y += 2000
        return y
    return None


def main():
    print("=" * 60)
    print("  Arlington Budget PDF Parser")
    print("=" * 60)
    print()

    all_data = {}  # year -> {revenue: {}, expenditures: {}}

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files\n")

    for filepath in pdf_files:
        fy = get_fy_from_filename(filepath.name)
        print(f"{filepath.name} (FY{fy}):")

        result = parse_budget_pdf(filepath)
        if result:
            for year, data in result.items():
                new_rev = data.get("revenue", {}).get("total_revenue")
                old_rev = all_data.get(year, {}).get("revenue", {}).get("total_revenue") if year in all_data else None
                # Prefer data that looks reasonable (>$50M for Arlington)
                use_new = False
                if year not in all_data:
                    use_new = True
                elif old_rev and old_rev < 50_000_000 and new_rev and new_rev > 50_000_000:
                    use_new = True  # Old data was bad, new is better
                elif year == fy and new_rev and new_rev > 50_000_000:
                    use_new = True  # Primary year with good data
                if use_new:
                    all_data[year] = data
                    rev_total = data["revenue"].get("total_revenue", "?")
                    exp_total = data["expenditures"].get("total_expenditures", "?")
                    if year == fy:
                        if isinstance(rev_total, int) and isinstance(exp_total, int):
                            print(f"    FY{year} (primary): Rev=${rev_total:,} Exp=${exp_total:,}")
                        else:
                            print(f"    FY{year}: partial data")
        print()

    # Sort by year
    years_sorted = sorted(all_data.keys())
    output_years = []
    for year in years_sorted:
        d = all_data[year]
        entry = {
            "fiscal_year": year,
            "revenue": d.get("revenue", {}),
            "expenditures": d.get("expenditures", {}),
        }
        output_years.append(entry)

    output = {
        "generated": datetime.now().isoformat(),
        "source": "Arlington Town Manager Annual Budget & Financial Plan",
        "years": output_years,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nOutput: {OUTPUT_PATH}")
    print(f"Years with data: {len(output_years)}")
    for entry in output_years:
        fy = entry["fiscal_year"]
        rev = entry["revenue"].get("total_revenue", "?")
        exp = entry["expenditures"].get("total_expenditures", "?")
        rev_str = f"${rev:,.0f}" if isinstance(rev, (int, float)) else str(rev)
        exp_str = f"${exp:,.0f}" if isinstance(exp, (int, float)) else str(exp)
        print(f"  FY{fy}: Revenue={rev_str}  Expenditures={exp_str}")


if __name__ == "__main__":
    main()
