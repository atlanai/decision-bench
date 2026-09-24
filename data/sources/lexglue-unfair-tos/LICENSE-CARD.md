---
annotations_creators:
- found
language_creators:
- found
language:
- en
license:
- cc-by-4.0
multilinguality:
- monolingual
size_categories:
- 10K<n<100K
source_datasets:
- extended
task_categories:
- question-answering
- text-classification
task_ids:
- multi-class-classification
- multi-label-classification
- multiple-choice-qa
- topic-classification
pretty_name: LexGLUE
config_names:
- case_hold
- ecthr_a
- ecthr_b
- eurlex
- ledgar
- scotus
- unfair_tos
dataset_info:
- config_name: case_hold
  features:
  - name: context
    dtype: string
  - name: endings
    sequence: string
  - name: label

LEDGAR dataset aims contract provision (paragraph) classification. The contract provisions come from contracts obtained from the US Securities and Exchange Commission (SEC) filings, which are publicly available from EDGAR. Each label represents the single main topic (theme) of the corresponding contract provision.

#### unfair_tos

The UNFAIR-ToS dataset contains 50 Terms of Service (ToS) from on-line platforms (e.g., YouTube, Ebay, Facebook, etc.). The dataset has been annotated on the sentence-level with 8 types of unfair contractual terms (sentences), meaning terms that potentially violate user rights according to the European consumer law.

#### case_hold


### Licensing Information

[More Information Needed](https://github.com/huggingface/datasets/blob/master/CONTRIBUTING.md#how-to-contribute-to-the-dataset-cards)

### Citation Information

[*Ilias Chalkidis, Abhik Jana, Dirk Hartung, Michael Bommarito, Ion Androutsopoulos, Daniel Martin Katz, and Nikolaos Aletras.*
*LexGLUE: A Benchmark Dataset for Legal Language Understanding in English.*
*2022. In the Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics. Dublin, Ireland.*](https://arxiv.org/abs/2110.00976)
```
@inproceedings{chalkidis-etal-2021-lexglue,
        title={LexGLUE: A Benchmark Dataset for Legal Language Understanding in English}, 
        author={Chalkidis, Ilias and Jana, Abhik and Hartung, Dirk and
        Bommarito, Michael and Androutsopoulos, Ion and Katz, Daniel Martin and
        Aletras, Nikolaos},
        year={2022},
        booktitle={Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics},
        address={Dubln, Ireland},
}
```

### Contributions

Thanks to [@iliaschalkidis](https://github.com/iliaschalkidis) for adding this dataset.