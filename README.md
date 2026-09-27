# larry-today
Daily summary page. `index.html` renders `data.json`, which a GitHub Action rebuilds hourly from two Notion databases (Athlete Log, Daily intake).

Setup: add repo secret `NOTION_TOKEN` (Notion internal integration, shared with both databases) → Settings › Pages › Deploy from branch `main` / root → DNS CNAME `today` → `<user>.github.io`. Run the workflow once by hand.
