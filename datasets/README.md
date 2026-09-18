# Datasets

These expert-annotated datasets are used to create and validate Learning Commons evaluators. They can also be used to complement other related edtech development work.

## Text Complexity dataset

[DOWNLOAD HERE](https://aidt-evaluators-files-public-prod.s3.us-west-2.amazonaws.com/Learning+Commons+annotations+of+CLEAR+for+qualitative+text+complexity+v1.0+2025-09-02.csv)

| Version                                                                                    | v1.0 2025-09-02 |
| ------------------------------------------------------------------------------------------ | --------------: |
| [Columns](https://docs.learningcommons.org/evaluators/dataset/student-facing-text#columns) <!-- TODO(text-complexity-docs): update when the docs site path is renamed --> |              14 |
| Rows                                                                                       |            1097 |

The [Text Complexity dataset](https://docs.learningcommons.org/evaluators/dataset/student-facing-text) <!-- TODO(text-complexity-docs): update when the docs site path is renamed --> contains high-quality text complexity annotations for the CommonLit Ease of Readability (CLEAR) Corpus by literacy and education experts.

The CLEAR Corpus was produced by [CommonLit in collaboration with Georgia State University](https://www.commonlit.org/blog/introducing-the-clear-corpus-an-open-dataset-to-advance-research-28ff8cfea84a/) ↗ and is comprised of nearly 5000 publicly available excerpts, each mapped against dimensions like Flesch-Kincaid and BT Easiness.

We expanded the dataset by scoring a subset of the rows for dimensions in Student Achievement Partners (SAP)‘s [Qualitative Text Complexity Rubric for Informational Text](https://learnwithsap.b-cdn.net/app/uploads/2026/04/Qualitative-Text-Complexity-Rubric-Informational.pdf) ↗.

Our [Text Complexity evaluators](../evals/text-complexity/) use this dataset as a benchmark when assessing AI-generated content.

## License

[License](https://github.com/learning-commons-org/evaluators/blob/main/LICENSE.md)
