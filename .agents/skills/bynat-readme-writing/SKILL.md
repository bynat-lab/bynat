---
name: bynat-readme-writing
description: "Use when creating, editing, restructuring, reviewing, or extending the bynat README: voice, structure, no-repetition rules, code accuracy, and minimal-change maintenance."
author: bynat
license: MIT
---

# bynat README writing

Guidance for any agent that touches the project README. It covers the README as a whole: how it sounds, how it is organized, where new content goes, and how to change it safely. Always read the current README end to end before editing; it is the source of truth for structure and conventions, and this skill describes the principles behind it.

## 1. Voice and tone

The README should sound like a friendly, competent developer explaining their own tool to a peer.

- **Plain and direct.** Short sentences, active voice, concrete nouns. Say what a thing does, then when you would use it.
- **Warm, not loud.** Friendliness comes from clear explanations and a welcoming opener, not exclamation marks, emojis, slang, or jokes. At most one light touch per section, and often none.
- **Modern and developer-oriented.** Talk to the reader as a capable person. Define a term once in passing (for example, a short parenthetical) instead of lecturing.
- **Credible.** Every claim is something the code does. No superlatives, no "powerful", "seamless", "blazing", "revolutionary".
- **Questions sparingly.** A question opener ("Got a table that needs tidying?") works at the top of a major section when it frames a real reader need. Do not put one on every subsection.
- **Second person.** Address the reader as "you". Use "bynat" or the object name as the subject when describing behavior.

If a sentence could appear in any project's README unchanged, rewrite it with something specific to this one.

## 2. Structure and organization

The README follows a progressive path from "what is this" to "every detail":

1. Overview and what you can do with it
2. Installation and requirements
3. Quick start (one tiny, runnable example)
4. General usage (import styles, shared concepts)
5. One top-level section per major area of functionality
6. Advanced features (deeper mechanics, provider/extension details)
7. Method and API reference (lookup tables)
8. Module layout
9. Limitations and operational notes
10. Development and verification
11. License

Rules:

- **Heading hierarchy.** `##` for major sections, `###` for topics inside them, `####` for details inside a topic. Do not skip levels. Do not go deeper than `####`.
- **One home per area.** A major area of the library (a package or a distinct capability) gets its own `##` section. Do not nest an area under a sibling just because it was added in the same change.
- **Keep related things together.** Explanation, example, and edge-case notes for one feature live in one place, in that order.
- **Match the existing order of tiers.** Friendly introduction first, then usage, then deeper behavior, then reference tables. Do not put a parameter table before the reader knows why they would call the method.
- **Avoid structural complexity.** Prefer adding a `###` over inventing a new pattern. No nested bullets deeper than two levels, no collapsible blocks unless the README already uses them.
- **Navigation.** If the README has a top navigation bar, add or update its links when you add or rename a major section.

## 3. Deciding where new content belongs

Work through these questions in order:

1. **Is it a new area of functionality** (a new package, module family, or distinct capability)? Give it a new `##` section placed where the reading flow wants it, usually after the sections a reader needs first.
2. **Is it a new method or option of an existing area?** Add it to that area's section (intro or example if it changes how people use the area) and to the reference tables.
3. **Is it deeper mechanics of something already introduced?** Put it in Advanced features or in a detail subsection under the existing topic, and keep the intro short.
4. **Is it a cross-cutting caveat** (network use, optional dependencies, logging, failure behavior)? It belongs in Limitations and operational notes, not scattered through feature sections.
5. **Is it about contributing, testing, or typing?** Development and verification.

When a new feature touches several places, update all of them in the same change: overview bullets, the feature section, reference tables, supported-imports lists, module layout, and navigation links. Missing one of these is the most common way the README drifts.

## 4. Writing quality

- **Lead with the reader's goal**, then the mechanism. "Need X? Do Y" beats "The Y subsystem provides X".
- **Explain without overwhelming.** One new idea per paragraph. Introduce a concept in plain words, show a short example, then list details.
- **Prefer lists and tables when content is parallel** (options, parameters, return types). Prefer prose when explaining why or how something fits together.
- **Use consistent terms.** Pick one name for each concept and keep it everywhere (for example, do not alternate between "accessor", "extension", and "namespace" for the same thing). Use the exact identifier names from the code, in backticks.
- **Be concise.** Cut filler ("basically", "simply", "in order to"). Keep the technical content; trim the words around it.
- **Make introductions earn their place.** An intro should tell the reader what the section is for and where to go deeper, not restate the heading.
- **Callouts** (blockquotes with a bold label) are for things that cause real mistakes, such as a missing dependency or a return value that must be used. Use them rarely.

## 5. Progressive documentation

Treat each feature as having up to three tiers:

1. **Accessible intro** in the feature's own section: what it is, why you would use it, one short example.
2. **Deeper behavior** in a detail subsection or in Advanced features: options, edge cases, how it works internally when that changes how people use it.
3. **Reference** in the tables: parameters and one-line purposes.

A short mention at a higher tier followed by a genuinely deeper treatment later is good. It must add information, not restate the intro in different words. Give deeper material its own subsection when it has its own example, its own rules, or would otherwise bury the main explanation.

## 6. Repetition and cross-references

- **Every fact has one home.** Before writing a sentence, search the README for the same fact. If it exists, do not restate it; extend the existing place if needed.
- **Allowed repetition:** a one-line high-level mention that points to a deeper, fuller explanation elsewhere. The deeper one must contain something the mention does not.
- **Tables and prose count as the same fact.** If a table already states a behavior, do not repeat it as a bullet.
- **Cross-references help navigation, they do not replace explanation.** Link when the reader genuinely needs to jump (to a reference table, a detailed subsection, a related area). Do not turn a section into a list of links, and do not link just to avoid writing a necessary sentence.
- **When removing duplicates, fix the neighbors.** Reword any sentence that depended on the removed text (for example, a bullet that said "without it"), and tell the requester what was removed and why.
- **Check anchors after any heading change.** Search for every link to the old anchor. Repeated headings get numeric suffixes on GitHub (`-1`, `-2`), so renaming one can silently change another's anchor.

## 7. Code examples and technical accuracy

- **Never invent.** Every parameter, default, return type, exception, and behavior must be verifiable in the source or tests. If you cannot verify it, read the implementation (and its tests). If it is still unclear, ask the requester instead of guessing.
- **Preserve existing examples.** Do not change code, signatures, or outputs unless there is a clear documentation error. If you fix one, say so.
- **Examples must be runnable** as written (imports included) or clearly continue an earlier example with the variable names it defined. Keep them small; one idea per example.
- **Show expected results** in comments when they help, and keep those results correct.
- **Conventions:** fenced code blocks with a language tag, 4-space indentation in Python, comments short as in the existing examples, backticks for identifiers, parameters, file names, and values.
- **Keep reference tables faithful to signatures:** parameter order, defaults, keyword-only markers.
- **Check for drift tooling.** If the repository has docs-sync or doc-drift checks (look in `tools/` and the tests), run them after editing and fix what they report.
- **Fictional data.** Example data should be obviously made up and harmless.

## 8. Workflows

### Add documentation for a new feature
1. Read the README fully, then the feature's code, tests, changelog entry, and PR description.
2. Decide where it lives (section 3). Note every place that must change.
3. Write the intro and example first, then details, then reference rows.
4. Update overview bullets, imports lists, module layout, and navigation.
5. Re-read for repetition, terminology, anchors.

### Restructure or move content
1. Inventory every piece of content that belongs to the area being moved, including scattered mentions.
2. Decide the target structure and reading flow before moving anything.
3. Move text verbatim where it already works; rewrite only to fix flow, remove duplication, or fix references.
4. Update navigation and anchors; check intros and transitions of the neighbors.
5. Report what moved, what was removed as duplicate, and what you left alone on purpose.

### Polish or rewrite specific sections
1. Edit only the sections you were given.
2. Keep technical meaning identical; change wording, flow, and clarity.
3. Match the voice of the surrounding sections.

### Review the README
1. Check structure (heading levels, order, one home per fact).
2. Check accuracy against the code on a sample of examples and tables.
3. Check voice, duplicated explanations, broken anchors, stale versions or lists.
4. Report findings; do not silently rewrite.

## 9. README maintenance

- **Smallest reasonable change.** Prefer moving and trimming over rewriting. Do not restyle sections you were not asked about.
- **Preserve unrelated sections** exactly, including whitespace and wording.
- **Keep lists in step** with the code as the project grows: feature bullets, optional extras, supported imports, module layout, type-checking scope, version number.
- **Do not remove useful technical information.** If something looks redundant, confirm it is truly duplicated elsewhere before deleting it.
- **Deliverable format.** When asked for the whole README, return the whole README, never a truncated one. For long outputs, deliver it as a file as well. When asked only for sections, return only those sections in a Markdown code block, with no commentary inside it.
- **Do not modify the repository** (no commits, no file writes in the repo) unless the requester explicitly asks.

## 10. Decisions in ambiguous situations

- **You have autonomy over wording, minor ordering, and where a small detail lives.** Make the call and mention it briefly.
- **Ask first** when the choice changes behavior documentation (what the code does is unclear), when two valid structures would lead to very different READMEs, or when content may need deleting rather than moving.
- **Do not ask** about things the README's existing conventions already answer.
- When an instruction conflicts with these guidelines, follow the requester's explicit instruction and note the trade-off.

## 11. Common mistakes and anti-patterns

- Nesting a new area under an unrelated section because it was added at the same time.
- Restating the same behavior in an intro, a bullet list, and a table.
- Replacing an explanation with "see section X".
- Marketing adjectives, hype, emojis, forced jokes, or heavy slang.
- Changing code examples or defaults while "polishing".
- Documenting behavior you inferred rather than verified.
- Updating one list (for example, supported imports) but not the others that mirror it.
- Renaming headings without updating links and the navigation bar.
- Leaving a sentence that referred to removed text.
- Rewriting unrelated sections for style.
- Returning a partial README when the whole file was requested.

## 12. Final checklist

- [ ] Read the full README and the relevant code before editing.
- [ ] New content sits in the right section and tier.
- [ ] Voice matches neighboring sections: plain, warm, specific.
- [ ] No fact is stated in two places without added depth.
- [ ] Cross-references are useful and anchors resolve.
- [ ] Examples, parameters, and defaults match the implementation.
- [ ] Related lists, tables, navigation, and module layout are updated.
- [ ] Unrelated sections are untouched.
- [ ] Any drift-check tooling passes.
- [ ] Summary tells the requester what moved, what was removed, and any open questions.
