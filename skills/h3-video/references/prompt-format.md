# H3 prompt format (Context-IR)

Three fields in this order, English, one paragraph each. Durations in the text must match the requested length.

```
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.   <- I2V only, first line, then a blank line

integrated_multimodal_description: [Shot 1] Live-action, cinematic, shot on 35mm film with subtle grain, <what <Picture 1>
shows, restated concretely so the model keeps it: subjects, layout, light>. The camera pushes in with small amplitude at
slow speed toward <target>. <What changes over the clip, in order.> <What must NOT change: "The lettering keeps its exact
shape…", "The architecture stays perfectly still".> No people appear. / No faces are visible.

overall_soundscape: <ambient + physical sounds for the whole clip, 1–4 sentences>

non_diegetic_music: <instruments, tempo, dynamics — or N/A>
```

- Camera = motion type + optional amplitude + speed: `pushes in / pulls out / trucks left / tilts up / holds a static
  shot`, `with small amplitude`, `at slow speed`. Write it as a sentence, not a tag list.
- Visible text goes in double quotes, verbatim, in its original language: `a sign reading "OPEN - 营业中"`.
- Singing/music the people in the scene can hear belongs in the description, not in `non_diegetic_music`.
- Don't repeat Veo's "no text, no subtitles" tail on shots that contain text — it fights the quoted text.
- Text-to-video: drop the first line; start at `integrated_multimodal_description:`.
- Abstract transformations work if described as an ordered sequence ("embers rise… slow… settle into a ring… each turns
  blue/violet/crimson… stone tracery emerges around them").
