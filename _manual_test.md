# Deep Manual Test — system answers vs ground truth

### Q1. Who owns 183 Mark Tree Rd, Centereach and is it connected to David DeRosa or his network?
- **Property:** 183 Mark Tree Rd, Centereach (ent_prop_0200468000500010000) · is_david=True
- **Ground truth:** owners=['183Ma Llc', 'JOANNE RIVERA'] · facts={'chain_of_title': 6, 'mortgages': 21, 'liens': 1, 'lis_pendens': 10, 'judgments': 21, 'assignments': 6} · events=66 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=9 verified=9 · sources={'title_report': 37, 'attachment': 252, 'email_body': 31}
- **Answer:**

**Record owner.** A Prowess Title Abstracts full search (search date 05/26/2026) for 183 Mark Tree Rd, Centereach, NY 11720 (Suffolk County, Parcel 0200-468-00-05-00-010-000) reports the vesting owner as "183MA LLC, AS TO A 90% INTEREST AND JOANNE RIVERA, AS ADMINISTRATOR TO THE ESTATE OF JOY RIVERA, DECEASED 04/29/2018, AS TO A 10% INTEREST" [#1]. The current vesting deed is dated 8/5/2024 (recorded 8/6/2024) from Joanne Rivera, as Administrator to the Estate of Joy Rivera, for a stated consideration of $2,500.00 [#1]. The Suffolk County assessment/owner record lists the owners as "183MA LLC" with the mailing address "RIVERA JOANNE 47 SARAH DR FARMINGDALE NY 11735" [#95].

**Connection to David DeRosa's network — yes, multiple links.**

1. **Shared business address.** The owner-of-record mailing address for 183MA LLC is 47 Sarah Drive, Farmingdale, NY 11735 [#95] — the same Farmingdale address used by DeRosa's corporate-defendant entities. The MangoTree complaint pleads that, e.g., "Defendant 91G, LLC is New York limited liability company and does business at 47 Sarah Drive, Farmingdale, New York 11735" [#230], and that David D. DeRosa "is the principal member and sole and/or majority owner of all the corporate defendants" operating out of the Sarah Drive offices [#90]. The 47 Sarah Drive address is the operational hub of the DeRosa/IPA network.

2. **The property was being managed/renovated through IPA.** A June 16, 2020 IPA check-request email to Rakesh Bhargava directed payment of "K&V Home Improvements Inc. - $350 for 183 Mark Tree Rd, Centereach" [#88], and the underlying K&V invoice (#367) is expressly captioned "K & V Home Improvements Inc Invoice #367 for 183 Mark Tree Centereach,NY" routed for payment through IPE Realty/IPA [#193].

3. **Utilities in IPA's name.** The Suffolk County Water Authority account for the property was billed to "IPA ASSET MANAGEMENT 183 MARK TREE RD CENTEREACH NY 11720-2237" [#194] — i.e., IPA Asset Management (DeRosa's entity) held the water account for the house.

**Bottom line.** Title is vested in 183MA LLC (90%) and Joanne Rivera as Administrator of the Estate of Joy Rivera (10%) [#1]. While no document in this corpus literally names David DeRosa as a member of "183MA LLC," the property is firmly tied into the DeRosa/IPA network: the LLC's owner-of-record address is the DeRosa entities' 47 Sarah Drive, Farmingdale hub [#95][#230][#90], renovation costs were paid through IPA's check-request process [#88][#193], and the water utility was carried in IPA Asset Management's name [#194]. The precise membership of 183MA LLC is not documented here, so direct DeRosa ownership is a reasonable inference rather than an established fact — I flag that gap.

— Provenance: 320 sources across {'title_report': 37, 'attachment': 252, 'email_body': 31} | corpora {'unknown': 320} | mode=analysis | date span 2019-01-07 → 2026-05-26 | facts verified 9/9

---

### Q2. What mortgages, liens, or judgments are recorded against 183 Mark Tree Rd, Centereach?
- **Property:** 183 Mark Tree Rd, Centereach (ent_prop_0200468000500010000) · is_david=True
- **Ground truth:** owners=['183Ma Llc', 'JOANNE RIVERA'] · facts={'chain_of_title': 6, 'mortgages': 21, 'liens': 1, 'lis_pendens': 10, 'judgments': 21, 'assignments': 6} · events=66 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=13 verified=13 · sources={'title_report': 108, 'email_body': 3, 'attachment': 88}
- **Answer:**

**Bottom line: As of the most recent (May 26, 2026) full title search, there are NO open mortgages, liens, or money judgments currently encumbering 183 Mark Tree Rd, Centereach.** The authoritative document is the Prowess Title Abstracts "Full Search," dated 05/26/2026 with an Effective Date of 05/16/2026, run on 183MA LLC / 183 Mark Tree Rd, Centereach, NY 11720, Suffolk County Parcel ID 0200-468-00-05-00-010-000 [#69].

**Current ownership.** Title is vested in "183MA LLC, AS TO A 90% INTEREST AND JOANNE RIVERA, AS ADMINISTRATOR TO THE ESTATE OF JOY RIVERA, DECEASED 04/29/2018, AS TO A 10% INTEREST," by a deed dated 8/5/2024, recorded 8/6/2024, for consideration of $2,500.00 [#69].

**Mortgages.** The report's deed-chain remark for the property states plainly: "No open mortgage/judgment/liens found" [#70]. The historical chain does show that several mortgages were recorded against prior owners decades ago — e.g., a MORTGAGE-MF in the name of RIVERA, JOY recorded 8/25/1987, with a corresponding SATISFACTION recorded 9/10/1987 [Timeline/#1]; MORTGAGE-MF entries for WALTERS recorded 11/20/1990 and 12/26/1990, followed by a SATISFACTION recorded 10/7/1991 [#1]; an ATKINSON mortgage recorded 10/7/1993; and a MORTGAGE-MF naming RIVERA, ROM... recorded 12/23/1991 [#99]. These are old instruments in the chain of title and the search did not flag any of them as an OPEN/unsatisfied mortgage encumbering the current owner [#70].

**Judgments.** The search's judgment index for the names searched (183MA LLC, RIVERA, JOY, RIVERA, JOANNE) returned a list of items tied to the individual JOANNE RIVERA — chiefly Suffolk County Traffic & Parking Violations Agency "1ST DISTRICT RED LT" entries (e.g., S13-000195689 dated 12/11/2014; S13-000050046 dated 12/8/2014) [#2], and one older entry: "RIVERA, JOANNE CEC 90 3242 MF 1/9/1991 11:20 am NEW YORK STATE HIGHER EDUCATION SERVIC..." [#2]. These are name-index hits against the individual, not perfected money-judgment liens that the report identified as attaching to and running with this parcel. Critically, the search summary remark for the property is "No open mortgage/judgment/liens found" [#70].

**Liens / UCC.** Immediately after the judgment list, the report states "Liens No Records Found" and "UCC No Records Found" [#2].

**Important caveats and gaps.** 
1. The traffic/red-light judgment entries against "RIVERA, JOANNE" [#2] are genuine name-index records. Because Joanne Rivera holds a 10% interest (as administrator of the Estate of Joy Rivera) [#69], you should confirm with a certified search whether any of those judgments could attach to her fractional interest. The body of the report nonetheless characterizes the property as having "No open mortgage/judgment/liens found" [#70].
2. The property and its owner-family of entities are entangled in the MangoTree v. DeRosa litigation, in which judgments and notices of pendency have been recorded as liens against numerous IPA/DeRosa-related properties, and a Stipulation and Order restrained the sale of dozens of properties [#115][#188]. I did not, within budget, locate a notice of pendency recorded specifically against 183 Mark Tree Rd. By contrast, other Prowess searches in this corpus expressly flag such encumbrances (e.g., one report notes "NOTICE OF PENDENCY OF ACTION RECORDED 05/17/2022" [#131]) — the 183 Mark Tree Rd report contains no such notation, which is consistent with the "No open mortgage/judgment/liens found" remark [#70].

**Recommendation.** Treat the 05/26/2026 Prowess Full Search as operative: it reports no open mortgages, no liens, and no judgments encumbering the parcel, only paid 2025 taxes [#69][#70][#2]. Before any sale/refinance, order a certified continuation search confirming (a) the Joanne Rivera traffic judgments do not attach to her 10% interest and (b) the property is not subject to any MangoTree-litigation notice of pendency.

— Provenance: 199 sources across {'title_report': 108, 'email_body': 3, 'attachment': 88} | corpora {'unknown': 199} | mode=analysis | date span 2020-06-16 → 2026-06-01 | facts verified 13/13

---

### Q3. Give me the chronological timeline of 183 Mark Tree Rd, Centereach.
- **Property:** 183 Mark Tree Rd, Centereach (ent_prop_0200468000500010000) · is_david=True
- **Ground truth:** owners=['183Ma Llc', 'JOANNE RIVERA'] · facts={'chain_of_title': 6, 'mortgages': 21, 'liens': 1, 'lis_pendens': 10, 'judgments': 21, 'assignments': 6} · events=66 · findings=[]
- **Verification:** KEPT_ORIGINAL · facts=21 verified=20 · sources={'title_report': 48, 'email_body': 1, 'attachment': 92}
- **Answer:**

Here is the chronological deed/title timeline for **183 Mark Tree Rd, Centereach, NY 11720** (Suffolk County; Parcel ID 0200-468-00-05-00-010-000), as established by the Prowess Title Abstracts full search dated 05/26/2026 (effective date 05/16/2026) [#1].

**1975–1977 (earliest record).** The chain of title traces back to deeds in the WALTERS family — a deed recorded 4/8/1975 (D00005837/569) and a prior deed recorded 7/11/1977 (Liber 8266, Page 263), from WALTERS FRANCE… to WALTERS, KENNE… (image not available) [#113][#139].

**1990s — Walters estate to Atkinson.** Following the death of Frances Elizabeth Walters (who died intestate on August 17, 1993), Mary Ortner, as Administrator of the Estate of Frances Elizabeth Walters, conveyed the property by Administrator's Deed dated 9/23/1993, recorded 10/7/1993 (Book/Page 11647/206), to **James Atkinson and Hazel Atkinson, his wife**, for consideration of **$80,000.00** [#113].

**2001 — Atkinson to Mignanelli.** James Atkinson and Hazel Atkinson conveyed the property by deed dated 8/13/2001, recorded 10/2/2001 (D00012144/744), to **Fred Mignanelli and Anna Mignanelli, as Joint Tenants with Right of Survivorship**, for consideration of **$144,000.00** [#1][#120].

**2006 — Mignanelli to Haberland.** Fred Mignanelli and Anna Mignanelli conveyed the property to **James Haberland** by deed dated 1/30/2006, recorded 2/2/2006 (Book/Page 12434/138), for consideration of **$383,250.00**. The deed recites the Mignanellis residing at 183 Mark Tree Road, Centereach, and James Haberland residing at 40 Asbury Avenue East, Westbury, NY [#1][#119].

**2014–2016 — Haberland estate to Joy Rivera.** James Haberland died on August 1, 2014. Joy Rivera, as Executor of the Last Will and Testament of James Haberland, conveyed the property by Executor's Deed dated 6/22/2016, recorded 7/14/2016 (Book/Page 12871/420), to **Joy Rivera**, for nominal consideration of $10.00 [#1][#131].

**2018 — Death of Joy Rivera.** Joy Rivera died on 04/29/2018, as reflected in the current vesting [#1].

**2024 — Estate of Joy Rivera to 183MA LLC.** By deed dated 8/5/2024, recorded 8/6/2024 (Book/Page 13258/570), Joanne Rivera, as Administrator to the Estate of Joy Rivera (deceased 04/29/2018), conveyed an interest to **183MA LLC**, for consideration of **$2,500.00** [#1].

**Current vesting (as of the 2026 search).** Title is held by **183MA LLC, as to a 90% interest, and Joanne Rivera, as Administrator to the Estate of Joy Rivera, deceased 04/29/2018, as to a 10% interest** [#1]. The 2025 property taxes were paid (1st Half $6,138.49; 2nd Half $6,138.48) [#1].

**Renovation activity (2020).** During the MangoTree/IPA holding period, the property was the subject of renovation work — a 6/16/2020 check request lists "K&V Home Improvements Inc. - $350 for 183 Mark Tree Rd, Centereach" [#4].

**Caveats / gaps.** The title report also lists numerous interim mortgages, satisfactions, assignments and a 1991 judgment (NY State Higher Education Services v. Rivera) within the historical index, but several of those index entries are truncated/abbreviated in the record and their amounts are not stated, so I have not asserted them as discrete dated events beyond the deed chain above. Also note one ambiguous figure: chunk [#112]/[#131] shows a "Deed Amount: $1,534,000.00" on a Suffolk County recording/endorsement page associated with this parcel — this does not match the $10.00 / $383,250 consideration figures and may be an OCR or indexing artifact; I flag it rather than treat it as a true sale price. The transfer-tax page at [#112] also shows a transfer tax of $1,534.00 (consistent with a ~$383,250 sale, not $1.5M). Treat the deed-chain consideration figures from the vesting summary [#1] as the operative values.

— Provenance: 141 sources across {'title_report': 48, 'email_body': 1, 'attachment': 92} | corpora {'unknown': 141} | mode=analysis | date span 2012-03-19 → 2026-05-26 | facts verified 20/21

---

### Q4. Are there any suspicious or voidable transfers involving 183 Mark Tree Rd, Centereach?
- **Property:** 183 Mark Tree Rd, Centereach (ent_prop_0200468000500010000) · is_david=True
- **Ground truth:** owners=['183Ma Llc', 'JOANNE RIVERA'] · facts={'chain_of_title': 6, 'mortgages': 21, 'liens': 1, 'lis_pendens': 10, 'judgments': 21, 'assignments': 6} · events=66 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=15 verified=15 · sources={'title_report': 42, 'attachment': 93, 'email_body': 1}
- **Answer:**

Yes. The title chain for 183 Mark Tree Rd, Centereach (Suffolk County Parcel ID 0200-468-00-05-00-010-000) contains transfers that bear classic badges of suspicious/voidable conveyance — most notably a deeply below-market, intra-control transfer to a DeRosa-style single-purpose LLC for nominal consideration, recorded years after it was executed.

**The 2024 transfer to 183MA LLC for $2,500.** The Prowess Title Abstracts full search (effective 05/16/2026) shows the current vesting owner is "183MA LLC, AS TO A 90% INTEREST AND JOANNE RIVERA, AS ADMINISTRATOR TO THE ESTATE OF JOY RIVERA, DECEASED 04/29/2018, AS TO A 10% INTEREST" [#94]. The operative deed — Joanne Rivera, as Administrator to the Estate of Joy Rivera, to 183MA, LLC [#100] — has a Document Date of 8/5/2024, a Recording Date of 8/6/2024, and a stated Consideration of only $2,500.00 (Book/Page/Doc ID 13258/570) [#94][#1]. A grant of a 90% interest in an improved single-family residence for $2,500 is facially well below reasonably equivalent value. Notably, the recording-and-endorsement page for that same instrument (Liber D00013258, Page 570, Transfer Tax Number 24-00627) records a "Deed Amount" of $28,500.00 [#1] — itself inconsistent with the $2,500 consideration stated on the deed [#94], a discrepancy that warrants scrutiny.

**The 2016 transfer for $10.** The prior deed in the chain is even more suggestive: Joy Rivera, as Executor of the Last Will and Testament of James Haberland (who died on August 1, 2014), conveyed the property with a Document Date of 6/22/2016 and Recording Date of 7/14/2016 for a Consideration of $10.00 (Book/Page/Doc ID 12871/420) [#94]. Separately, a deed instrument in the same title file recites a "Deed Amount: $1,534,000.00" for parcel 0200 468.00 05.00 010.000 [#3][#104] — a figure wildly out of line with both the $10 nominal consideration and the modest assessed value, and a hallmark of a transfer whose stated value does not reflect an arm's-length sale.

**Connection to the DeRosa/IPA enterprise.** The property is not a stray parcel — it sits inside the DeRosa/IPA Asset Management operation that is the subject of the fraudulent-transfer litigation in this file. A June 16, 2020 IPA "Check Requests" email (from latias@ipellc.net to Rakesh Bhargava) directs payment of "$350 for 183 Mark Tree Rd, Centereach" to K&V Home Improvements [#72], and the attached renovation scope describes gutting the house ("Remove all of the contents in the entire house, 2 floors, basement & garage, Demo finished basement, Demo entire 1st floor, demo shed & 2 extentions") [#97] — the same renovate-rent-and-hold pattern the complaints attribute to DeRosa's affiliated entities. The broader record establishes that DeRosa and his affiliates "were engaging in fraudulent transfers, including the fraudulent transfer of the Premises, with the actual" intent alleged [#7], that assets were routinely transferred to newly-formed single-purpose LLCs for nominal consideration such as "$10.00" without reasonably equivalent value [#12][#83], and that such transfers "violated New York's fraudulent transfer laws" [#10][#9].

**Why these may be voidable.** Under New York's Debtor and Creditor Law (DCL Article 10), conveyances made "without fair consideration" are constructively fraudulent regardless of intent [#21][#73], and conveyances made with "actual intent to defraud" creditors are likewise voidable [#9][#10]. The 183 Mark Tree Rd transfers exhibit several recognized badges of fraud: nominal/grossly inadequate consideration ($10 in 2016; $2,500 for a 90% interest in 2024), transfer into an opaque single-purpose LLC ("183MA LLC") matching DeRosa's documented modus operandi [#88], a long gap between an estate-fiduciary's authority and the actual conveyance, and internal value discrepancies ($2,500 vs. $28,500; $10 vs. $1,534,000) across the recorded instruments [#94][#1][#3].

**Gaps / caveats.** I could not, within budget, isolate a verbatim quote tying 183MA LLC's membership directly to DeRosa, or confirm whether a creditor judgment was docketed against the specific grantor before these transfers (the elements needed to fully establish a DCL §273/273-a claim as to this parcel). I also could not reconcile the $2,500-vs-$28,500 and $10-vs-$1,534,000 discrepancies, which should be verified against the underlying recorded deeds. Subject to those gaps, the 2016 ($10) and 2024 ($2,500) conveyances of 183 Mark Tree Rd are facially suspicious and plausibly voidable as fraudulent transfers under DCL Article 10, and merit a full asset-tracing workup.

— Provenance: 136 sources across {'title_report': 42, 'attachment': 93, 'email_body': 1} | corpora {'unknown': 136} | mode=analysis | date span 2018-10-25 → 2026-06-01 | facts verified 15/15

---

### Q5. Who owns 59 Beecher Avenue, East Islip and is it connected to David DeRosa or his network?
- **Property:** 59 Beecher Avenue, East Islip (ent_prop_0500322000100012000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'CAROL MARTINEZ'] · facts={'chain_of_title': 5, 'mortgages': 6, 'liens': 5, 'lis_pendens': 10, 'judgments': 24, 'assignments': 2} · events=38 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=14 verified=14 · sources={'title_report': 160, 'attachment': 104, 'email_body': 43}
- **Answer:**

**Owner: IPA Asset Management, LLC — squarely within David DeRosa's network.**

**Who owns 59 Beecher Avenue, East Islip, NY 11730.** The record (tax map parcel 0500-322.00-01.00-012.000) shows the property is vested in **IPA Asset Management, LLC**. A recorded Bargain and Sale Deed runs from **ERIC J. MARTINEZ to IPA ASSET MANAGEMENT, LLC** for the Town of Islip parcel at 59 Beecher Avenue [#114]. A ProTitleUSA Current Owner Search confirms the "Grantee(s)/Deed Owner | IPA ASSET MANAGEMENT LLC | Deed Date | 10/07/2015" with grantor "ERIC J MARTINEZ AS TO 50%" interest, at a sale price of $10,000 [#252]. The prior chain of title shows Eric and Carol Martinez had acquired the property from Barbara Ciarfello in 2005 [#252]. A later (2022) title report lists the owner field as "CAROL MARTINEZ AND IPA ASSET MANAGEMENT LLC," reflecting that IPA took title to the Martinez interest while a Martinez interest remained of record [#188].

**Connection to David DeRosa and his network — strong and direct.**

1. *Common control.* IPA Asset Management, LLC is one of the "DeRosa Parties." DeRosa personally executes agreements "on behalf of Island Properties & Associates, LLC" [#18], and Rosenberg Calica & Birney LLP appears as "Attorneys for David D. DeRosa, Island Properties & Associates, LLC, IPA Asset Management, LLC, IPA Asset Management III, LLC..." [#87]. A Notice of Default was sent to "David D. DeRosa, 45 Sarah Drive, Farmingdale, New York 11735" addressing the cluster of entities including "Island Properties & Associates, LLC / IPA Asset Management, LLC / IPA Asset Management III, LLC" [#33]. IPA "and its related companies are real estate holding companies" [#43].

2. *Same address.* The 59 Beecher deed directs that it be returned "RETURN BY MAIL TO: IPA ASSET MANAGEMENT, LLC, 45 SARAH DRIVE, FARMINGDALE, NY 11735" [#114] — the very same 45 Sarah Drive address used for David DeRosa and his entities in the default notice [#33].

3. *Operational/financial activity by the IPA office.* Internal IPA emails about "IPL # 47690 - 59 Beecher Ave, East Islip, NY" direct payments tied to the property — e.g., "Please issue a check to IPA Asset Management III, LLC in the amount of $10K as an investment in this rental property" [#98] and "Please issue a check to Polluki Construction in the amount of $8,000 as an additional rehab payment" [#27], showing the DeRosa/IPA office managing and funding the property as a rental/rehab investment.

4. *Litigation footprint.* 59 Beecher Avenue appears on "Exhibit A" of properties in the MangoTree v. DeRosa litigation — "59 Beecher Ave, East Islip, NY" is listed among the DeRosa-related funding properties [#103].

**Bottom line:** 59 Beecher Avenue is owned of record by IPA Asset Management, LLC (which took the Martinez interest via deed dated 10/07/2015) [#114][#252]. IPA Asset Management is one of David DeRosa's controlled entities — sharing his counsel, his 45 Sarah Drive Farmingdale address, and appearing in the MangoTree v. DeRosa litigation property schedule — so the property is firmly connected to David DeRosa and his network [#18][#33][#87][#103][#114].

— Provenance: 307 sources across {'title_report': 160, 'attachment': 104, 'email_body': 43} | corpora {'unknown': 307} | mode=analysis | date span 2012-03-20 → 2026-05-07 | facts verified 14/14

---

### Q6. What mortgages, liens, or judgments are recorded against 59 Beecher Avenue, East Islip?
- **Property:** 59 Beecher Avenue, East Islip (ent_prop_0500322000100012000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'CAROL MARTINEZ'] · facts={'chain_of_title': 5, 'mortgages': 6, 'liens': 5, 'lis_pendens': 10, 'judgments': 24, 'assignments': 2} · events=38 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=12 verified=12 · sources={'title_report': 204, 'attachment': 116, 'email_body': 7}
- **Answer:**

Based on the title reports of record for **59 Beecher Avenue, East Islip, NY 11730** (Suffolk County Parcel ID 0500-322.00-01.00-012.000), the following encumbrances appear:

**MORTGAGE (the principal encumbrance — now in foreclosure).** There is one open mortgage of record, given by Eric Martinez and Carol Martinez, signed 10/12/2005, in favor of Long Beach Mortgage Company, recorded 10/25/2005 in Book/Page 21157/911 [#130]. That mortgage was subsequently assigned to Deutsche Bank National Trust Company, as Trustee for Long Beach Mortgage Loan Trust 2006-WL2, recorded 09/05/2006 in Book/Page 21375/916 [#131]. The mortgage went into foreclosure: a Lis Pendens (Notice of Pendency) under Index No. 601308/2015 was filed by Deutsche Bank National Trust Company against Carol Martinez and recorded 02/10/2015 [#116][#131], with a further lis pendens recorded 5/6/2015 under the same index number [#118].

**FORECLOSURE JUDGMENT.** The most recent (2026) title update confirms the foreclosure has proceeded to judgment. The Prowess Title update dated 05/07/2026 lists three operative recordings: (1) an "Order confirming Referee Report and Judgment of Foreclosure and Sale recorded 6/15/2022 in 15 601308"; (2) a "Stipulation and Order recorded 08/02/2022 in 13167/300"; and (3) an "Amended Judgment of Foreclosure and Sale recorded 12/1/2025 in 15 601308" [#5]. This means the Long Beach/Deutsche Bank mortgage has been reduced to an amended judgment of foreclosure and sale as recently as December 1, 2025.

**JUDGMENTS AND LIENS against Eric Martinez (a prior co-owner).** The ProTitleUSA reports flag a senior non-mortgage lien and several civil judgments indexed against Eric/Erick Martinez. Specifically:
- A MUNI LIEN (Muni/City/Code Lien) by the Town Supervisor against Eric Martinez under index BATO 12 00272, recorded 08/31/2012, in the amount of $150.00 — this is the lien the report's alert note specifically highlights ("See lien BATO 12 00272") [#132][#217].
- A JUDGMENT (Civil Judgment) by the People of the State of New York against Eric Martinez, recorded 09/27/2012, in the amount of $840.00 [#132].
- A JUDGMENT by Teachers Federal Credit (Union) against Erick Martinez under index CV 004864 14 CE, recorded 10/02/2014, in the amount of $933.22 [#132].
- Additional district-court / People-of-the-State transcript judgments appear in the indexed debtor record for Eric/Erick Martinez (e.g. Index CV 00486414 CE, $669.06 perfected 10/2/2014 [#1]; Index CV 00013416 BA, judgment $3,314.10 / total $3,489.10 perfected 11/16/2016 [#83]; Index BATO 12 00272, $150.00 perfected 8/31/2012 [#84]).

**OWNERSHIP NOTE / CAVEAT.** Title vested in IPA Asset Management LLC by deed from Eric J. Martinez (as to a 50% interest) dated 10/07/2015, recorded 03/08/2016 (Book 12855, Page 318), with Carol Martinez retaining the other interest [#130][#217]. The judgments above are docketed against the individual Martinez debtors rather than IPA, and the title reports classify them under "NONMTGLN: Possible senior non-mortgage lien recorded" [#132] — i.e., the title examiner flagged them as possible (name-match) liens requiring confirmation, not confirmed money liens on the parcel.

**GAPS / LIMITATIONS.** I was not able to confirm from the chunks reviewed the original principal dollar amount of the Long Beach mortgage or the dollar amount of the amended judgment of foreclosure and sale; the reports list the mortgage line but the specific original-amount figure for this parcel was not captured in the quoted text. The judgment amounts above are drawn from the ProTitleUSA "Active Judgments and Liens" table and the Suffolk County judgment-index entries, which are name-indexed against Eric/Erick Martinez and should be confirmed against current county records before closing or sale, particularly given the December 1, 2025 amended judgment of foreclosure.

— Provenance: 327 sources across {'title_report': 204, 'attachment': 116, 'email_body': 7} | corpora {'unknown': 327} | mode=analysis | date span 2015-10-06 → 2026-05-23 | facts verified 12/12

---

### Q7. Give me the chronological timeline of 59 Beecher Avenue, East Islip.
- **Property:** 59 Beecher Avenue, East Islip (ent_prop_0500322000100012000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'CAROL MARTINEZ'] · facts={'chain_of_title': 5, 'mortgages': 6, 'liens': 5, 'lis_pendens': 10, 'judgments': 24, 'assignments': 2} · events=38 · findings=[]
- **Verification:** VERIFIED_AFTER_RETRY · facts=23 verified=23 · sources={'title_report': 424, 'email_body': 24, 'attachment': 105, 'insurance': 15}
- **Answer:**

Here is the chronological timeline for **59 Beecher Avenue, East Islip, NY 11730** (Suffolk County tax map / Parcel ID 0500-322.00-01.00-012.000):

**October 12, 2005 — Acquisition by the Martinezes.** Barbara Ciarfello (grantor) conveyed the property to Eric Martinez and Carol Martinez by Bargain and Sale Deed dated October 12, 2005 [#1]. The deed was recorded October 25, 2005 in Book 12416, Page 334, at a stated sale price of $430,000.00 [#336].

**October 12, 2005 — Mortgage to Long Beach Mortgage Company.** Concurrently, Carol Martinez (a/k/a Carol L. Martinez) and Eric Martinez (a/k/a Eric J. Martinez) gave a mortgage to Long Beach Mortgage Company "on
October 25, 2005." [#83].

**August 7, 2006 / September 5, 2006 — Mortgage assignment.** "Thereafter said mortgage was assigned to the Plaintiff by assignment of mortgage bearing date August 7, 2006 and recorded under Liber M00021375 of Mortgages at Page 916 in the County of Suffolk on September 5, 2006" [#83]. The foreclosing plaintiff is identified as Deutsche Bank National Trust Company [#365].

**February 9–10, 2015 — Foreclosure commenced / first Lis Pendens.** A foreclosure action (Index No. 15 601308) was commenced; the notice of pendency was dated February 9, 2015 [#84], and a Lis Pendens was recorded 2/10/2015 under Index Number 15 601308 with plaintiff Deutsche Bank National Trust Company and defendant Carol Martinez [#365]. A further Lis Pendens was recorded 5/6/2015 [#366].

**October 6–7, 2015 — IPA acquires an interest / investment.** On October 6, 2015 an instruction issued to cut a $10K check to IPA Asset Management III, LLC "as an investment in this rental property" [#70]. The deed records show IPA Asset Management LLC took title with a Deed Date of 10/07/2015 from "ERIC J MARTINEZ AS TO 50% INTEREST," recorded 03/08/2016 in Book 12855, Page 318, with a sale price of $10,000.00 [#336]. Internal schedules list the 59 Beecher purchase/closing date as 2015-10-07 [#549].

**October–December 2015; 2017 — Rehab and tenant turnover spending.** Rehab payments to Polluki Construction were directed: $8,000 on 10/19/2015 [#69] and $5,000 on 11/12/2015 [#20]. In December 2017, $4,316 was paid to Polluki Construction for painting and repairs [#17] and $500 to Steve Mac, Inc. as an asset-manager fee to prepare the house for the next tenant [#71].

**February 8, 2018 — Additional Lis Pendens.** A further Lis Pendens in the same foreclosure (Index No. 601308/2015) was recorded 2/8/2018 [#6][#367].

**February 4, 2021 / February 25, 2021 — Title search (ProTitleUSA).** A current-owner title search (Order #687670) indexed 02/04/2021 and completed 02/25/2021 vested title in IPA Asset Management LLC and flagged a possible senior non-mortgage lien [#336].

**June 15, 2022 — Judgment of Foreclosure and Sale.** "Order confirming Referee Report and Judgment of Foreclosure and Sale recorded 6/15/2022 in 15 601308" [#2].

**August 2, 2022 — Stipulation and Order.** "Stipulation and Order recorded 08/02/2022 in 13167/300" [#2], consistent with the recorded instrument in Liber D00013167, Page 300 [#5].

**October 28, 2024 / December 1, 2025 — Amended Judgment of Foreclosure and Sale.** A Referee's Report by Francesco P. Tini dated October 28, 2024 showed "the sum of $646,885.70 due as of May 04, 2023" [#388]. An "Amended Judgment of Foreclosure and Sale recorded 12/1/2025 in 15 601308" followed [#2].

**2025/2026 — Current status.** As of the most recent Prowess update search (effective 04/27/2026), the parcel's 2025 taxes ($13,637.35) were paid, and the owner of record is "MARTINEZ CAROL & IPA ASSET MANAGEMENT" [#2].

**Gaps / caveats.** The original principal amount of the 2005 Long Beach mortgage is not stated verbatim in the chunks I reviewed. The exact recording date of the August 2, 2022 stipulation derives from the title-report remark [#2] cross-checked against the recorded Liber 13167/300 instrument [#5]. The 50%-interest deed language [#336] suggests title may have transferred in stages; I could not fully reconcile the Carol Martinez interest from the available chunks.

— Provenance: 568 sources across {'title_report': 424, 'email_body': 24, 'attachment': 105, 'insurance': 15} | corpora {'unknown': 568} | mode=analysis | date span 2012-05-07 → 2026-05-27 | facts verified 23/23

---

### Q8. Are there any suspicious or voidable transfers involving 59 Beecher Avenue, East Islip?
- **Property:** 59 Beecher Avenue, East Islip (ent_prop_0500322000100012000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'CAROL MARTINEZ'] · facts={'chain_of_title': 5, 'mortgages': 6, 'liens': 5, 'lis_pendens': 10, 'judgments': 24, 'assignments': 2} · events=38 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=13 verified=13 · sources={'title_report': 188, 'attachment': 127, 'email_body': 26, 'insurance': 15}
- **Answer:**

Yes. The corpus shows at least one transfer involving 59 Beecher Avenue, East Islip (Suffolk County parcel 0500-322.00-01.00-012.000) that bears classic badges of a suspicious / potentially voidable conveyance, and the property is enmeshed in the broader MangoTree/Marie Holdings fraudulent-transfer litigation against the DeRosa/IPA group.

1. The suspicious deed itself. A recorded Bargain and Sale Deed conveyed 59 Beecher Avenue, East Islip, NY 11730 from Eric J. Martinez to IPA Asset Management, LLC, 45 Sarah Drive, Farmingdale, NY 11735 [#2]. The ProTitle/Prowess title work confirms the grantor conveyed only "ERIC J MARTINEZ AS TO 50% INTEREST," with a deed date of 10/07/2015 and a recorded date of 03/08/2016 [#347]. The reported Sale Price was just $10,000.00 [#347] — and the recording stamp shows a nominal "Consideration Amount $ /0000" with the deed reciting "consideration of Ten Dollars and other valuable consideration" [#103]. By contrast, the prior arms-length deed into Eric and Carol Martinez (from Barbara Ciarfello, 10/12/2005) carried a sale price of $430,000.00 (full doc preview, sha 06acb76b…). A $10,000 transfer of a half-interest in a property the same record valued at $430,000 — to a DeRosa-affiliated LLC — is exactly the kind of below-market, insider transfer that supports a fraudulent-conveyance / voidable-transaction theory.

2. The transfer was made against an encumbered, distressed property. 59 Beecher was already subject to a 2005 Long Beach Mortgage Company mortgage (dated October 12, 2005, recorded October 25, 2005) [#39][#48], later assigned to Deutsche Bank National Trust Company [#11], with Carol and Eric Martinez as mortgagors [#38]. The property has been in active foreclosure (Index 601308/2015), with a Judgment of Foreclosure and Sale, a recorded Stipulation and Order (08/02/2022 in 13167/300), and an Amended Judgment of Foreclosure and Sale recorded 12/1/2025 [#5]. Transferring a half-interest into an IPA shell for $10,000 while the property was mortgaged and heading to foreclosure is a suspicious circumstance.

3. It sits inside an adjudicated fraudulent-transfer dispute. IPA Asset Management, LLC and David D. DeRosa are core defendants in the Suffolk County MangoTree action (MANGOTREE REAL ESTATE HOLDING, L.P. v. DAVID D. DEROSA, ISLAND PROPERTIES & ASSOCIATES, LLC, … IPA ASSET MANAGEMENT, LLC …) [#12], and 59 Beecher Avenue appears on the MangoTree global-settlement property schedules and MOU exhibits [#197][#195]. In the related Marie Holdings Inc. v. David DeRosa decision (Hon. Vincent J. Martorana, Index 200331/2022), the court records the plaintiff's assertion "that the property was conveyed without fair consideration, rendering its borrower insolvent" [#41] — the very fraudulent-conveyance framework (Debtor and Creditor Law) that would render such transfers voidable. That decision concerns a different premises but reflects the same pattern alleged across the DeRosa/IPA portfolio.

Bottom line / caveats: The single most concretely suspicious transfer for 59 Beecher is the 03/08/2016-recorded deed of Eric J. Martinez's 50% interest to IPA Asset Management, LLC for a stated $10,000 [#347][#2], far below the property's earlier $430,000 value and made while the property was mortgaged and in foreclosure. I have not located in the corpus a specific court ruling that declares the 59 Beecher deed itself void; the fraudulent-conveyance findings/allegations I can quote (e.g., the Marie Holdings decision) relate to the broader DeRosa/IPA scheme rather than to 59 Beecher by name [#41]. So the evidence supports treating the 59 Beecher transfer as suspicious and potentially voidable as a below-fair-consideration insider conveyance, but a property-specific avoidance adjudication is not established in the documents I reviewed. A targeted pull of the 59 Beecher deed instrument and any avoidance order would be the next step to confirm.

— Provenance: 356 sources across {'title_report': 188, 'attachment': 127, 'email_body': 26, 'insurance': 15} | corpora {'unknown': 356} | mode=analysis | date span 2015-01-14 → 2026-05-23 | facts verified 13/13

---

### Q9. Who owns 12 Mallard Path, Coram and is it connected to David DeRosa or his network?
- **Property:** 12 Mallard Path, Coram (ent_prop_0200316000900027000) · is_david=True
- **Ground truth:** owners=['HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION INC'] · facts={'chain_of_title': 11, 'mortgages': 5, 'liens': 12, 'lis_pendens': 8, 'judgments': 6, 'assignments': 7} · events=42 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=20 verified=20 · sources={'title_report': 48, 'attachment': 97, 'email_body': 9, 'insurance': 2, 'equity_schedule': 2}
- **Answer:**

**Owner of 12 Mallard Path, Coram, NY (Suffolk County, Parcel ID 0200-316.00-09.00-027.000):**

The most current title evidence — a Prowess Title Abstracts "Update Search" dated 05/14/2026, effective 05/04/2026 — shows that 12 Mallard Path is vested in **IPA ASSET MANAGEMENT LLC**. The deed chain reflects a Grantee of "IPA ASSET MANAGEMENT LLC," with a Document Date of 07/27/2017, from Grantor "HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION, INC.," recorded 01/02/2024, for a stated consideration of $479,000.00 (Book/Page/Doc ID 13231/52) [#1]. The same report lists 2025 taxes of $7,513.11 as Unpaid [#1]. So the record owner is IPA Asset Management LLC, having taken title out of the Hunt Club at Coram HOA following the HOA's foreclosure of the prior owner (Betty Dyber, whose 2008 reverse mortgage and inter-family deeds are documented in the chain) [timeline].

**Connection to David DeRosa and his network — Yes, strongly.**

IPA Asset Management LLC is squarely within the DeRosa network. In the *MangoTree / Marie Holdings* litigation pleadings, "Defendant David D. DeRosa ('DeRosa')…upon information and belief is the principal member and sole and/or majority owner of all the corporate defendants identified below" — and IPA Asset Management, LLC is named among those corporate defendants [#12][#133][#21]. The complaints also identify David DeRosa on his companies' website as the "President and Owner of Island Properties & Associates, LLC" [#17][#50]. IPA Asset Management, LLC is further confirmed as a DeRosa entity in the December 2025 criminal referral, which lists it as one of DeRosa's "Bankruptcy Entities" — "IPA Asset Management, LLC (Case No. 8-25-72526-spg)" — under the heading identifying David D. DeRosa as the subject [#18].

The property's operational ties to DeRosa's network are pervasive and independent of the title record:

- The asset was managed as part of the DeRosa/IPA portfolio. RLE Homes, LLC billed "Island Properties, LLC" a $2,000.00 Asset Manager Fee for "12 Mallard Path, Coram" (July 2017) [#3] and a $2,450.00 Rental Commission (Aug. 2017) [#7].
- Vendor invoices for the property were billed/shipped to "ISLAND PROPERTIES & ASSOCIATES" and "IPA Asset Management," e.g., Capuano Home Appliance (Ship To: Island Properties & Associates, 12 Mallard Path, Coram) [#8], Weismiller Plumbing (To: IPA Asset Management, work at 12 Mallard Path) [#60], Bay Carpet (Island Properties, 12 Mallard Path) [#59], and Ripley21 (Island Properties & Associates, 12 Mallard Path) [#64].
- HOA statements for the unit were addressed to "IPA Asset" at 45 Sarah Drive, Farmingdale [#65], the DeRosa-network business address.
- A 2017 IPA email shows "David approved the payment of $100 each" for the deed purchase of 12 Mallard Path among others, tying David DeRosa personally to acquisition decisions [#57].
- The property also appears entangled with MangoTree Real Estate Holdings, L.P.: MangoTree's property schedule lists "12 Mallard Path, Coram, NY" (Property ID 104229), purchase-closing 2017-06-20, with $80,392.70 MangoTree investment and $103,009.19 rent received [#140][#52], and the property appears on Exhibit A to the MangoTree v. DeRosa stipulation restraining sale of the portfolio properties [#10][#141]. MangoTree is the DeRosa-affiliated/disputed partnership at the center of the litigation, whose website contact is Diana DeRosa, "David DeRosa's sister" [#16].

**Bottom line:** 12 Mallard Path, Coram is record-owned by **IPA Asset Management LLC** (per the 05/14/2026 title update, vested via a deed from Hunt Club at Coram HOA recorded 01/02/2024 for $479,000.00) [#1]. IPA Asset Management LLC is a David DeRosa entity — pleadings name DeRosa as the principal member and sole/majority owner of the corporate defendants including IPA [#12][#133], and the criminal referral lists IPA Asset Management, LLC as one of his bankruptcy entities [#18]. The property was acquired, managed, insured, repaired, and rented through the Island Properties / IPA / MangoTree apparatus operated out of 45 Sarah Drive, Farmingdale [#3][#7][#8][#57][#65], so it is unambiguously connected to David DeRosa and his network.

— Provenance: 158 sources across {'title_report': 48, 'attachment': 97, 'email_body': 9, 'insurance': 2, 'equity_schedule': 2} | corpora {'unknown': 158} | mode=analysis | date span 2017-03-14 → 2026-05-27 | facts verified 20/20

---

### Q10. What mortgages, liens, or judgments are recorded against 12 Mallard Path, Coram?
- **Property:** 12 Mallard Path, Coram (ent_prop_0200316000900027000) · is_david=True
- **Ground truth:** owners=['HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION INC'] · facts={'chain_of_title': 11, 'mortgages': 5, 'liens': 12, 'lis_pendens': 8, 'judgments': 6, 'assignments': 7} · events=42 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=14 verified=14 · sources={'title_report': 206, 'attachment': 134, 'email_body': 16, 'insurance': 10}
- **Answer:**

Based on the title records, the Suffolk County Clerk records, and the most recent Prowess Title Abstracts update search (effective 05/04/2026, completed 05/14/2026), the following mortgages, liens, and judgments appear of record against 12 Mallard Path, Coram, NY (Tax Map / Parcel ID 0200-316.00-09.00-027.000):

**MORTGAGES (reverse mortgage chain — Dyber)**
The property is encumbered by a HUD reverse-mortgage encumbrance originating with prior owner Betty Dyber. Two related instruments were recorded on 07/07/2008 — a mortgage in favor of Financial Freedom Senior Funding Corp. (Book/Page 21728/110) and a reverse mortgage in favor of the Secretary of Housing and Urban Development (Book/Page 21728/111), each in the original amount of $450,000.00, both noted as "subject to HOA Deed" with a maturity date of 09/07/2080 [#9-timeline]. That mortgage was assigned through MERS/Financial Freedom to OneWest Bank, FSB, and ultimately by an assignment dated 02/21/2019 and recorded 06/25/2019 as Liber M00023037 Page 464 to Bank of New York Mellon Trust Company, N.A., as Trustee for Mortgage Assets Management Series I Trust [#95][#166]. The most recent Prowess search shows a further assignment dated 05/24/2024 (recorded 06/25/2024, Book/Page 23594/214) to Wilmington Savings Fund Society, FSB, solely as owner trustee for Cascade Funding Mortgage Trust HB3 [#2].

**LIS PENDENS / FORECLOSURE (notice of pendency)**
A foreclosure on the reverse mortgage was commenced. A Lis Pendens / Amended Notice of Pendency naming the Secretary of Housing and Urban Development, the United States (IRS), the New York State Department of Taxation and Finance, and the Dyber heirs as defendants was recorded in connection with that foreclosure (Suffolk County, recorded 09/24/2019, Book/Vol 427 Page 216) [#154][#153]. (Note: the underlying mortgage-foreclosure litigation history reflected in the docket includes OneWest Bank, FSB v. Brigitte L. Dyber et al. in Suffolk County Supreme Court [#169].)

**HOA / CONDOMINIUM LIEN(S)**
The Hunt Club at Coram Homeowners' Association recorded a Condominium Lien Plus Real Property against the unit. One such lien was filed 07/02/2015 (Lien Num LMIS00010705, Tax Map 0200-316.00-09.00-027.000) [#4], which was the predicate for the HOA's foreclosure action (the complaint names William Dyber, the Estate of Christine Dyber, and numerous Dyber heirs as defendants, "foreclosing a lien recorded on July 2, 2015") [#8]. The HOA later took title by Foreclosure Deed (recorded 09/08/2017, Book 12928/753, sale price $483,640.19) and ultimately conveyed to IPA Asset Management LLC [#3 protitle]. The 05/04/2026 Prowess update shows a further Condominium Lien Plus Real Property filed 12/22/2025 against the parcel [#54], and the Suffolk County tax/assessment portal shows an active lien on the parcel with a total balance of $7,513.11 and Case No. LMIS00027323, owner IPA Asset Management LLC [#53].

**JUDGMENT (District Court)**
A small judgment is recorded against debtor "DYBER CRISTINE J" at 12 Mallard Path: 1st District Court (Suffolk County) judgment, Index No. S11-000001691, in the amount of $75.00, perfected/filed 08/01/2014 [#3][#56].

**UNPAID REAL-PROPERTY TAXES**
The current Prowess search reports 2025 taxes of $7,513.11 as Unpaid, and the county portal flags the parcel as past due with an active lien (total balance $7,513.11) [#2][#53].

**IMPORTANT CAVEATS / GAPS**
I was not able to pull the full "Open Mortgages Information," "Active Judgments and Liens," and "Lis Pendens" summary tables of the operative 05/04/2026 Prowess report or the 2021/2022 ProTitleUSA reports (Orders 687699 and 832794) within my search budget, so this list may not be exhaustive and some recording specifics (e.g., the exact current foreclosure index/amount and any satisfactions/discharges) could not be fully verified. The $450,000 reverse-mortgage figures and assignment chain come from the ProTitleUSA title reports and the recorded assignment; the HOA condominium liens, the $75.00 District Court judgment, and the unpaid 2025 taxes ($7,513.11) are directly supported. You should confirm the precise present status of each encumbrance against the operative title report before relying on this summary.

— Provenance: 366 sources across {'title_report': 206, 'attachment': 134, 'email_body': 16, 'insurance': 10} | corpora {'unknown': 366} | mode=analysis | date span 2017-06-14 → 2026-06-07 | facts verified 14/14

---

### Q11. Give me the chronological timeline of 12 Mallard Path, Coram.
- **Property:** 12 Mallard Path, Coram (ent_prop_0200316000900027000) · is_david=True
- **Ground truth:** owners=['HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION INC'] · facts={'chain_of_title': 11, 'mortgages': 5, 'liens': 12, 'lis_pendens': 8, 'judgments': 6, 'assignments': 7} · events=42 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=30 verified=30 · sources={'title_report': 95, 'attachment': 71, 'email_body': 17, 'insurance': 9, 'equity_schedule': 6}
- **Answer:**

Here is the chronological timeline of **12 Mallard Path, Coram, NY 11727** (Suffolk County Parcel ID 0200-316.00-09.00-027.000 [#71]), reconstructed from the title reports, recorded instruments, and the property/expense ledgers in the file.

**Early chain of title (1986–1996).** The recorded deed chain shows conveyances from TBS Enterprise to Barone Alfred recorded 4/11/1986, a deed to Hunt Club Inc. recorded 3/2/1987 [#67/title chain], a deed to Goldstein Henry recorded 10/5/1987, an intra-family deed to Helen Goldstein recorded 11/13/1992, and a deed from Helen Goldstein to Linda Binder recorded 8/5/1996 (per the deterministic timeline).

**Dyber ownership and the reverse mortgage (2006–2008).** Betty Dyber conveyed to Betty Dyber and Christine Dyber by quitclaim deed dated 12/12/2006, recorded 02/07/2007 (Book 12491 / Page 193) [#5]. On 06/23/2008 Christine Dyber conveyed back to Betty Dyber (Book 12556 / Page 981), and the same day Betty Dyber gave a $450,000.00 reverse mortgage to Financial Freedom Senior Funding Corp / Secretary of Housing and Urban Development, recorded 07/07/2008 (Book/Page 21728/110 and 21728/111), with a maturity date of 09/07/2080 [#67-mortgage]. That mortgage was later assigned to OneWest Bank, FSB by assignment dated 6/11/2012, recorded 11/10/2012 in Liber 22267 at page 793 [#67].

**HOA liens and the OneWest foreclosure (2011–2015).** The Hunt Club at Coram HOA recorded condominium liens against the Dybers — including an 08/19/2011 lien for $3,102.50 and a 07/02/2015 lien for $15,552.50 [#153]. OneWest Bank, FSB commenced a mortgage foreclosure under Index No. 12-21090 and recorded a Notice of Pendency (Lis Pendens) on 13-Jul-2012 against "DYBER, BETTY ALL THE HEIRS" [#142].

**HOA foreclosure deed (2017).** The Hunt Club at Coram Homeowners Association foreclosed its lien and took title: a Foreclosure Deed dated 06/28/2017 from Usha Srivastava Esq. (referee) to Hunt Club at Coram Homeowners Association Inc., recorded 09/08/2017 (Book 12928 / Page 753), with a sale price of $483,640.19 [#155]. The recording stamp confirms "RECORDED 2017 Sep 08 10:12:00 AM JUDITH A. PASCALE CLERK OF SUFFOLK COUNTY L D00012928 P 753" [#148].

**IPA's acquisition and rehab (2017).** IPA Asset Management acquired the unit from the HOA. The 2026 Prowess title abstract shows the vesting deed to IPA Asset Management LLC with Document Date 07/27/2017, Grantor Hunt Club at Coram Homeowners Association, Inc., Consideration $479,000.00, Book/Page 13231/52 [#71]. The MangoTree property schedules list the "Purchase Closing Date" as 6/20/2017 with a total MangoTree investment of $80,392.70 [#50][#20], and there were sizable HOA-related closing payments — David approved a $100 "deed purchase" payment [#14] and a $29,000.00 bank check payable to Hunt Club at Coram HOA, Inc. was requested in July 2017 [#12]. Immediately after acquisition, IPA paid for a rehab: Weismiller Plumbing $325.88 (7/12/2017) [#21][#63], Bay Carpet $1,573.24 (carpet rip-up/install, 7/24/2017) [#53][#18], Capuano appliances $1,635.89 (invoice 7/28/2017) [#22][#57], an RLE Homes asset-manager fee of $2,000 for 12 Mallard Path [#17], and an RLE rental commission of $2,450 (8/15/2017) [#51][#56]. A title charge of $531.00 was paid to TGI Title Guarantee Inc. on 7/31/2017 [#58].

**Holding period, HOA charges, taxes, and the later foreclosure (2018–2026).** IPA continued to incur ongoing carrying costs — additional Bay Carpet flooring of $2,200 (June 2018) [#52], recurring Hunt Club HOA common charges of $280/month plus late fees [#11][#59], and insurance and repair charges through 2021 [#13][#64]. The 2020/2021 tax lien was sold 12/10/2021 to Suffolk County for $6,462.48 (certificate #1880) [#149]. The OneWest reverse-mortgage foreclosure re-emerged: the 2026 abstract records a new Lis Pendens by OneWest Bank FSB dated 06/28/2023 against Brigitte L. Dyber a/k/a Brigitte L. Astrin et al., and an assignment of the mortgage to Wilmington Savings Fund Society, FSB, as owner trustee for Cascade Funding Mortgage Trust HB3 (document date 05/24/2024, recorded 06/25/2024, Book/Page 23594/214) [#71]. As of the 05/14/2026 Prowess search, the 2025 taxes of $7,513.11 were unpaid [#71].

**Gaps/caveats.** Several early-1986–1996 conveyances come from the deterministic timeline's deed-index entries (recording dates), which I could not independently re-quote verbatim within budget, so I cite them at lower confidence. The exact contents of the renewed 2023 lis pendens (e.g., judgment amount) were not located, and the relationship between the OneWest reverse-mortgage foreclosure and IPA's HOA-foreclosure title remains a live title-defect issue flagged in the reports ("Subordinate HOA Lien Foreclosure Deed") [#155].

— Provenance: 198 sources across {'title_report': 95, 'attachment': 71, 'email_body': 17, 'insurance': 9, 'equity_schedule': 6} | corpora {'unknown': 198} | mode=analysis | date span 2016-02-08 → 2026-05-23 | facts verified 30/30

---

### Q12. Are there any suspicious or voidable transfers involving 12 Mallard Path, Coram?
- **Property:** 12 Mallard Path, Coram (ent_prop_0200316000900027000) · is_david=True
- **Ground truth:** owners=['HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION INC'] · facts={'chain_of_title': 11, 'mortgages': 5, 'liens': 12, 'lis_pendens': 8, 'judgments': 6, 'assignments': 7} · events=42 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=18 verified=18 · sources={'title_report': 141, 'attachment': 85, 'email_body': 7}
- **Answer:**

## Suspicious / Voidable Transfers Involving 12 Mallard Path, Coram (SCTM 0200-316.00-09.00-027.000)

There are several transactions in the chain of title for 12 Mallard Path that bear classic hallmarks of suspicious or potentially voidable transfers. The corpus does not contain a single court ruling voiding a deed for this specific parcel, but it does contain the underlying deed records, lien history, an unresolved title defect, and fraudulent-transfer pleadings against David DeRosa and his affiliated entities (Island Properties & Associates / IPA / MangoTree) that frame the analysis.

**1. The $100 "deed purchase" acquisition by DeRosa's enterprise.** The most directly suspicious item is an internal email dated August 23, 2017, in which "David approved the payment of $100 each for the following 2 properties: 1. 12 Mallard Path, Coram" [#64]. A $100 nominal consideration for residential real estate is a textbook badge of a transfer for less than fair/reasonably-equivalent value — the same type of grossly inadequate consideration the Marie Holdings litigation flags as fraudulent elsewhere (e.g., transfers "without adequate consideration (i.e., $10.00)" [#63]). Around this same period IPA/Island Properties paid the HOA $29,000 [#10] and treated 12 Mallard Path as an "Asset Manager Fee" property it controlled [#15][#21], consistent with the property being swept into DeRosa's portfolio.

**2. The HOA foreclosure deed — an unresolved title defect.** Title shows the vested owner is HUNT CLUB AT CORAM HOMEOWNERS ASSOCIATION INC, by a Foreclosure Deed dated 06/28/2017 from referee Usha Srivastava, Esq., recorded 09/08/2017, reciting a Sale Price of $483,640.19 [#91]. The 2021 ProTitleUSA report flags this as an unresolved defect: "URHFC: Subordinate HOA Lien Foreclosure Deed" plus a "Possible senior non-mortgage lien recorded" [#91]. An HOA-lien foreclosure that wipes title while a senior reverse mortgage remains open is precisely the kind of subordinate-lien foreclosure whose resulting deed is frequently challenged/voidable, because the HOA lien was junior to the mortgage. That foreclosure traces to HOA condo liens against the Dybers, including a lien of $15,552.50 dated 07/02/2015 [#94].

**3. A still-open senior reverse mortgage / pending foreclosure.** Betty Dyber granted a Financial Freedom / HUD reverse mortgage with an Original Amount of $450,000.00, expressly noted "MTG-HOA: Mortgage is subject to HOA Deed" [#93]. A separate reverse-mortgage foreclosure (Notice of Pendency of Action, Index No. 021090/2012, servicer PHH Mortgage) was filed against 12 Mallard Path [#5], with the mortgage later assigned to OneWest/Bank of New York Mellon [#2]. So the HOA's foreclosure deed (and any downstream transfer to DeRosa entities for $100) sits atop an unextinguished senior lien — making the title, and any conveyance out of the HOA, vulnerable.

**4. Inter-family deeds.** The chain also includes inter-family quitclaim deeds — Betty Dyber to Betty Dyber and Christine Dyber (Quitclaim Deed, Title No. X8844) [#4], recorded 02/07/2007 [#91], and Christine Dyber back to Betty Dyber in 2008 [#91]. Inter-family transfers for no stated consideration are commonly scrutinized, though here they appear tied to the reverse-mortgage qualification rather than creditor avoidance.

**5. Broader fraudulent-transfer context.** Marie Holdings, Inc. has sued DeRosa and affiliated entities alleging they were "engaging in fraudulent transfers... with the actual or constructive intent of hindering and delaying creditors" [#58], that transfers were "concealed from Plaintiff" and made "with the actual intent to defraud" in violation of "New York's fraudulent transfer laws" [#7][#231], and that DeRosa used single-purpose entities "to hold title the properties acquired through his fraudulent schemes" [#6]. While these counts are pleaded primarily about other parcels, they establish the pattern and the legal theories (DCL §§ 273–276) under which a $100 acquisition of 12 Mallard Path could be attacked.

**Bottom line.** Yes — there are at least two suspicious, potentially voidable features here: (a) the nominal $100 acquisition of the deed approved by DeRosa [#64], a transfer for grossly inadequate consideration; and (b) the HOA subordinate-lien foreclosure deed, flagged in the title report as an unresolved defect with a surviving senior reverse mortgage [#91][#93]. **Caveat / gap:** the corpus does not contain a recorded deed actually conveying 12 Mallard Path *out* of the HOA to an IPA/DeRosa entity, nor a judgment voiding any deed for this parcel. The $100 approval [#64] and IPA's expense-bearing/management activity [#15][#21] strongly imply such an acquisition, but the operative out-deed itself was not located in the available chunks.

— Provenance: 233 sources across {'title_report': 141, 'attachment': 85, 'email_body': 7} | corpora {'unknown': 233} | mode=analysis | date span 2017-03-14 → 2026-05-23 | facts verified 18/18

---

### Q13. Who owns 83 Ann Drive S, Freeport and is it connected to David DeRosa or his network?
- **Property:** 83 Ann Drive S, Freeport (ent_prop_6220351) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 5, 'mortgages': 5, 'liens': 9, 'lis_pendens': 23, 'judgments': 0, 'assignments': 3} · events=39 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=7 verified=7 · sources={'title_report': 85, 'attachment': 98, 'insurance': 13, 'equity_schedule': 7, 'email_body': 14}
- **Answer:**

**Owner of record: IPA Asset Management, LLC.** The current-owner title reports for 83 S Ann Drive / 83 Ann Drive South, Freeport, NY 11520 (Nassau County, Section 62, Block 203, Lot 51) show title vested in IPA Asset Management, LLC by a Bargain and Sale Deed dated 10/25/2016, with MangoTree Real Estate Holdings, L.P. as the grantor/prior owner [#175]. The same vesting appears in the earlier 2021 ProTitle report (Order# 687668) [#217], and a Prowess Title Abstracts update search dated 04/29/2026 was again run in the name of "IPA Asset Management LLC" for "83 Ann Drive S Freeport NY," confirming IPA remains the named owner as of 2026 [#91].

**Yes — it is directly connected to David DeRosa and his network.** IPA Asset Management, LLC is DeRosa's flagship entity: he is publicly identified as "President and Owner of Island Properties & Associates, LLC" and as the "Managing Partner" of IPA Asset Management, LLC [#86]. The property is explicitly listed as the first item on "Exhibit A" of the MangoTree Real Estate Holding, L.P. v. David D. DeRosa litigation (Nassau County Index No. 601314/2021), which names DeRosa, Island Properties & Associates, LLC, IPA Asset Management, LLC and numerous affiliated LLCs as defendants [#33][#5]. An early IPA quiet-title action over this exact property — IPA Asset Management, LLC v. U.S. Bank N.A., as Trustee for JPMMAC 2006-WMC4, regarding "83 Ann Drive South, Freeport, New York, 11520" — further ties the property into the DeRosa/IPA network [#10].

In short: 83 Ann Drive S is owned by IPA Asset Management, LLC, a David DeRosa-controlled entity, and the property sits squarely within his real-estate network and the MangoTree foreclosure litigation.

— Provenance: 217 sources across {'title_report': 85, 'attachment': 98, 'insurance': 13, 'equity_schedule': 7, 'email_body': 14} | corpora {'unknown': 217} | mode=analysis | date span 2012-06-07 → 2026-05-27 | facts verified 7/7

---

### Q14. What mortgages, liens, or judgments are recorded against 83 Ann Drive S, Freeport?
- **Property:** 83 Ann Drive S, Freeport (ent_prop_6220351) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 5, 'mortgages': 5, 'liens': 9, 'lis_pendens': 23, 'judgments': 0, 'assignments': 3} · events=39 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=16 verified=16 · sources={'title_report': 83, 'attachment': 70, 'insurance': 15, 'equity_schedule': 7, 'email_body': 11}
- **Answer:**

**Encumbrances of record against 83 Ann Drive S (a/k/a 83 South Ann Drive), Freeport, NY 11520 — Section 62, Block 203, Lot 51, Nassau County (Parcel ID 62-203-51).**

The most current and authoritative source is the Prowess Title Abstracts update search dated 04/29/2026 (effective through 04/27/2026), ordered in the name of IPA Asset Management LLC [#1]. It and the underlying foreclosure documents establish the following.

**1. Mortgage (the principal lien).** The property is encumbered by a mortgage dated September 29, 2006, made by Victor Pereira to WMC Mortgage Corp. in the original principal sum of $308,800.00, recorded October 11, 2006 in Liber 31074 of Mortgages at Page 756 in Nassau County [#186][#110]. That mortgage was assigned to U.S. Bank National Association, as Trustee for JPMMAC 2006-WMC4, by assignment dated August 6, 2009, recorded October 27, 2009 in Book 34301, Page 937 [#134]. The Prowess report reflects a further assignment to "U.S. Bank Trust Company, National Association, as Trustee, as successor-in-interest to U.S. Bank National Association, as Trustee, on behalf of the holders of the J.P. Morgan Mortgage Acquisition Trust 2006-WMC4 Asset Backed Pass-Through Certificates, Series 2006-WMC4," with a document date of 08/15/2025, Book/Page/Doc ID 48112/421, recorded 09/03/2025 [#1][#110].

**2. Judgment of Foreclosure and Sale.** The Prowess report's "Remarks" state: "1. JUDGMENT OF FORECLOSURE AND SALE RECORDED 03/20/2025 IN BOOK 1154 AND PAGE 25" [#1]. This is the operative judgment on the WMC/U.S. Bank foreclosure of the Pereira mortgage. The judgment recites that the property "is commonly known as 83 S. Ann Drive a/k/a 83 Ann Drive South, Freeport, NY 11520" [#124].

**3. Lis pendens / notices of pendency.** The foreclosure has a long history of recorded lis pendens against the Pereira mortgage by U.S. Bank/JPMMAC 2006-WMC4: an earlier notice of pendency under Ref# 08-016311 (Book L 1429) [#184], and a later one under Ref# 10-002241 (Book L 1578, Pages 184-187), both naming Victor Pereira as defendant and referring to the mortgage at Book M 31074, Page 756 [#170][#130]. Index No. 2241/10 was assigned to the foreclosure action [#133].

**4. Stipulation and Order (litigation encumbrance).** Separately from the foreclosure, a Stipulation and Order arising from the MangoTree Real Estate Holding, L.P. and Opportunity Zone RE 2019, LLC v. David D. DeRosa / IPA Asset Management, LLC et al. action (Nassau County Index No. 601314/2021) was recorded against the property. Counsel confirmed by email of 04/28/2022 that "the Stipulation and Order... has been recorded against 132 West 130th and 83 South Ann Drive" [#74]. The recorded instrument (Nassau County Instrument No. 2022-42480, recorded April 07, 2022, Bk-D Vl-14230 Pg-771) is an "Order in Deeds" listing 83 S Ann Drive S, Freeport as an Exhibit A property [#27][#35].

**5. Unpaid taxes.** The Prowess search also shows outstanding real-estate taxes (not a recorded lien per se but a charge against the property): 2026 School Tax 1st Half $3,822.72 (Unpaid) and 2nd Half $3,822.71 (Unpaid), and 2026 Town Tax 1st Half $402.48 (Unpaid) and 2nd Half $402.47 (Unpaid) [#1].

**Summary.** Recorded against 83 Ann Drive S are: (a) the 2006 WMC Mortgage Corp. mortgage of $308,800.00 (now held by the U.S. Bank/JPMMAC 2006-WMC4 trust) [#186][#1]; (b) a Judgment of Foreclosure and Sale recorded 03/20/2025 in Book 1154, Page 25 [#1]; (c) lis pendens filings in the foreclosure action [#170][#184]; and (d) the MangoTree/IPA Stipulation and Order recorded April 2022 (Index No. 601314/2021) [#74][#27]. Unpaid 2026 school and town taxes also burden the parcel [#1].

**Gaps / caveats.** I was not able to isolate a clean "Judgments — No Records Found / Liens — No Records Found" line specific to this parcel in the chunks available, so I cannot affirmatively state there are zero money judgments or general liens beyond those above; the Prowess report's affirmative disclosures (mortgage, judgment of foreclosure) are what is reliably documented. The exact current payoff/judgment dollar amount on the foreclosure judgment was not located in the retrieved chunks.

— Provenance: 186 sources across {'title_report': 83, 'attachment': 70, 'insurance': 15, 'equity_schedule': 7, 'email_body': 11} | corpora {'unknown': 186} | mode=analysis | date span 2012-06-07 → 2026-06-02 | facts verified 16/16

---

### Q15. Give me the chronological timeline of 83 Ann Drive S, Freeport.
- **Property:** 83 Ann Drive S, Freeport (ent_prop_6220351) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 5, 'mortgages': 5, 'liens': 9, 'lis_pendens': 23, 'judgments': 0, 'assignments': 3} · events=39 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=23 verified=23 · sources={'title_report': 47, 'attachment': 158, 'email_body': 14}
- **Answer:**

Below is the chronological timeline for 83 Ann Drive S (a/k/a 83 Ann Drive South / 83 S. Ann Drive), Freeport, NY 11520, Nassau County, Section 62 Block 203 Lot 51 [#1][#12][#107]. The history runs through several owners, a longstanding WMC/U.S. Bank mortgage foreclosure, MangoTree's deed acquisition, the MangoTree v. DeRosa litigation, and culminates in a 2025 judgment of foreclosure and sale.

**2006 — Pereira purchase and dual mortgages.** On 09/29/2006 (recorded 10/11/2006), Catherine Lang, George John Lang, Thomas Joseph Lang and Barbara M. LaRosa conveyed the property to Victor Pereira by Bargain and Sale deed for $386,000 [#timeline]. The same day Pereira granted two MERS/WMC Mortgage Corp. mortgages, one of $77,200.00 and one of $308,800.00, both recorded 10/11/2006 [#timeline].

**2008–2010 — Default and foreclosure begins.** A lis pendens (08-016311) was filed 08/29/2008 by U.S. Bank N.A., as Trustee for JPMMAC 2006-WMC4 against Pereira [#timeline]. The WMC mortgage was assigned to U.S. Bank N.A. as Trustee for JPMMAC 2006-WMC4 (dated 08/06/2009, recorded 10/27/2009) [#timeline]. A second lis pendens (10-002241) was filed 02/02/2010, again by U.S. Bank as Trustee, commencing the foreclosure action under Index No. 2241/10 [#timeline].

**2012 — MangoTree's deed acquisition.** IPA/IP&E analysed the deal in mid-2012 — the strategy memo states "We are purchasing the deed for $7500" with the property "about 2 years before a foreclosure" [#5]. On 06/07/2012, IPA Asset Management III was directed to issue a $7,500 check "for this property" [#96]. The deed was conveyed from HUN-NED PROOF LLC to MangoTree Real Estate Holdings, L.P. dated 06/08/2012 (recorded 06/03/2013), Bargain and Sale [#timeline]. The MangoTree master schedule lists 83 S Ann Drive (Property ID 67557), purchase closing 06/07/2012, as a "Deed purchase" [#99].

**2014–2017 — Rent and repairs.** The MangoTree job ledger records rent activity and repair/legal expenses on "83 S. Ann Dr." through this period (e.g., 2013–2014 rent entries and 2017 repair/collateral expenses) [#8][#101].

**2018 — Quiet-title action.** IPA Asset Management, LLC commenced a quiet-title action (IPA Asset Management, LLC v. U.S. Bank N.A., as Trustee for JPMMAC 2006-WMC4) regarding 83 Ann Drive South, serving the defendant on January 29, 2018 and filing on February 8, 2018, under court case 600889/2018 [#100][#98].

**2021–2022 — MangoTree v. DeRosa litigation.** 83 S Ann Drive S, Freeport is listed on Exhibit A of the MangoTree Real Estate Holding, L.P. and Opportunity Zone RE 2019, LLC v. David D. DeRosa et al. action, Index No. 601314/2021 [#19][#41]. A Stipulation and Order (resolving the OTSC/Motion for Provisional Relief) was So Ordered by Hon. Jerome C. Murphy on 14 February 2022 and entered by the Nassau County Clerk on Feb 16 2022 [#17]. That Order was recorded in deeds as Instrument 2022-42480, "ORDER IN DEEDS," recorded April 07, 2022 [#73]. Counsel confirmed by email (04/28/2022) that "the Stipulation and Order … has been recorded against 132 West 130th and 83 South Ann Drive" [#185].

**2023 — Settlement and discharge of pendency.** The parties entered a Settlement Agreement in July 2023 requiring mortgages to be recorded against the Exhibit D properties "on or before August 15, 2023, time of the essence" [#216]. In August 2023 counsel added the Schedule A legal description for 83 South Ann Drive [#186], and a Stipulation to Discharge the Notice of Pendency for 83 South Ann Drive (Section 62 Block 203 Lot 51) was prepared (Scan dated 09/01/2023) [#102].

**2025 — Judgment of Foreclosure and Sale.** The 04/29/2026 Prowess title update reflects that a Judgment of Foreclosure and Sale was recorded 03/20/2025 in Book 1154 Page 25, and an assignment to U.S. Bank Trust Company, N.A. (successor trustee for the JPMMAC 2006-WMC4 trust) was dated 08/15/2025 and recorded 09/03/2025 (Book/Page 48112/421) [#1]. The Nassau County Land Records search confirms a document (55477) recorded 9/3/2025 against Section 62 Block 203 Lot 51, Hempstead [#108]. The judgment order recites the property "commonly known as 83 S. Ann Drive a/k/a 83 Ann Drive South, Freeport, NY 11520" [#107]. As of the 04/29/2026 update, 2026 school taxes ($3,822.72 / $3,822.71) and town taxes ($402.48 / $402.47) remained unpaid [#1].

**Gaps:** Some recording details (e.g., the exact liber/page of the recorded Stipulation against 83 S. Ann) come from the index/cover sheet [#73] rather than a fully legible body; the foreclosure auction/sale completion date is not confirmed in the corpus. The dollar amounts for the MangoTree HUN-NED deed itself are not stated on the conveyance record (the $7,500 figure derives from the acquisition memo/check directive [#5][#96]).

— Provenance: 219 sources across {'title_report': 47, 'attachment': 158, 'email_body': 14} | corpora {'unknown': 219} | mode=analysis | date span 2012-01-13 → 2026-05-14 | facts verified 23/23

---

### Q16. Are there any suspicious or voidable transfers involving 83 Ann Drive S, Freeport?
- **Property:** 83 Ann Drive S, Freeport (ent_prop_6220351) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 5, 'mortgages': 5, 'liens': 9, 'lis_pendens': 23, 'judgments': 0, 'assignments': 3} · events=39 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=24 verified=24 · sources={'attachment': 93, 'title_report': 92, 'email_body': 7}
- **Answer:**

**Short answer:** Yes. The chain of title to 83 Ann Drive South (a/k/a 83 S. Ann Drive), Freeport, NY 11520 (Section 62, Block 203, Lot 51) contains several features that warrant scrutiny for being suspicious or potentially voidable as fraudulent / constructively-fraudulent conveyances under New York's Debtor-Creditor Law. The strongest indicators are (1) a "deed-stripping" acquisition strategy on a property the buyer knew was in active foreclosure, acquired for nominal value; and (2) a 2016 inter-company transfer for no stated consideration while a lis pendens/foreclosure was pending — the same pattern that an existing court found actionable as a fraudulent transfer in a related DeRosa matter.

**1. The 2012 "deed-for-$7,500" acquisition strategy.** David DeRosa's own financing-evaluator worksheets describe the deal in candid terms: "We are purchasing the deed for $7500, the property has about 2 years before a foreclosure, the tenant will continue to pay us $1500 a month" [#1][#84]. In other words, the deed was acquired for a token $7,500 [#76] on a property already encumbered by a $308,800 WMC mortgage (recorded 10/11/2006, Book M 31074 Pg 756) [#3][#9] that was in active foreclosure (lis pendens filed 08/29/2008 and again 02/02/2010 by U.S. Bank as trustee for JPMMAC 2006-WMC4) [#77]. DeRosa later acknowledged in correspondence that "The closing on this property was for $7500, and that is what the closing statement reflects, which was the purchase of the deed," and openly asked counsel whether it would be "cleaner on your books" to instead paper a contract "for the full amount" — language suggesting deliberate structuring of how consideration was documented [#160]. Acquiring a deed for nominal value subject to a senior foreclosure is itself a hallmark of distressed/deed-stripping activity.

**2. The 2016 transfer for no stated consideration.** The title reports show MangoTree Real Estate Holdings, L.P. conveyed to IPA Asset Management, LLC by a Bargain and Sale deed dated 10/25/2016, recorded 11/17/2016 (Instrument 2016-113843, Book 13438, Page 34) with the Consideration and Sale Price fields blank [#171][#116]. The prior link in the chain (HUN-NED PROOF LLC → MangoTree, deed dated 06/08/2012) likewise shows no consideration [#171]. A no-consideration inter-entity transfer is precisely the type of conveyance that can be set aside as constructively fraudulent under the Debtor-Creditor Law if made by a debtor against whom claims existed.

**3. Pattern evidence from the related litigation.** This property and these very actors appear in litigation expressly built on fraudulent-transfer theory. In *Marie Holdings, Inc. v. David DeRosa, et al.* (Suffolk Index No. 200331/2022), the court recognized a "cause of action for fraudulent transfer under Article 10 of the Debtor Creditor Law," alleging a conveyance "made without fair consideration" that is "constructively fraudulent regardless of intent pursuant to DCL 273-A" because it was made "by defendant against whom a judgment had been docketed" [#20][#66][#19]. The court's Decision/Order describes the action as arising "from an alleged fraudulent transfer of real property that occurred after entry of a judgment of foreclosure and sale" and "after the foreclosure sale had been scheduled, but prior to the sale being held," from the judgment debtor to an LLC "owned or controlled by the co-defendants" [#36][#49]. While that specific fraudulent-transfer holding concerns the 132 West 130th Street property, 83 S Ann Drive S, Freeport appears on the Exhibit A schedules of the DeRosa/MangoTree disputed properties [#15][#31][#178][#179], tying it to the same web of entities (DeRosa, IPA, MangoTree, Bhargava) whose transfers are under fraudulent-conveyance attack.

**4. Continuing status — foreclosure and tax distress.** The property remains entangled: a Judgment of Foreclosure and Sale is reflected in the 2026 Prowess title update, with the WMC mortgage assigned to U.S. Bank Trust Company, N.A. as successor trustee (assignment dated 08/15/2025, recorded 09/03/2025) [#80][#7]. Taxes are delinquent (2026 school and town halves all "Unpaid"), and a Tax-Sale lien posted 02/17/2026 [#80][#10]. IPA also listed the property among "IPA owned properties that need to be sent to Nassau County Sheriff" [#73][#175].

**Gaps / cautions.** The corpus does not contain a court order specifically declaring the 83 Ann Drive 2016 deed void; the fraudulent-transfer adjudications I located concern the related 132 West 130th property. The "suspicious" character of the Ann Drive transfers rests on (a) nominal/blank consideration, (b) acquisition knowing of pending foreclosure, and (c) membership in the same scheme litigated as fraudulent elsewhere. A definitive voidability determination for this parcel would require pleadings naming this specific deed. I flag this honestly.

— Provenance: 192 sources across {'attachment': 93, 'title_report': 92, 'email_body': 7} | corpora {'unknown': 192} | mode=analysis | date span 2012-06-07 → 2026-05-07 | facts verified 24/24

---

### Q17. Who owns 26 Appel Dr E, Shirley and is it connected to David DeRosa or his network?
- **Property:** 26 Appel Dr E, Shirley (ent_prop_0200974600400065000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 13, 'mortgages': 2, 'liens': 14, 'lis_pendens': 6, 'judgments': 2, 'assignments': 0} · events=31 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME', 'high:Insider conveyance to 26AP LLC']
- **Verification:** VERIFIED_AFTER_RETRY · facts=16 verified=16 · sources={'title_report': 58, 'attachment': 122, 'email_body': 27, 'equity_schedule': 1, 'insurance': 8}
- **Answer:**

**Owner of 26 Appel Dr E, Shirley, NY 11967.** The property (Suffolk County Parcel ID 0200-974-60-04-00-065-000) is currently vested in **26 AP LLC**. The most recent Prowess Title Abstracts update search (search dated 05/19/2026) lists the "Vesting Owner: 26 AP LLC" for "26 APPEL DR E, SHIRLEY, NY 11967" [#1]. The deed chain confirms the current vesting: "Grantee: 26 AP LLC Document Date: 11/06/2024 Grantor: IPA ASSET MANAGEMENT, LLC Recording Date: 11/08/2024 Consideration: $10.00 Book/Page/Doc ID: 13271/400" [#1]. An earlier (03-19-2025) title update likewise records "Vesting Owner: 26 AP LLC" with the same grantor/grantee chain [#162].

**Yes — the property is squarely connected to David DeRosa's network, in two ways:**

1. **Immediate prior owner is a core DeRosa entity (IPA Asset Management, LLC).** Before the November 2024 transfer to 26 AP LLC, title was held by IPA Asset Management, LLC, which conveyed the parcel to 26 AP LLC for nominal consideration of $10.00 [#1]. The 2024-04-22 full title search also shows "Vesting Owner: Ipa Asset Management Llc" for this address [#86]. IPA Asset Management, LLC is one of the DeRosa-affiliated entities: the MangoTree litigation names "DAVID D. DEROSA, ISLAND PROPERTIES & ASSOCIATES, LLC, DIANA DEROSA, IPA ASSET MANAGEMENT, LLC, IPA ASSET MANAGEMENT III, LLC, 31F0, LLC, 453F, LLC, 91G, LLC, LONG ISLAND INVESTMENTS, LLC" together as defendants [#21], and David DeRosa is identified as President and Owner of the IPA/Island operation [#150]. Historical operating records for the property also tie it to that group — e.g., a 2015 instruction to issue a check "to IPA Asset Management III, LLC in the amount of $45K as an investment in this property" for "26 Appel Dr E, Shirley, NY" [#68], and invoices billed to "ISLAND PROPERTIES" at "26 APPEL DR ... SHIRLEY" [#7].

2. **The transfer to 26 AP LLC is flagged as a suspected fraudulent conveyance within the DeRosa pattern.** The internal "IPA properties for sheriff sale" schedule (2024-09-23) lists "IPA ASSET MANAGEMENT LLC | 26 Appel Dr E | Shirley | NY | Suffolk | 0200-974-60-04-00-065-000" with substantial equity (≈$539,203.92) under the heading "IPA owned properties that need to be sent to Suffolk County Sheriff" [#4], [#32]. That same schedule repeatedly characterizes IPA's transfers to single-purpose, similarly-named LLCs as a deliberate equity-stripping pattern — "Fraudulent conveyance by IPA ... our Court order is dated prior to the conveyance of these properties which directly violates Stipulation and Order Section 1 which was entered on February 16, 2022" [#34] — and notes other parcels transferred to "an entity owned by David" or "an entity that David has ownership interest in" [#35], [#161]. The 26 AP LLC name follows the same naming convention DeRosa used for other property-holding shells (e.g., 18RU LLC for 18 Rugby Dr [#13], [#17]; 6Vin LLC; 230R LLC [#35], [#54]).

The judgment underlying the sheriff-sale effort runs against the DeRosa entity group, with the title report listing the judgment debtor as "91G LLC / IPA ASSET LLC / ISLAND PROPERTIES & ASSOCIATES LLC / 453F LLC / 31F0 LLC / IPA ASSET MANAGEMENT III LLC / IPA ASSET MANAGEMENT LLC" (Index No. 24 617567, JUDGMENT 7/19/2024) [#3], [#215]. David DeRosa is also the subject of a criminal referral alleging "Bankruptcy Fraud ... Deed Theft, Equity Stripping" tied to these entities [#146].

**Bottom line / caveats.** 26 Appel Dr E is owned of record by 26 AP LLC, which took title from IPA Asset Management, LLC (a DeRosa entity) on 11/06/2024 for $10.00 [#1]. The corpus does not contain a document expressly stating 26 AP LLC's membership/ownership, so I cannot quote a record naming David DeRosa as 26 AP LLC's member. However, the chain of title from IPA, the $10 nominal consideration, the IPA-network naming pattern, and the contemporaneous "fraudulent conveyance"/equity-stripping characterization strongly connect 26 AP LLC and this property to David DeRosa's network. That ownership-of-26-AP-LLC point is the one evidentiary gap worth confirming with corporate/Secretary-of-State or the recorded deed itself.

— Provenance: 216 sources across {'title_report': 58, 'attachment': 122, 'email_body': 27, 'equity_schedule': 1, 'insurance': 8} | corpora {'unknown': 216} | mode=analysis | date span 2012-04-25 → 2026-05-19 | facts verified 16/16

---

### Q18. What mortgages, liens, or judgments are recorded against 26 Appel Dr E, Shirley?
- **Property:** 26 Appel Dr E, Shirley (ent_prop_0200974600400065000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 13, 'mortgages': 2, 'liens': 14, 'lis_pendens': 6, 'judgments': 2, 'assignments': 0} · events=31 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME', 'high:Insider conveyance to 26AP LLC']
- **Verification:** KEPT_ORIGINAL · facts=20 verified=19 · sources={'title_report': 104, 'attachment': 133, 'email_body': 1}
- **Answer:**

**Recorded encumbrances against 26 Appel Drive East, Shirley, NY 11967 (Suffolk County; APN 0200‑974‑60‑04‑00‑065‑000)**

The property is owned by 26 AP LLC, which took title from IPA Asset Management, LLC by deed dated 11/06/2024, recorded 11/08/2024, Book/Page 13271/400 [#73]. The same parcel was previously vested in IPA Asset Management, LLC by deed recorded 08/26/2021 (Book/Page 13117/555) [#216]. The multiple title searches in the file — the 04/22/2024 Full Search [#1], the 03/19/2025 Update Search [#5], and the most recent 05/19/2026 Update Search [#7] — together establish what is and is not recorded against the parcel.

**1. Mortgages — NONE of record.** No open or active mortgage is reported against 26 Appel Dr E. The title abstractor's "Mortgage Information" section for the prior deed chain shows "No Op[en]" mortgages [#70], and the IPA sheriff‑sale worksheet for this property lists the mortgage/lien column as "0," with equity of $539,203.92 — i.e., the property is essentially unencumbered by any mortgage and is treated as full‑equity collateral [#28][#64]. (By contrast, neighboring IPA properties such as 91 W Shore Rd and 119 Hidden Ponds Cir are expressly flagged as having a "Mortgage on this property" [#28][#43] — 26 Appel is not.)

**2. Judgment — the Mangotree money judgment.** The principal recorded encumbrance is the money judgment obtained by Mangotree/Opportunity Zone against the IPA family of entities. The 03/19/2025 title update expressly identifies a "Judgment Debtor: Ipa Asset Management Llc" with a document/judgment date of 07/19/2024 [#2]. The judgment was docketed against "91G LLC / IPA ASSET LLC / ISLAND PROPERTIES & ASSOCIATES LLC / 453F LLC / 31F0 LLC / IPA ASSET MANAGEMENT III LLC / IPA ASSET MANAGEMENT LLC," reflected as Index/Doc "24 617567 JUDGMENT 7/19/2024" [#2]. The underlying judgment by confession was entered July 19, 2024 in Suffolk County in the amount of $9,088,171.33 [#179]. Because IPA Asset Management, LLC was the record owner of 26 Appel when the judgment was entered, that judgment attaches to this parcel, and the plaintiff has in fact scheduled 26 Appel Drive E for a Suffolk County Sheriff's sale to execute on it [#62][#170].

**3. Execution / Sheriff's sale levy.** 26 Appel Drive E is one of the specific properties the Sheriff was directed to expose for sale to satisfy the judgment (Sale #6, RP‑24008722) [#170], and the public‑venue sale notice describes the premises as "26 APPEL DRIVE E., SHIRLEY, NY 11967" [#6]. Westerman's invoice records an "8/28/24 Suffolk County Sheriff – Initial fee – sale of property – 26 Appel Drive E" [#186]. The judgment debtors have moved to dismiss/vacate that judgment and execution (motions filed 05/29/2025) [#62], so the enforcement is contested.

**4. Town of Brookhaven nuisance lien / tax lien.** The file also shows a Town of Brookhaven "Nuisance Notice" recorded against the premises [#4], tied to a 2019 Notice of Order for the property at "26 APPEL DR, SHIRLEY, NY 11967" [#176]. A Suffolk County Real Estate Lien Bill (Bill Year 2020, Bill 5311) shows a delinquent amount of $13,942.06 with interest, total $18,973.20, on the parcel while owned by "HARKIN CHARLES & ARRON C" [#67].

**5. Delinquent real‑estate taxes (a statutory lien).** All recent tax years are delinquent. As of the 05/19/2026 search: 2025 — $12,909.54; 2024 — $12,382.75; 2023 — $13,864.22; 2022 — $14,242.00; 2021 — $14,863.90; 2020 — $13,954.06, all "Delinquent" [#73].

**Summary / gaps:** No mortgage is recorded against 26 Appel Dr E. The encumbrances of record are (a) the $9,088,171.33 Mangotree money judgment of 07/19/2024 (Index 617567/2024) against IPA Asset Management, LLC, now being executed by Sheriff's sale [#2][#179][#62][#170]; (b) a Town of Brookhaven nuisance lien / tax‑lien bill [#4][#67]; and (c) multiple years of delinquent property taxes [#73]. I was unable in the budget to retrieve a verbatim "Active Judgments and Liens" schedule line item specific to 26 Appel from the 2025/2026 title abstracts beyond the judgment‑debtor entry quoted above; a certified copy of the docketed judgment and the recorded nuisance lien should be pulled to confirm exact recording dates and lien amounts.

— Provenance: 238 sources across {'title_report': 104, 'attachment': 133, 'email_body': 1} | corpora {'unknown': 238} | mode=analysis | date span 2020-07-13 → 2026-06-02 | facts verified 19/20

---

### Q19. Give me the chronological timeline of 26 Appel Dr E, Shirley.
- **Property:** 26 Appel Dr E, Shirley (ent_prop_0200974600400065000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 13, 'mortgages': 2, 'liens': 14, 'lis_pendens': 6, 'judgments': 2, 'assignments': 0} · events=31 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME', 'high:Insider conveyance to 26AP LLC']
- **Verification:** KEPT_ORIGINAL · facts=32 verified=31 · sources={'title_report': 94, 'attachment': 79, 'email_body': 23, 'insurance': 8, 'equity_schedule': 7}
- **Answer:**

Here is the chronological title and ownership history of **26 Appel Drive East, Shirley, NY 11967** (Suffolk County, Parcel ID 0200-974-60-04-00-065-000), drawn from the Prowess Title Abstracts deed chains and the MangoTree/IPA records.

**1985 – Early conveyances.** The deed index records a deed to Angelina Geraci recorded 7/31/1985, and a deed from Geraci to Eileen McNamara also recorded 7/31/1985 [#2].

**November 1993 – DeGraaff → P.G. Builders.** Eileen DeGraaff (formerly known as Eileen McNamara) conveyed to P.G. Builders, Inc. by a Bargain and Sale Deed dated 11/03/1993, recorded 11/22/1993, consideration $10.00, Book/Page 11652/729 [#9][#115].

**December 1993 / January 1994 – P.G. Builders → Cilibrasi.** P.G. Builders, Inc. conveyed to Charles A. Cilibrasi and Linda A. Cilibrasi, husband and wife, by deed dated 12/17/1993, recorded 01/12/1994, consideration $10.00, Book/Page 11659/773 [#87][#115].

**June 2007 – Cilibrasi → Harkin.** Charles A. and Linda C. Cilibrasi conveyed to Charles Harkin and Anron C. Harkin, as joint tenants with rights of survivorship, by deed dated 06/18/2007, recorded 06/27/2007, consideration $0.00, Book/Page 12511/176 [#115].

**2015 – IPA acquires (the "deed purchase").** Charles Harkin and Anron C. Harkin conveyed to IPA Asset Management LLC by deed dated 07/30/2015 (recorded later, 08/26/2021), consideration $10.00, Book/Page 13117/555 [#120]. This is consistent with the contemporaneous MangoTree/IPA acquisition activity in 2015: a $5,000 "deed purchase 26 Appel Dr E, Shirley" check request (8/5/2015) [#150], a $45K investment in the property (8/18/2015) [#21], starter and additional rehab checks to RJV Home Improvement of $7K, $4,900, $6,800 and $1,300 (Aug 2015–Jan 2016) [#82][#19][#77][#80], and an appliance purchase of $1,738 (9/30/2015) [#81]. The MangoTree settlement sheet logs an Acquisition Date serial of 42222 (≈ Mar 2015) [#6].

**2015–2018 – Rental & rehab period under IPA.** The property was rented (e.g., $1,950/month rents recorded through 2016–2017) [#11][#13] and carried ongoing repair, extermination, tree-trimming and electrical expenses (e.g., Cheap Charlie's $706.07 on 6/15/2017 [#17][#93], Solution Exterminating $744 [#78], Cantiague Electric $298.71 on 8/24/2018 [#18][#84], K&V Home Improvements work in 2020 [#85]).

**2020 – Sale recorded on IPA/MangoTree books.** The MangoTree "Schedule of due from IPA" books a "Sale of 26 Appel Dr E, Shirley, NY" of $96,750 dated 6/30/2020 [#79][#189]; the settlement sheet shows a Proceeds/Principle Return serial of 44012 (≈ Aug 2020) and a deal length of about 59 months [#6].

**August/September 2020 – Brookhaven tax lien.** A Town of Brookhaven tax matter against Charles Harkin and Anron C. Harkin was recorded 09/18/2020 in the amount of $639.57 (Book 13071) [#115].

**July 2024 – MangoTree judgment.** Mangotree Real Estate Holdings, L.P. and Opportunity Zone RE 2019, LLC obtained a judgment of $9,088,151.33 entered 07/19/2024 against IPA Asset Management LLC and affiliated entities (Index 617567/24), which became a judgment lien against this and other IPA properties [#68][#208][#97].

**November 2024 – IPA → 26 AP LLC.** IPA Asset Management, LLC conveyed to 26 AP LLC by deed dated 11/06/2024, recorded 11/08/2024, consideration $10.00, Book/Page/Doc ID 13271/400 [#1]. The current vesting owner is 26 AP LLC [#1].

**2025 – Sheriff sale / litigation.** The property (26 Appel Drive E) is listed among IPA properties scheduled for Suffolk County sheriff's sale in execution of the MangoTree judgment [#14][#20][#211].

**Tax status (as of the 5/19/2026 update search).** All annual taxes from 2020 through 2025 are shown delinquent: 2025 $12,909.54; 2024 $12,382.75; 2023 $13,864.22; 2022 $14,242.00; 2021 $14,863.90; 2020 $13,954.06 [#190].

**Gaps:** The corpus shows the 2020 "sale" only as a bookkeeping entry on IPA/MangoTree schedules ($96,750) [#79][#189]; the title record does not reflect a 2020 recorded conveyance out of IPA — IPA remained record owner until the 11/08/2024 deed to 26 AP LLC [#1]. The dates of some old deeds appear as recording-date index entries rather than execution dates.

— Provenance: 211 sources across {'title_report': 94, 'attachment': 79, 'email_body': 23, 'insurance': 8, 'equity_schedule': 7} | corpora {'unknown': 211} | mode=analysis | date span 2012-04-25 → 2026-05-19 | facts verified 31/32

---

### Q20. Are there any suspicious or voidable transfers involving 26 Appel Dr E, Shirley?
- **Property:** 26 Appel Dr E, Shirley (ent_prop_0200974600400065000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 13, 'mortgages': 2, 'liens': 14, 'lis_pendens': 6, 'judgments': 2, 'assignments': 0} · events=31 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME', 'high:Insider conveyance to 26AP LLC']
- **Verification:** VERIFIED_FIRST_PASS · facts=19 verified=19 · sources={'attachment': 100, 'title_report': 57, 'email_body': 23, 'insurance': 13, 'equity_schedule': 7}
- **Answer:**

Yes. There is a strong, well-documented suspicion that the November 6, 2024 conveyance of 26 Appel Dr E, Shirley, NY (parcel 0200-974-60-04-00-065-000) from IPA Asset Management, LLC to 26 AP LLC is a voidable / fraudulent transfer.

**The suspect transfer.** The Prowess title abstract (search dated 05/19/2026) shows the operative vesting deed for 26 Appel Dr E: Grantee "26 AP LLC," Grantor "IPA ASSET MANAGEMENT, LLC," Document Date 11/06/2024, Recording Date 11/08/2024, Consideration $10.00, Book/Page/Doc ID 13271/400 [#2]. The recorded Suffolk County Bargain and Sale Deed with Covenant Against Grantor's Acts confirms the same instrument — "THIS INDENTURE, made the 6th day of November, 2024 BETWEEN IPA Asset Management, LLC … 45 Sarah Drive, Farmingdale, NY 11735" conveying "TO … 26 AP, LLC" the premises at "26 Appel Drive East, Shirley, NY 11967," with the deed return-addressed to Matthew K. Tannenbaum, Esq. [#82][#83]. IPA had itself only acquired the property from Charles Harkin and Aaron C. Harkin by deed "made the 30th day of July, 2015" [#13][#78].

**Badges of fraud.**

1. *Nominal / no real consideration.* The transfer recites consideration of only "$10.00" [#2], yet the property is a substantial asset — IPA's own schedule lists market value of 481,481 / 553,900 and equity of 539,203.92 with essentially no mortgage [#50][#79]. A transfer of half-a-million dollars of equity for $10 is a classic badge of a fraudulent conveyance.

2. *Transfer to a related/insider entity after the judgment.* MangoTree's internal equity schedule expressly flags 26 Appel Dr E as "vested in 26 AP LLC from IPA after our judgment" [#85]. MangoTree (and Opportunity Zone RE 2019) obtained a judgment of $9,088,151.33 entered July 19, 2024 against IPA Asset Management LLC and affiliated entities [#52], and IPA conveyed the property out on November 6, 2024 — months after that judgment.

3. *Violation of an existing court order barring transfers.* The Campisi/Westerman analysis (IPA properties for sheriff sale) characterizes IPA's pattern of transfers as fraudulent conveyances because "our Court order is dated prior to the conveyance of these properties which directly violates Stipulation and Order Section 1 which was entered on February 16, 2022 by the Honorable Jerome C Murphy" [#48][#10]. A So-Ordered Stipulation was in fact filed in Nassau County (Index No. 601314/2021) on 02/16/2022 [#152]. The 26 Appel conveyance (11/6/2024) post-dates that order.

4. *Part of a pattern of insider transfers.* The same schedule documents repeated IPA-to-affiliate transfers for nominal sums — e.g., "IPA to 230R LLC owned by David? for $50K recorded 5/9/24" and "IPA to 6Vin LLC owned by David? for $50K recorded 4/29/24" [#37][#47], "Transferred to an entity that David has ownership interest in" [#37], and 18 Rugby Dr transferred from IPA Asset Management LLC to 18ru LLC for $275,000 on 04/26/2024 [#70]. The 26 Appel transfer to "26 AP LLC" — an entity whose name mirrors the address — fits this insider/shell pattern.

**Creditor enforcement targeting the property.** 26 Appel Dr E was itself listed among the properties the Suffolk County Sheriff was directed to sell to satisfy the MangoTree judgment: the Execution names "Real Property Known As: 26 Appel Drive E, Shirley, NY" [#53], and IP&E Holdings' motion lists "26 Appel Drive E, Shirley, NY 11967" among the properties scheduled for Sheriff's sale [#77]. IPA's 2026 amended bankruptcy schedules (Case 25-72526) still list "26 Ap Llc / 26 Appel Dr E, Shirley, NY" with an 11/6/2024 date and reference a CITIBANK and federal lien [#1], indicating ongoing entanglement.

**Bottom line.** The 11/6/2024 IPA → 26 AP LLC deed for $10 [#2][#82] bears multiple badges of a fraudulent/voidable transfer under New York law: nominal consideration, transfer to an apparent insider entity, timing after a $9.08M judgment [#52] and after a court order restraining transfers [#48][#152], and a documented pattern of similar IPA conveyances [#37][#47][#70]. MangoTree's own files already treat it as such [#85][#48].

**Gaps / caveats.** I did not locate a court ruling that has actually *adjudicated* this specific deed as void — the fraudulent-conveyance characterization is drawn from the judgment creditor's analysis and the recorded deed terms, not from an entered avoidance order on 26 Appel. The "26 AP LLC owned by David" linkage is inferred from the parallel insider-transfer notations [#37][#85] rather than a direct ownership document for 26 AP LLC in the chunks reviewed.

— Provenance: 200 sources across {'attachment': 100, 'title_report': 57, 'email_body': 23, 'insurance': 13, 'equity_schedule': 7} | corpora {'unknown': 200} | mode=analysis | date span 2015-08-05 → 2026-06-08 | facts verified 19/19

---

### Q21. Who owns 91 West Shore Road, Huntington and is it connected to David DeRosa or his network?
- **Property:** 91 West Shore Road, Huntington (ent_prop_0400026000200048000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 28, 'lis_pendens': 7, 'judgments': 5, 'assignments': 0} · events=49 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=15 verified=15 · sources={'title_report': 95, 'attachment': 113, 'insurance': 83, 'equity_schedule': 7, 'email_body': 13}
- **Answer:**

**Owner: IPA Asset Management, LLC — and yes, it is firmly connected to David DeRosa and his network.**

**1. Current record owner.** The property at 91 West Shore Road, Huntington, NY 11743 (Suffolk County, Parcel ID 0400-026.00-02.00-048.000) is owned by **IPA Asset Management, LLC**. A ProTitleUSA current-owner title report (Order# 832788) shows the Grantee/Deed Owner as "IPA ASSET MANAGEMENT LLC," via a Bargain and Sale deed dated 12/18/2017 (recorded 03/01/2018, Book 12952, Page 224), conveyed from prior owners Brenda L. Reid, Mark C. Rooney and Danielle Rooney [#116]. A 2026 Prowess Title Abstracts update search likewise lists the tax-account owner as "IPA ASSET MANAG, 91 W SHORE RD," with the search run in the name "IPA Asset Management LLC" against this exact parcel [#1]. The prior, pre-2017 chain of title ran through the Rooney/Reid family [timeline].

**2. The DeRosa connection is direct and multi-layered.**

- *Equity ownership.* In the IPA Asset Management, LLC Chapter 11 bankruptcy petition (Case No. 25-72526, signed 06/27/2025), the "LIST OF EQUITY HOLDERS" identifies **David D. DeRosa — 100%** [#298]. David DeRosa is thus the sole equity owner of the LLC that holds title to 91 West Shore Road.

- *Management.* In a sworn 2019 closing affidavit, David D. DeRosa stated: "I am the managing member ('member') of IPA Asset Management, LLC" [#299]. He also executes notes on behalf of the entity ("IPA ASSET MANAGEMENT, LLC By: David DeRosa") [#302].

- *DeRosa's own underwriting of this property.* The "91 West Shore Rd, Huntington Financing Evaluator" was emailed from DeRosa's own address (dderosa@ipellc.net) and projects an "IP&E Investor Projection--Guaranteed Profit Share of 50%" on "91 West Shore Rd, Huntington, NY 11743-2040" [#82]. This ties the property into the IP&E/IPA investment-syndication model DeRosa ran.

- *Litigation / the MangoTree network.* 91 West Shore Road is one of the properties expressly listed in the Suffolk County litigation MangoTree Real Estate Holding, L.P. and Opportunity Zone RE 2019, LLC v. David D. DeRosa, et al. (Index No. 602335/2021). The schedule of affected properties lists "91 West Shore Road, Huntington, New York 11743, Township/District: 0400, Section: 026.00, Block: 02.00, Lot:048.000" [#8]. IPA Asset Management LLC and David DeRosa are named co-defendants in that action [#5], and the same property appears repeatedly on the MangoTree property/settlement schedules and the February 2022 Stipulation and Order restraining sale of the remaining properties [#21][#156][#160].

- *Insurance.* The property was insured under the Island Properties & Associates master policy (Lloyd's of London / Innovative Risk Solutions) at "91 West Shore Road … Huntington, NY 11743," with IPA Asset Management LLC and MangoTree Real Estate Holdings, LP as additional insureds [#90][#94][#107] — again linking it to the IPA/Island Properties/MangoTree cluster around DeRosa.

**3. Bottom line.** 91 West Shore Road, Huntington is owned of record by IPA Asset Management, LLC (since the December 2017 deed) [#116][#1]. That LLC is wholly owned (100% equity) and managed by David DeRosa [#298][#299], who personally promoted the property as an IP&E investment deal [#82]. The property is squarely embedded in the DeRosa/IPA/Island Properties/MangoTree network and is a named asset in the MangoTree v. DeRosa litigation (Index 602335/2021) [#8][#5].

*Gap note:* I confirmed the current owner from title reports and the 2026 tax-account search; I did not separately pull the operative 2017 deed instrument itself (the title reports summarize it). I also did not locate a post-2017 reconveyance, so IPA Asset Management appears to remain the owner as of the April 2026 update search [#1].

— Provenance: 311 sources across {'title_report': 95, 'attachment': 113, 'insurance': 83, 'equity_schedule': 7, 'email_body': 13} | corpora {'unknown': 311} | mode=analysis | date span 2017-11-01 → 2026-05-07 | facts verified 15/15

---

### Q22. What mortgages, liens, or judgments are recorded against 91 West Shore Road, Huntington?
- **Property:** 91 West Shore Road, Huntington (ent_prop_0400026000200048000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 28, 'lis_pendens': 7, 'judgments': 5, 'assignments': 0} · events=49 · findings=[]
- **Verification:** KEPT_ORIGINAL · facts=15 verified=14 · sources={'title_report': 149, 'attachment': 129, 'insurance': 13, 'equity_schedule': 7, 'email_body': 14}
- **Answer:**

Two ProTitleUSA "Current Owner Search" title reports on 91 West Shore Road, Huntington, NY 11743 (parcel 0400-026.00-02.00-048.000) — one ordered 02/27/2021 (Order #687692) and the updated one completed 03/07/2022 (Order #832788) — record the following recorded encumbrances against the property. The current vested owner is IPA Asset Management LLC (Bargain and Sale deed dated 12/18/2017, recorded 03/01/2018, Book 12952/Page 224, sale price $100,000) [#145].

MORTGAGE
There is one open mortgage of record. On August 23, 2006, Mark C. Rooney, Brenda L. Reid and Danielle Rooney gave a mortgage of $862,500.00 to MERS as nominee for HSBC Mortgage Corporation (USA), recorded September 25, 2006 in the Suffolk County Clerk's Office at Liber 21388 of Mortgages at Page 143, with a maturity date of 09/01/2036 [#246]. That mortgage was assigned to Deutsche Bank Trust Company Americas as Trustee for RALI 2006-QS15 (a corrective assignment of mortgage was recorded to fix an earlier 1/6/2012 assignment recorded in Liber M00022156, Page 021) [#75][#181]. Deutsche Bank, as trustee, later commenced a foreclosure: a Notice of Pendency under Index No. 18 606169 (Plaintiff: Deutsche Bank Trust Company Americas as Trustee for RALI 2006-QS15; Defendant: Reid, Brenda) was recorded 4/3/2018 against tax map 0400-026.00-02.00-048.000, referencing the same M00021388-143 mortgage [#146].

LIENS
• Federal tax lien — Dept. of Treasury / Internal Revenue Service against Mark C. Rooney and Danielle Rooney, recorded 05/31/2011, amount $196,925.47 [#1].
• The recurring Town of Huntington property taxes appear in the tax history (e.g., 2008 "Lien" $26,299.57), but those listed years are marked "Paid" [no separate fact cited beyond timeline].

JUDGMENTS
The reports list several recorded judgments in the "Active Judgments and Liens" section:
• National Collegiate Student Loan Trust (listed as "NATIONAL COLLEGIATE SCHOOL") v. Brenda Reid and Christian O'Connor — Civil Judgment, recorded 06/03/2014, $49,521.37 [#145].
• National Collegiate Student Loan Trust v. Brenda Reid and Christian O'Connor — Civil Judgment, recorded 02/10/2015, $60,489.15 [#145].
• Darren Burton v. Mark Rooney et al. — Civil Judgment, recorded 07/30/2015, $65,886.48 [#145].

LIS PENDENS (active property-right dispute)
• Mangotree Real Estate Holding, L.P. v. David DeRosa et al. — LIS PENDENS, recorded 02/23/2021, amount $0.00, under Suffolk County Index No. 21 602335 [#1]. This is the notice of pendency from the Mangotree litigation; the same lis pendens (Index 602335/2021, Sequence 322900) was recorded 2/23/2021 naming the DeRosa defendants [#47][#76], and 91 West Shore Road is among the Schedule A properties subject to that action [#13][#21].

CONTEXT / ENFORCEMENT
91 West Shore Road later became subject to the Suffolk County Sheriff's enforcement of the Mangotree judgment (Index No. 617567/2024); it is among the properties IP&E Holdings' motion identified as scheduled for Sheriff's sale [#61].

GAPS / CAVEATS
I was cut off before I could pull the full continuous "Active Judgments and Liens" block of the 2022 report (chunk #1 / doc_tr_832788), so there may be additional minor recorded items I could not individually verify. Note also a minor discrepancy in how the Mangotree entry is typed: the 2021 report (chunk #145) and the 31 Fort Hill report (#298) label it "LIS PENDENS (Active Property Right Dispute)" while chunk #1 mislabels the description as "(Civil Judgment)" — both reflect the same 02/23/2021 recording at Index 21 602335. The federal tax lien and the three judgments predate IPA's 2017 acquisition and run against the prior owners (Rooney/Reid/O'Connor); their current status (satisfied vs. open) is not confirmed in the chunks I reviewed, so they should be re-run for status before any closing.

— Provenance: 312 sources across {'title_report': 149, 'attachment': 129, 'insurance': 13, 'equity_schedule': 7, 'email_body': 14} | corpora {'unknown': 312} | mode=analysis | date span 2017-11-01 → 2026-05-07 | facts verified 14/15

---

### Q23. Give me the chronological timeline of 91 West Shore Road, Huntington.
- **Property:** 91 West Shore Road, Huntington (ent_prop_0400026000200048000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 28, 'lis_pendens': 7, 'judgments': 5, 'assignments': 0} · events=49 · findings=[]
- **Verification:** KEPT_ORIGINAL · facts=17 verified=16 · sources={'title_report': 150, 'attachment': 126, 'email_body': 7}
- **Answer:**

Below is the chronological timeline of **91 West Shore Road, Huntington, NY 11743** (Suffolk County tax parcel District 0400, Section 026.00, Block 02.00, Lot 048.000 [#3][#12]), reconstructed from the recorded chain of title (ProTitleUSA Orders #687692 and #832788), the Prowess update search, the Mangotree litigation record, and the 2024–2025 Sheriff's-sale execution papers.

**2003 — Inter-family deed (Rooney → Rooney & Reid).** Mark C. Rooney conveyed to Mark C. Rooney and Brenda L. Reid as joint tenants with right of survivorship; deed dated 09/18/2003, recorded 10/17/2003 (Book 12278, Page 494) [#f1].

**Aug.–Sept. 2006 — Inter-family deed and HSBC mortgage.** By deed dated 08/23/2006, recorded 09/25/2006 (Book 12470, Page 989), Brenda L. Reid and Mark C. Rooney conveyed to Brenda L. Reid, Mark C. Rooney and Danielle Rooney [#f2]. Concurrently, the three of them gave a mortgage to MERS as nominee for HSBC Mortgage Corporation (USA) in the amount of **$862,500.00**, dated 08/23/2006 and recorded 09/25/2006 at Liber 21388 of Mortgages, Page 143 (maturity 09/01/2036) [#f3].

**May 31, 2011 — Federal tax lien.** The Department of Treasury / IRS recorded a federal tax lien against Mark C. Rooney and Danielle Rooney for **$196,925.47** (Lien No. LFED00012866) [#f4].

**June 3, 2014 — Civil judgment.** A judgment was entered against Brenda Reid (and Christian O'Connor) in favor of National Collegiate; the title abstract reflects an associated amount of **$49,521.37** [#f5].

**Dec. 18, 2017 / Mar. 1, 2018 — Conveyance to IPA Asset Management LLC.** The Rooney/Reid owners conveyed the property to **IPA ASSET MANAGEMENT LLC** by Bargain and Sale deed dated 12/18/2017, recorded 03/01/2018 (Book 12952, Page 224), with a stated sale price of **$100,000.00** [#f6]. (Internal IP&E/Mango settlement schedules list the acquisition date as 2017-11-14 with an invested figure of 314715.2 [#f7] — this is the company's own accounting, not the recorded deed date.)

**Feb. 23, 2021 — Lis pendens (Mangotree litigation).** A Notice of Pendency was recorded by Mangotree Real Estate Holding, L.P. against David DeRosa et al., recorded 02/23/2021 under Suffolk County Index No. 21 602335 (Sequence No. 322900) [#f8]. 91 West Shore Road is one of the mortgaged premises listed in the related NYSCEF filing (Index No. 602335/2021) [#f9].

**2022 — Settlement / litigation activity.** The property appears throughout the 2022 global-settlement schedules and the Suffolk County District Attorney's June 29, 2022 document request concerning the DeRosa investigation, confirming 91 West Shore Road's inclusion among the DeRosa-controlled portfolio [#f10][#f9].

**July 19, 2024 — Money judgment docketed.** A transcript of judgment in Mangotree Real Estate Holdings, L.P. and Opportunity Zone RE 2019, LLC v. Island Properties & Associates, LLC et al. (Index No. 617567/2024) in the amount of **$9,088,151.33** was filed on July 19, 2024 with the Suffolk County Clerk [#f11]. IPA Asset Management LLC is among the named judgment debtors [#f11].

**Sept. 4–5, 2024 — Executions issued.** Westerman Ball Ederer Miller Zucker & Sharfstein, LLP delivered executions to the Suffolk County Sheriff to pursue a Sheriff's sale of seven properties under Index No. 617567/2024 [#f12], with 91 West Shore Road identified as one of the "Real Property Known As" parcels in the execution [#f13].

**May 22–27, 2025 — Notice of Sheriff's sale.** The Suffolk County Sheriff issued notices of sale; 91 West Shore Road, Huntington (the IPA Asset Management LLC parcel) was scheduled as one of the seven real-property judgment sales [#f13].

**May 29, 2025 — Motion to dismiss / stay.** IP&E Holdings moved by motion noting the plaintiff was attempting to execute on the judgment and that the Sheriff's properties (including 91 West Shore Road) would be scheduled for sale absent payment within fourteen days [#f14].

**Apr.–May 2026 — Current status.** A Prowess Title update search (search date 05/04/2026; new effective date 04/24/2026) for IPA Asset Management LLC at 91 West Shore Road found **no new documents after 03/04/2025**, and reported 2025 taxes paid (1st half $16,574.56; 2nd half $16,574.55) with a $0.00 balance [#f15].

**Gaps/caveats:** The earliest tax-lien entries (2001–2014) in the abstract reflect prior owners (Maracina, M Development Inc., Reid/Rooney) and are tax-payment history rather than title-transfer events. I did not locate a recorded satisfaction of the 2006 HSBC mortgage or confirmation that the May 2025 Sheriff's sale was actually consummated; the latest record (the 2026 Prowess update) shows no post-03/04/2025 filings.

— Provenance: 283 sources across {'title_report': 150, 'attachment': 126, 'email_body': 7} | corpora {'unknown': 283} | mode=analysis | date span 2015-08-06 → 2026-05-13 | facts verified 16/17

---

### Q24. Are there any suspicious or voidable transfers involving 91 West Shore Road, Huntington?
- **Property:** 91 West Shore Road, Huntington (ent_prop_0400026000200048000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 28, 'lis_pendens': 7, 'judgments': 5, 'assignments': 0} · events=49 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=14 verified=14 · sources={'title_report': 127, 'attachment': 229, 'email_body': 14, 'insurance': 13, 'equity_schedule': 7}
- **Answer:**

## Suspicious / potentially voidable transfers involving 91 West Shore Road, Huntington

Yes. The record contains at least one transfer of 91 West Shore Road (Suffolk County parcel 0400-026.00-02.00-048.000) that bears classic badges of a suspicious / potentially voidable conveyance, plus a subsequent encumbrance and litigation posture that reinforce the concern.

**1. The December 2017 conveyance into IPA Asset Management LLC for nominal consideration.** On December 18, 2017 (recorded March 1, 2018), the property was deeded from the individual owners — Brenda L. Reid, Mark C. Rooney and Danielle Rooney — to **IPA Asset Management LLC**, a David DeRosa-affiliated entity, by Bargain and Sale deed [#1, see f1]. The recorded sale price/consideration was only **$100,000** [#2/f2], a figure corroborated on the transfer-tax recording page ("Consideration Amount $ 100,000") [#3/f3]. That is far below the property's apparent value: MangoTree's own property schedule lists the property with a value of $314,715.20 [#4/f4], and the later equity schedule pegs market value at **$1,527,273** [#7/f7]. A transfer of a property worth seven figures for a stated $100,000 to an insider-controlled LLC is the type of below-fair-consideration, intra-network conveyance that supports a constructive fraudulent-transfer theory. The title report itself flagged the transaction as a "Transfer to a Third Party (Private, LLC, etc.) by Borrower" [#5/f5].

**2. Pattern evidence — the DeRosa fraudulent-transfer scheme.** The transfer fits a documented pattern. In the related *Marie Holdings, Inc. v. DeRosa* litigation, the plaintiff pleads a cause of action for **fraudulent transfer under Article 10 of the Debtor and Creditor Law** [#12/f12], alleging that a parallel conveyance (the September 17, 2016 transfer of 132 West 130th Street) "was made without fair consideration" [#13/f13]. The same DeRosa/IPA entities that received 91 West Shore Road are defendants in that fraudulent-conveyance action, so the $100,000 transfer of 91 West Shore Road into IPA should be examined under the same Article 10 framework (constructive fraud where the transfer leaves the transferor without fair consideration, and actual fraud where intent to hinder/delay/defraud creditors is shown).

**3. A large post-transfer mortgage / equity-stripping concern.** After the 2017 conveyance, the property carries a mortgage of **$1,235,322.47** against the $1,527,273 market value, leaving only ~$184,577 equity, and the property is in active foreclosure, with "IPA remains in title" [#7/f7, #8/f8]. (A prior $862,500 mortgage signed by Reid/Rooney existed as of 2006 [#11/f11].) The thin remaining equity is consistent with the broader allegation that DeRosa entities encumbered properties to strip equity from creditors.

**4. Lis pendens and judgment exposure.** MangoTree recorded a **Lis Pendens** against the property (and DeRosa et al.) signed 02/12/2021 and recorded 02/23/2021 [#6/f6]. The property is expressly named in the MangoTree execution and is scheduled for Sheriff's sale [#9/f9] on a judgment of **$9,088,151.33** (transcript filed July 19, 2024) [#10/f10]. MangoTree separately argues the DeRosa side has engaged in "a bad faith filing for the purpose of delay" [#14/f14].

**Assessment.** The single most suspicious / potentially voidable event is the **December 18, 2017 deed transferring 91 West Shore Road from the Reid/Rooney individuals to insider entity IPA Asset Management LLC for a stated $100,000** — a price grossly below the property's value [#1–#5/f1-f5]. Combined with the contemporaneous DeRosa fraudulent-transfer allegations [#12, #13], the heavy post-transfer mortgage that leaves minimal equity [#7], and the recorded lis pendens / multimillion-dollar judgment [#6, #9, #10], this conveyance is a strong candidate for avoidance as a fraudulent transfer under DCL Article 10 (and potentially under bankruptcy avoidance powers).

**Gaps / caveats:** The corpus's equity schedule marks this specific parcel "fraudulent=None" [#8] (unlike sister properties expressly flagged "fraudulent=yes"), and I did not locate a document recording the exact date or lender of the ~$1.235M mortgage relative to the MangoTree judgment, so I cannot confirm here whether that mortgage post-dates the judgment. Those two points should be confirmed against the recorded mortgage instrument and a current title continuation before pleading avoidance.

— Provenance: 390 sources across {'title_report': 127, 'attachment': 229, 'email_body': 14, 'insurance': 13, 'equity_schedule': 7} | corpora {'unknown': 390} | mode=analysis | date span 2017-11-01 → 2026-05-23 | facts verified 14/14

---

### Q25. Who owns 230 Ralph, Babylon and is it connected to David DeRosa or his network?
- **Property:** 230 Ralph, Babylon (ent_prop_0102002000200081000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'KATHLEEN PAGAN'] · facts={'chain_of_title': 2, 'mortgages': 1, 'liens': 7, 'lis_pendens': 8, 'judgments': 2, 'assignments': 5} · events=28 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=13 verified=13 · sources={'title_report': 55, 'equity_schedule': 7, 'attachment': 105, 'email_body': 30}
- **Answer:**

**Short answer: Yes — 230 Ralph Avenue, Babylon (Town of Babylon, Suffolk County, parcel 0102-002.00-02.00-081.000) is squarely inside the David DeRosa / IPA network. It was acquired and held by IPA Asset Management, LLC, and as of 2024 it was conveyed to 220 P LLC — a transfer the MangoTree creditors flag as fraudulent.**

**Ownership chain.** The property at 230 Ralph Avenue, Babylon, NY 11702 sits in the Town of Babylon at parcel/tax-map 0102-002.00-02.00-081.000 [#13]. IPA Asset Management, LLC took title via a deed dated 03/11/2016 from Andrew Sewell (as to his undivided 50% interest), per the ProTitleUSA current-owner title report [#156]. An earlier 2007 deed already directed recording "RETURN BY MAIL TO: IPA ASSET MANAGEMENT, LLC, 45 Sarah Drive, Farmingdale, NY 11735" [#13], and a separate recorded deed names "IPA Asset Management, LLC, 45 Sarah Drive, Farmingdale, NY 11735" as the grantee/party of the second part [#6]. A 2026 update title search (search date 05/04/2026) likewise lists the name given as "IPA ASSET MANAGEMENT LLC" for "230 Ralph Babylon NY" [#7]. The original 2007 arms-length sale price for the property was $434,600 (James to Sewell) [#12].

**The 2024 transfer to 220 P LLC.** The bankruptcy filings (Motion for Relief from Stay, 2025; Motion to Convert/Appoint Trustee, 2026) state that 230 Ralph Ave is "CURRENTLY OWNED BY 220 P LLC" [#10]. The underlying conveyance record shows a 05/09/2024 "Deed Transfer / Resale" from "Ipa Asset Management LLC" to "220 P LLC" for $50,000 [#12] — i.e., a sale at a nominal $50,000 of a property whose tax-map value/market value the creditors peg far higher.

**Connection to David DeRosa and his network.** This connection is direct and multi-layered:

1. *Through IPA.* David D. DeRosa is alleged to be "the principal member and sole and/or majority owner of all the corporate defendants," which include IPA Asset Management, LLC [#77]. IPA Asset Management, LLC is a named defendant alongside "DAVID D. DEROSA" in the MangoTree litigation [#5].

2. *Litigation/settlement schedules.* 230 Ralph Avenue, Babylon appears on MangoTree's master property schedule with a 2016 purchase date (2016-02-23) [#195], and is listed in the MOU Exhibit A of properties in the MangoTree/DeRosa global settlement [#104] — confirming the creditors and the DeRosa parties both treated it as a DeRosa-network asset.

3. *Fraudulent-transfer flag.* The internal equity schedule lists "IPA ASSET MANAGEMENT LLC | 230 Ralph, Babylon | parcel 0102-002.00-02.00-081.000 | mkt=533333.0 mortgage=434550.0 ... foreclosure=yes fraudulent=yes" [#3], expressly tagging the property as the subject of a fraudulent transfer and an active foreclosure. The same schedule entry sits next to a note describing the parallel pattern where "ipa conveyed to 18RU 4/26/24 and took out a mortgage for $247K" [#3] — the identical playbook of conveying IPA assets into newly-formed in-house single-letter/number LLCs (18RU, 220 P) to shield them from MangoTree's judgment.

**Bottom line.** 230 Ralph, Babylon is/was an IPA Asset Management, LLC property; IPA is one of David DeRosa's controlled entities; and the property was transferred to 220 P LLC for a nominal $50,000 in May 2024 — a move the MangoTree judgment creditors treat as a fraudulent transfer within DeRosa's network. 

**Gaps/caveats.** I did not find a recorded document in this corpus that independently states who owns/controls "220 P LLC." Its connection to DeRosa is inferred from (a) the seller being IPA, (b) the nominal $50,000 price, (c) the fraudulent-transfer flag, and (d) the documented pattern of conveying IPA assets into in-house LLCs (e.g., 18RU). Treat the 220 P LLC ownership/control link as a strong inference rather than a directly-recorded fact. Also note the bankruptcy records use the situs label "230 Ralph Ave, Copiague, NY 11726" while county/deed records say "Babylon, NY 11702" [#10][#13] — these are the same parcel (tax-map 0102-002.00-02.00-081.000 / APN 472003 2.-2-81).

— Provenance: 197 sources across {'title_report': 55, 'equity_schedule': 7, 'attachment': 105, 'email_body': 30} | corpora {'unknown': 197} | mode=analysis | date span 2016-02-22 → 2026-05-04 | facts verified 13/13

---

### Q26. What mortgages, liens, or judgments are recorded against 230 Ralph, Babylon?
- **Property:** 230 Ralph, Babylon (ent_prop_0102002000200081000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'KATHLEEN PAGAN'] · facts={'chain_of_title': 2, 'mortgages': 1, 'liens': 7, 'lis_pendens': 8, 'judgments': 2, 'assignments': 5} · events=28 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=12 verified=12 · sources={'title_report': 155, 'attachment': 90, 'equity_schedule': 7, 'insurance': 13, 'email_body': 13}
- **Answer:**

**Recorded encumbrances against 230 Ralph Avenue, Babylon, NY 11702 (parcel 0102‑002.00‑02.00‑081.000, Suffolk County)**

The property has been the subject of title searches by ProTitleUSA (Orders #687671 dated 02/25/2021 and #832774 dated 03/03/2022) and a 2026 update search by Prowess Title Abstracts. The following recorded items appear.

**1. Mortgage (GreenPoint / MERS — the open mortgage of record).** On 12/18/2006 Kathleen Pagan and Andrew Sewell, as borrowers, signed a mortgage to MERS as nominee for GreenPoint Mortgage Funding, Inc. [#182]. The mortgage was in the principal sum of **$347,650.00** and was recorded on 07/23/2007 in Liber M00021572, Page 243 [#138][#196]. This is the original purchase‑money mortgage carried in the title report's "Open Mortgages" section.

**2. Assignments of that mortgage.** The mortgage was assigned through a chain of holders:
 – On 06/13/2011 (recorded 10/05/2011), MERS assigned to HSBC Bank USA, N.A., as Trustee for the holders of the Deutsche Bank ALT‑A Securities, Inc., Mortgage Loan Trust Series 2007‑AR2 [#181 timeline].
 – On 01/04/2012 (recorded 01/17/2012), MERS as nominee for GreenPoint assigned to GreenPoint Mortgage Funding, Inc. [#82].
 – On 01/18/2018 (recorded 04/03/2018), GreenPoint assigned back to MERS [#82].
These are assignment instruments, not new debts; they reflect transfers of the single 2006 mortgage.

**3. Foreclosure Lis Pendens (HSBC).** A foreclosure Notice of Pendency under Index No. 12/31182 was filed against the property. The title chronology shows it filed/recorded 10/09/2012 and re‑filed/recorded 02/22/2019, with HSBC Bank USA, N.A. as Trustee (Series 2007‑AR2) as plaintiff and Kathleen Pagan, Andrew Sewell, et al. as defendants [#181 timeline]. The original 2012 lis pendens corresponds to the Notice of Pendency dated October 3, 2012 referencing "230 RALPH AVENUE, BABYLON, NY 11702" and Section 002.00, Block 02.00, Lot 081.000 [#3][#81].

**4. MangoTree litigation Lis Pendens (Notice of Pendency).** A second, more recent Notice of Pendency, Instrument 322873, signed 02/12/2021 and recorded 02/18/2021, names MANGOTREE REAL ESTATE HOLDING, L.P. as the filing party against DAVID D. DEROSA et al. [#79][#252]. This arises from the MangoTree v. DeRosa/IPA litigation in which 230 Ralph is among the listed properties [#68].

**5. Property taxes.** As of the 2026 Prowess update search, 2025 taxes were paid — 1st Half $6,126.27 (Paid) and 2nd Half $6,126.26 (Paid) — and "No new documents found after 03/04/2025" [#70]. The 2021 ProTitle report showed earlier tax installments (e.g., 2020/2021 1st installment $5,376.40, paid 12/20/2020) [#19 timeline]. There is no indication of an open tax lien.

**Money/ownership context.** A 2025 equity schedule entry for 230 Ralph lists mortgage=434550.0, taxes_owed=0.0, equity=75750.0, foreclosure=yes, fraudulent=yes, and notes "Ipa changed 50% vesting to another of their inhouse entities" [#72]. The $434,550 figure there does not match the recorded $347,650.00 mortgage principal and appears to be an internal estimate rather than a recorded instrument amount — I flag this discrepancy; the recorded mortgage of record is $347,650.00 [#138].

**Summary.** Recorded against 230 Ralph: (a) one open mortgage of $347,650.00 (Pagan/Sewell → GreenPoint/MERS, 2006, recorded 2007), with later assignments to/among HSBC Trustee, GreenPoint and MERS; (b) a foreclosure lis pendens (Index 12/31182) by the HSBC securitization trustee; and (c) a MangoTree litigation Notice of Pendency (Instr. 322873, recorded 02/18/2021). 

**Gaps:** I was unable to fully open the "Active Judgments and Liens" section text specific to 230 Ralph within the budget, so I cannot affirmatively quote a "no active judgments" line for this exact parcel; I therefore do not state that no judgments exist. The mortgage was not shown as satisfied in the records reviewed, so it should be treated as open. The internal equity‑schedule mortgage figure ($434,550) conflicts with the recorded amount and should be reconciled against the actual recorded instrument.

— Provenance: 278 sources across {'title_report': 155, 'attachment': 90, 'equity_schedule': 7, 'insurance': 13, 'email_body': 13} | corpora {'unknown': 278} | mode=analysis | date span 2017-03-01 → 2026-06-04 | facts verified 12/12

---

### Q27. Give me the chronological timeline of 230 Ralph, Babylon.
- **Property:** 230 Ralph, Babylon (ent_prop_0102002000200081000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'KATHLEEN PAGAN'] · facts={'chain_of_title': 2, 'mortgages': 1, 'liens': 7, 'lis_pendens': 8, 'judgments': 2, 'assignments': 5} · events=28 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=27 verified=27 · sources={'title_report': 74, 'attachment': 111, 'email_body': 5}
- **Answer:**

Here is the chronological timeline of 230 Ralph Avenue, Babylon, NY 11702 (Suffolk County, Parcel/APN 0102-002.00-02.00-081.000; also assessor No. 472003 2.-2-81), Property ID #60857 in the MangoTree/IPA portfolio. Note that some later records re-style the situs as "230 Ralph Ave, Copiague, NY 11726," which the title and motion records confirm is the same parcel [#11][#14].

• Sep. 4, 1924 — The lot (Lot 966 / Filed Map No. 641) was originally laid out and filed in the Suffolk County Clerk's Office [#21][#104].

• Dec. 18, 2006 — Kathleen Pagan and Andrew Sewell signed a mortgage to MERS as nominee for GreenPoint Mortgage Funding, Inc. [#118][#181].

• July 23, 2007 — Deed recorded transferring the property from John R. James and Vivienne T. James to Andrew Sewell & Kathleen Pagan; the deed (DEEDS/DDD) was recorded at Liber 12514, Page 645 with a sale price of $434,600.00 [#118][#112][#120].

• June 13, 2011 (recorded Oct. 5, 2011) — Assignment of mortgage from MERS to HSBC Bank USA, N.A., as Trustee for the Deutsche Bank ALT-A Securities 2007-AR2 trust [timeline; #119].

• Oct. 9, 2012 — Lis pendens (Notice of Pendency) filed by HSBC Bank USA, N.A. as Trustee against Kathleen Pagan, Andrew Sewell et al., Index No. 12/31182; the related notice was dated at Westbury, New York, October 3, 2012 by Druckman Law Group PLLC [#172][#108].

• Jan. 4, 2012 (recorded Jan. 17, 2012) — Assignment of mortgage from MERS as nominee for GreenPoint to GreenPoint Mortgage Funding, Inc. [timeline].

• Feb. 23, 2016 — Purchase/acquisition closing date for IPA Asset Management LLC (per the MangoTree property schedules, Property ID 60857, total MangoTree cash investment $55,959.23) [#73][#187][#189].

• Feb. 2016 – 2018 — Property-level activity by IPA: a $25,000 investment check to IPA Asset Management III, LLC (Feb. 22, 2016) [#24]; a $1,000 asset-manager fee to Steve Mac, Inc. (Feb. 23, 2016) [#90]; cesspool service $200.96 (Mar. 10, 2016) [#91]; LHC Floors $2,438.90 (Mar. 16, 2016) [#23]; K & V Home Improvements "no heat" boiler invoice $175 (Feb. 10, 2018) [#92].

• Mar. 11, 2016 (recorded Sep. 15, 2020) — Deed (Bargain and Sale with covenant) from Andrew Sewell, as to his undivided 50% interest, to IPA Asset Management LLC, consideration $5,000.00, recorded Liber 13071, Page 096 [#118 / timeline].

• Jan. 18, 2018 (recorded Apr. 3, 2018) — Assignment of mortgage from GreenPoint Mortgage Funding, Inc. to MERS [timeline].

• Feb. 19/22, 2019 — Lis pendens re-filed (Index 12/31182); notice dated Feb. 19, 2019 by RAS Boriskin, LLC, filed Feb. 22, 2019 [#102][#183][#3].

• May 20, 2020 (recorded May 28, 2020) — Corrective/gap assignment of mortgage (MERS as nominee for GreenPoint to MERS) [timeline].

• 2020–2022 — Tax activity: 2020/2021 combined taxes (1st installment $5,376.40 paid 12/20/2020; 2nd $4,376.39 due 05/30/2020) [timeline]; sewer lien due 3/15/2021 and water "Shut Off Active" due 4/29/2021 [timeline]; 2022 combined 2nd installment $5,690.98 due 05/31/2022 [timeline].

• Sep. 17, 2016 — Alleged fraudulent-conveyance date referenced in the Marie Holdings / MangoTree litigation against David DeRosa and IPA entities (Article 10 Debtor-Creditor Law claims) — relevant context to the IPA acquisition era [#125][#116].

• May 6/9, 2024 — Deed transfer (resale) recorded: IPA Asset Management LLC to 220 P LLC for $50,000; document dated 5/6/2024 and recorded 5/9/2024 [#8][#9][#11].

• Apr. 16, 2025 — Satisfaction of mortgage (M00023654/149) recorded [#106].

• Apr. 28, 2025 — Deed (D00013292/745) recorded, grantor "MCCLENDON, ..." [#106][#175].

• Sep. 25, 2025 — Judgment (transcript of judgment) IPA Asset Management LLC v. Matthais Eato [#13][#106].

• Dec. 10, 2025 — A further transcript-of-judgment record against IPA Asset Management LLC [#106].

• Dec. 22, 2025 — Two miscellaneous liens (LMIS00027319 and LMIS00027323) filed against IPA Asset Management LLC by Hunt Club at Coram Homeowners [#13][#186].

GAPS / CAVEATS: Several of the late-2025 judgment/lien entries (Eato judgment, Hunt Club liens, Dec. 10 judgment) are indexed against the IPA Asset Management LLC name in the Suffolk County Clerk online search and may relate to other IPA-owned parcels rather than 230 Ralph specifically. The McClendon deed (4/28/2025) and the mortgage satisfaction (4/16/2025) appear in the Prowess/IPA county search but the parties on the 230 Ralph chain after the 2024 sale to 220 P LLC are not fully resolved in the corpus.

— Provenance: 190 sources across {'title_report': 74, 'attachment': 111, 'email_body': 5} | corpora {'unknown': 190} | mode=analysis | date span 2012-07-17 → 2026-05-28 | facts verified 27/27

---

### Q28. Are there any suspicious or voidable transfers involving 230 Ralph, Babylon?
- **Property:** 230 Ralph, Babylon (ent_prop_0102002000200081000) · is_david=True
- **Ground truth:** owners=['IPA ASSET MANAGEMENT LLC', 'KATHLEEN PAGAN'] · facts={'chain_of_title': 2, 'mortgages': 1, 'liens': 7, 'lis_pendens': 8, 'judgments': 2, 'assignments': 5} · events=28 · findings=['medium:Insider conveyance to IPA ASSET MANAGEME']
- **Verification:** VERIFIED_FIRST_PASS · facts=10 verified=10 · sources={'equity_schedule': 7, 'attachment': 59, 'title_report': 30, 'email_body': 4}
- **Answer:**

Yes. The record shows at least one transfer of 230 Ralph Avenue, Babylon (also addressed as 230 Ralph Ave, Copiague, NY 11726; Suffolk County parcel 0102-002.00-02.00-081.000 / APN 472003 2.-2-81) that the creditor side has expressly flagged as a suspicious / fraudulent (and therefore potentially voidable) conveyance, plus underlying facts that support a voidable-transfer theory.

The key transaction: on 05/09/2024, IPA Asset Management LLC conveyed 230 Ralph to 220 P LLC for $50,000 by a "Deed Transfer Resale" [#83]. The property's title and ownership records confirm 230 Ralph is "CURRENTLY OWNED BY 220 P LLC" under a deed "DATED 5/6/2024 AND RECORDED 5/9/2024" [#82]. That same conveyance is described in the creditor's working schedule as "IPA to 230R LLC owned by David? for $50K recorded 5/9/24" [#48], i.e., a transfer to an insider entity that David allegedly controls.

The badges of fraud are significant. The $50,000 consideration is grossly below value: the same property is carried at a market value of 533333 with a 434550 mortgage and 75750 of equity on the sheriff-sale schedule [#13], and the internal equity schedule independently lists "230 Ralph, Babylon ... mkt=533333.0 mortgage=434550.0 taxes_owed=0.0 equity=75750.0 ... foreclosure=yes fraudulent=yes" [#1]. A $50,000 sale of a property worth roughly half a million dollars, to an apparent insider, is a classic indicator of a transfer for less than fair consideration.

The transfer also appears to violate a court order. The creditor characterizes the IPA conveyances as a "Fraudulent conveyance by IPA," explaining the intent "To pursue a fraudulent conveyance as our Court order is dated prior to the conveyance of these properties which directly violates Stipulation and Order Section 1 which was entered on February 16, 2022" [#37]. Because the 5/9/2024 transfer post-dates that February 16, 2022 Stipulation and Order, it is alleged to be a transfer made in defiance of an existing judgment/order — squarely the kind of transfer creditors seek to void.

Additional flags on the same parcel: the equity schedule notes "Ipa changed 50% vesting to another of their inhouse entities" [#1], consistent with IPA having earlier taken a 50% interest from Andrew Sewell. The title report records a deed in which IPA Asset Management LLC took "ANDREW SEWELL AS TO HIS UNDIVIDED 50% INTEREST," with a "Deed Date | 03/11/2016" but a "Recorded Date | 09/15/2020" [#96] — a multi-year delay between execution and recording, and the property was already in "21/602335 Foreclosure Pending" when IPA recorded that interest on 2020-09-15 [#72]. The parcel was also subject to a pre-existing lis pendens / foreclosure (HSBC mortgage), "Type of Instrument: LIS PENDENS Recorded: 09-Oct-2012 Index Number: 12 31182" [#92].

In short, the 5/9/2024 conveyance from IPA Asset Management LLC to 220 P LLC for $50,000 is the transaction most likely to be challenged as a suspicious/voidable (fraudulent) transfer: it is to an apparent insider, for consideration far below the property's ~$533,333 value (≈$75,750 equity), and was made after the February 16, 2022 Stipulation and Order, all of which the creditor has expressly flagged as a fraudulent conveyance.

— Provenance: 100 sources across {'equity_schedule': 7, 'attachment': 59, 'title_report': 30, 'email_body': 4} | corpora {'unknown': 100} | mode=analysis | date span 2016-02-22 → 2026-05-04 | facts verified 10/10

---

### Q29. Who owns 904 Bayshore Dr, Terra Ceia FL and is it connected to David DeRosa or his network?
- **Property:** 904 Bayshore Dr, Terra Ceia FL (ent_prop_2179310301) · is_david=False
- **Ground truth:** owners=['LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 1, 'lis_pendens': 0, 'judgments': 0, 'assignments': 0} · events=7 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=16 verified=16 · sources={'title_report': 159, 'attachment': 168, 'email_body': 36}
- **Answer:**

**Record owner.** According to the Prowess Title Abstracts full search dated 6/7/2026 for 904 Bayshore Dr, Terra Ceia, FL 34250 (Manatee County, Parcel ID 2179310301), the vesting owner is **LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY** [#1]. Laney Homes acquired title from the Estate of Janet S. Godwin (Sherry Stone, personal representative, and other heirs/devisees) by a deed dated 4/11/2025, recorded 5/21/2025, for a consideration of $400,000.00 [#1][#111]. The LLC's manager is **Timothy Dineen** — he signs the mortgage and the owner's affidavit as "Manager of Laney Homes LLC, a Virginia limited liability company" [#178][#233]. Laney Homes uses a Bassett, VA address (15236 Cedar Knoll Ct, Bassett VA 24055) on the county situs record [#2].

**Connection to David DeRosa's network — yes, a strong financial link runs through Rakesh Bhargava's entity.** On the same 904 Bayshore title chain, Laney Homes LLC granted a mortgage dated 6/3/2025, recorded 6/6/2025, in the amount of **$736,256.93**, and the lender is **RKB CONSULTING GROUP, INC.** [#111]. RKB Consulting Group, Inc. is tied directly to the DeRosa/MangoTree network:

- RKB Consulting Group, Inc. has an address at **24 Oak Lane, Roslyn Heights, NY 11577** [#339][#103]. That is the same address at which **Rakesh Bhargava** (manager of MangoTree's general partner) attests under oath that he resides [#256], and it is MangoTree Real Estate Holdings' stated place of business. "RKB" are Rakesh Bhargava's initials, and a 2012 settlement spreadsheet circulated from an ipellc.net (IPA/DeRosa) email expressly treats "RKB Consulting Group" and "Island Properties & Assoc" as the two profit-sharing parties on a deal [#335][#336].
- RKB Consulting Group, Inc. has transacted directly with the DeRosa side: a June 2020 "Agreement for the Sale of LLC Interest" — circulated from David DeRosa's own email (dderosa@ipellc.net) — names RKB Consulting Group, Inc. (24 Oak Lane, Roslyn Heights) as Buyer and **GMR Real Estate Holdings, LP at 45 Sarah Drive, Farmingdale** (DeRosa's IPA business address) as Seller [#339][#338]. DeRosa also executed an assignment of shares of 3FR, LLC from himself as Transferor to RKB Consulting Group, Inc. as Transferee [#345].

**The neighboring parcel reinforces the pattern.** The adjacent property, 910 Bayshore Dr, Terra Ceia (Parcel 2179310350), carried a mortgage from Listing Prophet, LLC d/b/a Listing Profit (9702 Gayton Rd, Ste 243, Richmond VA) that was **assigned to the same RKB Consulting Group, Inc. at 24 Oak Ln., Roslyn Heights, NY 11577** [#103][#104]. So RKB Consulting Group holds secured positions on at least two adjacent Terra Ceia parcels.

**Bottom line.** 904 Bayshore Dr is owned of record by Laney Homes LLC, a Virginia LLC managed by Timothy Dineen [#1][#178]. On its face the owner is not a named DeRosa entity. However, the property is encumbered by a $736,256.93 mortgage held by RKB Consulting Group, Inc. [#111], which operates from 24 Oak Lane, Roslyn Heights — Rakesh Bhargava's residence and MangoTree's address [#256][#339] — and which has a documented history of buying LLC interests from David DeRosa / GMR (45 Sarah Drive) and receiving share assignments directly from DeRosa [#339][#345]. Bhargava was DeRosa's long-time real-estate partner (manager of MangoTree's general partner and the IPA counterparty) [#22][#336]. 

**Caveat / gap:** I did not find a document that names David DeRosa or an IPA entity as an owner or member of Laney Homes LLC itself, and I could not confirm who controls Timothy Dineen or the Virginia LLC. The connection to the DeRosa "network" is therefore established through the financing party (RKB Consulting Group / Rakesh Bhargava), not through direct DeRosa ownership of Laney Homes. Whether Laney Homes is a DeRosa-controlled shell or simply a borrower from Bhargava's lending vehicle is not resolved on this record and warrants further investigation (e.g., Virginia SCC filings for Laney Homes and Dineen).

— Provenance: 363 sources across {'title_report': 159, 'attachment': 168, 'email_body': 36} | corpora {'unknown': 363} | mode=analysis | date span 2012-03-12 → 2026-06-08 | facts verified 16/16

---

### Q30. What mortgages, liens, or judgments are recorded against 904 Bayshore Dr, Terra Ceia FL?
- **Property:** 904 Bayshore Dr, Terra Ceia FL (ent_prop_2179310301) · is_david=False
- **Ground truth:** owners=['LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 1, 'lis_pendens': 0, 'judgments': 0, 'assignments': 0} · events=7 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=10 verified=10 · sources={'title_report': 177, 'attachment': 89}
- **Answer:**

**Subject property:** 904 Bayshore Dr, Terra Ceia, FL 34250/34221, Manatee County, Parcel ID 2179310301, vested in LANEY HOMES LLC, a Virginia Limited Liability Company [#66][#65]. The most current authority on encumbrances is the Prowess Title Abstracts Full Search dated 6/7/2026, effective date 5/28/2026 [#66].

**MORTGAGE.** The title search discloses one mortgage in the Mortgage Information section: Mortgage 1, with Borrower LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY, Document Date 5/20/2025, and Lender beginning "KIAV…" [#2]. This is consistent with the deed-chain grid, which shows a 5/20/2025 instrument (Inst. 202541064175) associated with the LANEY HOMES LLC vesting [#65]. The recorded warranty deed conveying the property to Laney Homes LLC from the heirs/devisees of the Estate of Janet S. Godwin was recorded 5/21/2025 for a consideration of $400,000.00 (Book/Page/Doc ID 202541064175) [#2]. The corpus snippet captures the borrower, document date and the start of the lender name but cuts off before the recorded mortgage amount and full lender name, so the principal sum of this Laney Homes mortgage is not legible in the retrieved text — that is a gap I flag rather than guess.

**JUDGMENTS / LIENS against Laney Homes LLC.** The title abstractor ran the name LANEY HOMES LLC through the court/clerk indices and the result returned was "NO RECORDS FOUND" with "Matching Results: 2" reflecting only the related recorded instruments (the Stone/Godwin affidavit and the deed), not adverse judgments or liens [#135]. In other words, the search of the vesting owner's name surfaced no civil judgments or liens against Laney Homes LLC itself.

**Other names searched.** Because title passed through the Estate of Janet S. Godwin, the abstractor also searched the heirs/grantors — GODWIN, STONE, YOUNG (Joseph and David), KEENE, JOHNSON (Kimberly and Wanda), MUNDY, LINDSEY and ADAMS [#66]. Those name runs returned mostly unrelated court matters (probate, traffic, misdemeanor, domestic-relations, small-claims cases tied to the individual heirs) rather than recorded liens or money judgments encumbering the parcel [#136][#137][#138][#139]. The Godwin/Janet probate matters (e.g., 2024CP000842AX, closed 04/04/2024) are estate proceedings, which is how title devolved to the grantors who then conveyed to Laney Homes [#136]. These personal-name hits are not, on their face, recorded encumbrances against 904 Bayshore Dr.

**Taxes (for completeness).** Ad valorem taxes for 2025 were $6,843.04 and are reported PAID [#66]; the combined taxes and assessments figure on the 2025 tax notice is 7,107.50, with a North River Fire District non-ad-valorem assessment [#3]. No delinquent-tax lien is indicated for the current owner.

**Bottom line.** As of the 5/28/2026 effective date, the only encumbrance affirmatively recorded against 904 Bayshore Dr in the name of the current owner is a single mortgage given by Laney Homes LLC dated 5/20/2025 to a lender whose name begins "KIAV…" [#2][#65]. The search of the vesting owner Laney Homes LLC returned no records of adverse judgments or liens [#135]. 

**Gaps / cautions:** (1) The retrieved text does not legibly capture the recorded principal amount or the complete lender name of the Laney Homes mortgage — pull the full instrument before relying on those particulars. (2) The title report's dedicated "Judgments" and "Liens" result lines for the parcel were not fully captured in the retrieved chunks; while the Laney Homes name search shows no records, I could not independently confirm a parcel-level "No Records Found" line for judgments/liens from the quoted text. I recommend confirming directly against the full Prowess report (Order dated 6/7/2026, effective 5/28/2026) and the recorded mortgage instrument.

— Provenance: 266 sources across {'title_report': 177, 'attachment': 89} | corpora {'unknown': 266} | mode=analysis | date span 2012-05-07 → 2026-06-08 | facts verified 10/10

---

### Q31. Give me the chronological timeline of 904 Bayshore Dr, Terra Ceia FL.
- **Property:** 904 Bayshore Dr, Terra Ceia FL (ent_prop_2179310301) · is_david=False
- **Ground truth:** owners=['LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 1, 'lis_pendens': 0, 'judgments': 0, 'assignments': 0} · events=7 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=18 verified=18 · sources={'title_report': 119, 'attachment': 82}
- **Answer:**

Here is the chronological title/event timeline for **904 Bayshore Dr, Terra Ceia, FL 34250 (Manatee County Parcel ID 2179310301)**, drawn from the Prowess Title Abstracts full search (Search Date 6/7/2026) and its attached deed chain and mortgage records [#108][#1].

**1982 — First recorded conveyance.** On 10/25/1982, Thomas Stanton, joined by his wife Virginia K. Stanton, conveyed the property to Paul R. Wilson and Martha I. Wilson, husband and wife, for a consideration of $24,800.00 (Book/Page 1036/3082) [#1].

**1984 — Interspousal quitclaim.** By deed dated 6/27/1984 and recorded 8/30/1984, Paul R. Wilson and Martha I. Wilson, his wife, conveyed the property to Paul R. Wilson alone, for nominal consideration of $10.00 (Book/Page 1089/3026) [#1].

**2000 — Sale to the Godwins.** On 2/23/2000, Paul R. Wilson, a single man, conveyed the property to John E. Godwin and Janet S. Godwin, husband and wife, for $215,000.00 (Book/Page 1625/3036) [#1][#108]. The Godwins held title for roughly the next 25 years; Janet S. Godwin's estate later figured into the chain.

**2025 — Estate conveyance to Laney Homes LLC.** By deed dated 4/11/2025 and recorded 5/21/2025 (Instrument 202541064175), Sherry Stone — as Personal Representative, individually, and heir/devisee of the Estate of Janet S Godwin a/k/a Janet Godwin — together with Joseph Young, Douglas Adams Jr. and the other Godwin heirs, conveyed the property to Laney Homes LLC, a Virginia limited liability company, for $400,000.00 [#108][#1]. The deed was signed/notarized in the Commonwealth of Virginia before notary Albert Coleman III [#2].

**2025 — Kiavi acquisition mortgage.** Laney Homes LLC, as borrower, gave a mortgage to Kiavi Funding, Inc., a Delaware corporation, dated 5/20/2025 and recorded 5/21/2025, in the amount of $360,000.00 (Instrument 202541064176) [#1][#182]. This mortgage was recorded the same day as the vesting deed, consistent with a purchase-money/acquisition loan.

**2025 — RKB Consulting construction/second mortgage.** Laney Homes LLC also gave a mortgage to RKB Consulting Group, Inc., dated 6/3/2025 and recorded 6/6/2025 (Instrument 202541071016), in the amount of $736,256.93 [#1][#169]. The instrument is styled as a Florida "Construction Mortgage" and recites the principal balance due upon maturity of $736,256.93 [#168][#169].

**2025 taxes.** The title report reflects 2025 taxes of $6,843.04 with a status of PAID [#108].

**2026 — Current status.** As of the Prowess Title Abstracts full search dated 6/7/2026 (effective date 5/28/2026), the vesting owner of record is Laney Homes LLC, a Virginia limited liability company [#108]. The current record reflects Laney Homes LLC as owner with the two 2025 mortgages (Kiavi $360,000.00 and RKB $736,256.93) outstanding against the property.

**Gaps / caveats.** This timeline is built almost entirely from a single source — the 6/7/2026 Prowess Title Abstracts full search and its attached deed-chain summary and recorded mortgage images [#108][#1]. The report itself notes some prior images were unavailable, and the 1984 quitclaim ($10.00) reflects an intra-family transfer rather than an arm's-length sale. I did not locate any recorded lis pendens, judgment, or foreclosure against this specific Terra Ceia parcel in the corpus (the $400,000.00 and $360,000.00 figures that appear elsewhere in the file relate to unrelated New York properties/litigation, not 904 Bayshore Dr). If you need the underlying recorded instruments (the Stone-to-Laney deed image, the Kiavi mortgage, and the RKB construction mortgage) as standalone exhibits, those should be pulled directly from Manatee County records for filing.

— Provenance: 201 sources across {'title_report': 119, 'attachment': 82} | corpora {'unknown': 201} | mode=analysis | date span 2012-07-17 → 2026-06-08 | facts verified 18/18

---

### Q32. Are there any suspicious or voidable transfers involving 904 Bayshore Dr, Terra Ceia FL?
- **Property:** 904 Bayshore Dr, Terra Ceia FL (ent_prop_2179310301) · is_david=False
- **Ground truth:** owners=['LANEY HOMES LLC, A VIRGINIA LIMITED LIABILITY COMPANY'] · facts={'chain_of_title': 3, 'mortgages': 2, 'liens': 1, 'lis_pendens': 0, 'judgments': 0, 'assignments': 0} · events=7 · findings=[]
- **Verification:** VERIFIED_FIRST_PASS · facts=16 verified=16 · sources={'title_report': 110, 'attachment': 98}
- **Answer:**

**Yes — there are at least two features of the 904 Bayshore Dr, Terra Ceia FL chain of title that warrant scrutiny, although nothing in the record establishes an adjudicated voidable transfer. The clearest red flag is an oversized, post-acquisition mortgage to a DeRosa-/Bhargava-affiliated insider.**

**The property and the operative transfer.** 904 Bayshore Dr (Manatee County Parcel ID 2179310301) is currently vested in Laney Homes LLC, a Virginia limited liability company [#90]. Title passed to Laney Homes by a warranty deed recorded 5/21/2025 (Inst. 202541064175) for stated consideration of $400,000.00, with documentary stamp tax of $2,800.00 — consistent with a $400,000 sale price [#1][#95]. The grantors were the heirs/devisees of the Estate of Janet S Godwin (Sherry Stone as Personal Representative, Joseph Young, David Young, Betty Keene, and Douglas Adams, Jr., among others), conveying out of the decedent's estate to Laney Homes LLC [#96][#100]. The Godwins had owned the property since a 2/23/2000 purchase for $215,000.00 [#1]. The estate-sale deed itself is an arm's-length-looking conveyance; the $400,000 price is below the 2025 county just/market value of $495,514, but a modest discount on an estate sale is not by itself voidable [#91].

**Red flag #1 — the RKB Consulting mortgage.** The same day-cluster as the purchase, Laney Homes encumbered the property twice. First, a purchase-money mortgage to Kiavi Funding, Inc. for $360,000.00 was recorded 5/21/2025 (the same day as the deed) [#1]. Then, only about two weeks later, a second mortgage to **RKB CONSULTING GROUP, INC. for $736,256.93** was recorded 6/6/2025 (Inst. 202541071016) [#1][#143]. This is the most suspicious item: (a) the second lien ($736,256.93) is larger than the entire purchase price ($400,000) and the appraised value ($495,514), so total recorded debt of roughly $1.096 million vastly exceeds the property's value — a classic equity-stripping / asset-shielding pattern; and (b) the lender, RKB Consulting Group, Inc., is not an independent institutional lender but an entity tied to the DeRosa/Bhargava network at the center of this case. RKB Consulting Group, Inc. is shown with an address at **24 Oak Lane, Roslyn Heights, NY 11577** [#175], the very same "24 Oak Ln c/o Rakesh Bhargava" address associated with the Bhargava-affiliated TN5161, LLC [#201]. RKB Consulting Group also appears as a buyer/counterparty in DeRosa-related LLC-interest transactions (e.g., the Contract-v1 MSW agreement with GMR Real Estate Holdings, LP) [#175]. An above-value mortgage to an insider entity is the hallmark of a transfer designed to encumber equity beyond the reach of creditors.

**Red flag #2 — relationship to the broader fraudulent-transfer pattern.** This case file is replete with adjudicated and alleged fraudulent-conveyance conduct by David DeRosa and his affiliated entities (Island Properties & Associates, IPA Asset Management, MangoTree, etc.), including causes of action for fraudulent transfer under New York Debtor & Creditor Law and a documented pattern of moving title among single-purpose LLCs without fair consideration [#7][#11][#79]. The RKB lien on 904 Bayshore fits that modus operandi (insider liens recorded against newly acquired property), which is why the transaction deserves investigative attention even though 904 Bayshore is a Florida property outside the New York litigation.

**What is NOT established.** Importantly, the Prowess title report dated 6/7/2026 found "No judgment/liens found" on the property apart from the two mortgages [#1], and there is no recorded lis pendens, judgment, or court order in the file declaring any 904 Bayshore transfer void or voidable. The estate deed and the Kiavi purchase-money mortgage appear regular on their face. I have not located any document directly linking Laney Homes LLC to DeRosa, so the insider connection runs through the RKB lender, not the buyer.

**Bottom line / recommendation.** The transfer most likely to be attacked as suspicious/voidable is the **$736,256.93 RKB Consulting Group mortgage recorded 6/6/2025**, because it is an above-value lien from a Bhargava-affiliated entity recorded immediately after acquisition — consistent with equity-stripping. I recommend (1) confirming who controls Laney Homes LLC and whether DeRosa has any beneficial interest; (2) obtaining the RKB note to test whether it secures any genuine advance (fair consideration); and (3) checking for any flow of funds between RKB/Bhargava and Laney Homes. The evidence here is suggestive, not conclusive.

— Provenance: 208 sources across {'title_report': 110, 'attachment': 98} | corpora {'unknown': 208} | mode=analysis | date span 2012-03-12 → 2026-06-08 | facts verified 16/16

---

