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



---

# Original brief (verbatim)

The request that started the project this pipeline was distilled from. Kept as an example of the kind of brief
`film-pipeline` is meant to turn into a screenplay, a shot list and a finished cut.

> 那接下来你设计一个剧本，做一个短片吧。我希望是那种在戛纳能获奖的、史诗级别、宏大场面、优秀的剧本、有深刻意义、又能展示出opus5.5剧本设计镜头设计导演功底的、镜头语言充分的小短片吧。  总是要惊艳众人，开场可以好莱坞级别的，比如背景音、字幕切换等，开头就可以展示出本片由opus 5.5 , gemini等制作，不用一次性出场，可以有合适的镜头、融入界面就会更高级等等。  有什么不明白的你可以和我沟通清楚再开工，推进视频落地等你看看要不要用opus5.5 high来执行，剧本设计、镜头等重要的内容要不要用 fable或者opus5.5max，这些子agent的安排由你来，但是还是要保证品质，因为我们要靠这个片子获奖。  同样bgm、音乐、音效、声音配音稳定性、人物角色场景稳定性都要考虑。这个不一定要动画，真人也行、3d也行、动画也行、或者新的艺术画风也行，你可以自由发挥，抽象也行。  有什么不清楚的你可以和我确认清楚再开工。

What the brief implies for the pipeline:

- clarify ambiguities with the user before starting, then keep going;
- spend strong models on screenplay / shot design / critique, cheaper ones on execution;
- treat voice consistency, character/scene consistency, score and SFX as first-class, not afterthoughts;
- credits can live inside the film's interface (terminal, split-flap board) instead of a title card.
- 