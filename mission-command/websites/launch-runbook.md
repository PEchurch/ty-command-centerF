# Launch-Day Runbook and Rollback Plan (DRAFT v2, revised 2026-10-25)
Target: **Saturday Oct 31, 2026**, US Central. Hard deadline: before Nov 1. These are **updates to existing sites**, not new builds.
**Nothing is published, deployed, or switched to live payments without Ty's written go-ahead (Ty for church sites; Ty and Lee for PE Clothing, BLK-FTHR, CLUB 1907).** Platform-specific steps are unknown until each site is audited. [CONFIRM]
No live broadcast exists, so there is no broadcast-hour freeze. Weekly videos are uploaded to the website; do not change the site while an upload is being published.

## Roles [CONFIRM names]
- Approver, church sites: Ty. Approver, private sites: Lee (admin) and Ty.
- Builder/deployer: [name unknown]. QA tester: [name; second person ideal]. Comms: [who posts].
- Backup admin per site: [name; see single-admin plan]. Launch is not "go" for a site with no backup admin who can log in.

## Site order (update to live)
1. positiveenergychurch.org (hub, Give page) 2. pe-church.online 3. 1stN8tions.store 4. BLK-FTHR 5. CLUB 1907 (waitlist unless terms reviewed) 6. PE Clothing 7. PE Frequency coming-soon page (optional).
Ship order if time is short: hub + Give > 1stN8tions.store > pe-church.online > BLK-FTHR > CLUB 1907 > PE Clothing > PE Frequency page.

## T-minus checklist
### By Mon Oct 26
- [ ] Audit of all 6 sites; backup/export of each taken and stored in two places.
- [ ] DNS records, registrar, and platform logins recorded in a shared password manager.
- [ ] Hub and pe-church.online role decided.

### By Thu Oct 29
- [ ] Backup admin added and tested on each site (Ty's 3 and Lee's 3), plus registrars and processors where possible.
- [ ] Church donation processor approved for the church account (EIN, bank). Timing unknown; if not approved, Give page ships as "giving opens soon" with signup. [CONFIRM]

### Fri Oct 30 (T-1)
- [ ] All [M] punch-list items done or deferred in writing.
- [ ] QA (punch-list K) passed on previews.
- [ ] CPA/attorney texts: resolved, or removed/neutral (donation wording, receipts, privacy policy, proceeds statement, church-support wording).
- [ ] Record DNS; lower TTL to 300 s at least 24 h ahead if possible. Do not touch DNS where the platform handles it.
- [ ] Processors in test mode and working; live credentials ready, not enabled.
- [ ] Announcements drafted, NOT scheduled (Central time set explicitly; DST ends Sun Nov 1).
- [ ] Written GO or NO-GO from Ty (and Lee for his sites). Log in plan.md decisions log.

### Sat Oct 31, launch day (Central)
| Time | Step |
|---|---|
| 8:00 AM | Confirm GO. Check blockers. Freeze edits. |
| 8:15 | Final backup of every site; note version/theme ID. |
| 8:30 | Update hub (Give page, directory). |
| 8:45 | Hub smoke test. |
| 9:15 | Ty approves live donations. One small real gift ($1-$5); confirm receipt and deposit to the CHURCH account. Refund and note it. |
| 9:45 | Update pe-church.online and 1stN8tions.store; smoke test each. |
| 10:30 | Lee/Ty update BLK-FTHR, CLUB 1907, PE Clothing; smoke test each. Deposit goes to the venture account, not the church. |
| 11:00 | Live store checkouts enabled with approvals. One test order per store (100% code), then cancel/refund. |
| 11:30 | Cross-links in both directions. Analytics real-time check. Submit sitemaps. |
| 12:00 | Go/no-go for announcement. P0 failures fixed or rolled back first. |
| 12:15 | Announce (email + socials) with Ty's approval. Halloween: no costume imagery in posts. |
| 2:30 | Monitor errors, forms, orders. |
| 6:00 PM | End-of-day check and launch note; fix-forward list. |

### Smoke test (each site, 5 min)
1. https works, no warnings. 2. Home, inner page, 404 on phone and desktop. 3. Signup works and lands in the right list/tag. 4. Primary action works (give, buy, waitlist, watch video). 5. Link to hub and hub link back both work. 6. Footer legal links open; correct legal name (church vs private seller). 7. No "[CONFIRM", "TBD", "lorem", staging URLs, or "live/on air" wording.

## Post-launch (Nov 1 to Nov 7)
Daily checks of forms, orders, donations. Fix-forward list. First weekly-video upload confirmed. Heritage Month content per campaign calendar. Schedulers checked after DST change. First-week metrics to Ty.
Giving-season dates: GivingTuesday page by Nov 13; day-of owner named Nov 20; Dec 1 (Tuesday); year-end page by Dec 15.

## Rollback plan
### Triggers (any one)
Donation form fails, wrong amount, or deposits to a wrong account. Checkout broken or taking payment without fulfillment. Site down, security warning, or data exposure. Harmful or wrong content (tax claim, rights problem, cultural misrepresentation, church money claim on a private site). Ty (or Lee for his sites) calls it.

### Decision rule
Ty or the deployer may call rollback on church sites; Lee or Ty on private sites. Decide within 15 minutes of confirming a P0 issue.

### Steps
1. **Contain:** replace the affected Give/Buy button with "Temporarily unavailable, email [CONFIRM contact]".
2. **Revert:** restore the pre-launch backup, theme version, or prior deploy; or restore recorded DNS.
3. **Payments:** processor back to test mode if needed; list live transactions during the issue; refund wrong charges and notify those people. Never delete donation records. Money that landed in the wrong entity's account: do not move it yourself; ask the CPA.
4. **Verify:** smoke test the rolled-back state.
5. **Communicate:** short note to Ty (and Lee); brief public update if announced.
6. **Post-mortem:** cause, fix, retest, new time, logged in plan.md.

### Rollback prerequisites (confirm by Thu Oct 29)
- Backup exists for every site. Previous state is known (sites exist, so we can restore them).
- A second admin on each site can log in, restore, and unpublish. This is the single-admin fix; without it, rollback depends on one person.
- Support contacts for platform and processor saved.
- Registrar/DNS access for a second person.

## Contingency
Anything not ready stays as it is today if working (do not break it), or becomes "coming soon + email signup" linking to the hub. Record the new date in the punch-list Phase 2.

## Approvals log
| Item | Approved by | Date/time (Central) |
|---|---|---|
| Hub choice and scope | | |
| Church-vs-private wording (CPA/attorney) | | |
| Legal text (donation, receipt, privacy) | | |
| Go-live: church sites (Ty) | | |
| Go-live: PE Clothing, BLK-FTHR, CLUB 1907 (Lee and Ty) | | |
| Live payments on | | |
| Public announcement | | |
