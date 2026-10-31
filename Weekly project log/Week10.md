# ECSE Week 10 Project Log

## 10/26
- Midterm Presentations, I had slides 4-7, I went a bit over time costing the team a point, but we ended up with a 40.5/45

## 10/28 
- Midterm Presentations part II, sat and listened to other groups and their progress on their P1,2,3

## 10/30 Independent Lab Time
- Discussed Meeting logistics for Sunday, check in with Roy, we made progress on the camera and detection system 3which made our project feasible enough to continue to pursue, we will not continue with inference based detection based off of our P3 results and will roll back to simple object based detection with the Ov5640 and ESP32-S3




# Team 1 (Bird Feeder): Internal Team Meeting Minutes, October 30, 2026

**Time:** 3:00–3:30 PM · **Platform:** Zoom · **Minutes recorded by:** Joe Falkenburg, team secretary

**Attendees (all present):** Joe Falkenburg, Ayan Sheikh, Emmett Gillespie, and Daniel Lim.

- Rehearsed our presentation for the following week.
- Planned to work on the Concept Selection and Gantt Chart resubmission, which was not yet complete.
- Reviewed progress on the drawings, cardboard mockup, and electronics, including the path from motion sensing through camera capture and laptop recognition to the light and buzzer. With no usable camera images yet, getting capture or streaming working was next. We compared developing recognition from saved images during camera debugging with waiting for live images.
- For the presentation, we considered a teammate judging whether a target was a deer and operating the light and buzzer by hand, giving the ESP32 simulated recognition results so it could control the outputs, or explaining the intended response using the drawings and mockup.
- We discussed comparing camera tilt, the camera opening's size and position, and the post's height and distance from the feeder once the camera works. For the enclosure, we considered keeping boards removable with connector access and wire slack, rearranging the boards and breadboard so wiring stays clear of sensor openings, or making the enclosure larger. The recognition approach, demonstration method, and layout changes remained undecided.
- Discussed checking that a confident deer identification at night activates the light and buzzer, and that they stay off for birds, people, unclear images, daytime, missing camera images, and late recognition results.