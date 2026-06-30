# Learning Commons Evaluators

<img style="width:100%" alt="Evaluators project banner logo" src="https://raw.githubusercontent.com/learning-commons-org/.github/refs/heads/main/assets/evals_hero_2.jpg" />

<p align="center">
  <a href="https://platform.learningcommons.org/apps/evaluators/playground" target="_blank">Demo</a>
   •
  <a href="https://docs.learningcommons.org/evaluators/getting-started/quickstart" target="_blank">Quickstart</a>
  •
  <a href="https://docs.learningcommons.org/evaluators" target="_blank">Docs</a>
</p>

[Learning Commons](https://learningcommons.org/) evaluators measure the quality of AI-generated educational content by assessing specific dimensions of text and identifying areas for improvement.

Edtech developers can use Evaluators to reliably assess their LLM outputs and build evidence-based tools that reinforce student learning.

## Available evaluators

| Evaluators                                                                                                | Description                                                                             |
| :-------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------- |
| [**Literacy evaluators**](https://docs.learningcommons.org/evaluators/literacy-evaluators/introduction)   | Assess the qualitative text complexity of a passage, often for a particular grade level |
| [**Feedback evaluators**](https://docs.learningcommons.org/evaluators/feedback-evaluators/introduction)   | Assess the quality of feedback on a student's response to a task goal                   |
| [**Standards evaluators**](https://docs.learningcommons.org/evaluators/standards-evaluators/introduction) | Assess the alignment of educational content to academic standards                       |

## Repository contents

| Path                      | Description                                                                                                                          |
| :------------------------ | :----------------------------------------------------------------------------------------------------------------------------------- |
| [`evals`](./evals/)       | Evaluators code (notebooks) and [prompts](./evals/prompts)                                                                           |
| [`datasets`](./datasets/) | [Expert-annotated datasets](https://docs.learningcommons.org/evaluators/dataset/introduction) used to create and validate evaluators |
| [`sdks`](./sdks/)         | [Python](./sdks/python/) and [TypeScript](./sdks/python/) SDKs for integrating evaluators into your own project                      |
| [`LICENSE`](./LICENSE.md) | Open source license details                                                                                                          |

## Getting started

Sign up for a [Learning Commons Platform](https://platform.learningcommons.org) account, then select one of the following access methods to start using Evaluators:

| Access method                                                                                | When to use                                         | Instructions                                                                                               |
| :------------------------------------------------------------------------------------------- | :-------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| [**Evaluators Playground**](https://platform.learningcommons.org/apps/evaluators/playground) | For a quick demo of how evaluators work             | [Quickstart](https://docs.learningcommons.org/evaluators/getting-started/quickstart#evaluators-playground) |
| **SDK**                                                                                      | To integrate into your TypeScript or Python project | [Quickstart](https://docs.learningcommons.org/evaluators/getting-started/quickstart#sdk)                   |
| **Python notebooks**                                                                         | For quick prototyping                               | [Quickstart](https://docs.learningcommons.org/evaluators/getting-started/quickstart#python-notebooks)      |

If you're using an SDK or Python notebook, you must also:

- Generate your Learning Commons [API keys](https://platform.learningcommons.org/api-keys) – Required for authentication
- Generate the API keys required for the evaluators you want to use – see [API key requirements here](https://docs.learningcommons.org/evaluators/getting-started/quickstart#required-api-keys).

## Resources

|                |                                                                                                                                                                                                                                                                                                                 |
| :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Basics**     | [Use cases](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction#when-to-use-evaluators), [Core concepts](https://docs.learningcommons.org/evaluators/understanding-evaluators/core-concepts)                                                                                      |
| **Evaluators** | [Literacy evaluators](https://docs.learningcommons.org/evaluators/literacy-evaluators/introduction), [Feedback evaluators](https://docs.learningcommons.org/evaluators/feedback-evaluators/introduction), [Standards evaluators](https://docs.learningcommons.org/evaluators/standards-evaluators/introduction) |
| **Datasets**   | [Introduction](https://docs.learningcommons.org/evaluators/dataset/introduction), [Literacy](https://docs.learningcommons.org/evaluators/dataset/literacy)                                                                                                                                                      |
| **Reference**  | [SDK API reference](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview)                                                                                                                                                                                                                     |
| **Other**      | [Roadmap](https://docs.learningcommons.org/evaluators/understanding-evaluators/roadmap)                                                                                                                                                                                                                         |

## Contact us

| Topic                      | Contact                                                                                                                                                              |
| :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Questions or feedback      | [Open a GitHub issue](https://github.com/learning-commons-org/evaluators/issues) or email [support@learningcommons.org](mailto:support@learningcommons.org)          |
| Reporting security issues  | Email [security@learningcommons.org](mailto:security@learningcommons.org)                                                                                            |

## Disclaimer

Use of the resources provided in this repository is subject to our [Terms of Use](https://learningcommons.org/terms-of-use/).
