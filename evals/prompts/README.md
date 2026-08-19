## Prompts For Evaluators

In this folder, you will find prompt files designed for evaluating text complexity. These prompts consist of system and user prompts that can be used with various LLMs to assess the complexity of text.


### Grade Level Appropriateness

Now lives at [`evals/literacy/ela-reading/grade-level-appropriateness/`](../literacy/ela-reading/grade-level-appropriateness/), alongside the `config.json` that pins its model, prompts, schemas and fixtures.

### Subject Matter Knowledge Evaluator

In file `smk_prompts.py`, we provide system and user prompts used in the Subject Matter Knowledge (SMK) Evaluator's code. These prompts can help assess the background knowledge demands of texts and serve as a starting point for your own prompt development.

### Vocabulary Evaluator

In file `vocab_prompts.py`, we provide system and user prompts used in the Vocabulary Evaluator's code. These prompts can help assess the difficulty of vocabulary in texts and serve as a starting point for your own prompt development.

### Sentence Structure Evaluator

In file `sent_str_prompts.py`, we provide system and user prompts used in the Sentence Structure evaluator's code. These prompts help assess the syntactic and structural complexity of sentences and can be adapted for your own evaluation needs.

### Conventionality Evaluator

In file `conventionality_prompts.py`, we provide system and user prompts used in the Conventionality Evaluator's code. These prompts help assess how explicit, literal, and straightforward a text's meaning is — measuring the degree to which language is conventional versus abstract, figurative, or ironic — and serve as a starting point for your own prompt development.

### Purpose Evaluator

In the `purpose/` directory, we provide the system and user prompts (`system.txt` and `user.txt`) used in the Purpose Evaluator's code. These prompts help assess how difficult it is for a reader to identify the author's purpose — distinguishing a text's topic from why the author wrote it — and serve as a starting point for your own prompt development.
