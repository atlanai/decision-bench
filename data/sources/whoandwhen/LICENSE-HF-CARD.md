<!-- Dataset card of Kevin355/Who_and_When, fetched 2026-09-23 from https://huggingface.co/datasets/Kevin355/Who_and_When/raw/main/README.md (states no license) (license metadata in the YAML header) -->

---
configs:
- config_name: Algorithm-Generated
  data_files: "Algorithm-Generated.parquet"
- config_name: Hand-Crafted
  data_files: "Hand-Crafted.parquet"
---

# Who&When: #1 Benchmark for MAS **automated failure attribution.**

- **184** annotated failure tasks collected from
  - **Algorithm-generated agentic systems** built using [CaptainAgent](https://docs.ag2.ai/latest/docs/use-cases/notebooks/notebooks/agentchat_captainagent/),
  - **Hand-crafted systems** such as [Magnetic-One](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/).
- **Fine-grained annotations** for each failure, including:
  - The failure-responsible agent (who failed),
  - The decisive error step (when the critical error occurred),
  - A natural language explanation of the failure.

The dataset covers a wide range of realistic multi-agent scenarios based on queries from [GAIA](https://huggingface.co/gaia-benchmark) and [AssistantBench](https://assistantbench.github.io/). It serves as a foundational resource for developing and evaluating methods that aim to automatically pinpoint the causes of failures in complex agentic systems. We follow the following guide to annotate these failure logs. More information could be found in the paper. 


# Reference
If you find it useful, please consider citing our work:

```md
@article{zhang2025agent,
  title={Which Agent Causes Task Failures and When? On Automated Failure Attribution of LLM Multi-Agent Systems},
  author={Zhang, Shaokun and Yin, Ming and Zhang, Jieyu and Liu, Jiale and Han, Zhiguang and Zhang, Jingyang and Li, Beibin and Wang, Chi and Wang, Huazheng and Chen, Yiran and others},
  journal={arXiv preprint arXiv:2505.00212},
  year={2025}
}
```