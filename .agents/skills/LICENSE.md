# License and Attribution

Agent skills in this directory come from six independent upstream sources plus
original work written for this repository. **No single copyright notice covers
all 19 skills.** Each section below names the source, the applicable licence,
and every bundled skill it covers.

## 1. `wdm0006/python-skills`

- Source: <https://github.com/wdm0006/python-skills>
- Licence: MIT
- Copyright: (c) 2025 Will McGinnis

| Bundled skill | Upstream directory |
| --- | --- |
| `api-design` | `skills/python/api-design` |
| `documenting-python-libraries` | `skills/python/documentation` |
| `improving-python-code-quality` | `skills/python/code-quality` |
| `packaging-python-libraries` | `skills/python/packaging` |
| `release-management` | `skills/python/release-management` |
| `reviewing-python-libraries` | `skills/python/library-review` |
| `setting-up-python-libraries` | `skills/python/project-setup` |
| `testing-python-libraries` | `skills/python/testing-strategy` |

`documenting-python-libraries`, `packaging-python-libraries`,
`reviewing-python-libraries`, `setting-up-python-libraries`, and
`testing-python-libraries` are earlier snapshots of the upstream files.
`reviewing-python-libraries` and `testing-python-libraries` additionally carry audit guidance written for this repository (see §8).
`api-design`, `improving-python-code-quality`, and `release-management` match
current upstream apart from the attribution fields noted in §8.

## 2. `NousResearch/hermes-agent`

- Source: <https://github.com/NousResearch/hermes-agent>
- Licence: MIT
- Copyright: (c) 2025 Nous Research

Covers `codebase-inspection` and `simplify-code`, both adapted from the bundled
Hermes Agent skills. `requesting-code-review` (see also §3) additionally
carries Hermes Agent authorship, including a community contribution credited
to MorAlekss.

## 3. `obra/superpowers`

- Source: <https://github.com/obra/superpowers>
- Licence: MIT
- Copyright: (c) 2025 Jesse Vincent

- `systematic-debugging`, adapted from `skills/systematic-debugging`
- `test-driven-development`, adapted from `skills/test-driven-development`
- `requesting-code-review`, adapted from `skills/requesting-code-review`

## 4. `gsd-build/get-shit-done`

- Source: <https://github.com/gsd-build/get-shit-done>
- Licence: MIT
- Copyright: (c) 2025 Lex Christopherson

Covers `spike`, adapted from the GSD `/gsd-spike` workflow. The original credit
line is retained inside `spike/SKILL.md`.

## 5. `wshobson/agents`

- Source: <https://github.com/wshobson/agents>
- Licence: MIT
- Copyright: (c) 2024 Seth Hobson

Covers `python-project-structure`, copied from
`plugins/python-development/skills/python-project-structure`.

## 6. `mattpocock/skills`

- Source: <https://github.com/mattpocock/skills>
- Licence: MIT
- Copyright: (c) 2026 Matt Pocock

Covers `handoff`, copied from `skills/productivity/handoff`.

## 7. Original `bynat` project skills

- Copyright: (c) 2026 bynat
- Licence: MIT, as granted by the repository [LICENSE](../../LICENSE)

- `bynat-documentation-conventions`
- `bynat-readme-writing`
- `python-package-release`

These three were written for this repository and contain no third-party
material.

## MIT permission and warranty disclaimer

The material listed in Sections 1–6 is redistributed under the MIT licence,
which is the licence of each named upstream source:

```text
MIT License

Copyright (c) 2025 Will McGinnis
Copyright (c) 2025 Nous Research
Copyright (c) 2025 Jesse Vincent
Copyright (c) 2025 Lex Christopherson
Copyright (c) 2024 Seth Hobson
Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 8. Modifications

Bundled copies preserve the technical content of their upstream sources.
Documented changes are limited to attribution metadata, internal link repair,
and wording localisation for harness portability; `reviewing-python-libraries`
and `testing-python-libraries` additionally include audit guidance written for this
repository. No functional instructions from an upstream source were removed.
