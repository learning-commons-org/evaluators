# Changelog

All notable changes to the `@learning-commons/evaluators` TypeScript SDK will be documented in this file.

## [1.1.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v1.0.0...sdks-typescript-v1.1.0) (2026-09-03)


### Features

* **evals:** add Critical Thinking onto the shared evaluator contract ([#188](https://github.com/learning-commons-org/evaluators/issues/188)) ([02d1a3c](https://github.com/learning-commons-org/evaluators/commit/02d1a3ced12d5985cc3ca0b0608e02cc7622244d))

## [1.0.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.8.0...sdks-typescript-v1.0.0) (2026-08-31)


### ⚠ BREAKING CHANGES

* **sdk:** give math one result-type name and finish its snake_case keys ([#263](https://github.com/learning-commons-org/evaluators/issues/263))
* **sdk:** bound the peer ranges and declare the Node versions that work ([#262](https://github.com/learning-commons-org/evaluators/issues/262))
* **sdk:** rename math standards alignment's contract keys to snake_case ([#260](https://github.com/learning-commons-org/evaluators/issues/260))
* **sdk:** point the require condition at the CommonJS declarations ([#261](https://github.com/learning-commons-org/evaluators/issues/261))
* **sdk:** generate input types from the contracts, with literal enum values ([#259](https://github.com/learning-commons-org/evaluators/issues/259))
* **sdk:** make zod a peer dependency so consumers own the single copy ([#258](https://github.com/learning-commons-org/evaluators/issues/258))
* **sdk:** publish declarations that typecheck, and export every evaluator's input type ([#255](https://github.com/learning-commons-org/evaluators/issues/255))
* **sdk:** return the shared envelope from math standards alignment ([#249](https://github.com/learning-commons-org/evaluators/issues/249))
* **sdk:** remove dead and misleading public exports ([#246](https://github.com/learning-commons-org/evaluators/issues/246))
* **sdk:** put Sentence Structure's output on its contract ([#229](https://github.com/learning-commons-org/evaluators/issues/229))
* **sdk:** put Grade Level Appropriateness on its contract ([#228](https://github.com/learning-commons-org/evaluators/issues/228))
* **sdk:** report the complexity model that actually ran for grades 3-4 ([#222](https://github.com/learning-commons-org/evaluators/issues/222))
* **sdk:** generate the three complexity-score schemas from their contracts ([#220](https://github.com/learning-commons-org/evaluators/issues/220))
* **sdk:** rename each evaluator's payload type from <Evaluator>Internal to <Evaluator>Result ([#219](https://github.com/learning-commons-org/evaluators/issues/219))
* **sdk:** consume the contract declarations, and fix three bugs ([#216](https://github.com/learning-commons-org/evaluators/issues/216))
* **sdk:** evaluate() takes named inputs validated against the contract ([#215](https://github.com/learning-commons-org/evaluators/issues/215))
* **sdk:** migrate evaluate() onto the result envelope ([#210](https://github.com/learning-commons-org/evaluators/issues/210))
* **sdk:** remove the TextComplexityEvaluator composite ([#209](https://github.com/learning-commons-org/evaluators/issues/209))
* **sdk:** rename TypeScript evaluators onto the eval taxonomy ([#208](https://github.com/learning-commons-org/evaluators/issues/208))
* **ts-sdk:** rename the batch grade column to grade_level ([#206](https://github.com/learning-commons-org/evaluators/issues/206))
* **ts-sdk:** name the grade level consistently at the Knowledge Graph boundary ([#205](https://github.com/learning-commons-org/evaluators/issues/205))
* **ts-sdk:** rename grade to gradeLevel on the evaluator API ([#204](https://github.com/learning-commons-org/evaluators/issues/204))
* **ts-sdk:** scope the Learning Commons key by purpose ([#203](https://github.com/learning-commons-org/evaluators/issues/203))
* **ts-sdk:** bound text at 1-10,000 chars measured as the caller sent it ([#202](https://github.com/learning-commons-org/evaluators/issues/202))
* **ts-sdk:** fault-domain error taxonomy with structured classification ([#200](https://github.com/learning-commons-org/evaluators/issues/200))

### Features

* Add new QTC evaluators to batch handling CLI ([#198](https://github.com/learning-commons-org/evaluators/issues/198)) ([8981913](https://github.com/learning-commons-org/evaluators/commit/8981913f37b42dbfd71c684b0833364835b92aec))
* Add organizational structure to the Typescript SDK ([#196](https://github.com/learning-commons-org/evaluators/issues/196)) ([59f25b0](https://github.com/learning-commons-org/evaluators/commit/59f25b0e5b7a7cf79da792060217aa2bcb6f36bd))
* add public StandardsCatalog for listing and validating academic standards ([#149](https://github.com/learning-commons-org/evaluators/issues/149)) ([16c30a5](https://github.com/learning-commons-org/evaluators/commit/16c30a55c6d187056c050e0ed2a69cc73fddf900))
* Add QTC dimension intertextuality to the typescript SDK ([#195](https://github.com/learning-commons-org/evaluators/issues/195)) ([17ae2cf](https://github.com/learning-commons-org/evaluators/commit/17ae2cf8df28e5c835825962c366e2c11dae891e))
* **evals:** add Background Knowledge Demands onto the shared evaluator contract ([#173](https://github.com/learning-commons-org/evaluators/issues/173)) ([658631f](https://github.com/learning-commons-org/evaluators/commit/658631fdcaba834f98e9f6960c790efb6ceaf412))
* **evals:** add Meaning Directness onto the shared evaluator contract ([#161](https://github.com/learning-commons-org/evaluators/issues/161)) ([5d0cee2](https://github.com/learning-commons-org/evaluators/commit/5d0cee2e0284839687f92a2a7cbb2fee4911b598))
* **evals:** add Organizational Structure onto the shared evaluator contract ([#176](https://github.com/learning-commons-org/evaluators/issues/176)) ([bc523d7](https://github.com/learning-commons-org/evaluators/commit/bc523d7cf8cc8315a5e822328d31f5d4ea0d455d))
* **evals:** add Purpose Clarity onto the shared evaluator contract ([#175](https://github.com/learning-commons-org/evaluators/issues/175)) ([ecf23cc](https://github.com/learning-commons-org/evaluators/commit/ecf23cc8999a35a1abe7e6e26f6a5e2d61bda883))
* **evals:** add Reference Knowledge Demands onto the shared evaluator contract ([#177](https://github.com/learning-commons-org/evaluators/issues/177)) ([00c031c](https://github.com/learning-commons-org/evaluators/commit/00c031c42b1ce82893f93c8b2f187506db43d325))
* **evals:** add Sentence Structure onto the shared evaluator contract ([#174](https://github.com/learning-commons-org/evaluators/issues/174)) ([10f2fcd](https://github.com/learning-commons-org/evaluators/commit/10f2fcd13f66ae2e8d62c260e0ad679263cb1554))
* **evals:** add Vocabulary Complexity onto the shared evaluator contract ([#163](https://github.com/learning-commons-org/evaluators/issues/163)) ([a434a7a](https://github.com/learning-commons-org/evaluators/commit/a434a7ac213a878148632755774a78a7b844871b))
* **sdk:** add a multi-step evaluator factory and migrate sentence-structure onto it ([#238](https://github.com/learning-commons-org/evaluators/issues/238)) ([ea14745](https://github.com/learning-commons-org/evaluators/commit/ea147458ab45e9a95439bfd802de8ba106c47b69))
* **sdk:** add an evaluator registry and collapse the two id-to-class maps onto it ([#252](https://github.com/learning-commons-org/evaluators/issues/252)) ([036c5f3](https://github.com/learning-commons-org/evaluators/commit/036c5f39712a85cda7807ddc02abbc21a7f8efdb))
* **sdk:** add the feedback family of seven evaluators ([#226](https://github.com/learning-commons-org/evaluators/issues/226)) ([cb57768](https://github.com/learning-commons-org/evaluators/commit/cb57768a15259ab2b87a5a6860603e75ce27e6e4))
* **sdk:** bind math standards alignment to both declared steps and cover it live ([#239](https://github.com/learning-commons-org/evaluators/issues/239)) ([e661ed0](https://github.com/learning-commons-org/evaluators/commit/e661ed0b505580b39c96d3197a64f393d82db0df))
* **sdk:** generate input types from the contracts, with literal enum values ([#259](https://github.com/learning-commons-org/evaluators/issues/259)) ([0134dae](https://github.com/learning-commons-org/evaluators/commit/0134daed3a6a53ddb32dd260672aec2a21467808))
* **sdk:** generate the three complexity-score schemas from their contracts ([#220](https://github.com/learning-commons-org/evaluators/issues/220)) ([af8215f](https://github.com/learning-commons-org/evaluators/commit/af8215f34530265e9a95d6d4481ab4550a93bfb5))
* **sdk:** make the feedback family runnable in batch, with csv and json output ([#227](https://github.com/learning-commons-org/evaluators/issues/227)) ([c19588b](https://github.com/learning-commons-org/evaluators/commit/c19588b37102a29624bc2e2e5b0f4d81c4979370))
* **sdk:** return the shared envelope from math standards alignment ([#249](https://github.com/learning-commons-org/evaluators/issues/249)) ([84e4085](https://github.com/learning-commons-org/evaluators/commit/84e40852b4d51b79c6de41b8d587651621f07cca))
* **ts-sdk:** batch outputs (JSON/HTML/CSV) + family-aware CLI with non-interactive mode ([#153](https://github.com/learning-commons-org/evaluators/issues/153)) ([d961f05](https://github.com/learning-commons-org/evaluators/commit/d961f050e209596e1344210df758285f8cfdad87))
* **ts-sdk:** expose llmProvider for bring-your-own-provider injection ([#115](https://github.com/learning-commons-org/evaluators/issues/115)) ([e9f3f83](https://github.com/learning-commons-org/evaluators/commit/e9f3f83d95d196cfe9192b4bee1660e174004dea))
* **ts-sdk:** family-adapter batch architecture + math standards-alignment family ([#152](https://github.com/learning-commons-org/evaluators/issues/152)) ([015ada1](https://github.com/learning-commons-org/evaluators/commit/015ada1156bcfc8582d5d31de2e22d310b952c31))


### Bug Fixes

* **deps:** bump js-yaml override to 4.3.1 for GHSA-5p4m-2wfm-xmqj ([#157](https://github.com/learning-commons-org/evaluators/issues/157)) ([29363ab](https://github.com/learning-commons-org/evaluators/commit/29363ab02fbe9d4f2c80a5f68a423dc4990ef90d))
* **deps:** patch brace-expansion and js-yaml DoS advisories in TS SDK dev tree ([#141](https://github.com/learning-commons-org/evaluators/issues/141)) ([1c36918](https://github.com/learning-commons-org/evaluators/commit/1c369185e70344057f9c7f89e38d10880e661952))
* **evals-prompts:** correct GLA grade bands and re-sync prompt copies ([#159](https://github.com/learning-commons-org/evaluators/issues/159)) ([5e581a2](https://github.com/learning-commons-org/evaluators/commit/5e581a274624ca3a6f4951344501745eb84e02fa))
* harden Knowledge Graph client pagination, code normalization, and ambiguity detection ([#148](https://github.com/learning-commons-org/evaluators/issues/148)) ([19a423a](https://github.com/learning-commons-org/evaluators/commit/19a423a8b2500de6037847b6304380d23d8e2b3f))
* isolate per-pair failures in evaluateItems instead of discarding the batch ([#150](https://github.com/learning-commons-org/evaluators/issues/150)) ([957b82e](https://github.com/learning-commons-org/evaluators/commit/957b82efe92ca9c1c9611ae1fc1ae879ae9b19ce))
* require ai&gt;=7 and @ai-sdk/* &gt;=4 peers to match supported provider spec ([#144](https://github.com/learning-commons-org/evaluators/issues/144)) ([6b980f4](https://github.com/learning-commons-org/evaluators/commit/6b980f4e85dfb841ef61daba76cba59c38d86804))
* **sdk:** bound the peer ranges and declare the Node versions that work ([#262](https://github.com/learning-commons-org/evaluators/issues/262)) ([aeedf15](https://github.com/learning-commons-org/evaluators/commit/aeedf155cb0097e84c2162ef064a7724bdcd387c))
* **sdk:** classify a missing adapter by structured signal only ([#257](https://github.com/learning-commons-org/evaluators/issues/257)) ([758024f](https://github.com/learning-commons-org/evaluators/commit/758024fb84d5ee87d0e80c343371d5f515cfec36))
* **sdk:** classify a provider-rejected model as ConfigurationError ([#233](https://github.com/learning-commons-org/evaluators/issues/233)) ([c45d5d0](https://github.com/learning-commons-org/evaluators/commit/c45d5d0ac0e89cc1a07ab2ae5cd301255ba84974))
* **sdk:** give math one result-type name and finish its snake_case keys ([#263](https://github.com/learning-commons-org/evaluators/issues/263)) ([a844fbf](https://github.com/learning-commons-org/evaluators/commit/a844fbf1312b7fadc656a0a7f24ade725f347e19))
* **sdk:** make the schema generator preserve per-field descriptions and re-enable its CI check ([#218](https://github.com/learning-commons-org/evaluators/issues/218)) ([ddf8a99](https://github.com/learning-commons-org/evaluators/commit/ddf8a998c5c07a7ed4cadacd5f40b8ca89514776))
* **sdk:** make zod a peer dependency so consumers own the single copy ([#258](https://github.com/learning-commons-org/evaluators/issues/258)) ([e86aa61](https://github.com/learning-commons-org/evaluators/commit/e86aa611446f58213bb36b19b91fc59a1e68e17c))
* **sdk:** point the require condition at the CommonJS declarations ([#261](https://github.com/learning-commons-org/evaluators/issues/261)) ([3dc4b64](https://github.com/learning-commons-org/evaluators/commit/3dc4b643ed4d3efb2282cd686d2f5f3097e3dc02))
* **sdk:** publish declarations that typecheck, and export every evaluator's input type ([#255](https://github.com/learning-commons-org/evaluators/issues/255)) ([0f17451](https://github.com/learning-commons-org/evaluators/commit/0f17451fecac20cc3d73a633a10119bc645fbf03))
* **sdk:** publish supportedGrades from the contract that declares it ([#251](https://github.com/learning-commons-org/evaluators/issues/251)) ([a6dfb45](https://github.com/learning-commons-org/evaluators/commit/a6dfb45ac6846a660f9abbc17e8ebf4dc1fbeefb))
* **sdk:** put Grade Level Appropriateness on its contract ([#228](https://github.com/learning-commons-org/evaluators/issues/228)) ([cf4d727](https://github.com/learning-commons-org/evaluators/commit/cf4d727aa54b50a4bbb658244144fe3ab49383d0))
* **sdk:** put Sentence Structure's output on its contract ([#229](https://github.com/learning-commons-org/evaluators/issues/229)) ([d8e4d6b](https://github.com/learning-commons-org/evaluators/commit/d8e4d6b950d05d7f757f0f267bccb9dd46d086bd))
* **sdk:** rename math standards alignment's contract keys to snake_case ([#260](https://github.com/learning-commons-org/evaluators/issues/260)) ([9f4d6a8](https://github.com/learning-commons-org/evaluators/commit/9f4d6a8083df333a5ad8561d669e431a76e05e46))
* **sdk:** report the complexity model that actually ran for grades 3-4 ([#222](https://github.com/learning-commons-org/evaluators/issues/222)) ([5ce4bc8](https://github.com/learning-commons-org/evaluators/commit/5ce4bc88863ef0f00a5d9b329b88164b3c6120ad))
* **sdk:** resolve symlinks in the batch CLI entry-point guard ([#253](https://github.com/learning-commons-org/evaluators/issues/253)) ([98943bb](https://github.com/learning-commons-org/evaluators/commit/98943bb48cf344e2b83f8fbbb2d890290493d5d3))
* **sdk:** stop evaluated text from splicing the text-complexity report template ([#230](https://github.com/learning-commons-org/evaluators/issues/230)) ([c6dbff1](https://github.com/learning-commons-org/evaluators/commit/c6dbff1c9c33ed284d70f8e0388830ae503b72ad))
* **sdk:** surface a swallowed KG failure, repoint the report grade filter, honour VC's declared conditions ([#247](https://github.com/learning-commons-org/evaluators/issues/247)) ([ad8e537](https://github.com/learning-commons-org/evaluators/commit/ad8e537486dd61d0cf6f349e250aa1d43b0aeb56))
* **ts-sdk:** bound text at 1-10,000 chars measured as the caller sent it ([#202](https://github.com/learning-commons-org/evaluators/issues/202)) ([d885e7b](https://github.com/learning-commons-org/evaluators/commit/d885e7bb3ab223f08d8c550479e829585339c3c4))
* **ts-sdk:** name the grade level consistently at the Knowledge Graph boundary ([#205](https://github.com/learning-commons-org/evaluators/issues/205)) ([4eee45a](https://github.com/learning-commons-org/evaluators/commit/4eee45a76c8453e62217872fd4c403e4bef91ddc))
* **ts-sdk:** omit temperature when the registry sends none ([#199](https://github.com/learning-commons-org/evaluators/issues/199)) ([a71c58d](https://github.com/learning-commons-org/evaluators/commit/a71c58dc55188a81637d41a34d1e7dbaa89d374c))
* **ts-sdk:** rename grade to gradeLevel on the evaluator API ([#204](https://github.com/learning-commons-org/evaluators/issues/204)) ([93c4650](https://github.com/learning-commons-org/evaluators/commit/93c46501cf873ff6b5916ba6f47bc4a68588d31d))
* **ts-sdk:** rename the batch grade column to grade_level ([#206](https://github.com/learning-commons-org/evaluators/issues/206)) ([0615daf](https://github.com/learning-commons-org/evaluators/commit/0615daff991da5626285c1927c7ff7bfedf40f30))
* **ts-sdk:** scope the Learning Commons key by purpose ([#203](https://github.com/learning-commons-org/evaluators/issues/203)) ([b73c036](https://github.com/learning-commons-org/evaluators/commit/b73c036b5ae90245a43784f261d0262d7188a613))
* **ts-sdk:** send maxTokens as maxOutputTokens so the vendor SDK reads it ([#201](https://github.com/learning-commons-org/evaluators/issues/201)) ([301686f](https://github.com/learning-commons-org/evaluators/commit/301686fa82eef27905935b86a71551a9729cebf7))


### Documentation

* **sdk:** correct and prune the SDK's comments after the migrations ([#231](https://github.com/learning-commons-org/evaluators/issues/231)) ([b0a3692](https://github.com/learning-commons-org/evaluators/commit/b0a3692dfbb125a3cd2c03c713827925bb7151da))
* **sdk:** correct the false claims and fill the gaps four clean-room runs found ([#264](https://github.com/learning-commons-org/evaluators/issues/264)) ([acfa064](https://github.com/learning-commons-org/evaluators/commit/acfa064c14a78b3f2c5fcc40f97a233eb95ed68b))
* **sdk:** fix the broken quickstart, document all sixteen evaluators, add a 0.8.0 migration guide ([#254](https://github.com/learning-commons-org/evaluators/issues/254)) ([f4b7608](https://github.com/learning-commons-org/evaluators/commit/f4b7608c60711eec266f8c68e17452999a04dce3))


### Code Refactoring

* **sdk:** consume the contract declarations, and fix three bugs ([#216](https://github.com/learning-commons-org/evaluators/issues/216)) ([cb712bc](https://github.com/learning-commons-org/evaluators/commit/cb712bcf495b7720ac29a694aceefa208e6c12de))
* **sdk:** evaluate() takes named inputs validated against the contract ([#215](https://github.com/learning-commons-org/evaluators/issues/215)) ([fa8f6f2](https://github.com/learning-commons-org/evaluators/commit/fa8f6f2268696d6ec85fe0a6fe5c23c2307b33ce))
* **sdk:** migrate evaluate() onto the result envelope ([#210](https://github.com/learning-commons-org/evaluators/issues/210)) ([5253375](https://github.com/learning-commons-org/evaluators/commit/5253375bd930bddc53da78b3e733417ec43a97b9))
* **sdk:** remove dead and misleading public exports ([#246](https://github.com/learning-commons-org/evaluators/issues/246)) ([fd0cd74](https://github.com/learning-commons-org/evaluators/commit/fd0cd74d6352cb8958dce71589a01065600d31d0))
* **sdk:** remove the TextComplexityEvaluator composite ([#209](https://github.com/learning-commons-org/evaluators/issues/209)) ([5c93dcd](https://github.com/learning-commons-org/evaluators/commit/5c93dcd9d7ae7609fdacae5125bc271e1694a5de))
* **sdk:** rename each evaluator's payload type from &lt;Evaluator&gt;Internal to &lt;Evaluator&gt;Result ([#219](https://github.com/learning-commons-org/evaluators/issues/219)) ([6b31269](https://github.com/learning-commons-org/evaluators/commit/6b312691f9c689766a495b440ad4e736c15a69a8))
* **sdk:** rename TypeScript evaluators onto the eval taxonomy ([#208](https://github.com/learning-commons-org/evaluators/issues/208)) ([d5f9533](https://github.com/learning-commons-org/evaluators/commit/d5f9533934bf1eb2d6be80b785d852ca9e41d584))
* **ts-sdk:** fault-domain error taxonomy with structured classification ([#200](https://github.com/learning-commons-org/evaluators/issues/200)) ([1a6acb3](https://github.com/learning-commons-org/evaluators/commit/1a6acb352497b7dcf8670670e2379698fb799b6c))

## [0.8.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.7.0...sdks-typescript-v0.8.0) (2026-06-30)


### Features

* **ts-sdk:** jurisdiction support for math standards alignment ([#108](https://github.com/learning-commons-org/evaluators/issues/108)) ([5c6bea8](https://github.com/learning-commons-org/evaluators/commit/5c6bea83905426a7499d24fe159072745e370aac))
* **ts-sdk:** Knowledge Graph client layer ([#97](https://github.com/learning-commons-org/evaluators/issues/97)) ([b4fec20](https://github.com/learning-commons-org/evaluators/commit/b4fec202b651e6162252dd2fe4673337c736bdd8))
* **ts-sdk:** Math Standards Alignment Evaluator ([#91](https://github.com/learning-commons-org/evaluators/issues/91)) ([94d8505](https://github.com/learning-commons-org/evaluators/commit/94d8505e99c05c229dbb6eaf0189e6affc823cb0))


### Bug Fixes

* **typescript-sdk:** prevent bundlers from requiring unused [@ai-sdk](https://github.com/ai-sdk) providers ([#105](https://github.com/learning-commons-org/evaluators/issues/105)) ([e02531a](https://github.com/learning-commons-org/evaluators/commit/e02531a4ca8d2847c7837344761a99e449304d50))

## [0.7.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.6.0...sdks-typescript-v0.7.0) (2026-06-11)


### Features

* **batch:** CLI enhancements and model override support ([#95](https://github.com/learning-commons-org/evaluators/issues/95)) ([b019c67](https://github.com/learning-commons-org/evaluators/commit/b019c672b023ad995e0dd17f0e9149de9b412f3b))


### Documentation

* Revise TypeScript SDK README ([#87](https://github.com/learning-commons-org/evaluators/issues/87)) ([125e46b](https://github.com/learning-commons-org/evaluators/commit/125e46bf0bd8cc6480a9d98f86b9c31016f2c181))

## [0.6.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.5.0...sdks-typescript-v0.6.0) (2026-05-22)


### Features

* **ts-sdk:** add bypassRowLimit option for batch evaluator ([#77](https://github.com/learning-commons-org/evaluators/issues/77)) ([902a60f](https://github.com/learning-commons-org/evaluators/commit/902a60fc934372a151f1d40c0b49ef3313d12609))
* **ts-sdk:** expose per-call token usage on EvaluationMetadata ([#59](https://github.com/learning-commons-org/evaluators/issues/59)) ([3c8fa0f](https://github.com/learning-commons-org/evaluators/commit/3c8fa0fd8e2389fc902c9cf1f63985b40d2e4b2c))

## [0.5.0](https://github.com/learning-commons-org/evaluators/compare/sdks-typescript-v0.4.0...sdks-typescript-v0.5.0) (2026-05-07)


### Features

* **ts-sdk:** add modelOverride option to all evaluators ([#34](https://github.com/learning-commons-org/evaluators/issues/34)) ([c57c4fc](https://github.com/learning-commons-org/evaluators/commit/c57c4fc86bc56846afe92e6d451705642e399309))
* **ts-sdk:** Add Purpose evaluator ([#57](https://github.com/learning-commons-org/evaluators/issues/57)) ([8b6d715](https://github.com/learning-commons-org/evaluators/commit/8b6d715b49ba1911de35ccc1b6aeaef888289a1d))

## [0.4.0] — 2026-03-23

### Added

- **Batch CSV Evaluator** — CLI tool and programmatic API for evaluating multiple texts from a CSV file in parallel. Runs the `text-complexity` group (GLA, SMK, Vocabulary, Sentence Structure, and Conventionality) across up to 50 rows and produces CSV and HTML reports.

---

## [0.3.0] — 2026-03-20

### Added

- **Conventionality Evaluator** — evaluates how explicit, literal, and straightforward a text's meaning is versus how abstract, ironic, figurative, or archaic it is, relative to grades 3–12.
- **Conventionality added to TextComplexityEvaluator** — composite evaluator now runs vocabulary, sentence structure, SMK, and conventionality in parallel; result includes `conventionality` key.

---

## [0.2.0] — 2026-03-18

### Added

- **Subject Matter Knowledge (SMK) Evaluator** — evaluates background knowledge demands of educational texts relative to grades 3–12.
- **SMK added to TextComplexityEvaluator** — composite evaluator now runs vocabulary, sentence structure, and SMK in parallel; result includes `subjectMatterKnowledge` key.
- **Prompt versioning** — prompts updated to v1.3.0 (`evals/prompts/subject-matter-knowledge/`).

---

## [0.1.0] — Early Release

Initial early release of the TypeScript SDK for Learning Commons educational evaluators.

### Added

- **Vocabulary Evaluator** — grades 3–12 vocabulary difficulty assessment.
- **Sentence Structure Evaluator** — syntactic complexity analysis by grade level.
- **Grade Level Appropriateness (GLA) Evaluator** — overall grade-level suitability scoring.
- **Text Complexity Evaluator** — composite evaluation combining Vocabulary, Sentence Structure, and GLA.
- **Provider abstraction** — model-agnostic via Vercel AI SDK; OpenAI, Google, and Anthropic supported.
- **Telemetry** — opt-in, with `partnerKey` and `recordInputs` (defaults to `false`).
- **Prompt versioning** — prompts versioned in `evals/prompts/` (v1.2.0), shared with Python notebooks.
