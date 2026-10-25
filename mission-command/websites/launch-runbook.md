# Launch-Day Runbook and Rollback Plan (DRAFT, 2026-10-25)

Target go-live: **Saturday Oct 31, 2026**, morning (before the 1-2 PM broadcast). Hard deadline: before Nov 1.
**Nothing is published, deployed, or switched to live payments without Ty's written go-ahead.** This document is a draft; platform-specific commands depend on the unknown platform [CONFIRM].

## Roles [CONFIRM names]
- Approver: Ty (go/no-go, final say).
- Builder/deployer: [name or tool unknown].
- QA tester: [name unknown; second person ideal].
- Comms: [who posts announcement].

## T-minus checklist
### Oct 30 (Fri), T-1 day
- [ ] All punch-list [M] items done or consciously deferred in writing.
- [ ] QA checklist (punch-list section K) passed on preview links.
- [ ] CPA/attorney flagged items: resolved, or the text is removed/neutral.
- [ ] Backup/export of every existing site/store taken and stored (so rollback exists).
- [ ] Record current DNS records (screenshot or export) and TTL; lower TTL to 300 s at least 24 h ahead if possible.
- [ ] Payment processors in test mode confirmed working; live-mode credentials ready but not enabled.
- [ ] Announcement posts/emails drafted, NOT scheduled.
- [ ] Ty sends written "GO for Oct 31" (or "NO-GO"). Record in plan.md decisions log.

### Oct 31 (Sat), launch day
| Time | Step |
|------|------|
| 8:00 AM | Confirm Ty's GO still stands. Check no new blockers. Freeze content edits. |
| 8:15 | Take final backup. Note current version/commit/theme ID. |
| 8:30 | Deploy HUB (site + Give page). Point DNS/publish if needed. |
| 8:45 | Hub smoke test: home loads over https, nav, Give page, signup form, contact form, spoke links. |
| 9:15 | Enable LIVE payments for donation (Ty approves). Make one small real gift ($1-$5, noted as test); confirm receipt email and deposit path to the CHURCH account; refund if appropriate. |
| 9:45 | Deploy spokes in order: 1st N8TIONS, BLK-FTHR, CLUB 1907, PE Frequency, PE Clothing. Smoke test each (see below). |
| 11:00 | Enable live store checkouts (Ty approves). One real or 100%-discount-code test order per store, then cancel/refund. |
| 11:30 | Cross-link test both directions. Analytics real-time view shows traffic. Search Console: submit sitemaps. |
| 12:00 | Go/No-go for announcement. If any P0 fail, fix or roll back first. |
| 12:15 | Announce (email + socials) with Ty's approval. |
| 1:00-2:00 | Broadcast: do NOT deploy. Mention sites on air if Ty wants. |
| 2:30 | Monitor errors, form submissions, orders. Respond to first messages. |
| 6:00 PM | End-of-day check; write launch note; list fix-forward items. |

### Smoke test (each site, 5 min)
1. Loads on https, no certificate warning, no mixed content.
2. Home, one inner page, and 404 page load on phone and desktop.
3. Email signup works (use a test address) and lands in the right list/tag.
4. Primary action works (Give, buy, waitlist, listen).
5. Link back to church works; hub link to this site works.
6. Footer legal links open.
7. No "[CONFIRM", "TBD", "lorem", or staging URLs visible.

## Post-launch (Nov 1 to Nov 7)
- Daily check of forms, orders, donations, errors, analytics.
- Fix-forward list reviewed; Phase 2 items dated in punch-list.
- Heritage Month content goes live per campaign-planner calendar.
- Report first-week metrics (visits, signups, donations, orders) to Ty; log in monthly metrics.

## Rollback plan
### Triggers (any one)
- Donation form fails, charges wrong amount, or deposits to a wrong account.
- Checkout broken or taking payment without fulfilling.
- Site down/unreachable, security warning, or data exposure.
- Wrong or harmful public content (legal claim, rights problem, cultural misrepresentation).
- Ty calls it.

### Decision rule
Ty or the deployer can call rollback. Decide within 15 minutes of confirming a P0 issue; do not debug live while donors are affected.

### Steps
1. **Contain**: disable the affected payment/checkout button first (swap for "Giving temporarily unavailable, email us at [CONFIRM contact]") rather than taking the whole site down.
2. **Revert**: restore the pre-launch backup / previous theme version / previous deploy; or restore recorded DNS records (TTL was lowered, so propagation should be ~5-30 min).
3. **If no prior site existed**: replace with a one-page "Coming soon" with email signup and the church contact; unpublish store.
4. **Payments**: switch processor back to test mode if needed; list any live transactions made during the issue; refund incorrect charges and notify those donors/buyers.
5. **Verify**: run the smoke test on the rolled-back state.
6. **Communicate**: short honest note to Ty; if public posts were made, post a brief update. Do not delete records of donations.
7. **Post-mortem**: cause, fix, re-test, new launch time, logged in plan.md decisions log.

### Rollback prerequisites (confirm by Oct 30)
- Backups exist for every site/store. 
- DNS admin access works for a second person [CONFIRM].
- Contact for platform support and payment processor saved.
- Previous-state record: whatever exists at the current domains is unknown [CONFIRM].

## Contingency: if only part is ready
- Ship order of priority: Hub + Give > 1st N8TIONS > BLK-FTHR > CLUB 1907 waitlist > PE Frequency > PE Clothing.
- Anything not ready ships as "Coming soon + email signup" with a link to the hub. Record the new date in punch-list Phase 2.

## Approvals log
| Item | Approved by | Date/time |
|------|-------------|-----------|
| Scope (MLV) | | |
| Legal text (CPA/attorney) | | |
| Go-live | | |
| Live payments on | | |
| Public announcement | | |
