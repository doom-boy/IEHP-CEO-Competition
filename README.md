# IEHP-CEO-Competition

Analysis for the IEHP CEO Business Challenge: how IEHP should respond to the January 1, 2027 move of UIS Medi-Cal members from managed care to FFS. The lead goal is a smooth transition for members. Money is a supporting view.

## Notebooks

| Notebook | Purpose |
|---|---|
| `source_b_demographic_analysis.ipynb` | County demographics (age, language, race, plan). Regional context only. Unchanged in this update. |
| `IEHP_Source_A_MediCal_ZIP_Analysis.ipynb` | Medi-Cal members by ZIP. Unchanged in this update. |
| `source_e_analysis.ipynb` | FFS provider list, plus the new ZIP-level primary-care access analysis (sections 8 to 11). |
| `financial_impact_analysis.ipynb` | Rebuild of the workbook model, plus the new IEHP-estimate case (section 12b). |
| `final_analysis_and_recommendations.ipynb` | Combines the saved outputs of the notebooks above into one story and maps the findings to the three recommendations. Run the others first. |

Outputs are written to `analysis_outputs/access/` (new) and `analysis_outputs/financial/`.

## Update log: what changed and why

### 1. `source_e_analysis.ipynb`: finished the access analysis (new sections 8 to 11)
The notebook stopped at a provider inventory. It now:
- Builds one ZIP table: Source A demand (Sep 2026) + Source E supply (Oct 26, 2026 list) + Source H region (Jun 2026).
- Defines primary care as individual physicians in Family, General, Internal Medicine, Pediatrics or Geriatrics, counted once per ZIP. Physician groups are left out so members are not double counted.
- Spreads IEHP's 119,600 estimate across ZIPs in proportion to Medi-Cal members (an assumption) and ranks ZIPs by estimated transitioning members per listed PCP. ZIPs with no listed PCP rank first.
- Adds a provider-conversion what-if and a high-confidence gap list.

**Why:** Recommendation 2 (targeted provider outreach) needs a ranked list of places, not an inventory.

### 2. `financial_impact_analysis.ipynb`: added IEHP's estimate as the base case (new section 12b)
After the notebook was built, the Q&A email gave IEHP's own estimate of 119,600 transitioning members. That is 8.8% of Source D enrollment, below the guide's 10% low case. The new section runs it through the same model and adds the DHCS county UIS count (172,459, June 2026) as context. The guide's 10% to 18% cases are kept as sensitivity. Nothing earlier in the notebook was changed.

**Why:** the team should lead with IEHP's number and show the guide's cases as a range, not the reverse.

### 3. Number reconciliation (`source_e_analysis.ipynb`, section 9)
One table lists each count, its source, its date and what it should be used for, so one source is cited per claim. Saved as `analysis_outputs/access/number_reconciliation.csv`.

**Why:** the files give several different totals (Source A, B, D, fact sheet, Q&A) and judges check traceability.

### 4. Ranking sensitivity (`source_e_analysis.ipynb`, section 8a)
Re-ranks ZIPs under 4 provider definitions and 2 ways of allocating the estimate (8 combinations), and shows scale cases (10%, 14.3%, 18%, 119,600).

**Why:** to see whether the top ZIPs are an artifact of our assumptions.

### 5. Monitoring baseline (`source_e_analysis.ipynb`, section 10)
A table of before-January values for Recommendation 3, with proposed owner roles and checks. Metrics that need IEHP data say "IEHP to set". Saved as `analysis_outputs/access/monitoring_baseline.csv`.

**Why:** the case asks what to monitor before, during and after the transition.

## Main results

| Item | Result |
|---|---|
| ZIPs ranked (at least 1,000 Medi-Cal members) | 126 |
| Ranked ZIPs with no listed FFS core PCP | 34 |
| Top 3 by demand with no listed PCP | Desert Hot Springs 92240, Moreno Valley 92551, Eastvale 92880 |
| ZIPs with no listed provider under the broadest definition | 15 (largest: Winchester 92596, San Jacinto 92582, Lake Elsinore 92532) |
| ZIPs in the top 10 under every definition tested | 3 (Lake Elsinore, San Jacinto, Winchester) |
| Does the allocation method change the ranking? | No. The provider definition does (top-10 overlap falls to 3 or 4 of 10) |
| IEHP estimate as share of Source D | 8.8% (below the guide's 10% low case) |
| Net effect on IEHP at 119,600, base mix | about -$29M a year (about 1.0x the budgeted surplus) |
| Fixed cost per remaining member, no action | +9.4% (yellow on the sample stoplight) |
| Net range across patient mixes at 119,600 | -$86M to +$56M |

The earlier statement that every scenario lands in red still holds for the guide's 10% to 18% cases. At IEHP's 119,600 the sample stoplight shows yellow.

## Limits to state in the video
- Source E lists FFS-enrolled providers and excludes managed-care providers. A ZIP with no listing may still have local primary care, and enrollment is not new-patient acceptance.
- Source A is all Medi-Cal, preliminary, and 20 ZIPs have suppressed counts that are not ranked.
- No file shows where UIS members live. The ZIP allocation of 119,600 is an assumption.
- The 172,459 county UIS count and the 119,600 IEHP estimate come from a Q&A email. The DHCS county file and the CHCF brief it mentions are not in this repository.
- The financial model uses the workbook's mix and cost assumptions, not IEHP's. Stoplight levels, benchmarks and owner roles are team proposals.
- Source B's FFS count for the two counties is 99,206 in Sep 2026 but 66,869 in Oct 2026 (preliminary). We did not confirm why, so use one month consistently (Sep) and state it.

## Running
Start Jupyter or VS Code with this folder as the working directory. Notebooks find the data by searching upward from the current folder. `openpyxl` is required (reads the crosswalk and workbook); it was installed in `.venv` for this update.