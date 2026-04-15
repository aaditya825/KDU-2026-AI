"""Test package.
Use these against your app after ingesting [Spider-Man - Wikipedia](https://en.wikipedia.org/wiki/Spider-Man). They’re grouped to test different failure modes, not just recall.

**Basic Fact Recall**
- Who is Spider-Man’s alter ego?
- Where is Spider-Man’s place of origin?
- In which comic and issue did Spider-Man first appear?
- In what month and year did Spider-Man first appear?
- Who created Spider-Man?
- Who is Spider-Man’s publisher?

**Attribute Extraction**
- List Spider-Man’s abilities.
- What team affiliations are listed for Spider-Man?
- Who are listed as Spider-Man’s partners?
- What is Spider-Man’s full alter ego name?

**Multi-Fact Composition**
- Summarize Spider-Man’s publication debut, creators, and publisher in one answer.
- Give Spider-Man’s alter ego, place of origin, and first appearance together.
- Name two team affiliations and two partnerships mentioned on the page.
- What abilities and intellectual skills are explicitly listed for Spider-Man?

**Section-Specific Retrieval**
- According to the publication information, when did Spider-Man debut?
- According to the in-story information, what is Spider-Man’s place of origin?
- According to the abilities section, does Spider-Man use web-shooters?
- According to the article intro, what does this page say it is about?

**Citation / Grounding Checks**
- Who created Spider-Man? Cite the source chunk.
- What are Spider-Man’s listed abilities? Cite the exact supporting chunk(s).
- What is Spider-Man’s first appearance? Include citation(s).
- What team affiliations are listed? Include citation(s).

**Precision / Exactness**
- Is Spider-Man’s first appearance listed as `Amazing Fantasy #15` or `The Amazing Spider-Man #1`?
- Does the page list Miles Morales as Spider-Man’s creator, partner, or team affiliation?
- Is Black Cat listed as a partner or a team affiliation?
- Does the page say Spider-Man originates from Manhattan or Queens?

**Negative / Insufficient Context**
- What is Spider-Man’s real-world box office total?
- Who played Spider-Man in the highest-grossing movie?
- What is Spider-Man’s exact height and weight?
- What is Spider-Man’s MBTI personality type?

These should trigger “insufficient context” if your app is properly constrained.

**Ambiguity Handling**
- Who is Spider-Man?
- What is Peter Parker known for?
- What does “Spidey” refer to on this page?
- Is this page about every Spider-Man version or the main/original version?

**Reasoning / Comparison**
- How does the page distinguish publication information from in-story information?
- Which of Spider-Man’s listed abilities are physical powers versus learned skills?
- Based on the page, is Spider-Man portrayed more as just a superhero or also as a scientist/engineer?
- What evidence on the page supports calling Spider-Man both superhuman and highly intelligent?

**List Completeness Checks**
- Give all team affiliations shown on the page.
- Give all partnerships shown on the page.
- Give all abilities shown on the page without adding anything extra.
- Name every creator listed on the page.

**Robustness Against Hallucination**
- What romantic interests are listed in the visible infobox?
- Is Mary Jane Watson listed in the visible partnerships section?
- Does the visible page say Spider-Man was created only by Stan Lee?
- Does the visible page list Daily Bugle as a team affiliation?

**Short vs Long Answer Quality**
- Answer in one sentence: Who is Spider-Man?
- Answer in three bullet points: publication debut, creators, and origin.
- Give a concise summary of Spider-Man based only on this page.
- Give a detailed summary with citations only from the ingested page.

If you want, I can turn this into:
1. a CSV/JSON evaluation set, or
2. a rubric with expected answer points and pass/fail criteria.

I called the Gemini models API with your configured key. Your requested model `gemini-3.1-flash-preview` is not available, which is why you got the `404 NOT_FOUND`.

Models available to your account for `generateContent` include:

- `models/gemini-2.0-flash`
- `models/gemini-2.0-flash-001`
- `models/gemini-2.0-flash-lite`
- `models/gemini-2.0-flash-lite-001`
- `models/gemini-2.5-flash`
- `models/gemini-2.5-flash-image`
- `models/gemini-2.5-flash-lite`
- `models/gemini-2.5-flash-preview-tts`
- `models/gemini-2.5-pro`
- `models/gemini-2.5-pro-preview-tts`
- `models/gemini-3-flash-preview`
- `models/gemini-3-pro-image-preview`
- `models/gemini-3-pro-preview`
- `models/gemini-3.1-flash-image-preview`
- `models/gemini-3.1-flash-lite-preview`
- `models/gemini-3.1-pro-preview`
- `models/gemini-3.1-pro-preview-customtools`
- `models/gemini-flash-latest`
- `models/gemini-flash-lite-latest`
- `models/gemini-pro-latest`

Recommended choices for your app:
- `gemini-2.5-flash` for stable/default use
- `gemini-2.5-pro` for stronger reasoning
- `gemini-3-flash-preview` if you want the newer preview flash model
- `gemini-3.1-flash-lite-preview` if you specifically want a `3.1` flash-family variant that your account actually has

So:
- `gemini-3.1-flash-preview` -> not available
- `gemini-3-flash-preview` -> available
- `gemini-3.1-flash-lite-preview` -> available

If you want, I can now update the app default to one of the available models, for example:
- `gemini-2.5-flash`
- `gemini-3-flash-preview`
- `gemini-3.1-flash-lite-preview`


Use these against `docs/test_doc.pdf`. They’re based on the extracted content of the PDF, which is ISO/IEC 27001:2022.

**Basic Fact Recall**
- What is the full title of ISO/IEC 27001:2022?
- Which edition of ISO/IEC 27001 is this document?
- In what month and year was this edition published?
- Which organizations form the specialized system for worldwide standardization mentioned in the foreword?
- Which committee prepared this document?

**Scope and Purpose**
- What does Clause 1 say this document specifies?
- Does the document say its requirements are generic or organization-specific?
- According to the scope, can Clauses 4 to 10 be excluded if an organization claims conformity?
- What does the introduction say an information security management system preserves?
- According to the introduction, why is adopting an ISMS considered a strategic decision?

**Exact Clause Questions**
- What does Clause 4.1 require an organization to determine?
- What does Clause 4.2 require regarding interested parties?
- What does Clause 4.3 require when determining the ISMS scope?
- What does Clause 4.4 require an organization to do?
- What does Clause 5.1 require from top management?

**Policy and Leadership**
- According to Clause 5.2, what must the information security policy include?
- According to Clause 5.2, how must the information security policy be handled inside the organization?
- What responsibilities must top management assign under Clause 5.3?
- What does Clause 5.1 say about continual improvement?
- What does Clause 5.1 say about resources for the ISMS?

**Risk Management**
- What does Clause 6.1.1 require the organization to consider when planning the ISMS?
- What are the purposes listed in Clause 6.1.1 for addressing risks and opportunities?
- According to Clause 6.1.2, what must the information security risk assessment process establish and maintain?
- What does Clause 6.1.2 say about repeated risk assessments?
- According to Clause 6.1.3, what must the risk treatment process do?

**Normative References and Definitions**
- What is the normative reference listed in Clause 2?
- Where does Clause 3 say the terms and definitions come from?
- Which terminology databases are mentioned in Clause 3?
- Does the document use dated or undated references for ISO/IEC 27000?
- What does the document say about amendments for undated references?

**Document Structure**
- What are the main clause headings from 4 to 10?
- Which clause covers “Support”?
- Which clause covers “Performance evaluation”?
- Which clause covers “Improvement”?
- Which clause contains “Planning”?

**Annex A Controls**
- How is Annex A structured at a high level?
- What are the four control themes shown in Annex A?
- Which Annex A section includes “People controls”?
- Which Annex A section includes “Physical controls”?
- Which Annex A section includes “Technological controls”?

**Annex A Specific Controls**
- What does control 5.7 cover?
- What does control 5.15 cover?
- What does control 5.23 cover?
- What does control 5.31 cover?
- What does control 5.34 cover?
- What does control 6.3 cover?
- What does control 7.7 cover?
- What does control 8.7 cover?
- What does control 8.15 cover?
- What does control 8.24 cover?
- What does control 8.31 cover?
- What does control 8.34 cover?

**Comparison / Reasoning**
- How does Clause 4.2 differ from Clause 4.3?
- How does Clause 6.1.2 differ from Clause 6.1.3?
- What is the difference between “risk assessment” and “risk treatment” in this document?
- How do people controls differ from technological controls in Annex A?
- Which controls seem most directly related to incident management?

**List Extraction**
- List the items top management must ensure under Clause 5.1.
- List the things an organization shall consider when determining ISMS scope under Clause 4.3.
- List the purposes of planning actions for risks and opportunities under Clause 6.1.1.
- List the controls in Annex A related to supplier security.
- List the controls in Annex A related to incident handling.

**Citation / Grounding Checks**
- What is the scope of ISO/IEC 27001:2022? Cite the clause.
- What does Clause 5.2 require for the information security policy? Cite the source.
- What does control 8.15 say about logging? Cite the exact chunk.
- What does control 5.23 say about cloud services? Cite the chunk.
- What does Clause 6.1.2 say about risk assessment consistency? Cite the relevant part.

**Negative / Insufficient Context**
- Who authored the original draft of ISO/IEC 27001:2005?
- What is the certification cost for ISO/IEC 27001 compliance?
- Which companies are currently certified against ISO/IEC 27001?
- What penalties apply for non-compliance with ISO/IEC 27001?
- What software tool does ISO recommend to implement these controls?

Those should produce “insufficient context” if the app is behaving correctly.

**Good Stress Questions**
- Summarize the purpose of ISO/IEC 27001:2022 in three sentences.
- Explain the difference between Clauses 4, 5, and 6.
- Give a concise overview of Annex A and its control categories.
- Which controls would be most relevant for remote work and cloud usage?
- Which controls would be most relevant for secure software development?

If you want, I can convert these into:
1. a structured evaluation sheet with expected answers, or
2. an easy/medium/hard benchmark set for your app.
"""

