# Datasets

## Learning Commons annotations of CLEAR for qualitative text complexity

[Download the dataset here](https://aidt-evaluators-files-public-prod.s3.us-west-2.amazonaws.com/Learning+Commons+annotations+of+CLEAR+for+qualitative+text+complexity+v1.0+2025-09-02.csv).

| Version           | v1.0 2025-09-02 |
| ----------------- | --------------: |
| Number of columns |              14 |
| Number of rows    |            1097 |

### Columns

> NOTE: If text was not annotated for a given column, it will contain the value `not scored`.

| Column                          | Description                                                                                                                                                                                                                                                                                  |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UID                             | Unique identifier for each row                                                                                                                                                                                                                                                               |
| Clear ID                        | Identifier for texts based on the CLEAR corpus. This is not a unique identifier, as some texts were scored for multiple grades.                                                                                                                                                              |
| Grade                           | Grade-level for which text is scored. For example, if Grade=3 and Sentence Score=`slightly complex`, then the text is slightly complex for a third grade student (see overall project documentation for specific assumptions).                                                               |
| Flesch Kincaid                  | Flesch-Kincaid Grade Level score for the text, provided from the CLEAR corpus.                                                                                                                                                                                                               |
| Text                            | Text from the CLEAR corpus that was annotated                                                                                                                                                                                                                                                |
| Sentence score                  | Overall annotator rating for sentence structure complexity. Takes the values `slightly complex`, `moderately complex`, `very complex`, and `exceedingly complex`. See the technical docs for additional details on these categories.                                                         |
| Sentence score rationale        | Annotators’ explanations for their sentence structure score.                                                                                                                                                                                                                                 |
| Vocabulary score                | Overall annotator rating for vocabulary complexity. Takes the values `slightly complex`, `moderately complex`, `very complex`, and `exceedingly complex`. See overall project documentation for additional details on these categories.                                                      |
| Vocabulary score rationale      | Annotators’ explanations for their vocabulary score.                                                                                                                                                                                                                                         |
| Tier 2 words                    | Tier 2 words identified by annotators.                                                                                                                                                                                                                                                       |
| Tier 3 words                    | Tier 3 words identified by annotators.                                                                                                                                                                                                                                                       |
| Archaic words                   | Archaic words identified by annotators.                                                                                                                                                                                                                                                      |
| Other complex words             | Additional complex words for students of the grade level, as identified by annotators.                                                                                                                                                                                                       |
| Background knowledge assumption | LLM-generated information on the background knowledge that students of a particular grade are likely to have about a topic. Information was provided to annotators as part of the scoring process. See the overall project documentation for detailed methodology on how this was generated. |

### Methodology

Annotators were provided with specific assumptions about the student, text and information to score. These and other details are included in the [project docs](https://docs.learningcommons.org/evaluators/literacy-evaluators/literacy-evaluators#expert-annotated-benchmark-datasets).

For detailed methodology on dataset creation, see the [Literacy dataset](https://docs.learningcommons.org/evaluators/dataset/literacy-dataset) documentation.

## License

[License](https://github.com/learning-commons-org/evaluators/blob/main/LICENSE.md)
