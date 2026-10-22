# Verbatim 13: CMD Named Employee Roster & Transfer Actionability

**Date Captured**: October 22, 2026, 04:47 UTC  
**Source**: Audio Recording  
**Persona**: Product Sponsor / CMD Interaction Lead  
**Tags**: `#hr-roster` `#cmd-view` `#transfers` `#employee-names` `#data-granularity` `#actionability`

---

## 1. Verbatim Transcript

> "The second thing is when I'm asking for a question, let's say give me the... as a CMD, so sometimes I would like to know the name of the employees. A CMD should be able to see the name of the employees. For example, the question can be:
> 
> 'Can you give me a list of all the people who are employed in the Delhi office for more than 5 years? Give me their name, their designation, their seniority in terms of E1, E2, and their tenure in ONGC, and their time in the Delhi office.'
> 
> Currently it is only giving me an aggregated view, it is not giving me the exact name of the people.
> 
> Now as a CMD, these are the kind of information that he would like to see, so that an action can be taken on that. So see what is missing in this, also save it as a verbatim and a feature request. So it can only be generated once the data is there, then we will talk about okay what is needed in the data and any data gaps. Also save this first."

---

## 2. Core Problem & User Friction Identified

1. **Over-Aggregation Blocks Action**: Currently, asking about employees in Delhi for 5+ years only displays an aggregated donut or bar chart of headcount counts (e.g., 419 executives by grade). A CMD cannot make transfer decisions or initiate HR workflows without seeing the actual individuals.
2. **Missing Granular Fields**: The leadership view requires specific individual-level columns:
   * **Full Name**
   * **Employee ID (PERNR)**
   * **Current Designation**
   * **Seniority / Grade (E1, E2, E3, etc.)**
   * **Discipline / Domain**
   * **Total ONGC Tenure**
   * **Delhi Station Tenure**
3. **Role-Based Access Control (RBAC)**:
   * **CMD & Director (HR)**: Full unmasked view with individual names and action triggers (e.g., "Add to Transfer Proposal", "Draft Board Note").
   * **Junior Officers (E1–E4)**: Aggregated or masked view (`******`) to preserve privacy and prevent unauthorized peer surveillance.
