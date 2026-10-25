---
id: raw-068
title: Situation Profile (a living "dossier" for each girl)
tags: [语料原文, HowToGetAlongWithGirls]
type: 语料原文
source: "https://github.com/Mayuqi-crypto/HowToGetAlongWithGirls (blob/HEAD/.claude/skills/dating-coach/references/profile-template.en.md)"
license: MIT
confidence: 中
---

> 语料原文层:整篇搬运自 MIT 许可仓库 Mayuqi-crypto/HowToGetAlongWithGirls,原文路径 `.claude/skills/dating-coach/references/profile-template.en.md`。
> 版权归原仓库作者所有,依据 MIT 许可证复制(保留版权与许可声明,全文见仓库 LICENSE)。

# Situation Profile (a living "dossier" for each girl)

> 🌐 **Language**: English (current) · [中文 / Chinese](./profile-template.md)

Before doing any analysis or giving any advice, the coach should first have a handle on the target girl's situation profile. This isn't a static form you fill out once — it's a **dossier that keeps getting updated as the conversation unfolds**: the top half is the basic profile, and the bottom half is the **overall situation analysis + timeline**. The more complete and up-to-date the information, the more precise the advice. It supports **managing multiple prospects at once** — one file per girl.

## Why build it

- The exact same line, "What are you up to?", calls for a completely different reply with a lively 22-year-old junior than with an aloof 30-year-old career woman.
- The stage, the landmines, and her interest points determine the force and direction of your wording.
- Across many separate conversations it's easy to lose the thread: where you left off last time, how the stage shifted, what pitfalls you've stepped in — all of it at a glance.
- When you're getting to know several girls at once, keep them recorded separately so they don't blur together, and advance each one on its own track.

## Record template

```markdown
# Situation Profile: <codename or nickname>            (Updated: <date>)

## I. Basic Profile
- Codename / what you call her:   (use a codename if you don't have a real name, e.g. "Bubble Tea Girl," "Dance Class A")
- Age / occupation:
- How you met:                    (introduced by friends / coworker or classmate / dating app / cold approach / …)
- How long you've known her & how many times you've met in person:
- Personality:                    (aloof / lively / slow to warm up / domineering / quiet / high-maintenance / …)
- Hobbies / things she likes:     (the more specific the better: a certain kind of pet, a certain sport, a certain type of food…)
- Looks / how sought-after she is: (affects her "habit of being chased" and the frequency of shit tests)
- How you two compare:            (roughly who has the edge — this sets the tone of your strategy)
- Known landmines / things she cares about: (exes, family, taboo topics, value red lines…)
- Your goal:                      (short-term dating / something serious / still observing …)

## II. Overall Situation Analysis (the core — update every time)
- **Current stage**:    Attraction / Plateau / Flirtation / Relationship / Long-term …
- **Her interest level**: about __ out of 10, trend ↑/→/↓
- **Overall read**:     one or two sentences making clear what the situation is right now and why (is there enough attraction, who's pushing, where it's stuck)
- **Current blocker**:  what's the biggest obstacle at this step
- **Next-step strategy**: where to steer it over the next 1–3 moves

## III. Timeline (reverse order, newest on top)
- <date>: what happened / a key thing she said / a shift in stage or interest / what action you took and how it landed
- <date>: ……
```

## How to use it

1. **First time a girl comes up**: if the user hasn't given you any information, **first ask about the key items in a sentence or two** — at minimum get to "age, how you met, current stage, her recent responses," and fill in the rest over the course of the conversation. **Don't dump a long table on her and interrogate her all at once**; ask for what's missing, as it's missing.
2. **Every time you answer**: use the profile to calibrate your advice; open your reply by **noting the current stage** per the SKILL.md rules (taken from "II. Overall Situation Analysis").
3. **Update as soon as you've answered**: fold this round's new information, new read, and stage/interest changes into "II. Overall Situation Analysis," and add an entry to "III. Timeline." **The record should always reflect the latest situation.**
4. **Multiple prospects**: record them separately, tell them apart by codename, and never apply A's situation to B.

## Persistence: the project-local knowledge base `profiles/`

The dynamic situation profiles have a fixed home — `profiles/` in the project root:

```
profiles/
├── _index.md     # Global overview table (all prospects + stage/interest/trend at a glance)
├── _template.md  # Copy this when creating a new record
└── <codename>.md  # One situation profile per girl
```

How it works:
- **Met someone new**: copy `_template.md` to `<codename>.md` and fill in the profile; add a row to `_index.md`.
- **Each time someone comes up**: first `Read` `profiles/<codename>.md` back in before analyzing; when you're done, write the updates back to that file and **sync this row in `_index.md`** (stage / interest / trend / last updated).
- **Want the big picture**: open `_index.md` and see at a glance where each person stands and whether to push forward or cut your losses.
- Before creating a record for someone for the first time, or before writing any file, get the user's consent first; the user may use a codename rather than a real name.

> This is the user's private data — be mindful of their privacy; unless the user asks, don't share it externally or write to anywhere outside `profiles/` on your own initiative.
