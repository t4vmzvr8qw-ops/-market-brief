#!/usr/bin/env python3
"""Collects recent public Google News RSS headlines. No LLM and no generated facts."""
import concurrent.futures
import datetime as dt
import email.utils
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime.now(dt.timezone.utc)
FEEDS = [
    ("earnings", '("earnings" OR "quarterly results" OR "profit forecast") (stocks OR shares OR company) when:1d', 'US', 'US'),
    ("earnings", '("earnings beat" OR "earnings miss" OR "guidance raised" OR "guidance cut") when:1d', 'US', 'US'),
    ("earnings", '("quarterly earnings" OR "quarterly profit" OR "revenue forecast") Europe when:1d', 'GB', 'EU'),
    ("earnings", '("quarterly results" OR "full-year outlook" OR "profit warning") European shares when:1d', 'GB', 'EU'),
    ("earnings", '("Quartalszahlen" OR "Gewinnwarnung" OR "Prognose angehoben") Aktie when:1d', 'DE', 'EU'),
    ("other", '("shares surge" OR "shares plunge" OR "stock jumps" OR "stock falls") (deal OR earnings OR forecast OR FDA) when:1d', 'US', 'US'),
    ("other", '("stocks rally" OR "shares slump" OR "acquisition" OR "regulator") Europe markets when:1d', 'GB', 'EU'),
    ("other", '("Fed" OR "ECB" OR "tariffs" OR "inflation") stock market when:1d', 'US', 'GLOBAL'),
]
KEY_EARN = ('earnings','quarterly','results','profit','revenue','guidance','forecast','outlook','eps','dividend','sales','quartalszahl','gewinnwarnung','prognose','umsatz','gewinn','forecast','beat estimates','miss estimates')
KEY_MOVE = ('shares','stocks','stock','markets','market','merger','acquisition','takeover','deal','tariff','fed','ecb','inflation','rate','fda','lawsuit','regulator','aktie','börse','übernahme','zinsen','rally','slump','surge','plunge','jumps','falls')
HIGH = ('guidance cut','guidance raised','profit warning','misses estimates','beats estimates','shares plunge','shares surge','forecast cut','forecast raised','gewinnwarnung','prognose gesenkt','prognose erhöht','acquisition','takeover')
WATCH_FILE = ROOT / 'config' / 'watchlist.json'
# Explicit publisher allowlist. Google News is discovery only, never the factual source.
SOURCES = ('Reuters', 'Bloomberg', 'Financial Times', 'The Wall Street Journal', 'CNBC', 'Associated Press', 'AP News', 'Handelsblatt', 'Dow Jones Newswires')
SOURCE_DOMAINS = {'Reuters': 'reuters.com', 'Bloomberg':'bloomberg.com', 'Financial Times':'ft.com', 'The Wall Street Journal':'wsj.com', 'CNBC':'cnbc.com', 'Associated Press':'apnews.com', 'AP News':'apnews.com', 'Handelsblatt':'handelsblatt.com', 'Dow Jones Newswires':'wsj.com'}

def watch_feeds():
    """Repository-level watchlist broadens collection; browser-only picks only filter existing data."""
    try:
        names=json.loads(WATCH_FILE.read_text(encoding='utf8'))
        if not isinstance(names,list):return []
    except (OSError,ValueError):return []
    result=[]
    for name in names[:35]:
        if not isinstance(name,str) or not 2<=len(name.strip())<=70:continue
        clean=re.sub(r'[^\w .&-]', ' ', name).strip()
        if clean:
            result.append(('watch', f'"{clean}" (earnings OR guidance OR results OR shares OR forecast) when:2d', 'US', 'GLOBAL'))
    return result

def bullet_points(item):
    """Only directly sourced excerpt text; no invented observations or metrics."""
    detail=item.get('detail','')
    if detail:
        # Display clearly as an excerpt, never imply multi-fact analysis.
        return ['Auszug aus dem Quellen-Feed: '+detail]
    return []

def rss_detail(node, title):
    """Google News RSS descriptions often consist of other headlines; exclude those."""
    raw=node.findtext('description') or ''
    # Exclude linked/article lists; they are not an article abstract.
    if '<a ' in raw.lower() or '<ol' in raw.lower() or '<li' in raw.lower():return ''
    raw=html.unescape(re.sub(r'<[^>]*>', ' ', raw))
    raw=' '.join(raw.split())
    if len(raw)<65 or raw.lower() in title.lower() or title.lower() in raw.lower():return ''
    return raw[:220]

def fetch(params):
    category, query, country, region = params
    url='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'de-DE' if country=='DE' else 'en-US','gl':country,'ceid':('DE:de' if country=='DE' else 'GB:en' if country=='GB' else 'US:en')})
    req=urllib.request.Request(url,headers={'User-Agent':'MarketBrief/1.0 (+GitHub Pages; public RSS reader)','Accept':'application/rss+xml,application/xml,text/xml'})
    with urllib.request.urlopen(req,timeout=15) as response:
        doc=ET.fromstring(response.read(1_500_000))
    items=[]
    for x in doc.findall('.//channel/item')[:60]:
        raw=html.unescape(' '.join((x.findtext('title') or '').split()))
        link=x.findtext('link') or ''
        source_node=x.find('source'); src=(source_node.text or '').strip() if source_node is not None else ''
        title=raw
        if src and raw.endswith(' - '+src):title=raw[:-(len(src)+3)]
        elif not src and ' - ' in raw:title,src=raw.rsplit(' - ',1)
        pub=x.findtext('pubDate')
        try:published=email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        except (ValueError,TypeError,AttributeError):continue
        age=(NOW-published).total_seconds()/3600
        if age < -2 or age > 30:continue
        if not link.startswith('https://'):continue
        if src not in SOURCES: continue  # Strict: never surface unknown/low-trust publishers.
        low=title.lower()
        is_earn=any(k in low for k in KEY_EARN)
        is_move=any(k in low for k in KEY_MOVE)
        if category=='earnings' and not is_earn:continue
        if category=='other' and not (is_move or is_earn):continue
        # The source outlet is displayed but is not evidence of the article being primary-source reporting.
        items.append({'detail':rss_detail(x,title),'title':title[:220],'url':link,'source':src[:60],'category':'earnings' if is_earn else 'other','region':region,'source_type':'journalism','published':published.isoformat().replace('+00:00','Z'),'_age':max(0,age)})
    return items

def rank(x):
    title=x['title'].lower();score=0
    if x['category']=='earnings':score+=100
    if x.get('source_type')=='filing':score+=65
    if any(k in title for k in HIGH):score+=32
    if any(k in title for k in ('quarterly','earnings','guidance','results','quartalszahlen','profit warning')):score+=12
    if any(s.lower()==x['source'].lower() for s in SOURCES):score+=14
    score-=min(35,x['_age']*1.2)
    return score

def sec_filings():
    """Primary-source filing alerts for repo watchlist, not reconstructed earnings data.
    Requires SEC_USER_AGENT='MarketBrief contact@example.com' (set as Actions secret).
    """
    import os
    agent=os.environ.get('SEC_USER_AGENT','').strip()
    if not agent or '@' not in agent:
        return [], ['SEC primary-source check skipped: configure SEC_USER_AGENT']
    try:
        names=json.loads(WATCH_FILE.read_text(encoding='utf8'))
        if not isinstance(names,list):return [], []
    except (OSError, ValueError):return [], []
    if not names:return [], []
    headers={'User-Agent':agent,'Accept':'application/json'}
    def sec_json(url):
        req=urllib.request.Request(url,headers=headers)
        with urllib.request.urlopen(req,timeout=18) as r:return json.load(r)
    try: lookup=sec_json('https://www.sec.gov/files/company_tickers.json')
    except Exception as exc:return [], ['SEC ticker lookup: '+str(exc)]
    companies=list(lookup.values()) if isinstance(lookup,dict) else []
    mapping={str(c.get('ticker','')).upper():c for c in companies}
    mapping.update({str(c.get('title','')).lower():c for c in companies})
    results=[]; errors=[]
    for original in names[:20]:
        key=str(original).strip()
        company=mapping.get(key.upper()) or mapping.get(key.lower())
        if not company:
            errors.append('SEC ticker unresolved: '+key)
            continue
        cik=int(company['cik_str'])
        try:
            doc=sec_json(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')
            recent=doc.get('filings',{}).get('recent',{})
            for i, form in enumerate(recent.get('form',[])[:65]):
                if form not in ('8-K','10-Q','10-K','6-K','20-F'):continue
                date=recent['filingDate'][i]
                filed=dt.datetime.fromisoformat(date).replace(tzinfo=dt.timezone.utc)
                if abs((NOW-filed).total_seconds())>72*3600:continue
                items=(recent.get('items',[]) or [])
                item_codes=items[i] if i<len(items) else ''
                if form=='8-K' and '2.02' not in item_codes:continue
                accession=recent['accessionNumber'][i].replace('-','')
                docname=recent['primaryDocument'][i]
                url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{urllib.parse.quote(docname)}'
                companyname=doc.get('name',company.get('title',key))
                isearn=form in ('10-Q','10-K','20-F') or '2.02' in item_codes
                title=f'{companyname}: {form} filing' + (' (results / Item 2.02)' if '2.02' in item_codes else '')
                bullets=[f'Offizielles SEC-Filing: Form {form}, eingereicht am {date}.',f'Emittent: {companyname}; Ticker: {company.get("ticker",key)}.']
                if '2.02' in item_codes:bullets.append('Form 8-K enthält Item 2.02 („Results of Operations and Financial Condition“).')
                results.append({'title':title,'url':url,'source':'SEC EDGAR','source_type':'filing','company':companyname,'ticker':company.get('ticker',key),'category':'earnings' if isearn else 'other','region':'US','published':filed.isoformat().replace('+00:00','Z'),'priority':'high' if '2.02' in item_codes else 'normal','bullets':bullets,'_age':max(0,(NOW-filed).total_seconds()/3600)})
        except Exception as exc:errors.append('SEC '+key+': '+str(exc))
    return results, errors

def main():
    results=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch,config):config for config in (FEEDS + watch_feeds())}
        for f in concurrent.futures.as_completed(futures):
            try:results.extend(f.result())
            except Exception as ex:errors.append(f'{futures[f][1][:35]}: {ex}')
    filings,sec_errors=sec_filings()
    errors.extend(sec_errors)
    results.extend(filings)
    seen=set();unique=[]
    # Ignore common duplicate syndications via headline normalization.
    for item in sorted(results,key=rank,reverse=True):
        key=re.sub(r'[^a-z0-9äöüß]','',item['title'].lower())[:110]
        if key in seen:continue
        seen.add(key)
        item['priority']=item.get('priority') or ('high' if any(k in item['title'].lower() for k in HIGH) else 'normal')
        item['bullets']=item.get('bullets') or bullet_points(item)
        item.pop('detail',None)
        unique.append(item)
    earnings=[a for a in unique if a['category']=='earnings'][:65]
    others=[a for a in unique if a['category']=='other'][:35]
    merged=(earnings+others)[:100]
    for item in merged:item.pop('_age',None)
    output={'updated_at':NOW.isoformat().replace('+00:00','Z'),'articles':merged,'source_policy':'Allowlist: Reuters, Bloomberg, Financial Times, Wall Street Journal, CNBC, AP, Handelsblatt, Dow Jones; optional SEC issuer filings.'}
    target=ROOT/'data/news.json'
    if not results and errors:
        print('All RSS sources failed. Existing data retained:', '; '.join(errors))
        raise SystemExit(1)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Updated {target}: {len(earnings)} earnings, {len(others)} other. Feed errors: {len(errors)}')
    for err in errors:print('WARNING:',err)

if __name__=='__main__':main()
