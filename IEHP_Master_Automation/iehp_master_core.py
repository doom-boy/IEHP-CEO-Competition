# Automated adaptation of previously supplied Source E integration analysis.
# Source datasets are required for corresponding modules; missing sources are logged, not fabricated.
# IEHP FINAL — paste this WHOLE cell at the bottom of source_e_analysis(1).ipynb
# Runs Source E standalone; adds A+H, B, D, F, IEHP directory (I) and finance if present.
# Requirement: run Source E's original loading cells first so `providers_df` exists.
# In Jupyter/Colab, install if needed: %pip install pandas openpyxl ipywidgets

from pathlib import Path
import re
import pandas as pd


# ------------ SETTINGS: edit only if auto-detection misses your uploads ------------
ROOT = Path(globals().get('repo_root', Path.cwd())).resolve()
OUT = ROOT / 'analysis_outputs' / 'integrated_iehp_dashboard'
OUT.mkdir(parents=True, exist_ok=True)
MONTHS = ('2026-09', '2026-08')  # Student Guide, Source A
COUNTY = {'06065': 'Riverside', '06071': 'San Bernardino'}
# Optional: specify full local paths here; None = look in the known repo locations.
OVERRIDE = {'A': None, 'H': None, 'F': None, 'I': None,
            'B_age': None, 'B_language': None, 'D': None, 'FIN': None}

if 'providers_df' not in globals():
    raise RuntimeError('Run the existing Source E loading cells first (creates providers_df).')

report = []
def note(source, status, details):
    report.append({'source': source, 'status': status, 'details': details})
    print(f'{source}: {status} — {details}')

def find_file(kind, candidates):
    if OVERRIDE.get(kind):
        p = Path(OVERRIDE[kind]).expanduser()
        if not p.is_file(): raise FileNotFoundError(f'{kind}: {p}')
        return p
    for candidate in candidates:
        p = ROOT / candidate
        if p.is_file(): return p
    return None

def read_csv(path, **kwargs):
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False,
                           encoding='utf-8-sig', low_memory=False, **kwargs)
    except UnicodeDecodeError:
        return pd.read_csv(path, dtype=str, keep_default_na=False,
                           encoding='cp1252', low_memory=False, **kwargs)

def zip5(x):
    return x.fillna('').astype(str).str.extract(r'(\d{5})', expand=False).fillna('')

def clean_count(x):
    return pd.to_numeric(x.astype(str).str.replace(',', '', regex=False)
                         .replace({'': None, '.': None, '*': None, '-': None,
                                   'NA': None, 'N/A': None}), errors='coerce')

def npi_valid(s):
    # NPI check: Luhn on '80840' + 10-digit identifier.
    if not re.fullmatch(r'\d{10}', str(s)): return False
    digits = [int(x) for x in '80840' + str(s)]
    total = 0
    for pos, digit in enumerate(reversed(digits)):
        if pos % 2: digit *= 2; digit = digit // 10 + digit % 10
        total += digit
    return total % 10 == 0

# ------------ E: FFS ENROLLED PROVIDERS, TYPES, ZIP, SPECIALTY ------------
e = providers_df.copy()
required = ['NPI','State','County','CountyName','ZIP','FI_Provider_Type',
            'FI_Provider_Specialty','Legal_Name','Address','City']
absent = sorted(set(required)-set(e.columns))
if absent: raise ValueError(f'Source E is missing columns: {absent}')
e[required] = e[required].fillna('').astype(str)
e['npi'] = e.NPI.str.strip()
e['npi_ok'] = e.npi.map(npi_valid)
e['county_a'] = e.County.str.upper().str.replace(' COUNTY','',regex=False).str.strip()
e['county_b'] = e.CountyName.str.upper().str.replace(' COUNTY','',regex=False).str.strip()
valid = ['RIVERSIDE','SAN BERNARDINO']
e['county_disagreement'] = (e.county_a.isin(valid) & e.county_b.isin(valid)
                             & e.county_a.ne(e.county_b))
# Use the official CountyName consistently with the prior audited provider dataset.
# Keep FIPS/County disagreements for QA, but do not silently replace CountyName.
e['county'] = e.county_b.str.title()
e['zip'] = e.ZIP.str.strip()
e['type'] = e.FI_Provider_Type.str.strip()
e['specialty'] = e.FI_Provider_Specialty.str.strip()
e['name'] = e.Legal_Name.str.strip()
e['street'] = e.Address.str.strip()
e['city'] = e.City.str.strip()
e_all_npi = set(e.loc[e.npi_ok, 'npi'])  # statewide, BEFORE county filter
is_local = (e.State.str.strip().str.upper().eq('CA') & e.county.isin(COUNTY.values()))
e = e.loc[is_local].copy()
e.loc[~e.npi_ok | e.zip.eq(''),
      ['npi','zip','county','name','type','specialty','street','city','npi_ok']].to_csv(
      OUT/'E_excluded_or_unmappable_review.csv', index=False)
e = e.loc[e.npi_ok & e.zip.str.fullmatch(r'\d{5}')].copy()

# Broad categories are ANALYTICAL LABELS. The source's exact specialty stays in the file.
def service_group(row):
    t = row['type'].lower(); s = row['specialty'].lower()
    if any(k in t+' '+s for k in ['psychiatr', 'psycholog', 'mental', 'behavior',
                                  'marriage and family', 'social worker', 'counselor']):
        return 'Mental health'
    if any(k in t+' '+s for k in ['dental', 'dentist', 'orthodont']): return 'Dental (E; check F)'
    if any(k in s for k in ['family practice', 'general practice', 'internal medicine', 'pediatrics']):
        return 'Primary care (candidate)'
    if 'physician' in t or 'surgeon' in t:
        return 'Specialist/physician (candidate)'
    return 'Other / unclassified'
e['service_group'] = e.apply(service_group, axis=1)
e['site_key'] = (e.npi+'|'+e.county+'|'+e.zip+'|'+
                 e.street.str.upper().str.replace(r'\s+',' ',regex=True))
# Retain multiple specialties for the same NPI and site.
e = e.drop_duplicates(['site_key','type','specialty'])
E_COLUMNS = ['npi','name','type','specialty','service_group','county','city',
             'zip','street','site_key']
e[E_COLUMNS].to_csv(OUT/'01_E_FFS_provider_locations_specialties.csv',index=False)
by_service = (e.groupby(['county','zip','service_group'],as_index=False)
                .agg(ffs_providers=('npi','nunique'),ffs_sites=('site_key','nunique')))
by_service.to_csv(OUT/'02_E_FFS_supply_by_ZIP_service.csv',index=False)
by_zip = (e.groupby(['county','zip'],as_index=False)
            .agg(ffs_providers_all=('npi','nunique'),ffs_sites_all=('site_key','nunique')))
note('E','READY',f'{e.npi.nunique():,} unique local NPIs; provider supply only, not appointment capacity')

# ------------ OPTIONAL I: IEHP PDF DIRECTORY *PRE-EXTRACTED CSV* ------------
i_file = find_file('I',[
    'IEHP_FINAL_4_CSVs/01_IEHP_providers_Riverside_San_Bernardino.csv',
    'IEHP_FINAL_VERIFIED_COLLECTION/01_IEHP_provider_sites_master.csv',
    'data/IEHP_provider_directory_extracted.csv'])
if i_file:
    i = read_csv(i_file)
    col = 'npi' if 'npi' in i else 'npi_as_printed' if 'npi_as_printed' in i else None
    if col is None: raise ValueError(f'IEHP CSV lacks NPI column: {i_file}')
    i['npi'] = i[col].astype(str).str.strip()
    i = i[i.npi.map(npi_valid)].copy()
    i['in_ffs_statewide'] = i.npi.isin(e_all_npi)
    local_npis = set(e.npi)
    i['in_ffs_local'] = i.npi.isin(local_npis)
    i['match_class'] = 'IEHP; no FFS NPI match statewide'
    i.loc[i.in_ffs_statewide,'match_class'] = 'IEHP and FFS statewide (location not verified)'
    i.loc[i.in_ffs_local,'match_class'] = 'IEHP and FFS in two-county roster'
    i.to_csv(OUT/'03_I_IEHP_provider_cross_reference.csv',index=False)
    i_unique = i.drop_duplicates('npi')
    iehp_npis = set(i_unique.npi)
    overlap = iehp_npis & local_npis
    ffs_only = local_npis - iehp_npis
    iehp_no_statewide = iehp_npis - e_all_npi
    pd.DataFrame([
        ('IEHP directory NPIs',len(iehp_npis)),
        ('FFS local NPIs',len(local_npis)),
        ('Both IEHP and local FFS',len(overlap)),
        ('FFS local with no supplied IEHP PDF match',len(ffs_only)),
        ('IEHP with no local FFS match',len(iehp_npis-overlap)),
        ('IEHP with no statewide FFS match',len(iehp_no_statewide)),
    ],columns=['metric','unique_NPIs']).to_csv(OUT/'04_I_E_overlap_summary.csv',index=False)
    note('I','READY',f'{len(overlap):,} NPIs overlap with local FFS (not confirmed same-clinic acceptance)')
else:
    note('I','MISSING','Upload pre-extracted IEHP directory CSV (not the PDF) for provider overlap')

# ------------ OPTIONAL F: DENTAL (NOT FULLY COVERED BY E) ------------
f_file=find_file('F',['data/provider-side/F-dental-ffs/dental_ffs.csv',
                     'data/F_dental.csv','F_dental.csv'])
f_loaded = False
if f_file:
    f=read_csv(f_file); f.columns=f.columns.str.strip()
    def col_of(cols):
        return next((c for c in cols if c in f.columns),None)
    fn=col_of(['NPI','npi','Provider NPI']); fz=col_of(['ZIP','Zip','Zip Code','ZIP Code'])
    fc=col_of(['County','CountyName','county']); fs=col_of(['State','state'])
    if fn and fz and fc:
        f['npi']=f[fn].astype(str).str.strip(); f['zip']=zip5(f[fz])
        f['county']=f[fc].str.upper().str.replace(' COUNTY','',regex=False).str.title()
        f=f[f.npi.map(npi_valid) & f.county.isin(COUNTY.values()) & f.zip.ne('')]
        if fs: f=f[f[fs].astype(str).str.upper().eq('CA')]
        dental=(f.groupby(['county','zip'],as_index=False).npi.nunique()
                  .rename(columns={'npi':'ffs_providers'}))
        dental['service_group']='Dental (F)'; dental['ffs_sites']=pd.NA
        by_service=pd.concat([by_service,dental],ignore_index=True)
        by_service.to_csv(OUT/'02_E_F_FFS_supply_by_ZIP_service.csv',index=False)
        f_loaded = True
        note('F','READY','Dental counts added separately; verify Source F provider identifiers and county schema')
    else:
        note('F','REVIEW','Found file but could not identify NPI, ZIP and county; use a normalized CSV')
else:
    note('F','MISSING','Dental not evaluated; do not report dental-provider shortage as zero')

# ------------ SOURCE A + H: MEDI-CAL MEMBERS BY ZIP (DEMAND) ------------
a_file=find_file('A',[
    'data/demand-side/A-medical-eligible-counts-by-ZIP/calendar-years-2020-to-the-most-recent-reportable-month.csv',
    'calendar-years-2020-to-the-most-recent-reportable-month.csv'])
h_file=find_file('H',[
    'data/provider-side/H-county-zip-crosswalk/ZIP-COUNTY_062026.xlsx',
    'ZIP-COUNTY_062026.xlsx'])
members = None
if a_file and h_file:
    # NOTE: total counts usually coexist with Female/Male; never add all three.
    a=read_csv(a_file)
    need={'Month of Eligibility','Zip Code','Sex','Total Eligibles'}
    if not need.issubset(a.columns): raise ValueError(f'A missing {need-set(a.columns)}')
    a['month']=a['Month of Eligibility'].str.strip()
    month=next((m for m in MONTHS if m in set(a.month)),None)
    if not month: raise ValueError('Source A has no Sep/Aug 2026; download the required period')
    a=a[a.month.eq(month)].copy()
    a['zip']=zip5(a['Zip Code']); a=a[a.zip.str.fullmatch(r'\d{5}')]
    a['sex']=a.Sex.str.strip().str.lower().map({'m':'Male','male':'Male','f':'Female',
                                                'female':'Female','t':'Total','total':'Total'})
    a['count']=clean_count(a['Total Eligibles'])
    if a.duplicated(['zip','sex']).any():
        raise ValueError('Duplicate Source A ZIP+Sex rows; inspect before aggregation')
    p=a.pivot(index='zip',columns='sex',values='count')
    for col in ('Female','Male','Total'):
        if col not in p: p[col]=float('nan')
    from_sexes=p.Female+p.Male
    conflicting=(from_sexes.notna() & p.Total.notna() & (from_sexes!=p.Total))
    p['members']=from_sexes.combine_first(p.Total)
    p.loc[conflicting,'members']=float('nan')
    p=p.reset_index()[['zip','members']]
    h=pd.read_excel(h_file,dtype=str)
    h.columns=h.columns.astype(str).str.lower().str.strip()
    if not {'zip','geoid','res_ratio'}.issubset(h.columns):
        raise ValueError('Source H needs zip, geoid, res_ratio columns')
    h['zip']=zip5(h['zip'])
    h['geoid']=h['geoid'].astype(str).str.replace(r'\.0$','',regex=True).str.zfill(5)
    h['ratio']=pd.to_numeric(h['res_ratio'],errors='coerce')
    h=h[h.geoid.isin(COUNTY) & h.ratio.between(0,1) & h.ratio.gt(0)].copy()
    if h.duplicated(['zip','geoid']).any():
        raise ValueError('Source H has duplicate ZIP+county; inspect before joining')
    h['county']=h.geoid.map(COUNTY)
    members=h[['zip','county','ratio']].merge(p,on='zip',how='left',validate='many_to_one')
    members['members_estimated']=members.members*members.ratio
    members['source_month']=month
    members['member_basis']='All Medi-Cal members, residential allocation; NOT transitioning members'
    members[['county','zip','members_estimated','ratio','source_month','member_basis']].to_csv(
        OUT/'05_A_H_MediCal_demand_by_ZIP.csv',index=False)
    note('A+H','READY',f'{month}; {len(members):,} ZIP/county rows; missing/suppressed counts remain blank')
else:
    note('A+H','MISSING',f"Need Source A and H files; A={'present' if a_file else 'missing'}, H={'present' if h_file else 'missing'}")

# ------------ COMBINED ACCESS TABLE: every demand ZIP, INCLUDING ZERO SUPPLY ------------
access = None
if members is not None:
    services=['Primary care (candidate)','Specialist/physician (candidate)',
              'Mental health','Other / unclassified']
    if f_loaded: services.append('Dental (F)')
    keys=members[['county','zip']].drop_duplicates()
    template=keys.merge(pd.DataFrame({'service_group':services}),how='cross')
    access=template.merge(by_service,on=['county','zip','service_group'],how='left',validate='one_to_one')
    # Zero is legitimate only when ZIP is in complete Source E supply and has valid A/H mapping.
    access['ffs_providers']=access.ffs_providers.fillna(0).astype(int)
    access=access.merge(members[['county','zip','members_estimated','source_month']],
                        on=['county','zip'],how='left',validate='many_to_one')
    access['providers_per_1000_all_MediCal']=1000*access.ffs_providers/access.members_estimated
    access['members_per_provider_proxy']=access.members_estimated/access.ffs_providers.replace(0,float('nan'))
    access['zero_listed_ffs']=access.ffs_providers.eq(0)
    access['eligible_for_ranking']=access.members_estimated.gt(0)
    # Rank MOST at risk first: zero providers, then fewest per 1000; no made-up transition volumes.
    access=access.sort_values(['service_group','zero_listed_ffs','providers_per_1000_all_MediCal',
                               'members_estimated'],ascending=[True,False,True,False],na_position='last')
    access['potential_access_rank']=access[access.eligible_for_ranking].groupby('service_group').cumcount()+1
    access['rank_definition']='Low FFS supply vs all Medi-Cal; does NOT verify accepting-new-patients'
    access.to_csv(OUT/'06_FINAL_ZIP_access_by_service.csv',index=False)
    access[access.eligible_for_ranking].groupby('service_group',group_keys=False).head(10).to_csv(
        OUT/'07_TOP10_potential_access_gaps_per_service.csv',index=False)
    note('A+E+H','READY','ZIP/service access ranking built; zero-provider ZIPs included')
else:
    note('A+E+H','BLOCKED','Cannot calculate providers per 1,000 or rank patient-access risk without A+H')

# ------------ OPTIONAL SOURCES B/D: DEMOGRAPHIC AND PLAN CONTEXT ------------
for kind,rel,output in [
    ('B_age','analysis_outputs/demographics/latest_age_summary.csv','08_B_age_by_county.csv'),
    ('B_language','analysis_outputs/demographics/latest_language_summary.csv','09_B_language_by_county.csv')]:
    path=find_file(kind,[rel,rel.replace('demographics','source_b'),
                  rel.replace('analysis_outputs/demographics','source_b_outputs')])
    if path:
        read_csv(path).to_csv(OUT/output,index=False)
        note(kind,'READY','Imported from Source B notebook output (county-level only)')
    else:
        note(kind,'MISSING','Run source_b_demographic_analysis.ipynb and set OVERRIDE if needed')

d_path=find_file('D',[
    'data/demand-side/D-mediCal-managed-care-enrollment/open-data-portal-managed-care-enrollment-count-september-2026.csv'])
if d_path:
    d=read_csv(d_path)
    need={'Plan Name','Enrollment Month','County','Count of Enrollees'}
    if not need.issubset(d.columns): raise ValueError(f'D missing {need-set(d.columns)}')
    d=d[(d['Enrollment Month'].eq(MONTHS[0])) & d.County.isin(COUNTY.values())
         & d['Plan Name'].str.startswith('Inland Emp',na=False)
         & ~d['Plan Name'].str.contains('CCI|CMC',regex=True,na=False)].copy()
    d['members']=clean_count(d['Count of Enrollees'])
    d.groupby('County',as_index=False).members.sum(min_count=1).to_csv(
        OUT/'10_D_IEHP_enrollment_by_county.csv',index=False)
    note('D','READY','IEHP enrollment by county (not count of people transitioning)')
else:
    note('D','MISSING','Upload Source D for September 2026 plan enrollment')

# ------------ FINANCE: READ RESULT CSV FROM FINANCIAL NOTEBOOK (NO UNSOURCED MODEL) ------------
fin_path=find_file('FIN',[
    'IEHP_FINAL_VERIFIED_COLLECTION/09_Financial_scenarios_MODELED.csv',
    'analysis_outputs/financial/scenario_results.csv'])
if fin_path:
    fin=read_csv(fin_path)
    fin.to_csv(OUT/'11_FIN_model_scenarios_source_labeled.csv',index=False)
    note('FIN','READY','Imported scenarios; all dollar impacts are ASSUMPTIONS, not confirmed IEHP losses')
else:
    note('FIN','MISSING','Run financial_impact_analysis.ipynb; provide scenario_results.csv via OVERRIDE')

# ------------ C / G: GUIDE REFERENCE + OPTIONAL SHORTAGE-AREA CONTEXT ------------
# C: the Access Guide states IEHP Medi-Cal = 1,321,983 (Oct 2026 fact sheet;
# count month unspecified). Do NOT substitute this for September Source D counts.
notes = [
    ('C', 'IEHP Medi-Cal fact-sheet count', '1321983', 'October 2026 fact sheet; count month unspecified'),
    ('A', 'ZIP-level enrollment', '', 'All Medi-Cal eligibles; not a transition-member count'),
    ('E', 'FFS enrollment', '', 'Provider listed; not proof of accepting new patients'),
    ('F', 'FFS dental', '', 'Separate file needed; Source E does not cover full dental supply'),
    ('G', 'HRSA shortage-area indicators', '', 'Context; not ZIP-level FFS enrollment or capacity'),
    ('I', 'IEHP published provider directory', '', 'PDF-derived list may omit some network contracts'),
    ('Case', 'Financial and access scenario results', '', 'Assumptions require source labels and AI disclosure'),
]
pd.DataFrame(notes, columns=['source','metric','value','interpretation']).to_csv(
    OUT/'12_CASE_GUIDE_REFERENCE_AND_CAVEATS.csv',index=False)
g_file = ROOT/'data/provider-side/G-shortage-areas/hpsa_context.csv'
if g_file.is_file():
    read_csv(g_file).to_csv(OUT/'13_G_HPSA_context_only.csv',index=False)
    note('G','READY','Saved as context only; do not directly assign county HPSA to a ZIP')
else:
    note('G','OPTIONAL','HRSA shortage-area context not required for the core ZIP ranking')
note('C','REFERENCE','IEHP Oct 2026 fact sheet baseline 1,321,983; not the Sep 2026 Source D baseline')

# ------------ RESEARCH GUARDRAILS / SOURCE TRACKER ------------
status=pd.DataFrame(report)
status.to_csv(OUT/'00_SOURCE_READINESS_AND_LIMITATIONS.csv',index=False)
print('\nFiles written to:', OUT.resolve())
print(status.to_string(index=False))

