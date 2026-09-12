# ECSE Week 3 Project Log

## 9/7 No Class (Labor Day)

## 9/8 No work due (Tuesday)

## 9/9 Guest Lecturer on Engineering Standards
- Interesting discussion and I liked the icebreaker example of having human software somehow breaking alien encryption as if aliens code in the latin alphabet and use the arabic numeral system, funny example of a standard that is paradoxically a plothole. There wasn't anything I didn't like, perhaps there were too many examples of standards themselves like basketball sizes cable plugs etc. The talk made me think about the standards that are used in device communication and graphical output like USB HDMI DisplayPort
- Completed engineering standards quiz (17/17)
- Completed my section **Personas** on project needfinding assignment for 10 of the rubric points, also created Figma and word document the team worked off of
## 9/10 No work done (Thursday)

## 9/11 Internal team meeting, Completed ESP32 Playing with sensors Lab
- I was responsible for setting a meeting time and leading the internal meeting discuss at 1:00 PM on Friday 9/11

**Minutes from the meeting via Joe F** 
## 2026-09-11: Internal Team Meeting Minutes

**Time:** 1:00–1:30 PM · **Platform:** Google Meet · **Minutes recorded by:** me (Joe Falkenburg), team secretary

| Meeting date | Team member | Attendance |
| --- | --- | --- |
| 2026-09-11 | Joe Falkenburg | Present |
| 2026-09-11 | Ayan Sheikh | Present |
| 2026-09-11 | Emmett Gillespie | Present |
| 2026-09-11 | Daniel Lim | Present |

### 1. Purpose of the Meeting

We reviewed our roles, how we will manage shared documents, and how to use our weekly meeting time as the project moves toward prototyping. We also discussed possible approaches to the seed loss at Don's feeder, building on the stakeholder interview and our work together on the Project Background and Needs Statement we'd completed 2 days earlier.


### 2. Roles and Division of Work

We went through the submitted team contract so everyone understands the responsibilities across the team, not just their own role. These roles establish who coordinates each part of the work; we will still contribute equally to the substance of our assignments of course.

#### Me (Secretary and Stakeholder Communication)

I will continue taking meeting minutes, distributing them to the team, documenting attendance, communicating with Don, and coordinating times for Don to meet with us. We also decided to make a change relative to the team contract. We decided that while I will continue to prepare agendas for meetings with Don, I will now share the responsibility of creating agendas for all other meetings with Ayan. I will continue to send all agendas. This shift relative to the contract is to be more consistent with the role of secretary and team lead. Secretaries wouldn't typically do this (though they do in the template I noticed), but we felt I had unique perspective having been taking minutes and tracking progress so I can be helpful at reconciliong between meetings to properly divide tasks.

We discussed including an attendance table at the beginning of the minutes with each team member's name. A stakeholder row can be included when relevant, with Don's attendance indicated for meetings involving him.

#### Ayan (Team Lead) — Internal Meetings, Schedule, and Instructor Communication

Ayan will now share the responsibility of preparing agendas for our internal meetings with me.

He will continue organizing our meetings, keeping us on schedule, reminding us about upcoming assignments, and following up on progress and completion. The team lead will also be the first point of contact with Professor Fu for clarification, extension requests or other input, and will copy the rest of us on those conversations so everyone stays in the know.

#### Emmett (Document Management and Shared Workflow)

Emmett will initiate new assignment documents and make them available for everyone to work on. This includes getting the templates from Canvas, setting up the working files, and making them shareable. He will also create web-based materials such as Figma boards, either from scratch or from the materials Professor Fu provides. Emmett has been using the shared Google Drive and has been handling document formatting and Canvas submissions; those responsibilities will continue.

We will add the two existing Word documents from OneDrive to our shared Google Drive so that the files are centralized and accessible to everyone.

Google Docs will be our main platform for collaborative writing. We prefer its shared editing, but we had been using Word because of formatting problems with the documents in Google Docs. For each assignment, we can either import the Word template and repair the formatting or work in a blank Google Doc, depending on how much effort the formatting fixes require.

Word remains an option when the required formatting does not transfer well. In that case, we can collaborate on the content in Google Docs and have Emmett transfer it into the final submission document. He will check the final formatting, upload the submission to Canvas, and keep the final version in our shared Drive.

#### Daniel (Procurement, Component Research, and Costs)

Daniel's procurement responsibilities will become more active as we move beyond the individual labs and start building prototypes. He will coordinate materials beyond the ESP32 and our laptops, including items such as a housing or enclosure and any additional resistors, wires or other components we need.

For lab supplies, the lab assistant (not sure how to spell his name --- Devonte?) was recommended as a good first point of contact rather than going straight to John Gibbons. We also noted that other graduate students working in the lab may be able to help us find what we need.

Daniel will take the lead on researching physical components needed to fulfill our design, and tracking costs, with the rest of us helping with again, the research of what we may need to fulfill our design (as that is less core to this role, which is sourcing the decided-upon tools, and moreso the project itself). The aim is to have materials coordinated and ready when we reach the stage that needs them, rather than leave sourcing until we are ready to build.

We discussed whether anyone had used their Thinkbox credit and expect to have the full $200 available as a team. Ayan reiterated Professor Fu's expectation that we should not need to spend our own money on the project. We can develop the initial concept ideas without buying materials, then use the available lab resources and Thinkbox credit as we move into more developed physical prototypes.

#### Changes to the Team Contract (sorta)

As mentioned above, we informally adjusted the team contract. Ayan suggested we document this adjustment in the minutes rather than revise the contract for this small change. Professor Fu has said the roles can change during the semester; we will update the contract if we make a more substantial change to the division of responsibilities.

We also clarified that meeting agendas do not need to be formal documents: a group-chat message before the meeting with two or three discussion points would suffice to give the conversation structure. This is less-so a contractual shift and moreso hardening how our roles will manifest.


### 3. Initial Design Directions

We all participated in the stakeholder interview and in writing the needfinding document. That work gave us time to think through Don's situation, background and preferences. The purpose of this discussion was to start generating possible directions from that understanding, not to repeat the entire needfinding exercise.

#### Preserving the Feeder

Don's weight-based idea remains a starting point, but we are concerned that implementing it could alter the feeder too much. Its sentimental value makes preserving its appearance an important consideration. We want to avoid modifications that could deface it or substantially change how it looks.

We discussed putting equipment in the surrounding area rather than building it into the feeder. The house and the support pole are possible mounting locations because the feeder hangs close to them. We all had different views on whether mounting underneath the feeder should be a fallback if those locations do not work well in a prototype, or whether the underside is already the most practical location. We did not settle on a mounting arrangement, but I think we're ahead anyways, and allstill gaining info, so all good.

#### Light-and-Sound Deterrent

One possible direction is a small animal-repellent device, potentially attached underneath the feeder, that responds to an approaching deer with a flashing light and sound. We discussed existing deterrent devices as a reference and the possibility of making a smaller version suited to this installation.

Connecting a light to the ESP32 seemed feasible with our current lab resources. For sound, dog whistles were raised as an example of animals responding differently to sound and suggested researching whether a sound could discourage deer without also discouraging the birds. The goal is to preserve the birds' ability to approach, perch and feed, rather than simply drive all animals away.

We also compared preventing a deer from reaching the seed with relying on a closure to work once it has already approached the feeder. A safety-training analogy I thought we cool also came up. Which was preventing an unwanted situation rather than depending on a last-minute safeguard such as a harness. In this case, the preference was to act as a deer approaches the area around the feeder rather than rely entirely on a trapdoor closing at the point of access.

#### Automatic Nighttime Closure

A second direction we discussed was to close access to the seed at night and reopen it during the day. This would address the period when Don has noticed the seed disappearing without necessarily having to distinguish between different animals.

The reasoning was that Don is not watching birds at night. Emmett looked it up and found that the birds expected at this type of feeder sleep at night. We therefore thought a nighttime closure might protect the seed without taking away a useful feeding period. It could also replace the extra handling involved in bringing the feeder inside overnight to protect it.

The main limitation we discussed is daytime access by deer. We cannot rule out a deer approaching and taking seed during the day, and a system that only closes at night would leave that situation unaddressed. We favor the simplicity of the idea, but that tradeoff still needs to be considered.

We discussed two ways to control the timing. An internal clock could determine when the feeder opens and closes, potentially with a way for Don to choose the active hours. Alternatively, a light detector could trigger closure when the surrounding light drops below a threshold. Both control methods remain in consideration.

We also considered whether the closure would be attached to the feeder itself or provided by a separate enclosure around it. We're leaning against a feeder-mounted trapdoor because it would require placing a mechanism directly on the feeder, contrary to our preference to avoid modifying it.

The separate-enclosure idea would sit above the feeder and lower around it at night, with the bottom then closing so that the seed is inaccessible from all sides. This was a possible way to block access without building a trapdoor into the existing feeder, but we have not worked out which physical arrangement would be feasible. More to come.

#### Weather Exposure and Moving Parts

We need to consider snow, rain and other harsh outdoor conditions. Moving closures may be more difficult to weatherproof, although we have not yet established how much harder they would be to protect.

The lowering enclosure would involve several moving parts. We were concerned that a weak link could break and prevent the whole closure from working. The light-and-sound idea appealed in part because it would avoid that moving enclosure or trapdoor. We all agreed that reducing reliance on moving parts is worth keeping in mind as we compare approaches.

#### How Far to Take the Planning Now

We reminded ourselves that the needfinding assignment was about understanding Don's needs, not choosing a solution. We should keep several realistic ideas available, avoid putting too much detailed planning into one approach too early, and be ready to change direction as we prototype and learn what we can implement.

We are still learning to use the devices in the individual labs, so this brainstorming may be ahead of the immediate course work. We nevertheless agreed it is useful to begin the conversation now that we have worked through the interview and needfinding document together. No final design was selected. We will continue discussing the ideas in the lab. An iterative and dynamic mindset is key!


### 4. Weekly Meeting Format and Time

Most of our future weekly meetings will be in person during the existing time slot, around the South Quad. Olin or another nearby location would be convenient given where we already meet for class and lab. Finding separate places to join a virtual call is inconvenient, including having to take the call from a hallway.

We can still use a brief phone call or a short meeting when there is little to cover. In the coming weeks, while we are mainly preparing for the project, some updates may be handled and documented over text. We will decide what makes sense based on the amount of work and discussion needed.

We considered reducing next week's meeting to 30 minutes rather than an hour. Ayan's call  was to keep the one-hour block reserved, even if the discussion itself only needs about 30 minutes. Once we move beyond the individual labs, that time can serve both for coordination and for working on the prototype. We had an idea for roughly half an hour of discussion followed by half an hour of project work as an example of how the block could be used. A good idea, but def not a fixed agenda for every week, which we agreed.


### 5. Recent Materials from Don and Email Follow-Up

Don has emailed me over the past few days with a link to the bird feeder and a video of birds feeding. I have already forwarded those messages to the rest of the team.

I will reply with the whole team included rather than only forwarding Don's emails afterward in hopes that Don will reply to all of us so everyone receives the correspondence directly and stays involved.

I will send a brief thank-you in response to the feeder link from gifts.com, acknowledging that it is helpful. We agreed not to say "looking forward to talking soon" without a concrete ask to meet.


### 6. Follow-Up

- **2026-09-11 — Assigned follow-up:** Ayan: Work together with Joe on short agendas before internal meetings, continue tracking assignments and progress, and keep the one-hour weekly block available for discussion and future project work.

- **2026-09-11 — Assigned follow-up:** My follow-up: Work together with Ayan on short agendas before internal meetings, continue the minutes, attendance and stakeholder coordination; prepare agendas for meetings with Don; and send the thank-you reply with everyone included in the email thread.

- **2026-09-11 — Assigned follow-up:** Emmett and shared documents: Emmett will set up future working documents and boards and continue handling final formatting and Canvas submissions. We will centralize the two existing Word documents in Google Drive and use Google Docs for collaborative drafting.

- **2026-09-11 — Assigned follow-up:** Daniel: Lead component and materials research with help from the team, coordinate access to supplies as prototyping develops, and track the costs.

- **2026-09-11 — Assigned follow-up:** All of us: Continue comparing the deterrent and nighttime-closure ideas, including the questions about effects on birds, daytime deer access, mounting, weather protection and moving parts. Keep the planning flexible and continue the discussion in the lab before committing to a design. Key is again to be dynamic with new info, and embrace the iterative process rather than locking in without full context.
