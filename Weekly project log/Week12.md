# ECSE Week 12 Project Log

## 11/9 Independent Lab Time

- Began Sound and Light Heuristic testing for tolerance of deterrence sequence, tested 1 subject, help write checkpoint document

## 11/11 Independent Lab Time

- Continued sound and light validation testing, adding more participant while controlling for the same variable, acheived larger sample size

## 11/13 Independent Lab Time

- Led team meeting. Checked in with Daniel who worked off site last class, integrated vibration sensor idea with entire system using ESP internal wifi, next steps include summitive validation tests and refill AB testing, working on priting the enclosrure for the vibration sensor and revision 2 of main enclosure

## Week 12 Team Meeting Minutes (Joe F.)

**Project:** Bird-feeder project

**Date:** Friday, November 13, 2026

**Time:** 1:00–1:45 PM

**Platform:** Google Meet

**Attendees (all present):** Joe Falkenburg, Ayan Sheikh, Emmett Gillespie, and Daniel Lim.

## Detection logic and integration

We agreed that deterrence should require the sequence PIR → feeder shaking → camera-size check → sound/light response. The PIR initiates the check, the feeder-mounted sensor confirms interaction, and the camera then checks for a sufficiently large foreground object. Each stage is required. We discussed making sure the events belong to the same interaction so unrelated detections cannot satisfy the sequence.

We removed the requirement that the object grow across successive camera frames. An animal already at the feeder may cause shaking while remaining at roughly the same distance from the camera. Requiring feeder interaction may allow some initial seed access, but we accepted that tradeoff to reduce nuisance activations from people or animals passing nearby without interacting with the feeder.

The revised sequence still needs to be implemented and integrated. Daniel leads the firmware and electronics work, with Joe supporting the code. Connecting the feeder controller to the main controller through ESP-NOW remains part of that work; successful component operation does not yet establish operation of the complete sequence.

## Sensor calibration and system testing

We discussed narrowing the PIR's useful detection area around the feeder and checking its boundary at measured positions. The purpose is to reduce responses to passersby while retaining coverage of the intended approach area. We also discussed the vibration sensor's calibration goal: reducing excessive noise while preserving a useful response to feeder shaking.

We planned to check the shake sensor's response to brisk wind and to ordinary handling and refilling. These checks should help distinguish intended feeder interactions from environmental movement and normal use.

We noted that sensor/event and activation logging had been implemented and used in trials. We planned controlled checks in which a person passes nearby without touching the feeder and attempts to take seed from it, allowing us to compare a nearby movement with an actual feeder interaction. We also planned to check that the sound and light stop correctly after activation. These trials will check system operation; they will not establish deterrence of real deer.

## Speaker integration and measurements

We reviewed the replacement speaker's standalone operation and the intermittent results encountered when incorporating it into the system. We discussed inadequate drive and shared-supply behavior as possible explanations. Additional amplification, potentially using an op-amp stage, was considered as a way to provide adequate drive for the 8-ohm speaker. The cause of the intermittent behavior and the final drive and supply arrangement remained unresolved.

We discussed comparing speaker-only operation with operation alongside the camera or lights to investigate whether combining components affected reliability. This comparison had not yet been carried out. We also planned to compare sound levels from the speaker and buzzer using a phone app and to measure the speaker's current draw during activation to assess battery demand.

## Enclosure design and printing

We agreed on a more compact main enclosure while retaining the height needed to place the camera and PIR close together vertically, aimed toward the same approach region. Joe will develop the main enclosure using the shared component measurements and our group's existing CAD as reference. The board dimensions need to inform internal retention and clearance separately from the exterior openings. The design should secure the boards, allow space for wiring and connections, improve the lid's fit, provide USB access, and retain the existing dowel arrangement.

Emmett will develop the feeder-mounted housing and its attachment. We selected a removable two-magnet clamp beneath the feeder base, with one magnet inside the feeder and the other outside holding the base and housing together. The package must accommodate its battery and hold the sensor firmly against the feeder so movement reaches it. The magnetic arrangement has been selected but still needs a physical check for holding strength, slipping, clearance, and removal for servicing. Its position must also preserve access for normal refilling.

Ayan will print both revised enclosures on Saturday. The CAD handoff needs to incorporate the measured components and their mounting and clearance requirements. Fit checks remain shared work: the printed parts must be checked with the actual electronics and feeder, including board retention, access, and the assembled mounting arrangement.

## Disturbance testing and interpretation

We reviewed the five complete disturbance-survey responses collected using the original buzzer. Each participant experienced sound only, light only, and sound and light together for 15 seconds per condition, then rated each mode on the existing 1–5 disturbance scale. The setup used a glass barrier and an observer approximately two feet from the glass to approximate the intended indoor viewing situation.

We agreed to retain the recorded buzzer ratings unchanged. They describe the configuration that participants experienced; the replacement speaker requires separate disturbance evidence. The participant test program exercises the outputs directly, so these responses concern human disturbance rather than the integrated detection sequence or effectiveness against deer.

We discussed the limits of the setup and sample. Some ambient lighting remained, the room's glass and acoustics differ from Mr. Fong's setting, and participants were asked to imagine the nighttime residential situation. The convenience sample and familiarity with the team also affect how broadly the findings can be applied.

## Refill study and testing procedure

We agreed on a paired refill study using the comparable feeder ordered for local testing. Each participant will complete the task with the feeder alone and with the shake-sensor package attached. The task should represent taking down, opening, refilling, closing, and rehanging the feeder, with the main unit remaining separate in its intended position. This comparison will assess whether the added package interferes with normal handling.

The recruitment goal is about ten volunteers outside the design team. Each person's two conditions must remain paired; this is a comparison of the same participants using both configurations. Recruitment and trials still need to be arranged. The physical usability study can proceed before ESP-NOW is finished, provided the attached package represents the housing and mounting arrangement being evaluated and that configuration is recorded.

Joe's refill procedure is the priority for the validation-testing manual. We agreed that the manual must make the study executable through consistent setup and task instructions, participant and condition records, and a defined recording method. It must specify how completion, efficiency or effort, errors, assistance, and perceived difficulty will be assessed before those measures are used. No refill results have been collected yet. Little or no added difficulty would still be a useful finding because the study is checking whether the installation preserves the normal refill routine.

## Reviews, analysis, and revision work

We planned a guided review of the revised installation with Mr. Fong. Joe will prepare the script, supported by photographs or video and a concluding feedback survey. The review should address the enclosures' appearance, feeder visibility, mounting, and access for refilling, servicing, and charging in his setting.

We discussed the invitation already sent to Mr. Fong and the pending reply. The proposed Sunday availability was noon–6 PM; no specific time had been agreed. We also planned a separate complete-system walkthrough with Professor Fu to obtain overall design and implementation feedback.

We planned to prepare at least one interpretable figure from the participant results for the data-analysis checkpoint. We agreed to ask Professor Fu to clarify whether both the disturbance and refill studies should be included.

We discussed ongoing revision work in response to Professor Fu's feedback.
