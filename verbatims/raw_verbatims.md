# User Requirements - Raw Verbatims & Transcripts

**Project**: ONGC HR and Finance Agent  
**Target Audience / Primary Persona**: Chief Managing Director (CMD), ONGC  
**Location**: `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`  
**Captured Date**: October 19, 2026  

---

## 1. Engagement & Workflow Plan (Audio 1)

> "Now, I want to make an HR and Finance agent. And I will be giving you a set of verbatims first. You capture those verbatims to understand the business requirement. And then subsequently we will be drafting a formal documentation, okay?
> 
> So the first idea is to capture the notes, and for that there would be a set of verbatims that I will be giving. You have to make a folder, let's say in HR and Finance, this particular part, right? And then I'll be sharing a set of verbatims, and you can capture those verbatims to capture the business requirement.
> 
> And then using those verbatims, you can ask me question and answer, and I'll be giving you more and more detail. So after we have sufficient detail, we can go about building what we need to build. Let me know if it is aligned, then I will start sharing the verbatims."

---

## 2. Core Purpose, Persona & Outputs (Audio 2)

> "So this particular agent is an HR and Finance agent, and would be answering and giving the relevant documents, sheets as an output.
> 
> Now, this demonstration is for the Chief Managing Director, the CMD of ONGC. And he would like to ask ONGC-specific questions.
> 
> For now, there are data silos. They want knowledge management. So this particular agent would concern HR and Finance."

---

## 3. Role-Based Access Control (RBAC) & Data Strategy (Audio 3)

> "Now, when the agent is responding, there will be role-based access. The senior management should be able to get everything. But when a junior employee is logging in, or is asking, it should deny the information.
> 
> So the demo has to include role-based access, and demonstrate that certain information would be rejected. Now, again, the first is right authorization.
> 
> Now, some of the questions, we have to write what the CMD is expecting, what is in CMD's mind, the data around decision making. So the first step would be to ask the questions that CMD might be interested in, would also like to see those working.
> 
> Once we have drafted those questions, some of which I will share, some of which we can brainstorm, then we can see. Now based on the questions, we have to generate the data. And the data would be put on GCP, from which we will be fetching. Yeah. Now next, I will be sharing the set of questions."

---

## 4. Specific HR & Finance Questions, Decision Intents & Hierarchy (Audio 4)

> "Now the questions would be around, for example:
> 
> How many employees are in the Delhi office for the past 5 years or more? When CMD asks this question, they want to take a decision of transfers. So questions around transfers: who should be transferred when, right?
> 
> Similarly, the CMD can ask which areas did not see a headcount increase, or which areas saw the most headcount. So this is again HR.
> 
> Similarly, there will be questions around finance: Which fields are the most profit-making? Or which fields are the loss-making? In which fields we have done the most investment? Which fields are under-invested? So all these questions around finance.
> 
> So we have to first deliberate a set of HR and finance questions that will be relevant to a CMD, the Director HR, and the Director Finance.
> 
> Then we should also think about, let's say, a person who is, let's say just an E1 officer in ONGC or an E2 officer, E1 to E4 hierarchy. So this is a case in point. Let me know what you think."

---

## 5. First Priority & Focus: Question Formulation by Role (Audio 5)

> "Now, you save this verbatim as well.
> 
> So the first step is not Cloud Run, and the first step is not front-end, it is none of that. The first step is not access.
> 
> The first step is: what are all the relevant questions you think a company like ONGC will have? This will be the first step.
> 
> So the questions for the CMD, the questions for the Director, and the questions for the E1 officer.
> 
> Once we have a clear idea on those questions, only then we can move forward. So let's align and discuss on the questions. Now save it as, again, the verbatim."

---

## 6. User Experience: Hands-Off & Voice/Audio-Governed Interaction (Audio 6)

> "Let's save the second verbatim.
> 
> So this is about how would the experience be, and then I will be giving details of the user interface, but let me talk about the user experience.
> 
> So first and foremost, the user would be completely hands-off. And the entire platform would just be governed by audio, mostly as a primary way to operate.
> 
> And the CMD should be able to ask a question, instruct, and should be able to get the desired output in the desired format. For example, if the CMD asked... let's say any data question from the list of questions..."

---

## 7. Interactive Visualizations (Plotly/Dash) & Multi-Format Export (Audio 7)

> "So let's take the very first example, right: 'How many executives have been posted in Delhi for the past 5 years or more? Breakdown by grade and discipline.'
> 
> So one is just showing the data, and what I'm saying is it should also be presented as a graph or something. Let's say in this case it can be, I would say, a pie chart, that these are employees posted for the 5 years and this is let's say the different segments.
> 
> And I would say this visualization has to be built in. And depending on the data types, there will be different pie charts, there'll be, you know, histograms, and the list of different visuals that we should have.
> 
> And this will be, I will say, in Plotly Dash, kind of a dashboard. One should be able to speak and those dashboards should appear.
> 
> And ultimately if I want to export it, it should be able to export either Google Sheets, Google Docs, even Word or PDFs.
> 
> So this is what the expectation is from the user experience. Now capture both of these in the verbatims."



---

## 8. Experience Clarifications (typed in chat, 19-Oct-2026 15:39)

> "1. Language will be Hindi and English. 2. When I say voice I meant voice and written text. There should be flexibility. 3. It will depend. If it's a different question then it can be a replacement. I am thinking if one can have kind of a running text as one has in Gemini Enterprise so that one will not have a new text but a running history of one chat and in that chat CMD can ask anything. 4. Agents should be brief in response — neither one-liner nor full answer. 5. It would be a female voice, pleasing, with an Indian accent. 7. Most likely it will be a big screen of some sort. 6. I will be using my Google account so it's OK. I will be giving a demo from my laptop."

---

## 9. Voice Choice, Floating Chat, Siri-like Input, AlphaEvolve Theme, Light/Dark (typed in chat, 20-Oct-2026 05:15)

> "I will go with Leda. Also on the design the chat interface will be on the right. It will be floating with an option to minimise and go full screen. Then only action will be done there. It can have something similar to Siri that you see that the audio is going in as input. So the flexibility will be there with the user. Also have downloaded the AlphaEvolve theme. Can you check if we can bring that alive in this demo? Also there will be an option of going dark and light mode and I will assume the CMD will prefer the light mode as default. As it concerns with policy, HR and finance, so they are usually documents and hence light theme."

---

## 10. Name, Greeting, Delegation of Remaining Choices (typed in chat, 20-Oct-2026 05:43)

> "1. Yukti AI. 2. You can say just give a basic intro. We can refine. Like 'Hello I am Yukti, your HR and Finance agent. Please tell me how can I help?' Rest go with what is most suitable. Now go."
