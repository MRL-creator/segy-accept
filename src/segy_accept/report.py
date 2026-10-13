"""Portable, offline reports. Every value from files or policies is escaped."""

import json
from html import escape


def json_text(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n"


def render_html(result):
    def text(value):
        return escape(str(value), quote=True)

    counts = {
        s: sum(f["status"] == s for f in result["findings"])
        for s in ["pass", "warning", "failure", "unknown"]
    }
    rows = "".join(
        f'<tr><th scope="row"><a href="#{text(f["rule_id"])}">{text(f["title"])}</a>'
        f'<small>{text(f["rule_id"])}</small></th><td><span class="badge {text(f["status"])}">'
        f"{text(f['status'])}</span></td><td>{f['count']}</td></tr>"
        for f in result["findings"]
    )
    findings = "".join(
        f'<section class="finding" id="{text(f["rule_id"])}"><div class="section-head">'
        f'<h3>{text(f["title"])}</h3><span class="badge {text(f["status"])}">{text(f["status"])}</span></div>'
        f"<p><code>{text(f['rule_id'])}</code> / {f['count']} reported events</p>"
        f"<p>{text(f['next_step']) if f['status'] != 'pass' else 'No contradiction detected by this implemented rule.'}</p>"
        + (
            f"<details open><summary>Evidence examples (bounded)</summary><pre>{text(json_text(f['examples']))}</pre></details>"
            if f["examples"]
            else ""
        )
        + "</section>"
        for f in result["findings"]
    )
    provenance = {key: result[key] for key in ["tool", "input", "policy", "scan"]}
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(result["status"].title())} - SEG-Y acceptance - {text(result["input"]["name"])}</title>
<style>
:root {{color-scheme:light; --ink:#18343c; --muted:#526970; --teal:#116c69; --line:#ccdcda; --paper:#fff;}}
* {{box-sizing:border-box}} body {{margin:0;background:#eef3f1;color:var(--ink);font:16px/1.6 system-ui,sans-serif}}
a {{color:var(--teal);text-underline-offset:3px}} a:focus-visible,summary:focus-visible {{outline:3px solid #9b5a25;outline-offset:4px}}
main {{max-width:1100px;margin:40px auto;background:var(--paper);padding:42px 48px;border-top:6px solid var(--teal)}}
.eyebrow {{font-size:12px;letter-spacing:2px;font-weight:750;color:var(--teal)}}
h1 {{font:clamp(30px,4vw,46px)/1.14 Georgia,serif;margin:14px 0}} h2 {{font:28px/1.3 Georgia,serif;margin:34px 0 16px}}
h3 {{font-size:18px;line-height:1.4;margin:0}} p {{margin:10px 0}} .muted,small {{color:var(--muted)}}
small {{display:block;font-weight:400;margin-top:3px}} code {{font-size:13px;overflow-wrap:anywhere}}
.hero {{display:flex;gap:24px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:24px}}
.badge {{display:inline-block;padding:4px 12px;border-radius:20px;font-size:13px;font-weight:700;text-transform:uppercase;white-space:nowrap}}
.accepted,.pass {{background:#dceee7;color:#18503b}} .rejected,.failure {{background:#f7ded6;color:#792c1d}}
.incomplete,.unknown {{background:#e4e9ed;color:#334c60}} .warning {{background:#fbebce;color:#755014}}
.metrics {{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0}}
.metric {{background:#f1f6f4;padding:14px 18px;border-left:3px solid var(--teal)}} .metric strong {{display:block;font-size:28px;line-height:1.2}}
.notice {{background:#faf3e8;padding:14px 18px;border-left:3px solid #9b5a25;margin:22px 0}}
table {{width:100%;border-collapse:collapse;font-size:14px}} caption {{text-align:left;color:var(--muted);padding-bottom:12px}}
th,td {{text-align:left;padding:14px 12px;border-bottom:1px solid var(--line);vertical-align:top}} thead {{background:#eef5f2}}
.finding {{padding:22px 0;border-bottom:1px solid var(--line)}} .section-head {{display:flex;gap:16px;align-items:flex-start;justify-content:space-between}}
pre {{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f6f5;padding:18px;font:13px/1.5 ui-monospace,monospace}}
summary {{cursor:pointer;font-weight:650}} footer {{margin-top:32px;color:var(--muted);font-size:13px}}
@media(max-width:680px) {{main {{margin:0;padding:24px 18px}} .hero {{display:block}} .metrics {{grid-template-columns:repeat(2,1fr)}} th,td {{padding:10px 6px}} .section-head {{display:block}}}}
@media print {{body {{background:white}} main {{margin:0;padding:20px;border:0}} details {{break-inside:avoid}} .finding {{break-inside:avoid}}}}
</style></head><body><main>
<header><div class="eyebrow">SEG-Y ACCEPT / DATASET REVIEW</div><div class="hero"><div>
<h1>SEG-Y acceptance report</h1><p class="muted">{text(result["input"]["name"])} / policy: {text(result["policy"]["definition"]["name"])}</p></div>
<span class="badge {text(result["status"])}">{text(result["status"])}</span></div></header>
<div class="metrics">{"".join(f'<div class="metric"><strong>{counts[s]}</strong>{s.title()} rules</div>' for s in counts)}</div>
<p><strong>Scan:</strong> {result["scan"]["traces_inspected"]} / {text(result["scan"]["traces_expected"])} trace headers inspected.
Complete: {text(result["scan"]["complete"])}. Mode: full header scan.</p>
<div class="notice"><strong>Interpretation limit.</strong> {text(result["scope"])}
Unknown findings prevent acceptance. A completed rejection may also contain unknown findings.</div>
<h2>Decision by rule</h2><table><caption>Counts are non-pass events, not necessarily distinct traces. Evidence examples are capped.</caption>
<thead><tr><th scope="col">Check</th><th scope="col">Status</th><th scope="col">Events</th></tr></thead><tbody>{rows}</tbody></table>
<h2>Evidence and next steps</h2>{findings}
<h2>Coordinate arithmetic examples</h2><p class="muted">Raw CDP X/Y and scalar arithmetic; unit compatibility is assessed separately. No CRS is inferred.</p>
<pre>{text(json_text(result["coordinate_examples"]))}</pre>
<h2>Reproduction record</h2><p>Input SHA-256 identifies file bytes. Policy SHA-256 identifies the canonical, default-expanded JSON definition below.</p>
<details><summary>Input, policy, tool versions, and scan scope</summary><pre>{text(json_text(provenance))}</pre></details>
<footer>segy-accept {text(result["tool"]["version"])} / read-only audit / generated without remote assets or scripts</footer>
</main></body></html>"""
