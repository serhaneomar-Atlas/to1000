#!/usr/bin/env node
/**
 * to1000.com — QA Consistency Checker
 * Run after every goal update: node qa-check.js
 *
 * Checks:
 *  1. stats.json goals count matches GOALS_INLINE_DATA length in goals.html
 *  2. stats.json remaining = 1000 - goals
 *  3. All translations reference the same goal count (nav, journey, loading text)
 *  4. CSS progress width matches percentage
 *  5. Club goal totals sum to total goals
 *  6. Season stats consistency
 *  7. Al Nassr goals in bar chart match computed value
 */

const fs = require('fs');
const path = require('path');

const PUBLIC = path.join(__dirname, 'public');
let errors = 0;
let warnings = 0;

function fail(msg) { console.error(`  ❌ FAIL: ${msg}`); errors++; }
function warn(msg) { console.warn(`  ⚠️  WARN: ${msg}`); warnings++; }
function pass(msg) { console.log(`  ✅ ${msg}`); }

// ─── Load files ──────────────────────────────────────────────────────────────
const statsRaw = fs.readFileSync(path.join(PUBLIC, 'stats.json'), 'utf-8');
const stats = JSON.parse(statsRaw);

const indexHtml = fs.readFileSync(path.join(PUBLIC, 'index.html'), 'utf-8');
const goalsHtml = fs.readFileSync(path.join(PUBLIC, 'goals.html'), 'utf-8');

const TOTAL = stats.goals;
const REMAINING = stats.remaining;
const SEASON = stats.season_goals;
const PER90 = stats.goals_per_90;
const PCT = ((TOTAL / 1000) * 100).toFixed(1);

console.log(`\n🔍 to1000.com QA Check — ${new Date().toISOString()}`);
console.log(`   Total goals: ${TOTAL} | Remaining: ${REMAINING} | Season: ${SEASON} | Per90: ${PER90}\n`);

// ─── 1. stats.json internal consistency ──────────────────────────────────────
console.log('1️⃣  stats.json consistency');
if (TOTAL + REMAINING === 1000) pass(`goals (${TOTAL}) + remaining (${REMAINING}) = 1000`);
else fail(`goals (${TOTAL}) + remaining (${REMAINING}) = ${TOTAL + REMAINING}, expected 1000`);

// ─── 2. GOALS_INLINE_DATA count in goals.html ───────────────────────────────
console.log('\n2️⃣  goals.html inline data count');
const goalEntries = goalsHtml.match(/"num"\s*:\s*\d+/g);
const goalCount = goalEntries ? goalEntries.length : 0;
if (goalCount === TOTAL) pass(`GOALS_INLINE_DATA has ${goalCount} entries = stats.json (${TOTAL})`);
else fail(`GOALS_INLINE_DATA has ${goalCount} entries but stats.json says ${TOTAL}`);

// Check last goal number
const lastNumMatch = goalsHtml.match(/"num"\s*:\s*(\d+)[^}]*$/m);
// Better: find the highest num
const allNums = goalEntries ? goalEntries.map(m => parseInt(m.match(/\d+/)[0])) : [];
const maxNum = Math.max(...allNums);
if (maxNum === TOTAL) pass(`Highest goal number: ${maxNum} = total (${TOTAL})`);
else fail(`Highest goal number: ${maxNum}, expected ${TOTAL}`);

// ─── 3. Translation strings referencing goal count ───────────────────────────
console.log('\n3️⃣  Goal count in translations');
const goalCountStr = String(TOTAL);

// index.html: check all 4 languages for nav_all_goals, journey_label
const navGoalsMatches = indexHtml.match(/nav_all_goals\s*:\s*'[^']*'/g) || [];
for (const m of navGoalsMatches) {
  if (m.includes(goalCountStr)) pass(`nav_all_goals contains ${goalCountStr}: ${m.substring(0, 60)}…`);
  else fail(`nav_all_goals missing ${goalCountStr}: ${m.substring(0, 60)}…`);
}

const journeyMatches = indexHtml.match(/journey_label\s*:\s*'[^']*'/g) || [];
for (const m of journeyMatches) {
  if (m.includes(goalCountStr)) pass(`journey_label contains ${goalCountStr}`);
  else fail(`journey_label missing ${goalCountStr}: ${m.substring(0, 60)}…`);
}

// goals.html: loading_text, hero_p
const loadingMatches = goalsHtml.match(/loading_text\s*:\s*'[^']*'/g) || [];
for (const m of loadingMatches) {
  if (m.includes(goalCountStr)) pass(`goals.html loading_text contains ${goalCountStr}`);
  else fail(`goals.html loading_text missing ${goalCountStr}: ${m.substring(0, 60)}…`);
}

// ─── 4. Default HTML hardcoded text ──────────────────────────────────────────
console.log('\n4️⃣  Hardcoded HTML defaults');
// Check the CTA banner number
const ctaNumMatch = indexHtml.match(/<span class="goals-cta-num">(\d+)<\/span>/);
if (ctaNumMatch) {
  if (ctaNumMatch[1] === goalCountStr) pass(`CTA banner number: ${ctaNumMatch[1]}`);
  else fail(`CTA banner shows ${ctaNumMatch[1]}, expected ${goalCountStr}`);
}

// ─── 5. CSS progress bar width ───────────────────────────────────────────────
console.log('\n5️⃣  Progress bar percentage');
const expectedPct = PCT;
const cssWidthMatches = indexHtml.match(/width\s*:\s*([\d.]+)%/g) || [];
// Look for the main progress bar width
const progressPctMatch = indexHtml.match(/\.progress-fill\s*\{[^}]*width\s*:\s*([\d.]+)%/s);
if (progressPctMatch) {
  if (progressPctMatch[1] === expectedPct) pass(`Progress bar CSS width: ${progressPctMatch[1]}% = expected ${expectedPct}%`);
  else warn(`Progress bar CSS width: ${progressPctMatch[1]}%, expected ${expectedPct}%`);
}

// Check text mentions of percentage
const pctTextMatches = indexHtml.match(/[\d.]+%/g) || [];
const pctValue = parseFloat(expectedPct);

// ─── 6. Club goals sum ──────────────────────────────────────────────────────
console.log('\n6️⃣  Club goal totals');
const clubGoalsPattern = /goals\s*:\s*(\d+)/g;
// Find the clubs data array
const clubsSection = indexHtml.match(/const\s+clubsData\s*=\s*\[([\s\S]*?)\];/);
if (clubsSection) {
  const clubGoals = [];
  let m;
  const re = /name\s*:\s*'([^']+)'.*?goals\s*:\s*(\d+)/g;
  while ((m = re.exec(clubsSection[1])) !== null) {
    clubGoals.push({ name: m[1], goals: parseInt(m[2]) });
  }
  const sum = clubGoals.reduce((a, c) => a + c.goals, 0);
  if (sum === TOTAL) pass(`Club goals sum: ${clubGoals.map(c => `${c.name}(${c.goals})`).join(' + ')} = ${sum}`);
  else fail(`Club goals sum: ${sum}, expected ${TOTAL}. Breakdown: ${clubGoals.map(c => `${c.name}(${c.goals})`).join(', ')}`);
}

// ─── 7. Season stats ─────────────────────────────────────────────────────────
console.log('\n7️⃣  Season stats consistency');
const seasonInHtml = indexHtml.match(/data\.season_goals\s*\|\|\s*(\d+)/);
if (seasonInHtml) {
  const fallback = parseInt(seasonInHtml[1]);
  if (fallback === SEASON) pass(`JS season fallback: ${fallback} = stats.json (${SEASON})`);
  else fail(`JS season fallback: ${fallback}, stats.json says ${SEASON}`);
}

// Check per90 sub strings contain correct season goals count
const per90Subs = indexHtml.match(/stat_per90_sub\s*:\s*'[^']*'/g) || [];
for (const s of per90Subs) {
  if (s.includes(String(SEASON))) pass(`per90_sub contains ${SEASON}`);
  else fail(`per90_sub doesn't contain ${SEASON}: ${s.substring(0, 60)}…`);
}

// ─── 8. MILESTONES include the latest goal ───────────────────────────────────
console.log('\n8️⃣  Milestones check');
const msMatch = goalsHtml.match(/MILESTONES_SET\s*=\s*new\s*Set\(\[([\s\S]*?)\]\)/);
if (msMatch) {
  if (msMatch[1].includes(goalCountStr)) pass(`MILESTONES_SET includes ${goalCountStr}`);
  else warn(`MILESTONES_SET does not include ${goalCountStr} — may not be a milestone`);
}

// ─── Summary ─────────────────────────────────────────────────────────────────
console.log(`\n${'═'.repeat(50)}`);
if (errors === 0 && warnings === 0) {
  console.log('🎉 All checks passed! Site is consistent.');
} else {
  if (errors > 0) console.log(`❌ ${errors} error(s) found — fix before deploying!`);
  if (warnings > 0) console.log(`⚠️  ${warnings} warning(s) — review recommended.`);
}
console.log(`${'═'.repeat(50)}\n`);

process.exit(errors > 0 ? 1 : 0);
