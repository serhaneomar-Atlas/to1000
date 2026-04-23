# New Goal Update Checklist — to1000.com

Run this checklist every time CR7 scores. Then run `node qa-check.js` to verify.

## Files to update

### 1. `public/stats.json`
- [ ] `goals` → new total
- [ ] `remaining` → 1000 - new total
- [ ] `last_goal_date` → match date
- [ ] `last_goal_opponent` → opponent name
- [ ] `last_goal_competition` → competition name
- [ ] `season_goals` → increment if same season
- [ ] `season_matches` → increment if he played
- [ ] `goals_per_90` → recalculate (season_goals / minutes * 90)
- [ ] `last_updated` → current ISO timestamp
- [ ] `last_match` → update all fields (score, venue, cr7_goal_num, minute, etc.)
- [ ] `next_match` → update if known

### 2. `public/goals.html`
- [ ] Add new goal entry to `GOALS_INLINE_DATA` array (at the end, before `];`)
- [ ] Format: `{"num":N,"date":"YYYY-MM-DD","club":"...","opponent":"...","type":"right|left|header|penalty|fk|bicycle","minute":M,"result":"X-Y","resultType":"W|D|L","competition":"...","season":"YYYY/YY","assist":"name|—","venue":"H|A|N","desc":"Goal #N","tags":[],"videoSec":null}`
- [ ] If milestone (every 50th, 100th, etc.): add to `MILESTONES_SET` and `BIG_MILESTONES`

### 3. `public/index.html` — Translations (all 4 languages: en, fr, es, ar)
- [ ] `nav_all_goals` → update goal count number
- [ ] `journey_label` → update goal count number
- [ ] `stat_per90_sub` → update season goals count and minutes
- [ ] `hero_p` (if it references total) → update
- [ ] CTA banner `<span class="goals-cta-num">` → update number
- [ ] Default HTML text in `nav-goals-btn` and `nav-goals-btn-mobile` spans
- [ ] JS fallback: `data.season_goals || N` → update N

### 4. `public/index.html` — Other updates
- [ ] CSS `.progress-fill` width → (goals/1000 * 100)%
- [ ] CSS `@keyframes fillProgress` to value → same %
- [ ] HTML progress percentage text → same %
- [ ] Al Nassr goals in `clubsData` → if Al Nassr goal, increment
- [ ] Club goals must sum to total goals

### 5. Verify
- [ ] Run `node qa-check.js` — must show 0 errors
- [ ] Open index.html locally, switch all 4 languages, verify numbers
- [ ] Open goals.html, verify new goal appears at top of list
- [ ] Check mobile view

### 6. Deploy
```powershell
npx wrangler pages deploy public/ --project-name to1000 --branch main
```
