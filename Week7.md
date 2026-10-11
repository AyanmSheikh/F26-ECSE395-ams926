# ECSE Week 7 Project Log

## 10/05 Work on System Archtecture and Prototype Plan, Lecture
- Catigorical Ordinal and Cardinal values
- Verification and Validation
- Usability and User Experience
- Assigned work to teammates
- Completted Functional Architecure diagram and part of system overview

## 10/07 Lecture
- Unit testing is important up until fall break
- Heuristic evaluation, usability test, measure the metrics of usability of our product
- define setup and experiement, independent and dependent varialbes, number of participants
- Simulation ???, look at method selection chart for ideas (in lecture notes)
 

## 10/09 Independent Lab Time
- 10 min Team design review for credit
- Project time in lab to discuss concept selection and directio 
- System Architecture feddback from fu: Make a state diagram with functional diagram, fix prototypes **they need to increase in fidelity** 
- Clarified grading scheme and bounderies for brainstorming and Gantt chart assignments
- I led the internal team meeting before our lab check in
- ESP32 S3 ordered with 2MP camera (arrives Wednesday of next week)






# Team 1 (Bird Feeder): Internal Team Meeting Minutes, October 9, 2026

**Time:** 12:30–1:10 PM · **Platform:** Google Meet · **Minutes recorded by:** Joe Falkenburg, team secretary

| Meeting date | Team member | Attendance |
| --- | --- | --- |
| 2026-10-09 | Joe Falkenburg | Present |
| 2026-10-09 | Ayan Sheikh | Present |
| 2026-10-09 | Emmett Gillespie | Present |
| 2026-10-09 | Daniel Lim | Present |

### 1. Purpose of the Meeting

We moved this week's meeting to 12:30 because Ayan had a philanthropy event. We met to plan our response to Dr. Fu's feedback on the brainstorming milestone and the concept selection, to work out what the hardware he ordered means for our design and who handles it, and to get ready for the design-review check-in in lab at 2:05.

### 2. Dr. Fu's Feedback and Our Resubmission Plan

Dr. Fu's comments on our brainstorming milestone came Thursday morning, October 8. He pointed to two filters we should have applied when choosing our final concepts. Our own rationale for Concept 1, the stand-off cage, was that it works without sensing, logic, or electrical power, which should have ruled it out for a course built on sensing and actuation. And the availability of parts should have screened out the camera: our SunFounder kit has no camera module, and the Feather ESP32 V2 lacks the digital video port that ESP32 camera modules use. Because his feedback came after the stakeholder presentation and the System Architecture were due, he offered that if we address these points in the brainstorming document, the related deductions won't carry into our later documents.

We decided to resubmit the brainstorming document with those fixes, so they carry down to the concept selection and the architecture.

One point didn't fit that plan. Dr. Fu's comments on our concept selection, from October 4, included one about Concept 2, the padded swat arm: it didn't consider that a deer, unlike a bird, touches the ground and the feeder at the same time, and he suggested sensing the pressure or vibration of its feet on the ground with sensors we have. We had lost points on the concept selection that we tied to that comment, even though that assignment was about documenting Don's feedback and presenting our slides, while the point itself is about the design of Concept 2 from the brainstorming. His brainstorming comments didn't mention it. Since the fixes are meant to flow down from the brainstorming, we agreed to ask Dr. Fu after lab whether our brainstorming resubmission also has to address it.

### 3. How We Divide the Work

Joe raised that much of this feedback, Concept 1's especially, came from how we divided the work rather than from misunderstanding the requirements. Taken as the combinable subsystems we meant them to be, our ideas met the requirements. But the people who distilled our forty ideas into three concepts were largely pooling other people's ideas, so the intent behind them didn't always carry through. One fix would be continuity, with each of us synthesizing the concept built from our own ideas. That avoids the reset that happens when a piece of divided work goes to someone who has to rebuild its context from scratch, which sometimes makes dividing the work slower than one person doing it alone, but it risks four concepts that don't agree with each other in their assumptions, terms, and structure. Developing the ideas into concepts together avoids both problems, because everyone sees the picture as it forms. We have divided our work all semester and will keep doing that; synthesizing together gives us the speed of splitting up without losing the shared picture.

We agreed in principle and plan to meet in person for that kind of work.

### 4. The ESP32-S3 and Camera Dr. Fu Ordered

Dr. Fu got department permission to order an ESP32-S3 Feather, which has the digital video port, and a 2 MP camera, which he hoped would arrive next week. The camera will work through the S3's digital video port, so the separate SPI camera module in our interface definitions, a part we would have had to buy, is no longer the plan. Changing boards from the Feather V2 to the S3 also reopens whether recognition runs on the board or on a laptop, which we'll re-evaluate on the S3. Joe's camera interface and pin assignments were written for the Feather V2's pins and need to be redone for the S3 when we resubmit the architecture.

### 5. Daniel's Role Going Forward

We clarified Daniel's procurement role as we move toward building. He'll get the ESP32-S3 and camera from Dr. Fu when they arrive next week and keep track of the parts our design needs against what the kit and the Sears Lab have. He'll also keep handling costs and our Thinkbox credit: finding out what Thinkbox actually offers, since we weren't sure what it stocks, checking with Dr. Fu whether a given use of the credit is acceptable, and leading the trip there to get what we need.

### 6. Preparing for the Check-In

The 2:05 check-in is a ten-minute, in-person design review with the teaching team on our System Architecture and Prototype Stages 1 and 2. We decided not to prepare a formal presentation. We'll have the submitted document open, let Dr. Fu lead, and have our questions ready: the Concept 2 point and the hardware he ordered.

### 7. Follow-Up

- **2026-10-09 — All of us:** Ask Dr. Fu after lab whether our brainstorming resubmission also has to address his Concept 2 comment.
- **2026-10-09 — All of us:** Resubmit the brainstorming document with Dr. Fu's fixes for Concept 1 and the camera's availability.
- **2026-10-09 — Daniel:** Get the ESP32-S3 and camera from Dr. Fu when they arrive next week, track the parts our design needs against the kit and the Sears Lab, find out what Thinkbox offers, check acceptable uses of the credit with Dr. Fu, and lead the trip there.
- **2026-10-09 — Joe:** Redo the camera interface and pin assignments for the S3 in the architecture resubmission.
- **2026-10-09 — All of us:** Meet in person to develop ideas into concepts together on our shared work. No date set yet.
- **2026-10-09 — All of us:** Go into the 2:05 check-in with the document open and our questions ready.
