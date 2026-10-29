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
SOURCES = ('Reuters','Bloomberg','Financial Times','CNBC','MarketWatch','The Wall Street Journal','AP News','Investing.com','Barron’s','Handelsblatt','Manager Magazin','Yahoo Finance','The Guardian','The Economic Times','Seeking Alpha','Morningstar','TheStreet','The Motley Fool','Business Insider')

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
        low=title.lower()
        is_earn=any(k in low for k in KEY_EARN)
        is_move=any(k in low for k in KEY_MOVE)
        if category=='earnings' and not is_earn:continue
        if category=='other' and not (is_move or is_earn):continue
        # The source outlet is displayed but is not evidence of the article being primary-source reporting.
        items.append({'title':title[:220],'url':link,'source':src[:60] or 'Google News','category':'earnings' if is_earn else 'other','region':region,'published':published.isoformat().replace('+00:00','Z'),'_age':max(0,age)})
    return items

def rank(x):
    title=x['title'].lower();score=0
    if x['category']=='earnings':score+=100
    if any(k in title for k in HIGH):score+=32
    if any(k in title for k in ('quarterly','earnings','guidance','results','quartalszahlen','profit warning')):score+=12
    if any(s.lower()==x['source'].lower() for s in SOURCES):score+=14
    score-=min(35,x['_age']*1.2)
    return score

def main():
    results=[];errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures={pool.submit(fetch,config):config for config in FEEDS}
        for f in concurrent.futures.as_completed(futures):
            try:results.extend(f.result())
            except Exception as ex:errors.append(f'{futures[f][1][:35]}: {ex}')
    seen=set();unique=[]
    # Ignore common duplicate syndications via headline normalization.
    for item in sorted(results,key=rank,reverse=True):
        key=re.sub(r'[^a-z0-9äöüß]','',item['title'].lower())[:110]
        if key in seen:continue
        seen.add(key)
        item['priority']='high' if any(k in item['title'].lower() for k in HIGH) else 'normal'
        item['note']='Originalmeldung öffnen →'
        unique.append(item)
    earnings=[a for a in unique if a['category']=='earnings'][:13]
    others=[a for a in unique if a['category']=='other'][:7]
    merged=(earnings+others)[:20]
    for item in merged:item.pop('_age',None)
    output={'updated_at':NOW.isoformat().replace('+00:00','Z'),'articles':merged}
    target=ROOT/'data/news.json'
    if not results and errors:
        print('All RSS sources failed. Existing data retained:', '; '.join(errors))
        raise SystemExit(1)
    target.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Updated {target}: {len(earnings)} earnings, {len(others)} other. Feed errors: {len(errors)}')
    for err in errors:print('WARNING:',err)

if __name__=='__main__':main()
