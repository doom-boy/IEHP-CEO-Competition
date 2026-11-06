# IEHP automated master data pipeline — setup

1. Copy `run_master_pipeline.py`, `iehp_master_core.py` and `requirements-automation.txt` to the **root** of your GitHub repository. Put `.github/workflows/iehp-master-analysis.yml` in that exact relative path.
2. Your Source E PART 1 and PART 2 CSV files need to exist anywhere in the repo, **either directly or inside ZIP archives**. They are detected by filename. Avoid committing patient-level identifiable health data. Do not use GitHub for private medical records.
3. For combined access rankings, supply **Source A September/August 2026 CSV** and **Source H ZIP-COUNTY crosswalk** at the paths in `iehp_master_core.py`. The script does NOT auto-download them. Other optional source data also follow the paths declared in that core script.
4. Push changes to GitHub. Go to **Actions > IEHP Master Data Pipeline > Run workflow** for a manual run; future matching data/code updates trigger the workflow automatically. It also reruns weekly using the currently committed sources (not refreshed online datasets).
5. Open the finished run > **Artifacts > IEHP-dashboard-tables**. Its `00_SOURCE_READINESS_AND_LIMITATIONS.csv` lists what is ready and missing. `06_FINAL_ZIP_access_by_service.csv` is created **only if A and H are available**.

### Local test

```bash
python -m pip install -r requirements-automation.txt
python run_master_pipeline.py --repo .
# Stronger check requiring patient ZIP analysis:
python run_master_pipeline.py --repo . --require-access
```

### What is (and is not) automated

- **Automated:** Load Source E both parts, clean/deduplicate, categorize, compute E supply, optional IEHP overlap, optional Source A/H ZIP demand and FFS providers per 1,000, optional dental, demographics, D enrollment, finance **scenario CSV import**, write CSVs, and emit a readiness report.
- **Not automatic:** Downloading new official CA data, extracting IEHP PDF directory data from PDFs, executing your independent A/B/financial Jupyter notebooks, full dental cleaning for arbitrary formats, validating every provider's availability, calculating actual switching-member counts, or saving notebook *output previews* back to GitHub.
- `IEHP_MASTER_CORE.py` uses candidate specialty labels, not a clinical taxonomy. Review it before claiming specialty-level shortages.
- Source H uses residential ratio to allocate all Medi-Cal members across counties; ZIP ratios are estimates, not individual patients.
- The generated results live in GitHub Actions artifacts, **not committed back to the repo**. To make GitHub itself display tables/previews, add a separate approval-controlled commit or pages step.
- Weekly schedule reprocesses existing files; it **does not retrieve new source data**.

### Sources used

Student Guide *Access to Care*: A (ZIP), B (age/language), C (fact sheet), D (plan enrollment), E (FFS), F (dental), G (shortage), H (ZIP county); separate user-provided IEHP directory CSV; financial workbook/model outputs.

CEO Challenge case: Assess IEHP operational and financial effects, where members may lose care, actions, and metrics. Numbers for transitions and financial scenarios are estimates where labeled, not confirmed real-world figures.
