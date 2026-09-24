<!-- Dataset card of BEE-spoke-data/consumer-finance-complaints, fetched 2026-09-23 from https://huggingface.co/datasets/BEE-spoke-data/consumer-finance-complaints/raw/088cc7308d4afc2a880f2329d08e2f7a09188ec6/README.md (license metadata in the YAML header) -->
---
language:
- en
license: cc0-1.0
size_categories:
- 1M<n<10M
source_datasets: consumer-finance-complaints
task_categories:
- text-classification
- text-generation
dataset_info:
- config_name: default
  features:
  - name: Date received
    dtype: string
  - name: Product
    dtype: string
  - name: Sub-product
    dtype: string
  - name: Issue
    dtype: string
  - name: Sub-issue
    dtype: string
  - name: Consumer complaint narrative
    dtype: string
  - name: Company public response
    dtype: string
  - name: Company
    dtype: string
  - name: State
    dtype: string
  - name: ZIP code
    dtype: string
  - name: Tags
    dtype: string
  - name: Consumer consent provided?
    dtype: string
  - name: Submitted via
    dtype: string
  - name: Date sent to company
    dtype: string
  - name: Company response to consumer
    dtype: string
  - name: Timely response?
    dtype: string
  - name: Consumer disputed?
    dtype: string
  - name: Complaint ID
    dtype: int64
  splits:
  - name: train
    num_bytes: 3427420677
    num_examples: 4707579
  download_size: 1061488683
  dataset_size: 3427420677
- config_name: has-text
  features:
  - name: Date received
    dtype: string
  - name: Product
    dtype: string
  - name: Sub-product
    dtype: string
  - name: Issue
    dtype: string
  - name: Sub-issue
    dtype: string
  - name: Consumer complaint narrative
    dtype: string
  - name: Company public response
    dtype: string
  - name: Company
    dtype: string
  - name: State
    dtype: string
  - name: ZIP code
    dtype: string
  - name: Tags
    dtype: string
  - name: Consumer consent provided?
    dtype: string
  - name: Submitted via
    dtype: string
  - name: Date sent to company
    dtype: string
  - name: Company response to consumer
    dtype: string
  - name: Timely response?
    dtype: string
  - name: Consumer disputed?
    dtype: string
  - name: Complaint ID
    dtype: int64
  splits:
  - name: train
    num_bytes: 1229876941.3934054
    num_examples: 1689573
  download_size: 925128908
  dataset_size: 1229876941.3934054
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train-*
- config_name: has-text
  data_files:
  - split: train
    path: has-text/train-*
tags:
- finance
- government data
- '2024'
---


# BEE-spoke-data/consumer-finance-complaints


`consumer-finance-complaints` but in a format that actually works.  

Pulled Feb 2024


