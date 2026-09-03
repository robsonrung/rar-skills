# Comments and names

Read on `design` after the interface is sketched, and on `improve` when names or comments are the work. Chapters 12–15.

## Contents

1. [Reject the four excuses](#reject-the-four-excuses)
2. [What a comment is for](#what-a-comment-is-for)
3. [Comments first](#comments-first)
4. [Names](#names)

## Reject the four excuses

Do not accept these as reasons to skip comments (ch. 12):

| Excuse | Answer |
| --- | --- |
| Good code is self-documenting | Code shows _how_. It cannot show why, units, invariants, or cross-module decisions. |
| No time | Late comments are the expensive ones. Early comments are the design. |
| They go stale | Stale comments are a **stay strategic** failure. Keep them next to the code; check the diff. |
| Every comment I've seen is worthless | Worthless comments repeat the code. That is a red flag, not an argument against **earned comments**. |

A comment is a design tool, not a consolation prize. The opposing view ("comments are failures") is Clean Code's; this skill follows the extract: comments are **not** failures. They carry information code cannot, and a short interface comment should make it unnecessary to read the method body.

Do not "fix" a comment by extracting a method whose name is a sentence (`isLeastRelevantMultipleOfNextLargerPrimeFactor`). That name is still cryptic, and every caller retypes the documentation. Keep the **earned comment**. `clean-code` still cuts comments that _repeat_ the code.

## What a comment is for

Comments describe things that are **not obvious from the code** (ch. 13).

| Kind | Job | Example of a failure |
| --- | --- | --- |
| Lower-level | Add precision the tokens lack (units, ranges, null means) | Restating `i++` |
| Higher-level | Enhance intuition — what this chunk _is_ | Narrating the next three lines |
| Interface | The abstraction and its contract. Never _how_ | "Uses a red-black tree" on a public method |
| Implementation | What and why, not how | A play-by-play of the algorithm |
| Cross-module | A decision that spans files, written in one place | The same caveat copied into three modules |

Pick the project's comment conventions already in context and stay consistent. Interface comments that run long or fill with caveats are the **hard to describe** red flag — simplify the interface; do not write a longer comment.

Cross-module decisions get one comment in the owning module. Duplicating them is how they rot (ch. 16.4).

## Comments first

Write the interface comment before the body (ch. 15). Delayed comments are bad comments: you have forgotten what was not obvious.

The comment is the design. If you cannot write a short, precise interface comment, the module is not **deep** yet — **design it twice** again.

Do not put the design in the commit log. Readers of the code will not see it (ch. 16.3).

## Names

A name is an abstraction. It should create an image of the thing (ch. 14).

- **Precise** — `data` / `obj` / `info` / `manager` fail. If you cannot pick a precise name, the entity is doing two jobs (**hard to pick name**).
- **Consistent** — same word, same meaning, everywhere. Two words for one thing is obscurity.
- **No extra words** — drop filler (`Data`, `Info`, `Object`) that does not change the image.
- **Most information in fewest words** — list candidate words, keep the few that convey the most (ch. 21; this _is_ **design it twice** for a name).
- Bad names cause bugs. Treat a vague public name as a defect, not style.

`clean-code` owns local rename mechanics. This file owns the test: does the name make the abstraction obvious, and does a hard-to-pick name mean the entity should be reshaped?
