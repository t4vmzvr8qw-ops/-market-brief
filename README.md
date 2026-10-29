# Market Brief — GitHub Pages (Version 3, trustworthy sources)

Static morning-brief dashboard: **Top 5 above the detailed feed**, Earnings-first prioritization, personal browser watchlist, source attribution, date/time and filters.

## Source integrity

- Only articles whose Google News RSS **publisher label exactly matches** the allowed editorial outlets: Reuters, Bloomberg, Financial Times, The Wall Street Journal, CNBC, Associated Press/AP News, Handelsblatt or Dow Jones Newswires. Google News is only a discovery mechanism; linking may point to Google News redirects.
- Optional SEC EDGAR official filings for US companies listed in `config/watchlist.json`. These show **filing metadata, not claimed financial performance**. A US 8-K is labeled earnings only when Item 2.02 is present; 10-Q/10-K/20-F use their official form labels. European coverage currently uses reliable editorial outlets, not European regulatory filings.
- No fabricated EPS, consensus surprises, outlook shifts, equity price moves, investor implications or AI summaries. When the feed has no reliable excerpt, the UI shows only the headline plus link; no speculative bullet-point padding.
- Exact publisher names in an RSS feed are **not independently authenticated** against the destination URL. Articles still require opening and checking the underlying source for investment decisions.
- Coverage is **not comprehensive**; restricted sources and paywalls may limit detail.

## Install

1. Upload all files including `.github/workflows/pages.yml`, `scripts/update_news.py`, `data/news.json` and `config/watchlist.json` into the **repository root**, not a nested directory.
2. Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Actions → Update Morning Brief → Run workflow**. Scheduled every weekday several times in the early Frankfurt morning (UTC hours 05–10).
4. Optional SEC filings: add a repo Actions secret `SEC_USER_AGENT` with a legitimate identifying application name **and your contact email address**, e.g. `MarketBrief your-contact@example.com`; do not use placeholder. Edit `config/watchlist.json` with US stock ticker strings such as `"MSFT"` and `"NVDA"`, commit, run workflow. Without the secret the SEC fetch is skipped. Browser watchlist is a local filter; it does not launch remote searches.
5. When updating an existing repo, replace files at root. If only `pages-build-deployment` appears under Actions, check that the `.github/workflows/pages.yml` file exists on `main`.

## Limitations

- No API key required for editorial feeds; SEC requires contact-bearing User-Agent as a secret. No cross-device sync. GitHub Actions schedule may be delayed or skipped; the dashboard shows the last update. The priority rules are simple heuristics, **not a materiality or investment score**.
- **Actual vs consensus, price response, professional event summaries and Europe official filings are not implemented**; add them only with licensed/verifiable data sources.
- The script keeps the previous JSON if all fetches fail. Initial `data/news.json` has no stories; run the workflow before expecting results.
