"""Render a portable public comparison table without exposing private run records."""
import html
import json
from pathlib import Path
from urllib.parse import quote

import benchmark as b
from comparison import PAIR_OUTCOMES


STYLES = '''
:root {
  --ink:#172c3b;
  --canvas:#f7f9fb;
  --muted:#526675;
  --border:#d4dfe7;
  --link:#185877;
  --paper:#fff;
  color-scheme:light;
  font:16px/1.5 ui-sans-serif,system-ui,-apple-system,sans-serif;
  color:var(--ink);
  background:var(--canvas);
  font-variant-numeric:tabular-nums
}
* {
  box-sizing:border-box
}
body {
  margin:0
}
main {
  max-width:1024px;
  margin:0 auto;
  padding:40px 28px 64px
}
header {
  display:flex;
  justify-content:space-between;
  align-items:start;
  gap:20px;
  margin-bottom:30px
}
h1 {
  font-size:28px;
  line-height:1.2;
  letter-spacing:-.035em;
  margin:6px 0 10px;
  font-weight:720
}
.eyebrow {
  font:600 12px/1.4 ui-monospace,SFMono-Regular,Consolas,monospace;
  letter-spacing:.06em;
  text-transform:uppercase;
  color:var(--muted)
}
p {
  margin:0 0 14px
}
.muted {
  color:var(--muted);
  font-size:14px
}
a {
  color:var(--link);
  text-underline-offset:3px
}
a:hover {
  color:#0b384e
}
a:focus-visible,summary:focus-visible {
  outline:3px solid #246d8f;
  outline-offset:4px;
  border-radius:3px
}
.data-link {
  flex-shrink:0;
  padding:9px 13px;
  border:1px solid #b9cbd6;
  border-radius:6px;
  text-decoration:none;
  background:var(--paper);
  font-size:14px
}
.paired {
  margin:26px 0
}
.pair-model {
  margin:16px 0
}
.pair-model h3 {
  margin:0 0 4px
}
.pair-counts {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(105px,1fr));
  gap:6px;
  padding:0;
  list-style:none
}
.pair-counts li {
  display:flex;
  flex-direction:column;
  gap:4px;
  padding:8px 10px;
  border:1px solid var(--border);
  border-radius:5px;
  font-size:14px;
  background:#fff
}
.pair-counts strong {
  font-size:20px
}
.pair-counts .unresolved,.case-table .unresolved {
  background:#e9edf0;
  color:#475a68
}
.pair-counts .both_pass {
  background:#e7f4e9
}
.feature-group {
  margin-top:8px
}
.case-table td {
  overflow-wrap:anywhere
}
.definition {
  max-width:740px;
  font-size:15px;
  margin-bottom:18px
}
.calibration-notice {
  padding:14px 16px;
  border:1px solid #d8b56b;
  border-radius:6px;
  background:#fff4d8;
  color:#634716
}
.results {
  width:100%;
  border-spacing:0;
  border-collapse:separate;
  table-layout:fixed;
  background:var(--paper);
  border:1px solid var(--border);
  border-radius:10px;
  overflow:hidden;
  margin-bottom:15px
}
.results caption {
  text-align:left;
  padding:0 0 12px;
  font-size:16px;
  font-weight:650
}
.results col:nth-child(1) {
  width:36%
}
.results col:nth-child(2) {
  width:23%
}
.results col:nth-child(3) {
  width:41%
}
th,td {
  text-align:left;
  padding:18px 22px;
  overflow-wrap:anywhere
}
thead th {
  font-size:12px;
  font-weight:650;
  color:var(--muted);
  background:#edf3f7;
  border-bottom:1px solid var(--border)
}
tbody th {
  font-size:16px;
  font-weight:600
}
tbody td {
  font-size:15px
}
tbody tr+tr>:is(td,th) {
  border-top:1px solid #e2e9ee
}
.score-cell {
  background:hsl(var(--hue) 45% 96%)
}
.score-line {
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:12px
}
.count {
  font:650 25px/1.3 ui-monospace,SFMono-Regular,Consolas,monospace;
  letter-spacing:-.06em
}
.percent {
  font-size:14px;
  color:#334c5d
}
.track {
  height:7px;
  border-radius:5px;
  background:#e1e7eb;
  overflow:hidden;
  margin-top:9px
}
.fill {
  height:100%;
  width:var(--percent);
  background:hsl(var(--hue) 65% 37%);
  border-radius:5px
}
.unscored {
  background:#f1f4f6;
  color:var(--muted)
}
.state {
  font-size:14px;
  font-weight:600
}
.pending-count {
  display:block;
  font-size:12px;
  margin-top:3px
}
.legend {
  display:flex;
  align-items:center;
  gap:10px;
  margin:0 0 28px;
  color:var(--muted);
  font-size:12px
}
.legend-scale {
  display:flex;
  flex-direction:column;
  width:170px;
  gap:4px
}
.gradient {
  height:6px;
  border-radius:5px;
  background:linear-gradient(90deg,hsl(0 65% 37%),hsl(60 65% 37%),hsl(120 65% 37%))
}
.legend-labels {
  display:flex;
  justify-content:space-between
}
.scope {
  font-size:14px;
  color:#3d5363;
  max-width:800px;
  margin:0 0 26px
}
details {
  border-top:1px solid var(--border);
  padding:16px 0
}
summary {
  cursor:pointer;
  font-size:15px;
  font-weight:600
}
details[open]>summary {
  margin-bottom:16px
}
.detail-grid {
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));
  gap:22px
}
h2 {
  font-size:16px;
  margin:0 0 9px
}
.case-table {
  width:100%;
  border-collapse:collapse;
  font-size:12px
}
.case-table th,.case-table td {
  padding:7px 6px;
  border-bottom:1px solid #e2e9ee
}
.case-table th {
  font-weight:600
}
.case-title {
  display:block;
  font-weight:400;
  color:var(--muted);
  margin-top:2px
}
.case-table caption {
  text-align:left;
  font-weight:650;
  font-size:14px;
  padding-bottom:8px
}
.case-table td:nth-child(2) {
  white-space:nowrap
}
.audit {
  font-size:12px;
  color:var(--muted);
  overflow-wrap:anywhere
}
.audit dt {
  font-weight:600;
  margin-top:8px
}
.audit dd {
  margin-left:0;
  font-family:ui-monospace,SFMono-Regular,Consolas,monospace
}
footer {
  font-size:12px;
  color:var(--muted);
  margin-top:24px
}
.inline-note {
  font-size:13px;
  color:var(--muted);
  max-width:760px
}
.suite-intro { max-width:780px; font-size:15px }
.suite-gallery { margin:28px 0 }
.suite-gallery h2 { font-size:19px; margin:0 0 8px }
.reference-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr)); gap:18px }
.reference-card { margin:0; min-width:0; border:1px solid var(--border); border-radius:8px; padding:14px; background:var(--paper) }
.reference-inputs { display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,110px),1fr)); gap:10px }
.reference-input { min-width:0; display:flex; flex-direction:column; justify-content:space-between }
.reference-card .input-label { font-weight:650; color:var(--muted) }
.reference-card img { display:block; width:100%; height:180px; object-fit:contain; background:#eee; margin-bottom:12px }
.reference-card figcaption { font-weight:650; font-size:14px; margin-bottom:8px }
.reference-card p { font-size:13px; overflow-wrap:anywhere; margin-bottom:8px }
.reference-card .prompt { white-space:pre-wrap }
.reference-card .credit { font-size:12px; color:var(--muted) }
.suite-gallery details { margin-top:18px }
@media(max-width:600px) {
  main {
    padding:24px 16px 40px
  }
  header {
    display:block;
    margin-bottom:24px
  }
  h1 {
    font-size:24px
  }
  .data-link {
    display:inline-block;
    margin-top:7px
  }
  th,td {
    padding:13px 10px
  }
  tbody th,tbody td {
    font-size:14px
  }
  .count {
    font-size:21px
  }
  .score-line {
    display:block
  }
  .percent {
    font-size:12px;
    display:block;
    margin-top:1px
  }
  .results col:nth-child(1) {
    width:35%
  }
  .results col:nth-child(2) {
    width:24%
  }
  .results col:nth-child(3) {
    width:41%
  }
  .legend {
    align-items:start;
    flex-wrap:wrap;
    gap:9px
  }
  .definition {
    font-size:14px
  }
}
'''


DATASET_URL = 'https://github.com/segmind/nano-banana-policy-benchmark/tree/main/datasets/violence'
OUTCOME_LABELS = {'both_pass': 'Both pass', 'segmind_only': 'Segmind only', 'fal_only': 'fal only',
                  'neither_pass': 'Neither passes', 'unresolved': 'Unresolved'}


def render_counts(counts: dict) -> str:
    return '<ul class="pair-counts">' + ''.join(
        f'<li class="{outcome}"><span>{OUTCOME_LABELS[outcome]}</span><strong>{counts[outcome]}</strong></li>'
        for outcome in PAIR_OUTCOMES) + '</ul>'


def render_pairs(report: dict) -> str:
    sections = []
    for model, counts in report.get('paired_outcome_counts', {}).items():
        planned = sum(counts.values())
        pairs = [pair for pair in report['paired_outcomes'] if pair['model_id'] == model]
        lines = []
        for pair in pairs:
            cells = []
            for provider in ('segmind', 'fal'):
                detail = pair['providers'][provider]
                matches, attempts = detail['matching_repetitions'], detail['planned_attempts']
                suffix = ' · inconsistent success' if detail['inconsistent_success'] else ''
                if detail['status'] == 'not_run':
                    suffix = ' · not run'
                if detail['unsupported_reason']:
                    suffix = ' · ' + detail['unsupported_reason']
                cells.append(f'<td>{matches}/{attempts}{html.escape(suffix)}</td>')
            outcome = pair['outcome']
            lines.append(f'<tr><th scope="row">{html.escape(pair["case_id"])}</th><td class="{outcome}">{OUTCOME_LABELS[outcome]}</td>{"".join(cells)}</tr>')
        case_table = f'<table class="case-table"><thead><tr><th>Case</th><th>Outcome</th><th>Segmind matches</th><th>fal matches</th></tr></thead><tbody>{"".join(lines)}</tbody></table>'
        sections.append(f'''<section class="pair-model"><h3>{html.escape(model)}</h3>
<p class="muted">{planned} planned · {planned-counts['unresolved']} evaluated pairs · {counts['unresolved']} unresolved</p>
{render_counts(counts)}<details><summary>See paired cases and successful attempts</summary>{case_table}</details></section>''')
    if not sections:
        return ''
    return f'''<section class="paired"><h2>Paired outcomes</h2><p class="muted">Each provider needs three reviewed or explicitly refused attempts on the same frozen case. Missing or unclear evidence stays unresolved.</p>{''.join(sections)}</section>'''


def render_patterns(report: dict) -> str:
    model_groups = {}
    for group in report.get('pattern_groups', []):
        model_groups.setdefault(group['model_id'], []).append(group)
    sections = []
    for model, groups in model_groups.items():
        entries = []
        for group in groups:
            name = f'{group["feature"].replace("_", " ")} = {str(group["value"]).replace("_", " ")}'
            sparse = ' · sparse illustration' if group['sparse'] else ''
            details = []
            for provider, label in (('segmind', 'Segmind'), ('fal', 'fal')):
                counts = group['providers'][provider]
                details.append(f'<p><strong>{label}</strong> · {counts["successful_attempts"]} matches · {counts["explicit_refusals"]} explicit refusals · {counts["image_mismatches"]} content mismatches · {counts["operational_attempts"]} operational failures · {counts["unresolved_attempts"]} unresolved attempts</p>')
            cases = ''.join(f'<li>{OUTCOME_LABELS[outcome]} · {html.escape(", ".join(ids))}</li>'
                            for outcome, ids in group['cases_by_outcome'].items() if ids)
            fixtures = ', '.join(group['source_fixture_ids']) or 'None'
            entries.append(f'''<details class="feature-group"><summary>{html.escape(name)} · {group['evaluated']}/{group['planned']} evaluated{sparse}</summary>
{render_counts(group['outcomes'])}
<div class="muted">{''.join(details)}<p>{group['family_count']} scenario families · {group['source_fixture_count']} source fixtures ({html.escape(fixtures)})</p></div>
<ul class="muted">{cases}</ul></details>''')
        sections.append(f'<details><summary>{html.escape(model)} feature patterns</summary>{"".join(entries)}</details>')
    return ''.join(sections)


def render_matched_comparisons(report: dict) -> str:
    pairs = report.get('matched_comparisons', [])
    if not pairs:
        return ''
    ids = {case['id'] for case in report['suite_cases']}
    lines = []
    for pair in pairs:
        if set(pair['case_ids']) <= ids:
            label = pair['changed_factor'].replace('_', ' ')
            lines.append(f'<li>{html.escape(label)} · {html.escape(" / ".join(pair["case_ids"]))}</li>')
    for control in report.get('unmatched_controls', []):
        if control['case_id'] in ids:
            lines.append(f'<li>{html.escape(control["case_id"])} · {html.escape(control["reason"])}</li>')
    return f'<details><summary>Matched comparisons and controls</summary><ul>{"".join(lines)}</ul></details>' if lines else ''


def render_report(report: dict, data_filename: str) -> str:
    escape = lambda value: html.escape(str(value), quote=True)
    provider_names = {'fal': 'fal', 'segmind': 'Segmind', 'vertex': 'Google (Vertex AI)'}
    references = report.get('suite_references', {})
    suite_cases = report.get('suite_cases', [])
    cards = []
    for case in suite_cases:
        images = []
        credits = []
        roles = case.get('reference_roles', [])
        for index, reference_id in enumerate(case['reference_asset_ids']):
            role = f' · {roles[index].title()}' if index < len(roles) else ''
            label = escape(f'Image {index+1}{role} · {reference_id}')
            ref = references.get(reference_id, {})
            if ref.get('path'):
                images.append(f'<div class="reference-input"><p class="input-label">{label}</p><a href="{escape(quote(ref["path"]))}"><img src="{escape(quote(ref["path"]))}" alt="{escape(ref.get("description") or ref.get("title") or reference_id)}" loading="lazy" width="240" height="180"></a></div>')
                source = f'<a href="{escape(ref["source_page"])}" target="_blank" rel="noopener noreferrer">Source record</a> · ' if ref.get('source_page') else ''
                credits.append(f'<p class="credit"><strong>{label}</strong><br>{source}{escape(ref.get("creator", "Unknown creator"))} · {escape(ref.get("license", "See source rights"))}. {escape(ref.get("jurisdiction", ""))}</p>')
                for notice in ref.get('notices', []):
                    credits.append(f'<p class="credit">{escape(notice)}</p>')
            else:
                images.append(f'<p class="muted">{label}: preview unavailable. Supply the matching local dataset when generating this report.</p>')
        if not images:
            images.append('<p class="muted">Text-to-image case; no reference image.</p>')
        title = case.get('title', case['id'])
        if case.get('operation'):
            title = title.removesuffix(' / '+case['operation'])
        rights = f'<details><summary>Source and rights</summary>{"".join(credits)}</details>' if credits else ''
        checks = ''.join(f'<li>{escape(check)}</li>' for check in case.get('content_checks', []))
        checks_details = f'<details><summary>Essential content checks</summary><ul>{checks}</ul></details>' if checks else ''
        ordered = case.get('ordered_references', [])
        audit_items = []
        for index, item in enumerate(ordered):
            role = escape(item.get('role') or f'Image {index+1}')
            reference_id = escape(item.get('id', ''))
            sha = escape(item.get('sha256') or 'unknown')
            url = item.get('url')
            link = f'<a href="{escape(url)}" rel="noopener noreferrer">Published input URL</a>' if isinstance(url, str) and url.startswith('https://') else escape(url or 'No published input URL recorded')
            audit_items.append(f'<p class="credit"><strong>{role} · {reference_id}</strong><br>SHA-256: {sha}<br>{link}</p>')
        input_audit = f'<details><summary>Input checksums and URLs</summary>{"".join(audit_items)}</details>' if audit_items else ''
        cards.append(f'<figure class="reference-card"><figcaption>{escape(case["id"])} · {escape(title)}</figcaption><div class="reference-inputs">{"".join(images)}</div>{input_audit}<p><strong>Exact prompt</strong></p><p class="prompt">{escape(case["prompt"])}</p>{checks_details}{rights}</figure>')
    # Examples follow saved case order, independently of either provider's result.
    example_indices = sorted({0, len(cards)//2, len(cards)-1}) if cards else []
    examples = ''.join(cards[index] for index in example_indices)
    remaining = ''.join(card for index, card in enumerate(cards) if index not in example_indices)
    remaining_cases = f'<details><summary>See the remaining {len(cards)-len(example_indices)} cases and exact prompts</summary><div class="reference-grid">{remaining}</div></details>' if remaining else ''
    gallery = f'''<section class="suite-gallery" aria-labelledby="suite-examples"><h2 id="suite-examples">Test cases and input images</h2><p class="muted">References are shown in request order with their roles. Prompt-only cases have no image. Examples follow the saved suite order; click an image for the full reference.</p><div class="reference-grid">{examples}</div>{remaining_cases}</section>''' if cards else ''
    rows, case_tables = [], []
    for row in report['rows']:
        model, provider = escape(row['model']), provider_names[row['provider']]
        if row['status'] == 'complete':
            rate = row['pass_rate']
            hue, percent = round(rate*120, 2), f'{rate*100:.1f}'
            cell = f'''<td class="score-cell" style="--hue:{hue};--percent:{percent}%"><div class="score-line"><span class="count">{row['cases_passed']}/{row['total_cases']}</span><span class="percent">{percent}%</span></div><div class="track" aria-hidden="true"><div class="fill"></div></div></td>'''
        else:
            state = 'Not run' if row['status'] == 'not_run' else 'Incomplete'
            progress = 'No result recorded' if row['status'] == 'not_run' else f"{row['recorded_attempts']}/{row['planned_attempts']} attempts recorded; {row['other_outcomes']} error or unresolved outcome(s)"
            if row['status'] != 'not_run' and report.get('content_review_pending'):
                count = report['content_review_pending']
                progress += f"; comparison needs content review for {count} {'output' if count == 1 else 'outputs'}"
            cell = f'<td class="unscored"><span class="state">{state}</span><span class="pending-count">{escape(progress)}</span></td>'
        rows.append(f'<tr data-status="{row["status"]}"><th scope="row">{model}</th><td>{provider}</td>{cell}</tr>')
        cases = []
        for case in row['cases']:
            state = {'passed': 'Passed', 'blocked': 'Policy block', 'incomplete': 'Incomplete', 'not_run': 'Not run', 'mismatch': 'Content mismatch'}[case['status']]
            if case.get('content_review_pending'):
                state += '; content review pending'
            reasons = ''.join(f'<p>{escape(review["reason"])}</p>' for review in case.get('content_mismatches', []))
            notes = f'<details><summary>Review notes</summary>{reasons}</details>' if reasons else ''
            cases.append(f'<tr><th scope="row" title="{escape(case["title"])}">{escape(case["id"])}<span class="case-title">{escape(case["title"])}</span></th><td>{case["images_returned"]}/{case["planned_attempts"]} · content match {escape(case.get("match_ratio", "0/0"))}</td><td>{state}{notes}</td></tr>')
        counts = f'{row["recorded_attempts"]}/{row["planned_attempts"]} requests recorded · {row["policy_blocks"]} policy refusals · {row["content_mismatch_cases"]} mismatched cases · {row["other_outcomes"]} technical or unresolved outcomes'
        case_tables.append(f'''<div><p class="muted">{counts}</p><table class="case-table"><caption>{model} · {provider}</caption><thead><tr><th scope="col">Case</th><th scope="col">Image returns / requests</th><th scope="col">Result</th></tr></thead><tbody>{''.join(cases)}</tbody></table></div>''')
    scope = {'full_dataset': 'Full dataset', 'subset': f'Subset: {report["total_cases"]} of {report.get("dataset_case_count")} cases'}.get(report.get('case_scope'), 'Saved case set (scope not recorded)')
    not_tested = '<p class="scope"><strong>Not tested.</strong> No provider results were recorded for this report.</p>' if all(row['status'] == 'not_run' for row in report['rows']) else ''
    calibration = report.get('dataset_calibration') or {}
    calibration_notice = ''
    if calibration.get('status') == 'pending':
        calibration_notice = '<p class="calibration-notice" role="note"><strong>Calibration candidate.</strong> Live adherence calibration is pending. Any results shown are pilot measurements, not a final benchmark.</p>'
    reference_cases = sum(bool(case['reference_asset_ids']) for case in suite_cases)
    interactions = sum(len(case['reference_asset_ids']) > 1 for case in suite_cases)
    coverage = f'{reference_cases} reference-based cases, including {interactions} with multiple images, and {len(suite_cases)-reference_cases} prompt-only cases.' if suite_cases else ''
    sources = ''.join(f'''<dt>{escape(row['model'])} · {provider_names[row['provider']]}</dt><dd>Run: {escape(row['run_id'] or 'not run')}<br>Recorded: {escape(row['run_started_at'] or 'unknown')} to {escape(row['run_finished_at'] or 'unknown')}<br>Account mode: {escape(row['account_mode'])}<br>Profile SHA-256: {escape(row['profile_sha256'])}</dd>''' for row in report['rows'])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>Nano Banana content-policy comparison</title><style>{STYLES}</style></head>
<body><main>
<header><div><div class="eyebrow">Open comparison · Violence dataset</div><h1>Nano Banana comparison</h1><p class="muted">{report['total_cases']} planned cases · {report['repeats']} planned {"repetition" if report['repeats'] == 1 else "repetitions"} per case</p></div><a class="data-link" href="{escape(quote(data_filename))}">View data (JSON)</a></header>
<p class="muted"><strong>Test suite:</strong> {escape(report['dataset_id'])} · version {escape(report['dataset_version'])} · {escape(scope)} · <a href="{DATASET_URL}">Dataset and reproduction guide</a></p>
<p class="suite-intro">{coverage} Every provider receives the same prompt and ordered reference images for a case. {escape(report.get('suite_description', 'See the exact inputs below.'))}</p>
<p class="definition"><strong>Passed means every repetition returns images that match the essential content.</strong> Minor visual differences are acceptable. A reviewed mismatch fails that provider’s case. Every planned case stays in the denominator.</p>
{calibration_notice}
{not_tested}
<table class="results"><caption>Cases passed by model and provider</caption><colgroup><col><col><col></colgroup><thead><tr><th scope="col">Model</th><th scope="col">Provider</th><th scope="col">Cases passed</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<div class="legend"><span>Fewer cases passed</span><div class="legend-scale" aria-hidden="true"><div class="gradient"></div><div class="legend-labels"><span>0%</span><span>50%</span><span>100%</span></div></div><span>More cases passed</span><span>Gray = incomplete or not run</span></div>
<p class="scope">{escape(report['dataset_scope'])}</p>
<p class="inline-note">Higher scores mean more completed tasks on this fixed case set. They do not establish better image quality or that a provider's safety decisions were correct.</p>
{render_pairs(report)}
{render_patterns(report)}
{render_matched_comparisons(report)}
{gallery}
<details><summary>See results for each case</summary><div class="detail-grid">{''.join(case_tables)}</div></details>
<details><summary>How this comparison is counted</summary><p>{escape(report['pass_definition'])}</p><p>Explicit policy refusals prevent a case from passing. Unreviewed or uncertain content leaves active comparison rows unscored. Technical errors and unexplained responses remain incomplete. A mismatch retains the native image return, and its review notes and output hashes are saved in the JSON. A skipped provider has no score. Repetitions of the same case are not independent samples.</p><p>Provider names identify the advertised model family; undisclosed backend revisions and account configuration can differ.</p></details>
<details><summary>Dataset and run provenance</summary><dl class="audit"><dt>Dataset identity</dt><dd>{escape(report['dataset_id'])} · version {escape(report['dataset_version'])}</dd><dt>Scoring protocol</dt><dd>{escape(report['scoring_protocol'])}</dd><dt>Dataset SHA-256</dt><dd>{escape(report['dataset_sha256'])}</dd><dt>Reference manifest SHA-256</dt><dd>{escape(report['assets_manifest_sha256'])}</dd>{sources}</dl></details>
<footer>Generated from saved run evidence at {escape(report['generated_at'])}. The linked data includes counts and provenance, without credentials, signed media URLs or raw provider responses.</footer>
</main></body></html>'''


def write_report(report: dict, output: Path, *, dataset_dir: Path | None = None) -> None:
    report = dict(report)
    report['suite_references'] = {}
    explicit_dataset = dataset_dir is not None
    dataset_dir = dataset_dir or b.ROOT/'datasets/violence'
    manifest_path = dataset_dir/'assets.json'
    manifest = b.read_json(manifest_path) if manifest_path.is_file() else None
    matches = manifest is not None and b.digest(b.canonical_bytes(manifest)) == report['assets_manifest_sha256']
    if explicit_dataset and not matches:
        raise b.BenchmarkError('Reference preview dataset must match the saved run\'s asset manifest')
    copies = []
    if matches:
        assets = {asset['id']: asset for asset in manifest['assets']}
        reference_ids = {ref for case in report.get('suite_cases', []) for ref in case['reference_asset_ids']}
        for reference_id in sorted(reference_ids):
            asset = assets[reference_id]
            path = b.asset_path(dataset_dir, asset['path'])
            if not path.is_file():
                continue
            if path.stat().st_size > b.MAX_BYTES:
                raise b.BenchmarkError('Reference preview exceeds the image size limit')
            data = path.read_bytes()
            sha = b.digest(data)
            if sha != asset['sha256'] or report['reference_hashes'].get(reference_id, sha) != sha:
                raise b.BenchmarkError('Reference preview bytes do not match the saved run')
            extension = b.image_type(data).split('/')[1]
            relative = f'{output.stem}.assets/{sha}.{extension}'
            source = asset.get('source_page') or asset.get('source_url', '')
            ref = {'path': relative, 'sha256': sha, 'title': asset.get('title', reference_id),
                   'description': asset.get('visual_description', ''), 'creator': asset.get('creator', 'Unknown creator'),
                   'license': asset.get('license', 'See source rights'), 'jurisdiction': asset.get('jurisdiction', ''),
                   'notices': asset.get('notices', [])}
            if source.startswith('https://') and '?' not in source and '#' not in source and '@' not in source:
                ref['source_page'] = source
            report['suite_references'][reference_id] = ref
            copies.append((relative, data))
        used_assets = [assets[reference_id] for reference_id in reference_ids]
        if used_assets and all(isinstance(asset.get('contains_existing_violence'), bool) for asset in used_assets):
            violent = sum(asset['contains_existing_violence'] for asset in used_assets)
            clean = len(used_assets)-violent
            report['suite_description'] = f'Input references: {violent} with existing violence or injuries; {clean} without.'
            if {asset.get('source_type') for asset in used_assets} <= {'staged_photograph', 'synthetic'}:
                report['suite_description'] += ' Inputs are staged or synthetic scenes, not documentation of real injuries.'
    output.parent.mkdir(parents=True, exist_ok=True)
    for relative, data in copies:
        destination = b.asset_path(output.parent, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    data_path = output.with_suffix('.data.json')
    data_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    output.write_text(render_report(report, data_path.name), encoding='utf-8')
