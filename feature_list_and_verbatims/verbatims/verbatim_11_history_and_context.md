# Verbatim 11: Multi-Turn History Preservation & Conversational Context

**Date Captured**: October 22, 2026, 04:40 UTC  
**Source**: Audio Recording  
**Persona**: Product Sponsor / CMD Interaction Lead  
**Tags**: `#ux` `#history` `#canvas-stream` `#multi-turn-memory` `#context`

---

## 1. Verbatim Transcript

> "Now save this as first verbatims and then we will save a feature list.
> 
> Now currently the application is running, but I would like to see: if I'm asking a question and a response, every time I'm asking a question, the screen changes and I do not see the previous question. So basically in a way, every question, even in an interaction, becomes a new question without the reference to the history.
> 
> So what I would like in the application is, so if a person logs in and is there on their screen, if a person asks a question, let's say 'how many employees are there in New Delhi?', then it will show a screen. Now if the next question is asked, the second thing should appear, and then the first thing should not completely disappear. It should scroll up, as generally happens on let's say Gemini or any other interface of Claude or ChatGPT. So this is the first feature, I think, to preserve the history.
> 
> And secondly, when a person is responding, there should be certain context, right, that should be captured. So this is, I would say, the second.
> 
> So save this as a verbatim and as a feature list, and I would like to maybe separate out these verbatims so that it is clear what is expected.
> 
> And then I would like to review and audit, and make the most exhaustive list of how those visuals can be represented. Currently it is okay, but identify any gaps in a sense that how it can be made better. This will be the second thing. So let's implement this, like identify, build the feature list, and then we talk about the next. So save this verbatim first."

---

## 2. Core Problem & User Friction Identified

1. **Destructive Canvas Replacement**: Every question clears the entire display canvas. Users lose visual context of previous data, tables, or charts they just analyzed.
2. **Context Amnesia**: Each query is treated as an isolated single-turn command. Follow-up queries (e.g. asking for discipline breakdown after asking for Delhi headcount) fail to inherit the active entity, filters, or parameters.

---

## 3. Key Directives Extracted

* **Preserve History in View**: Do not replace the screen. Append subsequent turns and smoothly scroll upward (standard Gemini / Claude / ChatGPT interaction model).
* **Multi-Turn Context Carry-Over**: Maintain conversational session state so subsequent responses inherit context from earlier questions in the same session.
* **Separation of Concerns**: Maintain clean, separated verbatim logs and corresponding actionable feature specifications.
