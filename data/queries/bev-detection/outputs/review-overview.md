# BEV Detection Single-paper Summary

## Query
- Topic: bev detection
- Query slug: `bev-detection`
- Test mode: single-paper

## Selected Paper
- Title: MetaBEV: Solving Sensor Failures for BEV Detection and Map Segmentation
- Year: 2023
- Source: arXiv
- PDF: `data/queries/bev-detection/papers/2304.09801.pdf`
- Markdown: `data/queries/bev-detection/papers-md/2304.09801.md`
- Note: `data/queries/bev-detection/notes/2304.09801.md`

## Why this paper was selected
This paper is tightly aligned with BEV detection and also studies robustness under sensor failure, which is highly relevant for autonomous driving deployment. It has an open-access PDF and is therefore suitable for a fast end-to-end test.

## Short review
MetaBEV proposes a BEV-Evolving decoder plus switched-modality training to keep BEV detection and map segmentation robust when camera or LiDAR inputs are missing or corrupted. On nuScenes, it preserves competitive performance under full-modality input and substantially outperforms BEVFusion in missing-modality settings, making it a strong reference for robust BEV perception.

## Test result
- Search: completed
- Paper selection: completed
- PDF download: completed
- PDF to Markdown conversion: completed in fast mode
- Structured note extraction: completed
- Multi-paper synthesis: skipped for this single-paper test
