# videoclip

Claude Code skills for making short films from a day's photos, phone footage and a written piece, with
open-source generators on a remote GPU box. Distilled from a real ~4-minute travel short (screenplay → 30 generation
todos → rough cut → revisions).

## Skills

| skill | use it for |
|---|---|
| [film-pipeline](skills/film-pipeline/SKILL.md) | The whole job: screenplay → per-shot todo folders → generate → pick takes → assemble → revise from notes. Start here; it calls the others. |
| [h3-video](skills/h3-video/SKILL.md) | Image-to-video / text-to-video with sound on MiniMax H3 (sglang): serving flags, Context-IR prompts, batch runs. |
| [qwen-outpaint](skills/qwen-outpaint/SKILL.md) | Widening portrait photos to 16:9 with Qwen-Image-2.1 while keeping every original pixel. |
| [cosyvoice-narration](skills/cosyvoice-narration/SKILL.md) | Narration lines in one cloned voice with Fun-CosyVoice3. |
| [acestep-score](skills/acestep-score/SKILL.md) | Instrumental score cues of fixed length with ACE-Step 1.5. |
| [film-assembly](skills/film-assembly/SKILL.md) | Grading, timeline, vertical footage, Ken Burns, mix, subtitles — the rough cut. |

## Dependencies

- **humanize** (install separately) — all work on the remote GPU server goes through it; these skills don't
  ship their own remote-execution layer.
- ffmpeg, python3 with numpy / scipy / opencv on the machine that runs `film-assembly`.

## Layout / adding a skill

```
skills/<name>/SKILL.md        frontmatter: name, description (with trigger words); body: when, steps, pitfalls
skills/<name>/scripts/        runnable helpers, each with a usage line in its docstring/header
skills/<name>/references/     longer notes (prompt formats, lessons) that SKILL.md links to
```

One capability per skill. Cross-link with relative paths (`../h3-video/SKILL.md`) instead of copying text.
No hosts, users or absolute paths in this repo: scripts read them from environment variables
(documented in each SKILL.md, e.g. `VC_WORK`, `VC_TODO`, `VC_MODELS`). Keep it that way — this repo is public.
Add the new skill to the table above.

Install: symlink the ones you want into `~/.claude/skills/`, e.g.
`ln -s "$PWD/skills/h3-video" ~/.claude/skills/h3-video`.
