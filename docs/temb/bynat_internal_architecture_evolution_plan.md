# bynat Internal Architecture Evolution Plan

**Status:** Draft --- research and planning template\
**Applies after:** Top-Level Architecture Refactor Phase 4 and Phase 5
are fully completed\
**Primary purpose:** Guide a research-first review of bynat's internal
architecture, from package boundaries down to implementation-level
contracts, while leaving explicit questions and evidence gaps for Hermes
to investigate and resolve.

------------------------------------------------------------------------

## 1. Purpose and operating model

The Top-Level Architecture Refactor establishes the approved
package-level structure, public API boundaries, and dependency rules.
This plan begins only after its remaining phases have been completed and
verified.

The purpose of this follow-up initiative is to understand and improve
the architecture *inside* the approved package boundaries. It must not
reopen already-approved top-level decisions without concrete repository
evidence or a documented reason.

The initiative follows this sequence:

1.  **Research the current state** from the actual repository.
2.  **Identify and verify architectural gaps** against explicit
    criteria.
3.  **Propose a target design** only where a meaningful gap exists.
4.  **Review and approve the design** before implementation.
5.  **Implement only approved changes**, in bounded scopes.
6.  **Verify implementation and evidence** against the original
    acceptance criteria.

A documentation note describing an unresolved gap does not count as
completing that gap. Each acceptance criterion must be verified as
implemented, or explicitly marked as blocked pending a decision. Partial
acceptance requires a genuine blocker or explicit approval.

### 1.1 Core principles

-   The checked-out repository is the source of truth for current
    behavior and structure.
-   Approved architecture documents and dependency rules are the source
    of truth for intended top-level boundaries.
-   Existing public APIs and documented compatibility commitments must
    not be changed casually.
-   Do not refactor merely to make the tree look cleaner.
-   Do not introduce abstractions, managers, base classes, protocols,
    registries, or shared packages without a demonstrated responsibility
    and concrete benefit.
-   Similar-looking code is not automatically shared behavior. Compare
    semantics, invariants, contracts, and ownership before consolidating
    helpers.
-   Prefer the smallest change that resolves a verified problem.
-   Keep structural design, behavioral design, and implementation
    decisions distinguishable.
-   Every proposed change must state its impact on public API,
    dependencies, typing, documentation, tests, and distribution.
-   Preserve explicit `__all__` declarations where appropriate and keep
    exports intentional.
-   No implementation phase begins while its design checkpoint is
    unresolved.

### 1.2 Scope boundaries

**In scope**

-   Internal package organization and ownership.
-   Module responsibilities and dependency relationships.
-   Class/function/helper responsibilities and contracts.
-   Cross-package shared behavior and canonical helper ownership.
-   Data and execution flows.
-   Mutation, return-type, error, and state contracts.
-   Internal typing and extension boundaries.
-   Architecture documentation and architecture-focused verification.

**Out of scope unless separately approved**

-   New user-facing features.
-   Broad API redesign.
-   Unrelated performance optimization.
-   Opportunistic style cleanup.
-   Compatibility-breaking changes.
-   Rewriting working implementations without an evidenced architectural
    reason.
-   Reopening the completed Top-Level Architecture Refactor merely
    because another arrangement is aesthetically preferable.

------------------------------------------------------------------------

## 2. Entry gate: close the Top-Level Architecture Refactor

This initiative must not start its repository-wide design work until
both remaining phases are complete.

### 2.1 Required predecessor work

-   [ ] Phase 4 --- Package Boundaries and Documentation completed.
-   [ ] Phase 5 --- Final Architecture Verification completed.
-   [ ] Every predecessor acceptance criterion is either verified or
    explicitly blocked with a decision owner and rationale.
-   [ ] No undocumented or silently accepted residual gaps remain.
-   [ ] The final architecture documents describe the architecture
    actually implemented.
-   [ ] The final verification evidence is available to Hermes.

### 2.2 Entry checkpoint --- Architecture baseline freeze

**Checkpoint ID:** `AE-CP0`

Hermes must collect and record:

  -----------------------------------------------------------------------------------------
  Required item           Evidence / reference                      Status
  ----------------------- ----------------------------------------- -----------------------
  Approved top-level      `[FILL: document and section]`            `[OPEN]`
  target structure                                                  

  Dependency rules,       `[FILL: document and section]`            `[OPEN]`
  especially Section 4.1                                            

  Approved root and       `[FILL: document and section]`            `[OPEN]`
  package public APIs                                               

  Phase 4 completion      `[FILL: report / PR / commit]`            `[OPEN]`
  evidence                                                          

  Phase 5 verification    `[FILL: report / CI / build artifacts]`   `[OPEN]`
  evidence                                                          

  Known accepted          `[FILL: issue / decision]`                `[OPEN]`
  limitations or blockers                                           

  Repository revision     `[FILL: commit SHA]`                      `[OPEN]`
  used as baseline                                                  
  -----------------------------------------------------------------------------------------

**Research questions for Hermes**

1.  Which exact documents define the approved target architecture?
2.  Are any architecture documents contradictory, stale, or less
    authoritative than another?
3.  Which final commit represents the verified baseline?
4.  Are any Phase 4 or Phase 5 acceptance criteria still open?
5.  Are there known limitations that should constrain the next
    initiative?

**Exit criteria**

-   [ ] The baseline commit is identified.
-   [ ] The authoritative architecture references are identified.
-   [ ] Phase 4 and Phase 5 are complete under their acceptance rules.
-   [ ] Any unresolved item is a genuine blocker with an explicit
    disposition.
-   [ ] The baseline is frozen for the first research pass.

**Gate:** If any predecessor criterion is not verified and is not a
genuine blocker with an approved disposition, stop. Return the missing
work to the responsible phase rather than starting the next initiative
on an incomplete foundation.

------------------------------------------------------------------------

## 3. Initiative structure

The work is divided into research/design levels followed by controlled
implementation and verification. The levels are related, but not every
finding requires a code change.

  --------------------------------------------------------------------------
  Stage                   Focus                   Primary output
  ----------------------- ----------------------- --------------------------
  0                       Baseline and research   Verified baseline and
                          protocol                research inventory

  1                       Package Architecture    Package-internal target
                                                  designs and ownership maps

  2                       Module Architecture     Module responsibilities,
                                                  contracts, and dependency
                                                  maps

  3                       Component Architecture  Class/function/helper
                                                  boundaries and interaction
                                                  designs

  4                       Behavioral /            Explicit data flows,
                          Implementation          invariants, and execution
                          Architecture            contracts

  5                       Architecture            Verified
                          Integration and         implementation-to-design
                          Verification            traceability
  --------------------------------------------------------------------------

The order is intentional: establish ownership before designing module
boundaries; establish module boundaries before making component-level
decisions; understand component responsibilities before specifying
detailed execution behavior.

### 3.1 Research and implementation are separate workstreams

For each level, use two distinct passes:

**Pass A --- Research and design** - Inventory the current state. -
Gather source evidence. - Identify actual problems and uncertainty. -
Fill the research questions in this plan. - Propose alternatives where
necessary. - Record decisions and obtain approval.

**Pass B --- Implementation and verification** - Implement only approved
changes. - Keep changes within the approved scope. - Add or update
focused tests. - Verify original acceptance criteria. - Update
documentation only where it reflects the implemented result. - Report
any remaining gaps honestly.

Do not combine discovery, design approval, and broad implementation into
one unreviewed task.

------------------------------------------------------------------------

## 4. Level 1 --- Package Architecture

**Objective:** Understand the internal architecture of each approved
package, establish clear ownership of its subsystems, and determine
whether its internal organization supports its responsibility without
violating top-level boundaries.

### 4.1 Research inventory

Hermes must inspect every package that exists in the approved baseline.
Do not assume package names or internal structure from this template;
derive them from the repository and approved architecture.

**Package inventory --- fill from repository**

  ---------------------------------------------------------------------------------
  Package        Current               Entry points / Internal       Research
                 responsibility        public surface subsystems     status
  -------------- --------------------- -------------- -------------- --------------
  `cleaning`     `[FILL]`              `[FILL]`       `[FILL]`       `[OPEN]`

  `caching`      `[FILL]`              `[FILL]`       `[FILL]`       `[OPEN]`

  `analytics`    `[FILL]`              `[FILL]`       `[FILL]`       `[OPEN]`

  `profiling`    `[FILL]`              `[FILL]`       `[FILL]`       `[OPEN]`

  Other approved `[FILL if present]`   `[FILL]`       `[FILL]`       `[OPEN]`
  package(s)                                                         
  ---------------------------------------------------------------------------------

### 4.2 Questions to investigate for every package

For each package, Hermes must answer with repository evidence:

1.  What is the package's actual responsibility today?
2.  What responsibility does the approved architecture assign to it?
3.  Do actual behavior and intended ownership agree?
4.  What distinct subsystems or domains exist inside it?
5.  Which modules belong to each subsystem, and why?
6.  Are there modules with multiple unrelated responsibilities?
7.  Are any responsibilities implemented in another package even though
    this package should own them?
8.  Does this package depend on another package in a way that violates
    the approved dependency direction?
9.  Are there imports that create hidden coupling or make independent
    testing difficult?
10. Are internal helpers duplicated? If so, are their semantics
    genuinely identical?
11. Does the package expose a coherent public API?
12. Are internal implementation details accidentally reachable through
    package exports?
13. Are there package-level side effects or initialization
    responsibilities that belong elsewhere?
14. What should remain unchanged?

For every identified issue, record: - Exact files and symbols. - The
current behavior or dependency. - The relevant architecture rule or
invariant. - Why the current arrangement is a problem. - A minimal
target-state proposal. - Alternatives considered. - Risks and
compatibility impact. - Tests or other evidence needed.

### 4.3 Package ownership map

Create one ownership map per package.

  ----------------------------------------------------------------------------
  Subsystem /      Current owner  Proposed owner Evidence       Decision
  responsibility                                                
  ---------------- -------------- -------------- -------------- --------------
  `[FILL]`         `[FILL]`       `[FILL]`       `[FILL]`       `[OPEN]`

  ----------------------------------------------------------------------------

The map must distinguish: - Domain responsibility. - Public API
ownership. - Implementation ownership. - Shared infrastructure
ownership. - Integration/adaptor ownership.

Do not use "shared" as a default owner. A shared component must have a
demonstrated cross-domain responsibility and a clearly defined contract.

### 4.4 Package dependency review

For each package, document:

-   Allowed dependencies.
-   Actual direct dependencies.
-   Actual indirect or transitive coupling where relevant.
-   Imports that cross architectural boundaries.
-   Whether dependencies are runtime, typing-only, test-only, or
    optional-extra dependencies.
-   Whether dependency direction is stable and intentional.

**Dependency matrix --- fill from repository and approved rules**

  ------------------------------------------------------------------------------------
  Consumer package  Permitted dependencies         Actual            Violations /
                                                   dependencies      questions
  ----------------- ------------------------------ ----------------- -----------------
  `cleaning`        `[FILL from approved rules]`   `[FILL]`          `[FILL]`

  `caching`         `[FILL]`                       `[FILL]`          `[FILL]`

  `analytics`       `[FILL]`                       `[FILL]`          `[FILL]`

  `profiling`       `[FILL]`                       `[FILL]`          `[FILL]`
  ------------------------------------------------------------------------------------

Do not infer permission from an import that happens to work. Compare it
with the approved dependency rules.

### 4.5 Special investigation: `cleaning._common.py`

This module requires an explicit ownership and invariant review. Do not
automatically move its contents or replace it with a generic shared
package.

For every helper in `cleaning._common.py`, record:

  ------------------------------------------------------------------------------
  Helper      Call sites  Semantic         Invariants /  Candidate   Decision
                          responsibility   assumptions   owner       
  ----------- ----------- ---------------- ------------- ----------- -----------
  `[FILL]`    `[FILL]`    `[FILL]`         `[FILL]`      `[FILL]`    `[OPEN]`

  ------------------------------------------------------------------------------

Hermes must answer:

1.  Which helpers are cleaning-domain-specific?
2.  Which helpers are shared only by multiple cleaning modules?
3.  Which helpers are genuinely domain-independent?
4.  Do similarly named or implemented helpers have different contracts?
5.  Which invariants are relied upon by callers?
6.  Would moving a helper change import direction, initialization,
    behavior, or public/private status?
7.  Is there a demonstrated need for a canonical shared location?
8.  If so, what is the narrowest appropriate location and why?

**Explicit constraint:** Do not create `bynat._shared` merely because
multiple packages use helper-like code. A shared location requires
evidence of a stable, domain-independent responsibility. If no such
responsibility exists, retain package ownership or use a narrower,
justified location.

### 4.6 Package documentation questions

-   What should the package-level documentation promise?
-   Which concepts belong in the package overview?
-   Which APIs are public and supported?
-   Which modules are implementation details?
-   Are examples consistent with actual imports and signatures?
-   Are optional dependencies and extras described accurately?
-   Are package-specific guarantees documented without duplicating
    unrelated package documentation?

### 4.7 Package Architecture deliverables

For each package:

-   [ ] Current-state package map.
-   [ ] Responsibility and ownership statement.
-   [ ] Subsystem inventory.
-   [ ] Module-to-subsystem mapping.
-   [ ] Dependency review.
-   [ ] Public/internal boundary review.
-   [ ] Shared-helper ownership findings.
-   [ ] Verified issue list with evidence.
-   [ ] Target-state proposal, only where needed.
-   [ ] Alternatives and trade-offs.
-   [ ] Package-level documentation requirements.
-   [ ] Explicit list of items that should not change.

### 4.8 Checkpoints

**`AE-CP1A` --- Package inventory complete** - \[ \] Every approved
package has been inspected. - \[ \] Every relevant module has an
identified responsibility or an explicit unresolved question. - \[ \] No
package has been skipped based on assumptions.

**`AE-CP1B` --- Ownership and dependency review complete** - \[ \]
Ownership maps are complete. - \[ \] Dependency rules have been checked
against actual imports. - \[ \] `cleaning._common.py` has been reviewed
helper by helper. - \[ \] Shared ownership decisions are evidence-based.

**`AE-CP1C` --- Package design approved** - \[ \] Current state and
target state are clearly separated. - \[ \] Each proposed change has a
concrete rationale. - \[ \] No unapproved top-level boundary change is
hidden in the proposal. - \[ \] Risks and compatibility effects are
documented. - \[ \] Design review is complete before implementation
begins.

**Level 1 exit criteria** - \[ \] Every package has a documented
responsibility. - \[ \] Internal subsystem ownership is clear. - \[ \]
Package dependency relationships are intentional. - \[ \] All material
findings have a decision: retain, change, defer with blocker, or
reject. - \[ \] The target design is approved.

------------------------------------------------------------------------

## 5. Level 2 --- Module Architecture

**Objective:** Define the responsibility, boundaries, interfaces, and
dependencies of individual modules inside each approved package.

This level begins after Level 1 package ownership is approved. It must
not independently reassign package-level responsibilities.

### 5.1 Module inventory

Hermes must derive the complete module list from the repository,
including relevant private modules and nested packages.

  ----------------------------------------------------------------------------
  Package     Module path Current     Main        Proposed         Status
                          purpose     symbols     responsibility   
  ----------- ----------- ----------- ----------- ---------------- -----------
  `[FILL]`    `[FILL]`    `[FILL]`    `[FILL]`    `[FILL]`         `[OPEN]`

  ----------------------------------------------------------------------------

### 5.2 Questions for each module

1.  Does the module have one coherent reason to change?
2.  Is its responsibility consistent with its owning package and
    subsystem?
3.  Are its classes and functions cohesive?
4.  Does it contain unrelated domain logic?
5.  Does it import implementation details unnecessarily?
6.  Are its dependencies directed toward stable abstractions or
    appropriate lower-level modules?
7.  Does it create import cycles or initialization-order sensitivity?
8.  Are module-level constants, registries, caches, or mutable state
    intentional?
9.  Are public and private symbols distinguishable?
10. Are type-only dependencies separated where appropriate?
11. Is the module independently testable?
12. Does its filename and location communicate its actual
    responsibility?
13. Would splitting or merging it solve a demonstrated problem?
14. What existing behavior must remain unchanged?

### 5.3 Module contract record

Complete one record per module where architectural decisions are needed.

**Module:** `[FILL: full module path]`

-   Owning package: `[FILL]`
-   Owning subsystem: `[FILL]`
-   Current responsibility: `[FILL]`
-   Intended responsibility: `[FILL]`
-   Public symbols: `[FILL]`
-   Private/internal symbols: `[FILL]`
-   Imports and dependencies: `[FILL]`
-   Inputs and outputs: `[FILL]`
-   State or side effects: `[FILL]`
-   Invariants: `[FILL]`
-   Callers and consumers: `[FILL]`
-   Tests covering it: `[FILL]`
-   Confirmed issues: `[FILL]`
-   Proposed changes: `[FILL]`
-   Compatibility risks: `[FILL]`
-   Open research questions: `[FILL]`
-   Decision: `[RETAIN / CHANGE / BLOCKED / REJECTED]`

### 5.4 Module interaction map

For each package, produce a module dependency map based on actual
imports. Label edges as:

-   Runtime dependency.
-   Type-checking-only dependency.
-   Optional integration.
-   Test-only dependency.

Record whether each edge is allowed under the approved package and
subsystem design.

**Questions to resolve** - Which modules are central dependency hubs? -
Are there modules that know too much about other modules? - Are there
cycles hidden by local imports or delayed imports? - Are there
dependency edges that exist only because responsibilities are
misplaced? - Would a narrow interface or function-level dependency solve
the issue without adding unnecessary abstractions?

### 5.5 Module design checkpoints

**`AE-CP2A` --- Module inventory complete** - \[ \] All relevant modules
are accounted for. - \[ \] Every module has a current responsibility. -
\[ \] Main symbols and import relationships are inventoried.

**`AE-CP2B` --- Module contracts reviewed** - \[ \] Responsibility and
cohesion are assessed. - \[ \] Inputs, outputs, state, side effects, and
invariants are recorded where relevant. - \[ \] Test coverage and gaps
are identified. - \[ \] Dependency concerns are evidence-backed.

**`AE-CP2C` --- Module target design approved** - \[ \] Proposed splits,
merges, moves, or interface changes are justified. - \[ \] Package
ownership remains intact. - \[ \] Public API and compatibility effects
are documented. - \[ \] No implementation begins before approval.

**Level 2 exit criteria** - \[ \] Every material module has a clear
responsibility. - \[ \] Module dependencies match the approved package
design. - \[ \] Important module contracts are documented. - \[ \] All
proposed structural changes are approved or explicitly blocked.

------------------------------------------------------------------------

## 6. Level 3 --- Component Architecture

**Objective:** Review the architecture of classes, functions, helpers,
data structures, and other implementation components without assuming
that every component needs an abstraction or redesign.

### 6.1 Component inventory

Build the inventory from actual source code and include only components
relevant to package/module responsibility or behavior.

  -------------------------------------------------------------------------------------------------
  Component   Kind                             Module      Responsibility   Callers /   Status
                                                                            consumers   
  ----------- -------------------------------- ----------- ---------------- ----------- -----------
  `[FILL]`    `[class/function/helper/type]`   `[FILL]`    `[FILL]`         `[FILL]`    `[OPEN]`

  -------------------------------------------------------------------------------------------------

### 6.2 Questions for classes

-   Does the class represent a meaningful domain concept or stable
    responsibility?
-   Is its state necessary and internally coherent?
-   Are initialization and lifecycle responsibilities clear?
-   Does it own behavior or merely forward calls?
-   Does it have hidden dependencies or side effects?
-   Are its public methods consistent with its intended role?
-   Are subclassing and extension contracts intentional?
-   Is inheritance justified, or would composition or plain functions be
    clearer?
-   Are constructor and method signatures stable and documented?
-   Does it preserve existing API and mutation guarantees?

### 6.3 Questions for functions

-   Is the function cohesive and named according to its actual behavior?
-   Are input and output contracts explicit?
-   Are side effects and mutation behavior clear?
-   Does it depend on hidden global or module state?
-   Does it mix validation, transformation, I/O, and orchestration
    unnecessarily?
-   Is it reused because it has shared semantics, or merely because its
    code looks similar?
-   Are edge cases and error behavior consistent?
-   Is the function vectorized or otherwise appropriate for the
    library's performance expectations?
-   Does it preserve index, ordering, dtype, and data-shape guarantees
    where relevant?

### 6.4 Shared helper decision protocol

Before consolidating any helper:

1.  Enumerate all implementations and call sites.
2.  Compare semantics, not just code shape.
3.  Compare input/output contracts.
4.  Compare validation and error behavior.
5.  Compare mutation and side-effect behavior.
6.  Compare assumptions and invariants.
7.  Identify the domain that owns the behavior.
8.  Determine whether a canonical implementation reduces real
    duplication without coupling unrelated domains.
9.  Record migration and regression risks.
10. Obtain approval before changing ownership.

**Decision outcomes** - Keep separate: contracts or semantics differ. -
Keep within one package: behavior is shared only within that domain. -
Consolidate within an existing owner: one domain owns the canonical
behavior. - Introduce a narrowly scoped shared location: only when
domain-independent ownership is demonstrated. - Defer: evidence is
insufficient or migration risk is unresolved.

### 6.5 Component interaction and call-flow review

For components with meaningful collaboration, document:

-   Entry point.
-   Validation steps.
-   Main transformation or operation.
-   Helper calls.
-   External or optional integrations.
-   State changes and side effects.
-   Return path.
-   Error paths.

Do not draw speculative flows. Every material edge must be traceable to
code or a verified test.

### 6.6 Component checkpoints

**`AE-CP3A` --- Component inventory complete** - \[ \] Relevant classes,
functions, and helpers are inventoried. - \[ \] Call sites and consumers
are identified for components under review.

**`AE-CP3B` --- Contracts and ownership reviewed** - \[ \] Inputs,
outputs, side effects, and invariants are assessed. - \[ \]
Shared-helper decisions compare semantics and contracts. - \[ \]
Unnecessary abstractions are explicitly avoided.

**`AE-CP3C` --- Component design approved** - \[ \] Responsibility
changes are justified. - \[ \] Interactions and call flows are
evidence-backed. - \[ \] API and behavior compatibility are addressed. -
\[ \] Implementation scope is approved.

**Level 3 exit criteria** - \[ \] Material components have coherent
responsibilities. - \[ \] Shared behavior has intentional ownership. -
\[ \] Important interactions and contracts are understood. - \[ \] Every
proposed change has an approved design.

------------------------------------------------------------------------

## 7. Level 4 --- Behavioral and Implementation Architecture

**Objective:** Make the library's important behavioral contracts and
execution flows explicit, then verify that implementation choices
preserve them.

This level is not a license for broad implementation rewrites. It is a
systematic review of behavior that crosses modules or components.

### 7.1 Behavioral domains to investigate

Hermes must determine which domains actually exist in the current
repository and complete the relevant sections. Do not assume every topic
applies to every package.

#### A. Data flow and transformation lifecycle

Questions: - What enters each public operation? - Where does validation
happen? - What transformations occur, and in what order? - Which
components own each step? - How are intermediate values represented? -
How are failures propagated? - What is returned? - Are index, ordering,
shape, dtype, and metadata preserved where promised?

**Evidence / diagrams:** `[FILL]`

#### B. Mutation and `inplace` contracts

Questions: - Which operations mutate the original object? - Which
operations return a new object? - What exactly does `inplace` mean for
each applicable API? - Are copy/view behavior and chained operations
predictable? - Are mutation guarantees consistent between class APIs and
DataFrame accessors? - Are partial mutations possible if an operation
fails? - Are tests asserting the actual contract rather than an
implementation detail?

**Contract matrix:** `[FILL from actual public API]`

  ----------------------------------------------------------------------------
  API /       Default     `inplace`        Return      Failure     Evidence
  operation   behavior    behavior         value       mutation    
                                                       behavior    
  ----------- ----------- ---------------- ----------- ----------- -----------
  `[FILL]`    `[FILL]`    `[FILL / N/A]`   `[FILL]`    `[FILL]`    `[FILL]`

  ----------------------------------------------------------------------------

Do not infer or standardize behavior without reviewing the approved API
and actual implementation.

#### C. Return types and typing contracts

Questions: - Are return types explicit and accurate? - Do runtime
behavior and annotations agree? - Are unions and optional values
intentional? - Are pandas/numpy types represented accurately? - Are type
stubs synchronized with runtime APIs? - Are overloads needed, or would
they add unnecessary complexity? - Are internal and public typing
boundaries clear?

**Evidence / unresolved typing questions:** `[FILL]`

#### D. Error handling and validation

Questions: - Which layer validates each input? - Are errors raised at
the right boundary? - Are exception types stable and meaningful? - Are
errors wrapped or suppressed unnecessarily? - Do optional integrations
fail clearly when dependencies are missing? - Can a failure leave
partially modified data or persistent state? - Are error contracts
documented and tested?

**Error behavior matrix:** `[FILL]`

#### E. State, resources, and lifecycle

Investigate only where applicable: - Module-level state. - Per-instance
state. - Temporary resources. - File handles. - Database connections and
transactions. - Cache lifecycle and invalidation. - Migration
lifecycle. - Cleanup and recovery behavior. - Concurrency and process
boundaries.

Questions: - Who owns the resource? - Who creates and closes it? - What
happens after interruption or failure? - Are transactions and atomicity
guarantees clear? - Is state shared unexpectedly? - Are lifecycle
guarantees tested?

**Resource/state ownership map:** `[FILL]`

#### F. Optional integrations and extras

Questions: - Which integrations are core versus optional? - Where are
optional imports performed? - Are missing-extra errors actionable? - Do
optional dependencies leak into core import paths? - Are extras
boundaries consistent across code, metadata, docs, and tests? - Are
integration adapters isolated from domain logic?

**Integration inventory:** `[FILL]`

#### G. Performance and memory contracts

This is an architecture review, not an open-ended optimization project.

Questions: - Are there architectural bottlenecks caused by ownership or
data flow? - Are large DataFrames copied unnecessarily? - Are row-wise
operations used where vectorized approaches are expected? - Are caches
bounded and invalidated correctly? - Are performance-sensitive paths
measurable? - Is a performance change required to solve an architectural
problem, or is it a separate optimization task?

Any optimization proposal must include a reproducible baseline,
representative workload, correctness checks, and measurable expected
benefit.

**Evidence / benchmarks / decision:** `[FILL]`

### 7.2 Behavioral contract records

For each important public operation or cross-module flow, record:

-   Public entry point: `[FILL]`
-   Owning package/module/component: `[FILL]`
-   Accepted inputs: `[FILL]`
-   Validation rules: `[FILL]`
-   Execution sequence: `[FILL]`
-   Output and return type: `[FILL]`
-   Mutation behavior: `[FILL]`
-   Side effects/state changes: `[FILL]`
-   Error behavior: `[FILL]`
-   Index/order/dtype guarantees: `[FILL]`
-   Optional dependency requirements: `[FILL]`
-   Relevant tests: `[FILL]`
-   Documentation reference: `[FILL]`
-   Unresolved questions: `[FILL]`

### 7.3 Behavioral checkpoints

**`AE-CP4A` --- Behavioral inventory complete** - \[ \] Applicable
behavioral domains are identified. - \[ \] Important public operations
and cross-module flows are inventoried. - \[ \] No behavior has been
inferred solely from names or docstrings.

**`AE-CP4B` --- Contracts documented** - \[ \] Inputs, outputs,
mutation, errors, and side effects are documented where relevant. - \[
\] Runtime behavior is compared with annotations and stubs. - \[ \]
Tests are mapped to the contracts they verify.

**`AE-CP4C` --- Implementation design approved** - \[ \] Any proposed
behavior change has an explicit rationale. - \[ \] Compatibility impact
is documented. - \[ \] Implementation boundaries and test requirements
are agreed. - \[ \] No broad rewrite is bundled into a narrow fix.

**Level 4 exit criteria** - \[ \] Important behavioral contracts are
explicit. - \[ \] Cross-module flows and ownership are understood. - \[
\] Material mismatches have approved resolutions or genuine blockers. -
\[ \] Implementation work is bounded and traceable.

------------------------------------------------------------------------

## 8. Level 5 --- Architecture Integration and Final Verification

**Objective:** Verify that the resulting repository, runtime behavior,
documentation, typing, tests, and distribution all agree with the
approved architecture.

### 8.1 Traceability matrix

Every approved architectural decision must map to implementation and
verification evidence.

  -------------------------------------------------------------------------------------
  Decision /    Approved    Implementation   Test /         Documentation   Status
  requirement   design      location         verification   reference       
  ID            reference                    evidence                       
  ------------- ----------- ---------------- -------------- --------------- -----------
  `[FILL]`      `[FILL]`    `[FILL]`         `[FILL]`       `[FILL]`        `[OPEN]`

  -------------------------------------------------------------------------------------

### 8.2 Verification checklist

#### Structure and ownership

-   [ ] Repository structure matches the approved package, subsystem,
    and module design.
-   [ ] Each package and module has clear ownership.
-   [ ] No responsibility was moved without an approved decision.
-   [ ] No unnecessary abstraction or generic shared layer was
    introduced.

#### Dependencies and imports

-   [ ] Package and module dependency directions comply with approved
    rules.
-   [ ] No circular imports exist.
-   [ ] No hidden dependency on private implementation details crosses
    an ownership boundary without justification.
-   [ ] Optional dependencies remain isolated as intended.

#### Public API and compatibility

-   [ ] Root and package exports remain consistent with the approved
    API.
-   [ ] Explicit `__all__` declarations are accurate and intentional.
-   [ ] Private helpers and implementation details are not accidentally
    exported.
-   [ ] Existing class APIs and accessor APIs preserve their approved
    contracts.
-   [ ] Signatures, return types, mutation behavior, and error behavior
    match approved contracts.
-   [ ] No compatibility commitment was removed without explicit
    approval.

#### Runtime behavior

-   [ ] Important data flows match the approved design.
-   [ ] Mutation and state behavior are verified.
-   [ ] Error and recovery paths are tested where applicable.
-   [ ] Index, ordering, dtype, and shape guarantees are verified where
    applicable.
-   [ ] Optional integrations behave correctly with and without their
    extras.

#### Tests and quality

-   [ ] Focused tests cover each changed contract.
-   [ ] Regression tests cover affected existing behavior.
-   [ ] The full required test suite passes.
-   [ ] Ruff passes.
-   [ ] Mypy passes.
-   [ ] Test standards and repository-specific testing rules are
    followed.
-   [ ] No tests were weakened, deleted, or bypassed merely to make the
    suite pass.

#### Documentation and typing

-   [ ] Package and module documentation reflects actual ownership.
-   [ ] Examples use valid current imports and APIs.
-   [ ] Docstrings accurately describe runtime behavior.
-   [ ] Type annotations and stubs agree with runtime behavior.
-   [ ] Architecture documents describe the implemented state, not an
    aspirational design.
-   [ ] No stale paths, exports, or behavioral claims remain.

#### Distribution

-   [ ] Wheel builds successfully.
-   [ ] Source distribution builds successfully.
-   [ ] Built artifacts install in an appropriate clean environment.
-   [ ] Installed-package smoke tests pass.
-   [ ] Core imports and intended public entry points work from the
    built distribution.
-   [ ] Optional extras are tested according to the project's supported
    matrix.

### 8.3 Final checkpoints

**`AE-CP5A` --- Implementation complete** - \[ \] All approved
implementation tasks are complete. - \[ \] No unapproved scope was
introduced. - \[ \] Every change maps to an approved decision.

**`AE-CP5B` --- Verification complete** - \[ \] All applicable checklist
items have evidence. - \[ \] Test and quality commands and results are
recorded. - \[ \] Distribution artifacts and smoke-test evidence are
recorded. - \[ \] Remaining blockers are explicit and genuine.

**`AE-CP5C` --- Documentation and closure review** - \[ \] Documentation
matches the final implementation. - \[ \] Traceability matrix is
complete. - \[ \] No undocumented residual gap is treated as complete. -
\[ \] Final review confirms all acceptance criteria.

**Final acceptance rule:** The initiative is complete only when every
acceptance criterion is implemented and verified, or is explicitly
blocked pending a decision. A note in a report is not a substitute for
implementation. Partial acceptance requires a genuine blocker or
explicit approval.

------------------------------------------------------------------------

## 9. Hermes research protocol

This section defines how Hermes should use the plan. It is intentionally
explicit so that research fills evidence gaps rather than silently
converting assumptions into design decisions.

### 9.1 Research responsibilities

Hermes must:

1.  Read the approved architecture documents and the repository's
    applicable development/testing standards before making
    recommendations.
2.  Inspect the actual repository at the recorded baseline commit.
3.  Build inventories from source, imports, tests, packaging metadata,
    docs, and stubs rather than relying on memory or old reports.
4.  Cite exact file paths and relevant symbols for every material
    finding.
5.  Use line references or concise code excerpts where they help
    reviewers verify claims.
6.  Distinguish observed facts, interpretations, hypotheses, and
    recommendations.
7.  Fill every relevant `[FILL]` field with evidence or mark it
    `UNKNOWN` with a specific research action.
8.  Resolve questions through repository research where possible; do not
    ask the user to decide facts that can be established from code.
9.  Present genuine design decisions to the user with alternatives and
    trade-offs.
10. Avoid changing code during read-only investigation.
11. Identify contradictory documentation and state which source is
    authoritative, with justification.
12. Record negative findings when useful (for example, a suspected cycle
    was investigated and not found).

### 9.2 Evidence quality

A finding is not considered established merely because: - A filename
suggests a responsibility. - A docstring claims behavior that code does
not implement. - An import currently succeeds. - Two helpers have
similar names or bodies. - A test passes without checking the relevant
contract. - An earlier architecture report makes the claim.

Prefer evidence from: - Actual implementation and call sites. -
Import/dependency analysis. - Runtime behavior and focused
experiments. - Tests that assert the relevant contract. - Packaging
metadata and built artifacts. - Current documentation and stubs, checked
against implementation.

### 9.3 Required finding format

For every material finding:

**Finding ID:** `[FILL]`\
**Level / package / module:** `[FILL]`\
**Category:**
`[OWNERSHIP / DEPENDENCY / COHESION / API / BEHAVIOR / TYPING / DOCS / TESTABILITY / PERFORMANCE / OTHER]`\
**Severity / priority:** `[FILL with rationale]`\
**Observed fact:** `[FILL]`\
**Evidence:** `[FILE PATHS, SYMBOLS, TESTS, COMMAND OUTPUT]`\
**Relevant rule or contract:** `[FILL]`\
**Why it matters:** `[FILL]`\
**Confidence:** `[HIGH / MEDIUM / LOW]`\
**Alternatives:** `[FILL]`\
**Recommendation:** `[FILL]`\
**Compatibility / regression risks:** `[FILL]`\
**Required tests:** `[FILL]`\
**Decision needed from user:** `[YES / NO — explain]`

### 9.4 Unknowns and decision register

Do not hide uncertainty inside prose. Maintain a register:

  -----------------------------------------------------------------------------
  ID          Question / Why it     Research   Evidence   Decision   Status
              unknown    matters    action                owner      
  ----------- ---------- ---------- ---------- ---------- ---------- ----------
  `AE-Q001`   `[FILL]`   `[FILL]`   `[FILL]`   `[FILL]`   `[FILL]`   `[OPEN]`

  -----------------------------------------------------------------------------

Use these statuses consistently: - `OPEN` --- not yet researched. -
`INVESTIGATING` --- research is in progress. - `ANSWERED` --- evidence
supports an answer. - `DECISION_REQUIRED` --- facts are known, but a
design choice is needed. - `BLOCKED` --- a genuine external or technical
blocker prevents progress. - `CLOSED` --- resolved and recorded.

### 9.5 Decision record

For every non-trivial architectural decision:

-   Decision ID: `[FILL]`
-   Date / baseline commit: `[FILL]`
-   Context and verified problem: `[FILL]`
-   Constraints: `[FILL]`
-   Options considered: `[FILL]`
-   Chosen option: `[FILL]`
-   Reasons and trade-offs: `[FILL]`
-   Rejected options and reasons: `[FILL]`
-   API / behavior / typing / docs / test impact: `[FILL]`
-   Approval: `[FILL]`
-   Revisit trigger, if any: `[FILL]`

### 9.6 Workstream and concurrency rules

-   Use subagents for bounded investigation or implementation tasks
    where that reduces duplicated effort.
-   No more than **two subagents may be active at the same time**. This
    is a maximum, not a requirement to use two.
-   Sequential jobs are allowed when one task depends on another.
-   Give each subagent a narrow scope, expected evidence, and explicit
    exclusions.
-   Avoid assigning overlapping write scopes.
-   Investigation tasks should be read-only unless write access is
    explicitly authorized.
-   A subagent may implement focused tests when assigned; the supervisor
    must independently review the tests and verify that they prove the
    required behavior.
-   The supervisor owns integration, acceptance-criteria traceability,
    and final decisions.
-   The supervisor must not treat a subagent's completion summary as
    proof of completion.
-   If a deliverable is incomplete but the missing work is feasible,
    return it for completion rather than accepting a documented gap.
-   Do not begin dependent work until the required upstream checkpoint
    is approved.

### 9.7 Supervisor review protocol

For each completed workstream, the supervisor must:

1.  Re-read the original task and its acceptance criteria.
2.  Inspect the actual diff or research artifacts.
3.  Verify each claim against source evidence.
4.  Check scope boundaries and excluded files.
5.  Confirm tests cover the intended contract and are not weakened.
6.  Identify missing acceptance criteria.
7.  Return feasible omissions for completion.
8.  Mark genuine blockers with evidence and the decision required.
9.  Record the final disposition in the decision/traceability registers.

------------------------------------------------------------------------

## 10. Deliverable and documentation strategy

The following are proposed deliverables. Hermes must inspect the
existing documentation structure and recommend exact paths before
creating files. Do not create duplicate or competing architecture
documents.

  -----------------------------------------------------------------------------------------
  Deliverable       Purpose            Proposed path                      Decision
  ----------------- ------------------ ---------------------------------- -----------------
  Initiative plan   Overall phases,    `[FILL: this file's final path]`   `[OPEN]`
                    gates, and                                            
                    protocol                                              

  Package           Package inventory, `[FILL after docs audit]`          `[OPEN]`
  architecture      ownership,                                            
  research          dependencies                                          

  Module            Module             `[FILL after docs audit]`          `[OPEN]`
  architecture      responsibilities                                      
  research          and contracts                                         

  Component         Component          `[FILL after docs audit]`          `[OPEN]`
  architecture      ownership and                                         
  research          interactions                                          

  Behavioral        Important data and `[FILL after docs audit]`          `[OPEN]`
  contracts         execution                                             
                    contracts                                             

  Decision register Approved and       `[FILL after docs audit]`          `[OPEN]`
                    rejected design                                       
                    decisions                                             

  Final             Evidence of final  `[FILL after docs audit]`          `[OPEN]`
  verification      acceptance                                            
  report                                                                  
  -----------------------------------------------------------------------------------------

Documentation rules:

-   Reuse existing authoritative documents where appropriate.
-   Avoid duplicating the same architecture facts in several places.
-   Keep research findings separate from approved target-state
    decisions.
-   Update architecture documents after implementation, not before it is
    known to be complete.
-   Do not describe proposed behavior as implemented behavior.
-   Do not create a report file merely to satisfy a template if the
    repository's established documentation process requires another
    location or format.

------------------------------------------------------------------------

## 11. Risks and safeguards

  -----------------------------------------------------------------------
  Risk                                Safeguard
  ----------------------------------- -----------------------------------
  Reopening top-level decisions       Treat the completed top-level
  without evidence                    architecture as the baseline;
                                      escalate only verified
                                      contradictions or blockers.

  Refactoring based on aesthetics     Require a concrete problem,
                                      evidence, and acceptance criteria.

  Creating generic shared             Require demonstrated shared
  abstractions                        semantics and explicit ownership.

  Missing private/internal modules    Derive inventories from the full
                                      repository, not public exports
                                      alone.

  Treating documentation as proof of  Verify claims against
  behavior                            implementation and tests.

  Losing API compatibility            Record signatures, return types,
                                      mutation behavior, and existing
                                      contracts before changes.

  Large, risky implementation batches Split work into approved, bounded
                                      scopes with checkpoints.

  Subagent summaries accepted without Supervisor independently verifies
  review                              source, diff, tests, and acceptance
                                      criteria.

  Scope creep into features or        Move unrelated work to a separate
  optimization                        issue or roadmap decision.

  Unresolved gaps silently accepted   Require explicit blocker or user
                                      approval; otherwise return feasible
                                      work for completion.
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 12. Initial research questions Hermes must answer before Level 1 starts

These questions are deliberately left open because they require
inspection of the final repository and existing project documentation.

### 12.1 Repository baseline

-   [ ] What is the exact final commit after Phase 4 and Phase 5?
-   [ ] What is the actual package tree at that commit?
-   [ ] Which architecture documents are authoritative?
-   [ ] Which development and testing standards govern the work?
-   [ ] Are there known unresolved architecture issues or approved
    exceptions?

**Findings:** `[FILL]`

### 12.2 Package inventory and boundaries

-   [ ] What packages and nested packages actually exist?
-   [ ] What are their current responsibilities?
-   [ ] Which packages contain multiple distinct subsystems?
-   [ ] Are package boundaries already sufficiently clear?
-   [ ] Which package needs the deepest investigation, and what evidence
    supports that prioritization?

**Findings:** `[FILL]`

### 12.3 Existing internal architecture evidence

-   [ ] Are there existing module maps, dependency reports, import
    graphs, or architecture notes?
-   [ ] Are those artifacts current and reproducible?
-   [ ] Which tests reveal important ownership or behavioral contracts?
-   [ ] Are there known hotspots, but only where supported by concrete
    evidence?

**Findings:** `[FILL]`

### 12.4 Research sequencing

-   [ ] Can package investigations run independently?
-   [ ] Which packages have dependencies that require sequential
    investigation?
-   [ ] What is the smallest useful workstream breakdown?
-   [ ] Which tasks are read-only?
-   [ ] Which outputs require user approval before proceeding?

**Recommended sequence and rationale:** `[FILL]`

### 12.5 Documentation placement

-   [ ] What is the existing architecture documentation convention?
-   [ ] Where should level-specific research and decision records live?
-   [ ] Can existing documents be updated instead of creating new ones?
-   [ ] Which generated documentation or stubs are affected by internal
    design changes?

**Recommendation:** `[FILL]`

**Gate:** Level 1 may begin only after this initial research establishes
the actual inventory, authoritative references, and a non-overlapping
investigation plan.

------------------------------------------------------------------------

## 13. Initiative completion criteria

The initiative is complete when all of the following are true:

-   [ ] The package, module, and component architecture is understood
    and documented to the level justified by the codebase.
-   [ ] Ownership is clear at each relevant level.
-   [ ] Dependency directions comply with approved architecture.
-   [ ] Important shared behavior has intentional, evidence-based
    ownership.
-   [ ] Important behavioral contracts and cross-module flows are
    explicit.
-   [ ] Approved changes are implemented without unrelated refactoring.
-   [ ] Existing approved public APIs and compatibility commitments are
    preserved, unless an explicit change was approved.
-   [ ] Tests verify the relevant contracts and all required test suites
    pass.
-   [ ] Ruff and Mypy pass.
-   [ ] Documentation, examples, type stubs, and implementation agree.
-   [ ] Distribution builds and appropriate installed-package smoke
    tests pass when affected or required.
-   [ ] Every architectural decision is traceable to evidence and
    approval.
-   [ ] Every acceptance criterion is verified or explicitly blocked
    pending a decision.
-   [ ] No residual gap is treated as completed merely because it is
    documented.

**Final outcome:** A maintainable internal architecture whose package,
module, component, and behavioral boundaries are intentional,
documented, and verified---without unnecessary abstractions or
uncontrolled refactoring.
