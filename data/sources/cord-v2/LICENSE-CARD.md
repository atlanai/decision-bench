# CORD-v2 — licence evidence (read 2026-09-23)

- Dataset card: https://huggingface.co/datasets/naver-clova-ix/cord-v2/blob/7f0115a4b758a71d6473b8d085751692da2fef98/README.md
  Card metadata `license: cc-by-4.0`.
- Repository README (https://github.com/clovaai/cord): "This work is licensed under a Creative Commons Attribution
  4.0 International License"; the dataset "consists of thousands of Indonesian receipts" from shops and
  restaurants, with "images and box/text annotations for OCR, and multi-level semantic labels for parsing".
  The README notes that "some class labels shown in the original paper were removed due to Indonesian legal issues".
- Paper: Park et al., CORD: A Consolidated Receipt Dataset for Post-OCR Parsing, Document Intelligence Workshop
  at NeurIPS 2019.
- Images were fetched once from the rows API's signed image URLs and resized into data/assets/finance/.
