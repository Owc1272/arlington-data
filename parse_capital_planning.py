"""
Parse Arlington Capital Planning Committee Report PDFs.
Extracts:
  - Capital budget vote line items (project, amount, department, funding type)
  - 5-year plan summary (debt service, cash, new debt by fiscal year)
  - 5% rule table (net non-exempt plan vs pro forma budget)
  - Department detail tables (project-level 5-year plans)
Output: website/data/capital_planning.json
"""

import pdfplumber
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import json
import re
import io
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path(__file__).parent / "input" / "Capital Planning"
OUTPUT_PATH = Path(__file__).parent / "website" / "data" / "capital_planning.json"


def ocr_pdf(filepath):
    """OCR a scanned PDF using PyMuPDF + pytesseract. Returns full text."""
    doc = fitz.open(filepath)
    full_text = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img)
        full_text.append(text)
        if i % 5 == 0:
            print(f"    OCR page {i+1}/{len(doc)}...")
    doc.close()
    return "\n\n".join(full_text)


def parse_dollar(s):
    """Parse a dollar string like '$52,500' or '$(3,200)' to int."""
    if not s:
        return None
    s = str(s).strip()
    s = s.replace("$", "").replace(",", "").replace(" ", "").replace("\u2013", "-").strip()
    if s in ("-", "", "—", "–"):
        return 0
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    elif s.startswith("-"):
        negative = True
        s = s[1:]
    # Remove trailing % if present
    s = s.rstrip("%")
    try:
        val = int(float(s))
        return -val if negative else val
    except ValueError:
        return None


def get_report_year(filename, pdf=None):
    """Extract the report year from the filename, or from title page text."""
    name = filename.lower()
    # Try patterns like "2025", "2024", "2010", etc.
    matches = re.findall(r'(\d{4})', name)
    for m in matches:
        y = int(m)
        if 2000 <= y <= 2030:
            return y
    # Special case: "FY2226" in the 2021 report
    if "2021" in name or "fy2226" in name:
        return 2021
    # Fall back to reading the title page of the PDF
    if pdf:
        for page in pdf.pages[:3]:
            text = page.extract_text() or ""
            # Look for "April 2019" or "May 2018" etc.
            date_match = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', text)
            if date_match:
                y = int(date_match.group(1))
                if 2000 <= y <= 2030:
                    return y
            # Look for FY patterns
            fy_match = re.search(r'FY\s*(\d{4})', text)
            if fy_match:
                y = int(fy_match.group(1))
                if 2000 <= y <= 2030:
                    return y
    return None


def extract_vote_items(pdf):
    """Extract capital budget vote line items from tables.
    Returns list of dicts with: item, amount, project, department, section."""
    items = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 2:
                continue
            # Check if this is a vote item table (Item/Amount/Project/Department)
            header = [str(c or "").strip().lower() for c in table[0]]
            header_str = " ".join(header)

            # Detect vote item tables
            is_vote_table = False
            section = None

            if "item" in header and "amount" in header and ("project" in header or "department" in header):
                is_vote_table = True
            elif "item" in header and "amount to be transferred" in header_str:
                is_vote_table = True
                section = "reappropriations"
            elif "item" in header and "amount to be paid" in header_str:
                is_vote_table = True
                section = "reappropriations"

            if not is_vote_table:
                continue

            for row in table[1:]:
                if not row or len(row) < 3:
                    continue
                cells = [str(c or "").strip() for c in row]

                # Skip total rows and empty rows
                if not cells[0] or cells[0].lower() in ("", "total"):
                    continue
                if "total" in cells[-1].lower() and cells[0] == "":
                    continue

                item_num = cells[0]
                amount_str = cells[1]
                amount = parse_dollar(amount_str)

                if amount is None or amount == 0:
                    continue

                # Determine project and department based on column count
                project = ""
                department = ""
                if len(cells) >= 5:
                    project = cells[2]
                    department = cells[3]
                    if not section:
                        section = cells[2] if "from original" in header_str else None
                elif len(cells) >= 4:
                    project = cells[2]
                    department = cells[3]
                elif len(cells) >= 3:
                    project = cells[2]

                if project or department:
                    items.append({
                        "item": item_num,
                        "amount": amount,
                        "project": project,
                        "department": department,
                        "section": section,
                    })

    return items


def extract_five_year_plan(pdf):
    """Extract the 5-year plan summary table with debt service, cash, etc.
    Returns dict with fiscal years as keys."""
    plan = {}
    for page in pdf.pages:
        text = page.extract_text() or ""
        tables = page.extract_tables()

        for table in tables:
            if not table or len(table) < 3:
                continue

            # Look for the 5-year plan table with fiscal year columns
            # Check first few rows for fiscal year headers
            header_text = " ".join(str(c or "") for row in table[:3] for c in row)

            # Find fiscal year columns
            fy_matches = re.findall(r'FY?\s*(\d{4})', header_text)
            if not fy_matches:
                fy_matches = re.findall(r'\b(20\d{2})\b', header_text)

            if len(fy_matches) < 3:
                continue

            years = []
            for m in fy_matches:
                y = int(m)
                if 2000 <= y <= 2035 and y not in years:
                    years.append(y)
            if len(years) < 3:
                continue

            # Look for key rows: Prior Non-Exempt Debt, Cash, New Non-Exempt Debt,
            # Net Non-Exempt Plan, Pro Forma Budget
            key_labels = {
                "prior_debt": ["prior non-exempt debt", "prior debt service"],
                "cash": ["cash"],
                "new_debt": ["new non-exempt debt", "new debt service"],
                "total_non_exempt": ["total non-exempt", "net non-exempt plan"],
                "exempt_debt": ["exempt debt"],
                "adjustments": ["adjustments", "adjust"],
                "pro_forma": ["pro forma budget"],
                "plan_5pct": ["budget for plan at 5%", "5% budget"],
                "plan_pct": ["plan as % of revenues", "plan as %"],
            }

            for row in table:
                if not row:
                    continue
                row_text = " ".join(str(c or "") for c in row).lower()

                for key, labels in key_labels.items():
                    for label in labels:
                        if label in row_text:
                            # Extract dollar values from this row
                            values = []
                            for cell in row:
                                cell_str = str(cell or "").strip()
                                if not cell_str:
                                    continue
                                # Try to parse dollar values
                                dollar_matches = re.findall(r'\$?\s*[\(\-]?[\d,]+(?:\.\d+)?%?[\)]?', cell_str)
                                for dm in dollar_matches:
                                    val = parse_dollar(dm)
                                    if val is not None:
                                        values.append(val)

                            # Map values to years
                            if values:
                                for i, year in enumerate(years):
                                    if i < len(values):
                                        if year not in plan:
                                            plan[year] = {}
                                        plan[year][key] = values[i]
                            break
                    if key in (plan.get(years[0], {}) if years else {}):
                        break

    return plan


def extract_five_pct_table(pdf):
    """Extract the 5% rule table specifically."""
    result = {}
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 3:
                continue

            # Check for 5% table markers
            header_text = " ".join(str(c or "") for row in table[:3] for c in row).lower()
            if "net non-exempt" not in header_text and "pro forma" not in header_text:
                continue
            if "fiscal year" not in header_text and "fy" not in header_text:
                continue

            # Find year columns
            fy_matches = re.findall(r'FY?\s*(\d{4})', header_text, re.IGNORECASE)
            if not fy_matches:
                fy_matches = re.findall(r'\b(20\d{2})\b', header_text)

            years = []
            for m in fy_matches:
                y = int(m)
                if 2000 <= y <= 2035 and y not in years:
                    years.append(y)

            if len(years) < 3:
                continue

            for row in table:
                if not row:
                    continue
                row_str = " ".join(str(c or "") for c in row)
                row_lower = row_str.lower()

                entry_key = None
                if "net non-exempt" in row_lower:
                    entry_key = "net_non_exempt_plan"
                elif "pro forma" in row_lower:
                    entry_key = "pro_forma_budget"
                elif "budget for plan" in row_lower or "5%" in row_lower:
                    entry_key = "budget_at_5pct"
                elif "plan as %" in row_lower:
                    entry_key = "plan_pct_of_revenues"
                elif "variance" in row_lower:
                    entry_key = "variance"

                if entry_key:
                    values = []
                    for cell in row:
                        cell_str = str(cell or "").strip()
                        v = parse_dollar(cell_str)
                        if v is not None:
                            values.append(v)

                    for i, year in enumerate(years):
                        if i < len(values):
                            if year not in result:
                                result[year] = {}
                            result[year][entry_key] = values[i]

    return result


def extract_funding_sources(pdf):
    """Extract funding source breakdown (Cash, Bond, Other by department)."""
    sources = {}
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 2:
                continue
            header_text = " ".join(str(c or "") for c in table[0]).lower()
            if "department" in header_text and ("bond" in header_text or "cash" in header_text):
                for row in table[1:]:
                    if not row:
                        continue
                    dept = str(row[0] or "").strip()
                    if not dept or "total" in dept.lower():
                        continue
                    # Extract dollar values
                    amounts = []
                    for cell in row[1:]:
                        v = parse_dollar(str(cell or ""))
                        if v is not None:
                            amounts.append(v)
                    if dept and amounts:
                        sources[dept] = amounts
    return sources


def extract_dept_details(pdf):
    """Extract department-level project detail tables.
    Returns list of dicts: department, program, expenditure, amounts by year."""
    details = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = [str(c or "").strip().lower() for c in table[0]]
            header_str = " ".join(header)

            # Look for dept detail tables
            if "department" not in header_str:
                continue
            if "program" not in header_str and "expenditure" not in header_str:
                continue

            # Find fiscal year columns from header
            all_header_text = " ".join(str(c or "") for row in table[:3] for c in row)
            fy_matches = re.findall(r'\b(20\d{2})\b', all_header_text)
            years = []
            for m in fy_matches:
                y = int(m)
                if 2000 <= y <= 2035 and y not in years:
                    years.append(y)

            current_dept = ""
            current_program = ""

            for row in table[1:]:
                if not row or len(row) < 3:
                    continue
                cells = [str(c or "").strip() for c in row]

                # Skip header/total rows
                if cells[0].lower() in ("sum of amount", "sum of debtservicepmt", ""):
                    if cells[0] == "" and cells[1]:
                        pass  # continuation row
                    else:
                        continue

                dept = cells[0] if cells[0] else current_dept
                if dept and "total" not in dept.lower():
                    current_dept = dept

                if "total" in " ".join(cells).lower():
                    # This is a subtotal row — extract the total
                    total_val = None
                    for cell in reversed(cells):
                        v = parse_dollar(cell)
                        if v is not None and v > 0:
                            total_val = v
                            break
                    if total_val and current_dept:
                        details.append({
                            "department": current_dept,
                            "program": "",
                            "expenditure": "SUBTOTAL",
                            "grand_total": total_val,
                            "years": {},
                        })
                    continue

                # Parse program and expenditure
                program = ""
                expenditure = ""
                grand_total = None

                if len(cells) >= 4:
                    program = cells[1] if cells[1] else current_program
                    if program:
                        current_program = program
                    expenditure = cells[2]

                    # Try to get grand total from last column
                    grand_total = parse_dollar(cells[-1])

                    # Try to parse year amounts from the amounts column
                    year_amounts = {}
                    for ci, cell in enumerate(cells[3:-1] if len(cells) > 4 else cells[3:]):
                        # Some cells contain multiple years smashed together
                        dollar_vals = re.findall(r'\$?\s*[\d,]+', cell)
                        for vi, dv in enumerate(dollar_vals):
                            v = parse_dollar(dv)
                            if v is not None and v > 0 and vi < len(years):
                                year_amounts[years[vi]] = v

                if expenditure and expenditure != "EXPENDITURE":
                    # Handle multi-line expenditure cells
                    exp_lines = expenditure.split("\n")
                    for exp_line in exp_lines:
                        exp_line = exp_line.strip()
                        if not exp_line:
                            continue
                        details.append({
                            "department": current_dept,
                            "program": current_program,
                            "expenditure": exp_line,
                            "grand_total": grand_total,
                        })

    return details


def split_camelcase_dept(text):
    """Split concatenated CamelCase/ALL-CAPS department names.
    E.g., 'COMMUNITYSAFETY-FIRESERVICES' -> 'COMMUNITY SAFETY - FIRE SERVICES'"""
    # Insert space before each uppercase letter that follows a lowercase letter
    # or before a sequence of uppercase letters after another uppercase sequence
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    # Insert space between concatenated ALL-CAPS words like PUBLICWORKS -> PUBLIC WORKS
    result = re.sub(r'([A-Z]{2,})([A-Z][a-z])', r'\1 \2', result)
    return result


def extract_text_vote_items(pdf_or_text):
    """Extract vote items from text (for older reports where tables don't parse well).
    Accepts a pdfplumber PDF object or a string of text (for OCR'd PDFs).
    Looks for patterns like: 1. $25,000 Vehicle Replacement COMMUNITY SAFETY"""
    items = []

    if isinstance(pdf_or_text, str):
        all_text = pdf_or_text
    else:
        all_text = "\n".join(page.extract_text() or "" for page in pdf_or_text.pages)

    # Fix OCR artifacts: "$5 ,000" -> "$5,000", "$1 15,000" -> "$115,000"
    all_text = re.sub(r'\$\s*(\d{1,2})\s+,', r'$\1,', all_text)
    all_text = re.sub(r'\$\s*(\d{1,2})\s+(\d)', r'$\1\2', all_text)

    for line in all_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        # Pattern: "1. $25,000 Project Name DEPARTMENT NAME"
        # or "1. $ 5,500 ProjectName DEPARTMENTNAME" (concatenated text)
        match = re.match(
            r'(\d+)\.\s+\$\s*([\d,]+)\s+(.+)',
            line
        )
        if not match:
            continue

        item_num = match.group(1)
        amount_str = match.group(2).replace(" ", "")
        amount = parse_dollar("$" + amount_str)
        remainder = match.group(3).strip()

        if not amount or amount <= 0:
            continue

        # Skip summary/subtotal lines
        remainder_lower = remainder.lower()
        skip_keywords = [
            "sub-total", "subtotal", "sub total", "grand total",
            "total general fund", "total enterprise", "total capital",
            "prior debt", "priordebt", "priordebts", "acquisitionssub",
            "reductionssub", "calculation", "netappropriation",
            "debt service", "debtservice", "newdebtservice",
            "less:", "lessmwra", "lesstransfer", "adjustment",
            "acquisitions sub",
        ]
        if any(kw in remainder_lower for kw in skip_keywords):
            continue

        # Split remainder into project and department
        # Try two strategies:

        # Strategy 1: Normal spaced text — look for ALL-CAPS department at end
        dept_match = re.search(
            r'\s+((?:[A-Z][A-Z/&\-]+(?:\s+|$)){2,}.*)$',
            remainder
        )
        if dept_match:
            department = dept_match.group(1).strip()
            department = department.replace("\u2010", "-").replace("\u2011", "-").replace("\u2012", "-").replace("\u2013", "-").replace("\u2014", "-")
            project = remainder[:dept_match.start()].strip()
            project = project.rstrip(" -\u2013\u2014")
        else:
            # Strategy 2: Concatenated text like "PhotocopierLease BOARDOFASSESSORS"
            # or "VehicleReplacementProgram COMMUNITYSAFETY-POLICESERVICES"
            space_match = re.search(r'\s+([A-Z][A-Z/&\-\']+(?:[A-Z/&\-\']+)*)$', remainder)
            if space_match:
                raw_dept = space_match.group(1)
                department = split_camelcase_dept(raw_dept)
                project = split_camelcase_dept(remainder[:space_match.start()].strip())
            else:
                project = split_camelcase_dept(remainder)
                department = ""

        if project:
            items.append({
                "item": item_num,
                "amount": amount,
                "project": project,
                "department": department,
                "section": None,
            })

    return items


def parse_capital_planning_pdf(filepath):
    """Parse a single capital planning PDF and return all extracted data."""
    try:
        pdf = pdfplumber.open(filepath)
    except Exception as e:
        print(f"  Cannot open {filepath.name}: {e}")
        return None

    # Check if PDF needs OCR (scanned/image PDF)
    total_chars = sum(len(page.extract_text() or "") for page in pdf.pages[:5])
    ocr_text = None
    if total_chars < 100:
        print(f"  Scanned PDF detected, running OCR...")
        ocr_text = ocr_pdf(filepath)
        print(f"  OCR extracted {len(ocr_text)} chars")

    report_year = get_report_year(filepath.name, pdf)
    print(f"\n{'='*60}")
    print(f"  {filepath.name}")
    print(f"  Report Year: {report_year}")
    print(f"{'='*60}")

    num_pages = len(pdf.pages)
    print(f"  Pages: {num_pages}")

    # Extract all data types
    vote_items = extract_vote_items(pdf)
    if not vote_items:
        if ocr_text:
            vote_items = extract_text_vote_items(ocr_text)
        else:
            vote_items = extract_text_vote_items(pdf)
    print(f"  Vote items: {len(vote_items)}")

    five_year = extract_five_year_plan(pdf)
    print(f"  5-year plan years: {sorted(five_year.keys()) if five_year else 'none'}")

    five_pct = extract_five_pct_table(pdf)
    print(f"  5% table years: {sorted(five_pct.keys()) if five_pct else 'none'}")

    dept_details = extract_dept_details(pdf)
    print(f"  Department detail items: {len(dept_details)}")

    # Compute summary totals from vote items
    total_amount = sum(item["amount"] for item in vote_items if item["amount"])
    dept_totals = {}
    for item in vote_items:
        dept = item.get("department", "Unknown")
        if dept:
            dept_totals[dept] = dept_totals.get(dept, 0) + (item["amount"] or 0)

    if vote_items:
        print(f"  Total vote amount: ${total_amount:,.0f}")
        print(f"  Departments: {len(dept_totals)}")
        for dept, total in sorted(dept_totals.items(), key=lambda x: -x[1])[:5]:
            print(f"    {dept}: ${total:,.0f}")

    # Merge 5% table into five_year plan
    for year, data in five_pct.items():
        if year not in five_year:
            five_year[year] = {}
        five_year[year].update(data)

    pdf.close()

    return {
        "report_year": report_year,
        "filename": filepath.name,
        "pages": num_pages,
        "vote_items": vote_items,
        "total_vote_amount": total_amount,
        "dept_totals": dept_totals,
        "five_year_plan": {str(k): v for k, v in sorted(five_year.items())},
        "dept_details": dept_details,
    }


def main():
    print("=" * 60)
    print("  Arlington Capital Planning Report Parser")
    print("=" * 60)

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    print(f"\nFound {len(pdf_files)} PDF files in {INPUT_DIR}\n")

    all_reports = []
    for filepath in pdf_files:
        result = parse_capital_planning_pdf(filepath)
        if result:
            all_reports.append(result)

    # Sort by report year
    all_reports.sort(key=lambda r: r.get("report_year") or 0)

    # Build summary
    summary = {
        "generated": datetime.now().isoformat(),
        "source": "Arlington Capital Planning Committee Reports to Town Meeting",
        "num_reports": len(all_reports),
        "year_range": f"{all_reports[0]['report_year']}-{all_reports[-1]['report_year']}" if all_reports else "",
        "reports": all_reports,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"Reports parsed: {len(all_reports)}")
    print(f"Output: {OUTPUT_PATH}")
    print()
    for r in all_reports:
        fy = r["report_year"]
        n_items = len(r["vote_items"])
        total = r["total_vote_amount"]
        n_5yr = len(r["five_year_plan"])
        n_dept = len(r["dept_details"])
        total_str = f"${total:,.0f}" if total else "$0"
        print(f"  {fy}: {n_items} vote items ({total_str}), "
              f"{n_5yr} plan years, {n_dept} dept details")


if __name__ == "__main__":
    main()
