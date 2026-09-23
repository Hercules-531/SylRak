# Recognition fine-tuning: not completed

The presentation release uses pretrained publisher weights. It does **not** contain a fine-tuned Indian OCR model or demonstrate 90% accuracy.

The CCT publisher's Keras checkpoint and configurations are available under `assets/models/training`, with source URLs and hashes in `artifacts/recognition-upgrade/provenance.json`. The installed Keras training runtime loads successfully. The current Torch installation is CPU-only; no GPU training run was performed.

The available bundled material has 31 transcribed non-demo development images and only four of those have matching publisher plate-box annotations. These images have already been inspected and compared across models. They cannot serve as an untouched final test set. The external DataCluster public listing inspected during this work exposed only 47 XML annotations, below the 200-independent-image test gate, and is evaluation-only with redistribution restrictions. It was not bundled or used for training.

Before training, obtain licensed real plate crops with reviewed transcriptions and source/vehicle identifiers. Deduplicate decoded image hashes and group all captures of the same vehicle into one split. Reserve at least 200 independent real test images before tuning. Keep the presentation samples separate. Use synthetic plates only in training. Track single/two-line plates, angles, lighting and vehicle types in every split.

Use the FastPlateOCR training CLI with the downloaded CCT checkpoint, 20 epochs initially, batch size 16, learning rate 0.00001, and validation-based checkpoint selection. The baseline has 10 character slots; use a compatible extended plate configuration for longer Indian registrations and document any resized output head. Export the best validation checkpoint to ONNX, verify numerical parity, then evaluate the untouched test set once. Choose a deployment model from validation results and latency, never from demonstration success or reference-driven candidate selection.

Official training workflow: https://ankandrew.github.io/fast-plate-ocr/latest/training/cli/train/

Retain `SYLRAK_OCR_BACKEND=cct` in `.env` as a rollback option, then restart the server. The default release reader is `en_PP-OCRv5_mobile_rec`; original CCT readings remain attached as alternatives from the same image.
