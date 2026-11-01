# ECSE Week 10 Project Log

## 10/26
- Midterm Presentations, I had slides 4-7, I went a bit over time costing the team a point, but we ended up with a 40.5/45

## 10/28 
- Midterm Presentations part II, sat and listened to other groups and their progress on their P1,2,3

## 10/30 Independent Lab Time
- Discussed Meeting logistics for Sunday, check in with Roy, we made progress on the camera and detection system 3which made our project feasible enough to continue to pursue, we will not continue with inference based detection based off of our P3 results and will roll back to simple object based detection with the Ov5640 and ESP32-S3




# Week 10 Team Meeting Minutes

**Project:** Bird-feeder project

**Date:** Friday, October 30, 2026

**Time:** 1:00–1:45 PM

**Platform:** Google Meet

**Attendees (all present):** Joe Falkenburg, Ayan Sheikh, Emmett Gillespie, and Daniel Lim.

## MVP direction and operating behavior

We committed the immediate MVP to local image-area detection while retaining PIR and the camera. We set aside replacing them with ultrasonic or other range sensing. Ordinary detection and response should operate without the laptop, while the computer remains available for training and diagnostics. We agreed to continue AI work without holding up the detector, enclosure, or demonstration.

We accepted the area rule as a practical proxy with limits: a person can trigger it, and a nearby small animal may appear large. We discussed calibration of a clear installed view, a provisional area cutoff, confirmation across multiple frames, reference refresh, camera aim, and capture delay as parts of making the behavior useful. Our demonstration must distinguish this filtering from deer identification.

We agreed on night-only operation and a usable pause/resume control for the MVP. A deliberate pause must suppress deterrence despite qualifying images and must remain in effect when the nighttime window begins; operation resumes when Mr. Fong re-enables it. We also agreed that new detections should not restart or extend an active light/buzzer sequence. These requirements address separate stages of operation.

## Model findings and next investigation

We reviewed the completed confidence-threshold comparison: the high cutoff missed all held-out deer, and lowering it recovered some detections while still missing most. We also reviewed the confirmed numerical failure in the emulator, so its saturated scores could not be used as an accuracy result.

We discussed the recovered model/data starting point, adequate deer and non-deer examples, training/validation separation, and fitting a compact model and image buffers on the ESP32. We considered data quality and evaluation methods alongside further training. Saved-image testing, matched float/INT8 execution, and actual camera input should be investigated separately to locate the failure.

We agreed to a controlled float/INT8 comparison using the same checkpoint and consistent image preparation and decoding. Further training should preserve the baseline and produce a separately comparable candidate. Before we replace the practical detector with AI, it must repeatedly detect positive cases, remain quiet on relevant empty/non-deer cases, clear when the target is removed, and operate acceptably on the board. A controlled empty-scene → deer-picture → empty-scene procedure with repeated-frame confirmation provides a starting point; passing it would permit further integration, not establish field accuracy.

## Enclosure and mounting

We reviewed the printed base's height problem and considered retaining the full wired breadboard versus downsizing it. We discussed a taller top as a way to retain the base while gaining clearance. We did not decide either the board choice or the taller-top remedy in this meeting.

We chose the removable external arrangement with two supports. Supporting both sides should limit rocking or rotation while allowing the enclosure to slide off for installation and servicing. We discussed sealing and gaskets, but whether sealing had to be completed for the immediate MVP remained undecided.

## Tests, documentation, and coordinated work

We agreed to a representative-load battery test of the complete assembly, including idle time, camera checks, illumination, and deterrent events. We should record elapsed runtime and event frequency so the result reflects how the device is used. We placed the real feeder-outcome comparison after the immediate MVP.

We agreed to revise the prototype submission to give P1, P2, and P3 distinct explanations of purpose, test, learning, and subsequent change, with actual camera and response evidence alongside the AI attempt and practical detector.

We planned a short video, photographs, and a narrated assembled-MVP walkthrough for weekend work. The walkthrough should show calibration, small-object rejection, a large-target response, and the fitted enclosure. Further AI investigation, unfinished controls, enclosure completion, and evidence preparation remain our collective work toward the MVP.

