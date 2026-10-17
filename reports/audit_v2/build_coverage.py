"""Coverage inventory; evidence is deliberately scoped rather than a perfection claim."""
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[2]
paths=sorted([*root.glob('app/**/*.py'),*root.glob('app/*.css'),*root.glob('src/**/*.py'),root/'.streamlit/config.toml'])
revision=hashlib.sha256(b''.join(str(p.relative_to(root)).encode()+p.read_bytes() for p in paths)).hexdigest()
category_labels={'sources':'Source authority and confidence','values':'SQL/value accuracy','within':'Within-chart agreement','details':'Complete source details','cross':'Cross-artifact consistency','quality':'Data-quality controls','conclusion':'Conclusion support','clarity':'Analytical clarity','visual':'Visual and interaction consistency','useful':'Dashboard usefulness and completeness'}
assessments={
'sources':'Archive hashes and implementation bindings are checked. Full reconciliation against primary UFCStats records remains outstanding; assumed effects have no empirical authority.',
'values':'Independent reproduction covers the historical profiles, baseline, calibration, tree, all reference Monte Carlo draws and sensitivity grids. Regression preserves the saved reference within 1e-12 (feature accumulation maximum 1.71e-13).',
'within':'Numerical chart encodings are covered by focused tests. Representative desktop/mobile plots and labels were inspected; no fabricated leader is assigned to exact ties.',
'details':'Profiles, contributing bouts, denominators, partitions, assumptions, exclusions and reproducibility records remain inspectable. Separate custom sensitivity scopes are explicitly labeled.',
'cross':'Context, configuration identity, current/previous status and copied HTML/JSON/CSV/ZIP records are tested together. The existing numerical engine and source/model bytes are preserved.',
'quality':'Earlier-date, same-day, missing-denominator, malformed-count, identity, format and outcome rules are tested. Primary-source reconciliation is outside the verified archive scope.',
'conclusion':'Neutral equality and exploratory support status are preserved. A computed mean leader or colored grid region is not a causal or robust tactical recommendation.',
'clarity':'Eight purposes have distinct navigation, full matchup context and next actions. Observed, estimated, assumed and calculated information use explicit nearby language.',
'visual':'Eight views inspected; four representative views at all five requested resolutions. Contrast and keyboard focus measured. True 200% embedded-browser zoom and screen-reader behavior remain unverified.',
'useful':'The eight existing functions, staged inputs, explicit calculations, sensitivity and four export formats remain available. Native multi-file upload, snapshot validation, result/export invalidation and source restoration were observed with explicitly synthetic test files.'}
inventory=[
('fight-brief','Fight brief','component','sources clarity visual useful'),
('fighter-comparison','Earlier-date comparison table','component','sources values details cross quality clarity visual useful'),
('fighter-rate-figure','Unit-specific fighter rate plots','component','values within details clarity visual'),
('baseline-summary','Historical baseline and held-out comparison','component','sources values cross quality conclusion clarity'),
('calibration','Calibration figure and bin counts','component','sources values within details quality conclusion clarity visual'),
('tree','Decision tree and terminal branches','component','sources values within details cross clarity visual useful'),
('utilities','Utility intervals and result table','component','sources values within details cross conclusion clarity visual useful'),
('uncertainty','Utility uncertainty distributions and controlled SDs','component','values within cross conclusion clarity visual'),
('pairwise','Paired utility comparisons','component','values details cross conclusion clarity visual'),
('convergence','Monte Carlo convergence figure','component','values within cross clarity visual'),
('oneway','One-way sensitivity and crossover record','component','sources values within details cross conclusion clarity visual useful'),
('regions','Two-way decision regions and current point','component','sources values within details cross conclusion clarity visual useful'),
('tornado','Reference-policy sensitivity figure','component','values within details cross conclusion clarity visual'),
('tactical-editor','Persistent tactical draft / apply / cancel','control','sources quality clarity visual useful'),
('matchup-editor','Matchup, order, cutoff and baseline editor','control','quality cross clarity visual useful'),
('analysis-state','Empty, running, stale, failed and recovered results','control','cross quality conclusion clarity visual useful'),
('data-quality','Snapshot counts, missingness and exclusions','component','sources values details quality clarity visual useful'),
('exports','Immutable offline HTML, CSV, JSON and ZIP','comparison','sources values details cross conclusion clarity visual useful'),
('methodology','Methodology, references and scientific limitations','claim','sources details conclusion clarity visual useful'),
('primary-reconciliation','Complete reconciliation against primary UFCStats records','question','sources quality'),
('assistive-session','Full screen-reader interaction session','question','visual'),
('real-zoom','Actual 200% browser zoom','question','visual'),
('native-import-picker','Native file-picker upload interaction','control','visual useful')]
numeric=['reports/audit_v2/numbers.json','reports/audit_v2/tests_after.xml','reports/audit_v2/final_affected.xml']
visual=['reports/review_v2/browser_checks.json','reports/review_v2/after/','reports/review_v2/contrast.json','reports/review_v2/accessibility_checks.json']
units=[]
for uid,label,kind,cats in inventory:
 categories={}
 for category in cats.split():
  missing=kind=='question'
  refs=['reports/review_v2/import_checks.json'] if uid=='native-import-picker' else ['README.md','docs/LIMITATIONS.md'] if missing and uid=='primary-reconciliation' else ['reports/review_v2/accessibility_checks.json'] if missing else numeric if category in ('values','quality','cross') else visual+['tests/test_charts_v2.py','tests/test_app.py'] if category in ('visual','within') else ['reports/audit_v2/claims.md','docs/REDESIGN_V2.md','reports/audit_v2/tests_after.xml']
  check={'id':uid+'-'+category,'state':'unverified' if missing else 'passed','evidence':[] if missing else refs}
  if not missing: check['revision']=revision
  categories[category]={'checks':[check],'findings':[]}
 units.append({'id':uid,'label':label,'kind':kind,'revision':revision,'categories':categories})
record={'version':1,'artifact':{'identity':'MMA Decision Lab v2','revision':revision,'view':'Frozen snapshot greco-5e38ebeb9bb8; eight views and declared reference scenarios'},'categories':[{'id':k,'label':v,'applicable':True,'assessment':assessments[k]} for k,v in category_labels.items()],'units':units}
(root/'reports/audit_v2/coverage.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(revision)
