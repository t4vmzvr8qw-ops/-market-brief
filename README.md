# Market Brief — Morning Movers

Mobile-friendly, static morning market news briefing. GitHub Actions fetches recent Google News RSS headlines and deploys the briefing to GitHub Pages. Earnings take priority, with US and European sources and macro/company catalyst fallback. No API key required.

## Deploy

1. Create a **public** repository on GitHub (e.g., `market-brief`).
2. Upload **all files and folders** from this project to the repository root, retaining `.github/workflows/pages.yml`, and use branch `main`.
3. Under **Settings → Pages → Build and deployment**, select **GitHub Actions** as the source.
4. Under **Actions → Update Morning Brief → Run workflow**, start the first update. The GitHub Pages URL will appear under Settings → Pages / deployment.

Updates are requested at `05:17`, `06:17`, `07:17`, `08:17`, `09:17`, `10:17` UTC on weekdays. This corresponds to 07:17–12:17 during Central European summer time, 06:17–11:17 during winter time. GitHub schedules are best effort and may be delayed. Use **Actions → Run workflow** anytime to refresh the deployed snapshot.

## What it does / limitations

- Fetches public Google News RSS **headlines**, filters for earnings and market-moving terms, ranks and deduplicates results, and displays up to 13 earnings and 7 other stories from the past 30 hours.
- The categorization, regional tags, and priority indicators are *heuristic*, not proof of market movement. Regional tags indicate the target search feed, not validated company headquarters or listing market.
- Links go to Google News article URLs. Stories may link to paywalled outlets. Neither full articles nor market prices are collected. Titles are presented in their original language, primarily English, sometimes German.
- Google News RSS is not a contractual API and can change or become unavailable. If all feeds fail, the workflow errors rather than overwriting the prior data. Existing deployed data persists from the last successful deployment.
- This is **not** a verified earnings calendar, not equity return attribution, and not a comprehensive feed. Professional-grade financial data would require reliable licensed feeds and potentially paid API credentials kept in GitHub Actions secrets.
- GitHub Pages websites are public; do not put private API keys in browser files or `data/news.json`.

## Local preview

Run `python3 -m http.server 8000` in the project directory and open `http://localhost:8000`. For live data, run `python3 scripts/update_news.py` before previewing.
