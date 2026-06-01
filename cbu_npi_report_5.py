#!/usr/bin/env python3
"""
CBU NPI Milestone Report – auto-fetch, build & publish to Confluence
"""

import json, os, sys, uuid, base64, ssl
import urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone

def _make_ssl_context():
    ctx = ssl._create_unverified_context()
    return ctx

_SSL_CTX = _make_ssl_context()

CONFLUENCE_BASE = "https://netgearcloud.atlassian.net"
REPORT_PAGE_ID  = "1321172995"
REPORT_TITLE    = "CBU NPI Milestone Report"
DASHBOARD_PAGE_ID    = None
DASHBOARD_PAGE_TITLE = "CBU NPI Program Dashboard"
CSE = f"{CONFLUENCE_BASE}/wiki/spaces/CSE/pages"
MP  = f"{CONFLUENCE_BASE}/wiki/spaces/MP/pages"

HW_COLUMNS = ["Project","G1 Explore Exit","G2 Concept Exit","G3 Plan Exit","T-food","Dogfood",
               "Ext. Beta","G4 Dev Exit","G5 MP Ready","FAI","XF","Launch","DTC","Amazon","Best Buy"]
HW_WIDTHS  = [180,90,90,90,90,90,90,90,90,90,90,90,90,90,90]
SW_COLUMNS = ["Project","G1 Explore Exit","G2 Concept Exit","G3 Plan Exit",
              "Feature Complete","Teamfood","Dogfood","Ext. Beta",
              "Release Candidate","Release Date"]
SW_WIDTHS  = [180,90,90,90,90,90,90,90,90,90]
HEADER_BG  = "var(--ds-background-accent-gray-subtle,#b3bac5)"
SECTION_BG = "#4c9aff"
HW_PRE_FAI_COLS = frozenset(range(1, 9))

HW_LABEL_MAP = {
    "explore exit":1,"explore":1,"concept exit":2,"concept":2,"planning exit":3,
    "plan exit":3,"planning":3,"teamfood":4,"t-food":4,"tfood":4,"dogfood":5,
    "external beta":6,"ext. beta":6,"ext beta":6,"development exit":7,"dev exit":7,
    "mp fw ready":8,"mp ready":8,"fai":9,"xf":10,"launch":11,
    "on shelf - dtc":12,"dtc":12,"on shelf - amazon":13,"amazon":13,
    "on shelf - best buy":14,"best buy":14,
}
SW_LABEL_MAP = {
    "explore exit":1,"explore":1,"concept exit":2,"concept":2,"planning exit":3,
    "plan exit":3,"planning":3,"feature complete":4,"teamfood":5,"t-food":5,
    "tfood":5,"team food start":5,"team food":5,"dogfood":6,"dog food start":6,
    "dog food":6,"external beta":7,"ext. beta":7,"ext beta":7,
    "release candidate":8,"mr firmware release to svt":8,"mr fw release to svt":8,
    "release date":9,"official release date":9,
}
REGIONAL_SUFFIXES = (" - eu"," - aus"," - na","-eu","-aus","-na"," eu"," aus")

CSE_HW = [
    ("Project Nova - Best","925794307","Project Nova - Best"),
    ("WiFi 8 \u2013 Nova","925794307",None),
    ("WiFi 7 \u2013 RBE973 Refresh","1338048529",None),
    ("Outdoor Extender","1368457405",None),
    ("Wifi7 RBE300Y (Outdoor Orbi)","934969345",None),
    ("Project Zenith RBE78x (Smarthome)","945127425",None),
    ("EAX17 Derivative SKU","1052246023","EAX17",HW_PRE_FAI_COLS),
    ("EXS27-100PES","1187053599","EXS27",HW_PRE_FAI_COLS),
    ("EXS27-100UKS","1187053599","EXS27",HW_PRE_FAI_COLS),
    ("Orbi RBE770v2","934806258","RBE770"),
    ("RBE77x v2 \u2013 NAS","934806258","RBE770"),
    ("RBE77x v2 \u2013 RBE773-100EUS","934806258","RBE770"),
    ("RBE77x v2 \u2013 RBE773-100APS","934806258","RBE770"),
]
CSE_APP_DIGITAL = [
    ("NETGEAR IQ","1206386835",None),
    ("New NETGEAR App \u2013 Orbi Smart Home","950993231","Smart Home"),
    ("New NETGEAR App \u2013 Armor","950993231","Armor"),
    ("New NETGEAR App \u2013 M7 & M7 Telstra","950993231","M7"),
    ("New NETGEAR App \u2013 NS300","950993231","NS300"),
    ("New NETGEAR App \u2013 M8","950993231","M8"),
    ("NHORA \u2013 Outdoor Orbi","1006698810","Outdoor"),
    ("NHORA \u2013 Improvements","1006698810","Improvements"),
    ("NHORA \u2013 Diagnostic Checks","1006698810","Diagnostic"),
    ("Stripe Rollout","1003978772",None),
    ("AWS IoT Implementation","1004503041",None),
    ("Insight Pro (Mobile SW)","996474990","Insight Pro"),
]
MP_PROJECTS = [
    ("MH7150-100EUS","205685244","MH7150"),
    ("MH7150-100PAS","205685244","MH7150"),
    ("MH7150-100APS","205685244","MH7150"),
    ("MH7110-111PAS (M7 PAS)","1025474959",None),
    ("MH7110-111APS (M7 APS)","1026622358",None),
    ("MH7110-111EUS (M7 EU/EMEA)","767688814",None),
    ("MH7110-1TLAUS (M7 Telstra)","1282146367",None),
    ("NS310-111EUS","286098586","NS310-111EUS"),
    ("NS310-111PAS","1332674561",None),
    ("NS300-100EUS","1344700434",None),
    ("NS300-100PAS","1344340004",None),
    ("MR8400-1A1NAS (M8 Pro ATT)","499351616",None),
    ("Lifeline-5G","928743485",None),
    ("MX - Low-cost Mobile","1108869650",None),
]
FW_SDK = [
    ("NextGear OS","977109069",None,False),
    ("Orbi SDK 12.5 \u2013 RBE97x","929988664","RBE97x",True),
    ("Orbi SDK 12.5 \u2013 RBE87x","929988664","RBE87x",True),
    ("Orbi SDK 12.5 \u2013 RBE77x","929988664","RBE77x",True),
]

def ts_to_date(ts_ms):
    dt = datetime.fromtimestamp(int(ts_ms)/1000,tz=timezone.utc)
    return f"{dt.month}/{dt.day}/{str(dt.year)[2:]}"

def get_texts(node):
    if node.get("type")=="text": return [node.get("text","")]
    out=[]
    for c in node.get("content",[]): out.extend(get_texts(c))
    return out

def get_dates(node):
    out=[]
    if node.get("type")=="date": out.append(ts_to_date(node["attrs"]["timestamp"]))
    for c in node.get("content",[]): out.extend(get_dates(c))
    return out

def has_done_status(node):
    if node.get("type")=="status":
        a=node.get("attrs",{})
        if a.get("text","").lower()=="done" and a.get("color")=="green": return True
    for c in node.get("content",[]):
        if has_done_status(c): return True
    return False

def has_tbd_status(node):
    if node.get("type")=="status":
        if node.get("attrs",{}).get("text","").lower()=="tbd": return True
    for c in node.get("content",[]):
        if has_tbd_status(c): return True
    return False

def cell_to_milestone_value(cell_node):
    dates=get_dates(cell_node); done=has_done_status(cell_node)
    is_tbd=has_tbd_status(cell_node)
    text=" ".join(get_texts(cell_node)).strip()
    text_l=text.lower().replace("/","").replace(" ","")
    if not dates:
        if is_tbd: return "TBD"
        if not text: return None
        if text_l in ("na","n/a"): return "N/A"
        if text_l=="tbd": return "TBD"
        if text_l=="skip": return "skip"
        return text if text else None
    if len(dates)==1:
        if done: return {"date":dates[0],"done":True}
        return {"date":dates[0]}
    sep_text=text.strip()
    if sep_text in ("->","-->","\u2192"): sep="\u2192"
    elif sep_text=="~": sep="~"
    else: sep=sep_text if sep_text else "\u2192"
    return {"dates":dates,"sep":sep}

def label_to_col(label_text,col_map):
    label=label_text.lower().strip()
    if any(label.endswith(s) for s in REGIONAL_SUFFIXES): return None
    if label in col_map: return col_map[label]
    best_col,best_len=None,0
    for key,col in col_map.items():
        if key in label and len(key)>best_len: best_col,best_len=col,len(key)
    return best_col

def parse_nested_milestone_table(nested_adf_str,col_map):
    milestones={}; mentioned=set(); cell_colors={}
    try:
        nested_doc=json.loads(nested_adf_str); nested_table=nested_doc["content"][0]
    except: return milestones,mentioned,cell_colors
    for row in nested_table.get("content",[]):
        cells=row.get("content",[])
        if len(cells)<2: continue
        label_text=" ".join(get_texts(cells[0])).strip()
        if not label_text or label_text.lower() in ("milestones","date","milestone"): continue
        col=label_to_col(label_text,col_map)
        if col is None: continue
        mentioned.add(col)
        value=cell_to_milestone_value(cells[1])
        if value is not None: milestones[col]=value
        bg=cells[1].get("attrs",{}).get("background")
        if bg: cell_colors[col]=bg
    return milestones,mentioned,cell_colors

def find_npi_summary_tables(doc):
    results=[]
    def walk(node):
        t=node.get("type","")
        if t=="bodiedExtension":
            for child in node.get("content",[]): walk(child)
        elif t=="table":
            rows=node.get("content",[])
            if rows:
                frc=rows[0].get("content",[])
                if len(frc)>=2:
                    headers=[" ".join(get_texts(c)).strip().lower() for c in frc]
                    if any("project" in h for h in headers[:3]) and len(frc)>=2:
                        results.append(node); return
        for child in node.get("content",[]): walk(child)
    walk(doc); return results

def extract_nested_table_adf(cell_node):
    def walk(node):
        if (node.get("type")=="extension" and
                node.get("attrs",{}).get("extensionKey")=="nested-table"):
            return node.get("attrs",{}).get("parameters",{}).get("adf")
        for c in node.get("content",[]):
            r=walk(c)
            if r: return r
        return None
    return walk(cell_node)

def find_best_milestone_adf(table_node, col_map):
    """Search every cell in the table; return the nested-table ADF with the most label matches."""
    best_adf, best_count = None, 0
    for row in table_node.get("content", []):
        for cell in row.get("content", []):
            adf_str = extract_nested_table_adf(cell)
            if not adf_str: continue
            _, mentioned, _ = parse_nested_milestone_table(adf_str, col_map)
            if len(mentioned) > best_count:
                best_count, best_adf = len(mentioned), adf_str
    return best_adf

def project_cell_text(table_node):
    rows=table_node.get("content",[])
    for row in rows[1:]:
        cells=row.get("content",[])
        if cells: return " ".join(" ".join(get_texts(c)) for c in cells).strip()
    return ""

def extract_milestones_from_page(doc,match_key,col_map):
    tables=find_npi_summary_tables(doc)
    if not tables: return {},set(),{}
    target_table=None
    if match_key is None:
        for t in tables:
            if find_best_milestone_adf(t,col_map): target_table=t; break
        if target_table is None: target_table=tables[0]
    else:
        key_l=match_key.lower()
        for t in tables:
            if key_l in project_cell_text(t).lower(): target_table=t; break
    if target_table is None: return {},set(),{}
    nested_adf=find_best_milestone_adf(target_table,col_map)
    if nested_adf is None: return {},set(),{}
    return parse_nested_milestone_table(nested_adf,col_map)

def make_auth_header(email,token):
    creds=base64.b64encode(f"{email}:{token}".encode()).decode()
    return f"Basic {creds}"

TOKEN_REGEN_URL = "https://id.atlassian.net/manage-profile/security/api-tokens"

def _handle_auth_error(code, body, context=""):
    """Print a clear, actionable message for 401/403 errors and exit."""
    sep = "\n" + "─" * 60
    if code == 401:
        print(f"{sep}\n❌  AUTHENTICATION FAILED (HTTP 401){(' — ' + context) if context else ''}", file=sys.stderr)
        print("    Your API token was rejected. This usually means:", file=sys.stderr)
        print("      • The token was revoked or silently invalidated by Atlassian", file=sys.stderr)
        print("      • The ATLASSIAN_API_TOKEN env var wasn't updated after generating a new token", file=sys.stderr)
        print("      • The email in ATLASSIAN_EMAIL doesn't match the token's account", file=sys.stderr)
        print(f"\n    ➜  Generate a new token at: {TOKEN_REGEN_URL}", file=sys.stderr)
        print("    ➜  Then run:  export ATLASSIAN_API_TOKEN=\"<new-token>\"", file=sys.stderr)
    elif code == 403:
        print(f"{sep}\n❌  ACCESS DENIED (HTTP 403){(' — ' + context) if context else ''}", file=sys.stderr)
        if "not permitted to use Confluence" in body:
            print("    Your account does not have a Confluence license on this instance.", file=sys.stderr)
            print("    Ask your Atlassian admin to grant your account Confluence access.", file=sys.stderr)
        else:
            print("    Your token is valid but lacks permission for this resource.", file=sys.stderr)
            print("    Possible causes:", file=sys.stderr)
            print("      • The token was silently invalidated — try generating a new one", file=sys.stderr)
            print("      • Page/space permissions were changed by an admin", file=sys.stderr)
            print(f"\n    ➜  Generate a new token at: {TOKEN_REGEN_URL}", file=sys.stderr)
            print("    ➜  Then run:  export ATLASSIAN_API_TOKEN=\"<new-token>\"", file=sys.stderr)
    print(f"    Raw response: {body[:300]}", file=sys.stderr)
    print(sep, file=sys.stderr)
    sys.exit(1)

def confluence_get(path,auth_header):
    url=f"{CONFLUENCE_BASE}{path}"
    req=urllib.request.Request(url,headers={"Authorization":auth_header,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,context=_SSL_CTX) as resp: return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code in (401, 403):
            _handle_auth_error(e.code, body, context=f"GET {path}")
        print(f"  GET {path} \u2192 HTTP {e.code}: {body[:200]}",file=sys.stderr)
        return None

def confluence_put(path,payload,auth_header):
    url=f"{CONFLUENCE_BASE}{path}"; data=json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method="PUT",headers={
        "Authorization":auth_header,"Accept":"application/json",
        "Content-Type":"application/json","X-Atlassian-Token":"no-check"})
    try:
        with urllib.request.urlopen(req,context=_SSL_CTX) as resp: return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code in (401, 403):
            _handle_auth_error(e.code, body, context=f"PUT {path}")
        print(f"  PUT {path} \u2192 HTTP {e.code}: {body[:400]}",file=sys.stderr)
        sys.exit(1)

def confluence_post(path,payload,auth_header):
    url=f"{CONFLUENCE_BASE}{path}"; data=json.dumps(payload).encode()
    req=urllib.request.Request(url,data=data,method="POST",headers={
        "Authorization":auth_header,"Accept":"application/json",
        "Content-Type":"application/json","X-Atlassian-Token":"no-check"})
    try:
        with urllib.request.urlopen(req,context=_SSL_CTX) as resp: return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code in (401, 403):
            _handle_auth_error(e.code, body, context=f"POST {path}")
        print(f"  POST {path} \u2192 HTTP {e.code}: {body[:400]}",file=sys.stderr)
        return None

def fetch_page_doc(page_id,auth_header):
    result=confluence_get(f"/wiki/rest/api/content/{page_id}?expand=body.atlas_doc_format",auth_header)
    if result is None: return None
    try:
        adf_str=result["body"]["atlas_doc_format"]["value"]; return json.loads(adf_str)
    except: return None

def txt(text,bold=False,url=None):
    marks=[]
    if bold: marks.append({"type":"strong"})
    if url: marks.append({"type":"link","attrs":{"href":url}})
    n={"type":"text","text":text}
    if marks: n["marks"]=marks
    return n

def para(*content): return {"type":"paragraph","content":list(content)}

def date_node(date_str):
    parts=date_str.strip().split("/"); m,d,y=int(parts[0]),int(parts[1]),int(parts[2])
    if y<100: y+=2000
    dt=datetime(y,m,d,tzinfo=timezone.utc); ts=str(int(dt.timestamp()*1000))
    return {"type":"date","attrs":{"timestamp":ts,"localId":str(uuid.uuid4())}}

def status_done():
    return {"type":"status","attrs":{"color":"green","style":"bold","text":"done","localId":str(uuid.uuid4())}}

def render_value(v):
    if v=="" or v is None: return []
    if isinstance(v,str): return [txt(v)]
    if isinstance(v,dict):
        nodes=[]
        if "date" in v: nodes.append(date_node(v["date"]))
        if "dates" in v:
            sep=v.get("sep","~")
            nodes+=[date_node(v["dates"][0]),txt(f" {sep} "),date_node(v["dates"][1])]
        if v.get("done"):
            if nodes: nodes.append(txt(" "))
            nodes.append(status_done())
        return nodes
    return [txt(str(v))]

def make_cell(content_list,bg=None,colwidth=None):
    attrs={}
    if bg: attrs["background"]=bg
    if colwidth: attrs["colwidth"]=[colwidth]
    return {"type":"tableCell","attrs":attrs,"content":content_list}

def section_row(label,ncols):
    return {"type":"tableRow","content":[{
        "type":"tableCell","attrs":{"colspan":ncols,"background":SECTION_BG},
        "content":[{"type":"heading","attrs":{"level":1},
                    "marks":[{"type":"alignment","attrs":{"align":"center"}}],
                    "content":[txt(label,bold=True)]}]}]}

def header_row(columns,widths):
    return {"type":"tableRow","content":[
        make_cell([para(txt(c,bold=True))],bg=HEADER_BG,colwidth=widths[i])
        for i,c in enumerate(columns)]}

DONE_NA_BG="#EBECF0"  # light grey for completed and N/A milestone cells

NO_NA_GREY_COLS=frozenset({"DTC","Amazon","Best Buy"})

def data_row(name,url,milestones,ncols,na_cols=None,cell_colors=None,no_na_grey_cols=None):
    na_cols=na_cols or set(); cell_colors=cell_colors or {}; no_na_grey_cols=no_na_grey_cols or set()
    cells=[make_cell([para(txt(name,url=url))])]
    for i in range(1,ncols):
        if i in na_cols and i not in milestones:
            # auto-generated N/A (e.g. pre-FAI cols that don't apply)
            bg=None if i in no_na_grey_cols else DONE_NA_BG
            cells.append(make_cell([{"type":"paragraph","content":[txt("N/A")]}],bg=bg))
        else:
            v=milestones.get(i,""); nodes=render_value(v)
            if cell_colors.get(i):
                bg=cell_colors.get(i)  # TPM traffic-light color takes highest priority
            elif isinstance(v,dict) and v.get("done"):
                bg=DONE_NA_BG          # completed milestone → light grey
            elif v=="N/A" and i not in no_na_grey_cols:
                bg=DONE_NA_BG          # explicit N/A → light grey (except exempted cols)
            else:
                bg=None
            cells.append(make_cell([{"type":"paragraph","content":nodes if nodes else []}],bg=bg))
    return {"type":"tableRow","content":cells}

def build_table_rows(section_label,registry,url_prefix,col_map,columns,widths,page_docs):
    ncols=len(columns); all_data_cols=set(col_map.values())
    no_na_grey={i for i,c in enumerate(columns) if c in NO_NA_GREY_COLS}
    rows=[section_row(section_label,ncols),header_row(columns,widths)]
    for entry in registry:
        name,page_id,match_key=entry[0],entry[1],entry[2]
        na_for_missing=entry[3] if len(entry)>3 else False
        url=f"{url_prefix}/{page_id}"; doc=page_docs.get(page_id)
        milestones,mentioned,cell_colors=(extract_milestones_from_page(doc,match_key,col_map) if doc else ({},set(),{}))
        if na_for_missing and milestones:
            eligible=all_data_cols if na_for_missing is True else set(na_for_missing)
            na_cols=eligible-mentioned
        else: na_cols=set()
        rows.append(data_row(name,url,milestones,ncols,na_cols=na_cols,cell_colors=cell_colors,no_na_grey_cols=no_na_grey))
    return rows

def build_body(page_docs):
    rows=[]
    rows+=build_table_rows("HW Projects - NA (CSE Space)",CSE_HW,CSE,HW_LABEL_MAP,HW_COLUMNS,HW_WIDTHS,page_docs)
    rows+=build_table_rows("Mobile Products (MP Space)",MP_PROJECTS,MP,HW_LABEL_MAP,HW_COLUMNS,HW_WIDTHS,page_docs)
    rows+=build_table_rows("Firmware & SDK Projects (CSE Space)",FW_SDK,CSE,SW_LABEL_MAP,SW_COLUMNS,SW_WIDTHS,page_docs)
    rows+=build_table_rows("App & Digital Projects (CSE Space)",CSE_APP_DIGITAL,CSE,SW_LABEL_MAP,SW_COLUMNS,SW_WIDTHS,page_docs)
    table={"type":"table","attrs":{"layout":"full-width","width":1800},"content":rows}
    today=datetime.now().strftime("%B %-d, %Y at %-I:%M %p")
    intro={"type":"paragraph","content":[txt("Generated:",bold=True),txt(f" {today}    "),txt("Source:",bold=True),txt(" "),
           txt("CBU NPI Program Review",url=f"{CONFLUENCE_BASE}/wiki/spaces/CPAPM/pages/861896737")]}
    legend1={"type":"paragraph","content":[txt("The Next Milestone for each project is shaded")]}
    legend2={"type":"paragraph","content":[txt("Green = On Track. Yellow = At Risk, have plan to green. Red = At Risk, no plan to green yet")]}
    spacer={"type":"paragraph","content":[{"type":"text","text":"\u200c"}]}
    doc={"type":"doc","content":[intro,legend1,legend2,spacer,table]}
    return json.dumps(doc,separators=(",",":"))

def _dash_status(milestone_dict):
    for v in milestone_dict.values():
        if isinstance(v,dict) and ("date" in v or "dates" in v): return ("In Progress","blue")
        if isinstance(v,str) and v not in ("","N/A","TBD","skip"): return ("In Progress","blue")
    return ("Pending","neutral")

def _dash_next_milestone(milestone_dict,columns):
    today=datetime.now(tz=timezone.utc); candidates=[]
    for col_idx,v in milestone_dict.items():
        if not isinstance(v,dict): continue
        raw_dates=[v["date"]] if "date" in v else v.get("dates",[])
        for d in raw_dates:
            try:
                parts=d.strip().split("/"); m,day,y=int(parts[0]),int(parts[1]),int(parts[2])
                if y<100: y+=2000
                dt=datetime(y,m,day,tzinfo=timezone.utc)
                if dt>=today: candidates.append((dt,col_idx,d))
            except: pass
    if not candidates: return None
    candidates.sort(key=lambda x:x[0]); _,col_idx,date_str=candidates[0]
    col_name=columns[col_idx] if col_idx<len(columns) else f"Col {col_idx}"
    return col_name,date_str

def _inline_status(text,color):
    return {"type":"status","attrs":{"color":color,"style":"bold","text":text,"localId":str(uuid.uuid4())}}

def _th(content_nodes,colwidth=None):
    attrs={}
    if colwidth: attrs["colwidth"]=[colwidth]
    return {"type":"tableHeader","attrs":attrs,"content":[{"type":"paragraph","content":content_nodes}]}

def build_dashboard_adf(page_docs):
    today_str=datetime.now().strftime("%B %-d, %Y at %-I:%M %p"); content=[]
    content.append({"type":"paragraph","content":[
        txt("Generated: ",bold=True),txt(today_str+"   \u00b7   "),
        txt("See full milestone table: ",bold=True),
        txt("CBU NPI Milestone Report",url=f"{CONFLUENCE_BASE}/wiki/rest/api/content/{REPORT_PAGE_ID}"),
        txt("   \u00b7   Milestone data sourced live from each project's Confluence page.")]})
    SECTIONS=[
        ("HW Projects \u2013 NA (CSE Space)",CSE_HW,HW_LABEL_MAP,HW_COLUMNS,CSE),
        ("Mobile Products (MP Space)",MP_PROJECTS,HW_LABEL_MAP,HW_COLUMNS,MP),
        ("Firmware & SDK Projects (CSE Space)",FW_SDK,SW_LABEL_MAP,SW_COLUMNS,CSE),
        ("App & Digital Projects (CSE Space)",CSE_APP_DIGITAL,SW_LABEL_MAP,SW_COLUMNS,CSE),
    ]
    for section_name,registry,col_map,columns,url_prefix in SECTIONS:
        content.append({"type":"heading","attrs":{"level":2},"content":[txt(section_name)]})
        tbl_rows=[{"type":"tableRow","content":[
            _th([txt("Project",bold=True)],colwidth=280),_th([txt("Status",bold=True)],colwidth=110),
            _th([txt("Next Milestone",bold=True)],colwidth=190),_th([txt("Date",bold=True)],colwidth=100),
            _th([txt("Milestones Filled",bold=True)],colwidth=130)]}]
        for entry in registry:
            name,page_id,match_key=entry[0],entry[1],entry[2]
            doc=page_docs.get(page_id)
            milestones,_,__=extract_milestones_from_page(doc,match_key,col_map) if doc else ({},set(),{})
            status_text,status_color=_dash_status(milestones)
            next_ms=_dash_next_milestone(milestones,columns)
            filled=sum(1 for v in milestones.values() if v and v not in ("","N/A","TBD","skip"))
            total=len(columns)-1; proj_url=f"{url_prefix}/{page_id}"
            tbl_rows.append({"type":"tableRow","content":[
                make_cell([para(txt(name,url=proj_url))]),
                make_cell([{"type":"paragraph","content":[_inline_status(status_text,status_color)]}]),
                make_cell([para(txt(next_ms[0] if next_ms else "\u2014"))]),
                make_cell([para(txt(next_ms[1] if next_ms else "\u2014"))]),
                make_cell([para(txt(f"{filled} / {total}"))])]})
        content.append({"type":"table","attrs":{"layout":"default"},"content":tbl_rows})
        content.append({"type":"paragraph","content":[{"type":"text","text":"\u200c"}]})
    doc={"type":"doc","version":1,"content":content}
    return json.dumps(doc,separators=(",",":"))

def find_or_create_dashboard_page(auth_header):
    global DASHBOARD_PAGE_ID
    if DASHBOARD_PAGE_ID:
        info=confluence_get(f"/wiki/rest/api/content/{DASHBOARD_PAGE_ID}?expand=version",auth_header)
        if info: return info["id"],info["version"]["number"]
    qs=urllib.parse.urlencode({"title":DASHBOARD_PAGE_TITLE,"spaceKey":"CPAPM","expand":"version"})
    found=confluence_get(f"/wiki/rest/api/content?{qs}",auth_header)
    if found and found.get("results"):
        page=found["results"][0]; pid,ver=page["id"],page["version"]["number"]
        print(f"  Found existing dashboard page (id={pid}, v{ver})")
        DASHBOARD_PAGE_ID=pid; return pid,ver
    print(f"  Creating '{DASHBOARD_PAGE_TITLE}' as a new page\u2026")
    stub=json.dumps({"type":"doc","version":1,"content":[{"type":"paragraph","content":[{"type":"text","text":"Initializing\u2026"}]}]})
    result=confluence_post("/wiki/rest/api/content",{
        "type":"page","title":DASHBOARD_PAGE_TITLE,"space":{"key":"CPAPM"},
        "ancestors":[{"id":REPORT_PAGE_ID}],
        "body":{"atlas_doc_format":{"value":stub,"representation":"atlas_doc_format"}}},auth_header)
    if not result: return None,None
    pid=result["id"]; print(f"  \u2713 Created dashboard page (id={pid})")
    DASHBOARD_PAGE_ID=pid; return pid,1

def publish_dashboard(page_docs,auth_header):
    print("\nBuilding dashboard\u2026"); dash_adf=build_dashboard_adf(page_docs)
    pid,cur_ver=find_or_create_dashboard_page(auth_header)
    if pid is None: print("  \u2717 Could not find or create dashboard page \u2014 skipping.",file=sys.stderr); return
    nxt_ver=cur_ver+1; print(f"  Publishing dashboard v{cur_ver} \u2192 v{nxt_ver}\u2026")
    result=confluence_put(f"/wiki/rest/api/content/{pid}",{
        "version":{"number":nxt_ver},"title":DASHBOARD_PAGE_TITLE,"type":"page",
        "body":{"atlas_doc_format":{"value":dash_adf,"representation":"atlas_doc_format"}}},auth_header)
    ver=result.get("version",{}).get("number")
    link=(result.get("_links",{}).get("base","")+result.get("_links",{}).get("webui",""))
    print(f"  \u2713 Dashboard published (v{ver})")
    if link: print(f"    {link}")

def serialize_milestones(milestones):
    """Convert int keys to strings for JSON serialization."""
    return {str(k): v for k,v in milestones.items()}

def export_json(page_docs, output_path=os.path.expanduser("~/scripts/cbu_npi_data.json")):
    """Export all milestone data to a JSON file for use with the HTML report."""
    SECTIONS=[
        {"label":"HW Projects \u2013 NA (CSE Space)","registry":CSE_HW,"url_prefix":CSE,
         "col_map":HW_LABEL_MAP,"columns":HW_COLUMNS,"widths":HW_WIDTHS},
        {"label":"Mobile Products (MP Space)","registry":MP_PROJECTS,"url_prefix":MP,
         "col_map":HW_LABEL_MAP,"columns":HW_COLUMNS,"widths":HW_WIDTHS},
        {"label":"Firmware & SDK Projects (CSE Space)","registry":FW_SDK,"url_prefix":CSE,
         "col_map":SW_LABEL_MAP,"columns":SW_COLUMNS,"widths":SW_WIDTHS},
        {"label":"App & Digital Projects (CSE Space)","registry":CSE_APP_DIGITAL,"url_prefix":CSE,
         "col_map":SW_LABEL_MAP,"columns":SW_COLUMNS,"widths":SW_WIDTHS},
    ]
    all_data_cols_hw=set(HW_LABEL_MAP.values())
    all_data_cols_sw=set(SW_LABEL_MAP.values())
    rows=[]
    for sec in SECTIONS:
        all_data_cols=all_data_cols_hw if sec["col_map"] is HW_LABEL_MAP else all_data_cols_sw
        for entry in sec["registry"]:
            name,page_id,match_key=entry[0],entry[1],entry[2]
            na_for_missing=entry[3] if len(entry)>3 else False
            url=f"{sec['url_prefix']}/{page_id}"
            doc=page_docs.get(page_id)
            milestones,mentioned,cell_colors=(extract_milestones_from_page(doc,match_key,sec["col_map"]) if doc else ({},set(),{}))
            if na_for_missing and milestones:
                eligible=all_data_cols if na_for_missing is True else set(na_for_missing)
                na_cols=list(eligible-mentioned)
            else: na_cols=[]
            rows.append({
                "section":sec["label"],
                "name":name,
                "url":url,
                "columns":sec["columns"],
                "widths":sec["widths"],
                "milestones":serialize_milestones(milestones),
                "cell_colors":serialize_milestones(cell_colors),
                "na_cols":na_cols,
            })
    output={
        "generated":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "rows":rows,
    }
    with open(output_path,"w") as f: json.dump(output,f,indent=2)
    print(f"\u2713 Exported JSON data to {output_path}  ({len(rows)} projects)")

def main():
    export_only="--export-json" in sys.argv
    json_path=next((sys.argv[sys.argv.index("--export-json")+1]
                    for i,a in enumerate(sys.argv) if a=="--export-json" and i+1<len(sys.argv)
                    and not sys.argv[i+1].startswith("-")),
                   os.path.expanduser("~/scripts/cbu_npi_data.json")) if "--export-json" in sys.argv else os.path.expanduser("~/scripts/cbu_npi_data.json")

    email=os.environ.get("ATLASSIAN_EMAIL","kevin.driscoll@netgear.com")
    token=os.environ.get("ATLASSIAN_API_TOKEN","")
    if not token:
        print("─" * 60, file=sys.stderr)
        print("❌  ATLASSIAN_API_TOKEN is not set.", file=sys.stderr)
        print(f"    ➜  Generate a token at: {TOKEN_REGEN_URL}", file=sys.stderr)
        print("    ➜  Then run:  export ATLASSIAN_API_TOKEN=\"<your-token>\"", file=sys.stderr)
        print("                  export ATLASSIAN_EMAIL=\"<your-email>\"", file=sys.stderr)
        print("─" * 60, file=sys.stderr)
        sys.exit(1)
    auth=make_auth_header(email,token)
    print(f"Checking credentials for {email}...")
    me = confluence_get("/wiki/rest/api/user/current", auth)
    if me is None:
        print("❌  Could not verify credentials — check errors above.", file=sys.stderr)
        sys.exit(1)
    print(f"✓  Authenticated as: {me.get('displayName','unknown')} ({me.get('publicName',email)})\n")
    all_projects=([(e[1],"CSE") for e in CSE_HW]+[(e[1],"CSE") for e in CSE_APP_DIGITAL]+
                  [(e[1],"MP") for e in MP_PROJECTS]+[(e[1],"CSE") for e in FW_SDK])
    unique_page_ids=dict.fromkeys(pid for pid,_ in all_projects)
    print(f"Fetching {len(unique_page_ids)} source pages...")
    page_docs={}; fetched=ok=0
    for page_id in unique_page_ids:
        fetched+=1; doc=fetch_page_doc(page_id,auth)
        if doc: page_docs[page_id]=doc; ok+=1; print(f"  [{fetched}/{len(unique_page_ids)}] {page_id} \u2713")
        else: print(f"  [{fetched}/{len(unique_page_ids)}] {page_id} \u2717 (will use empty milestones)")

    if export_only:
        export_json(page_docs, json_path)
        return

    export_json(page_docs, json_path)  # always export alongside publish

    print("\nBuilding report..."); body_str=build_body(page_docs)
    doc=json.loads(body_str); tbl=doc["content"][2]; n_rows=len(tbl["content"])
    n_sec=sum(1 for r in tbl["content"] if r.get("content") and r["content"][0].get("attrs",{}).get("background")==SECTION_BG)
    n_sticky=sum(1 for r in tbl["content"] if r.get("content") and r["content"][0].get("type")=="tableHeader")
    print(f"  {n_rows} rows | {n_sec} section banners | {n_sticky} sticky headers (must be 0)")
    if n_sticky>0: print("ERROR: sticky headers detected \u2013 aborting.",file=sys.stderr); sys.exit(1)
    info=confluence_get(f"/wiki/rest/api/content/{REPORT_PAGE_ID}?expand=version",auth)
    cur_ver=info["version"]["number"]; nxt_ver=cur_ver+1
    print(f"\nPublishing v{cur_ver} \u2192 v{nxt_ver}...")
    result=confluence_put(f"/wiki/rest/api/content/{REPORT_PAGE_ID}",{
        "version":{"number":nxt_ver},"title":REPORT_TITLE,"type":"page",
        "body":{"atlas_doc_format":{"value":body_str,"representation":"atlas_doc_format"}}},auth)
    ver=result.get("version",{}).get("number")
    link=(result.get("_links",{}).get("base","")+result.get("_links",{}).get("webui",""))
    print(f"\u2713 Published milestone report v{ver}")
    if link: print(f"  {link}")
    publish_dashboard(page_docs,auth)

if __name__=="__main__":
    main()
