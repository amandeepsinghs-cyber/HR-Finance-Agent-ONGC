# User Requirements - Raw Verbatims & Transcripts

**Project**: ONGC HR and Finance Agent  
**Target Audience / Primary Persona**: Chief Managing Director (CMD), ONGC  
**Location**: `/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC`  
**Captured Date**: October 19–22, 2026 (entries 1–10 on 19–20 Oct; 11–14 on 22 Oct)  

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

---

## 11. Multi-Turn History Preservation & Conversational Context (Audio, 22-Oct-2026 04:40)

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

## 12. Voice Orb Elegance (Siri/Infinity Loops) & Executive UI Modernization (typed in chat, 22-Oct-2026 04:45)

> "Now also save this in the feature list. The current orb seems chaotic. I was looking for something more elegant like what you see in Siri with those infinity link of loops that move. I saw we did something decent for AlphaFold. See what can be improved, log this as a feature request. Also the frontend seems a bit too basic, how can we make it better and more professional without losing the simplicity?"

---

## 13. CMD Named Employee Roster & Transfer Actionability (Audio, 22-Oct-2026 04:47)

> "The second thing is when I'm asking for a question, let's say give me the... as a CMD, so sometimes I would like to know the name of the employees. A CMD should be able to see the name of the employees. For example, the question can be:
> 
> 'Can you give me a list of all the people who are employed in the Delhi office for more than 5 years? Give me their name, their designation, their seniority in terms of E1, E2, and their tenure in ONGC, and their time in the Delhi office.'
> 
> Currently it is only giving me an aggregated view, it is not giving me the exact name of the people.
> 
> Now as a CMD, these are the kind of information that he would like to see, so that an action can be taken on that. So see what is missing in this, also save it as a verbatim and a feature request. So it can only be generated once the data is there, then we will talk about okay what is needed in the data and any data gaps. Also save this first."



---

## 14. Upgrade Approval, Governance, UI-First Order & Granular-Data RBAC (typed in chat, 22-Oct-2026 05:21)

> "1. yes I approve the build but we should have a build.md file, a feature list and a step by step upgrade checklist.md before doing anything. We should have a robust documentation and confirmation mechanism and review mechanism so that we have a robust build. I will go with the UI first as it changes the feel and UI is ultimately tied to the brain as you said. See with names or any other data my idea is to show and expose the granular data on the CMD and Director level. On the E1-E4 level it can be aggregated summary or rejection. yes commit the current version first and say it as a baseline build."

---

## 15. Any-Chart Re-presentation & Elegant, Professional Plots (typed in chat, 22-Oct-2026 05:37)

> "go ahead. CMD and Directors see everything. 4. agree, 5 ok, 6. ok, as I said there should be many ways to present data and the user can also at time ask if the data needs to present in a different way. Eg if there is a histogram presented as default then the user may ask to present it in a pie chart or other type of plots and the interface should be able to plot the data in the required format. Also the plots should be elegant and the most professional it is the main thing giving the impression of the platform and interface."

---

## 16. Google AI Mode "Aura" Palette (typed in chat, 22-Oct-2026 06:32–06:57)

> "for the color pallete. On the new google home page there is a color aura type on Ai mode. can we have that color palette?"
>
> "I have taken a photo of the screenshots and are in the repo. Now the thing is there are just photos I would like actual brand colors. Can you first confirm that you understood which colors are these? 2. yes I agree with this. 3. I agree with the order"
>
> "Wait my concern is that what you are saying seem you are recommeding the dark bold colors while the aura is very light feathery and majestic. Are we aligned in that? do you want to build it and show me first so that i can trust you?"
>
> "yes" (prototype v3 approved)
