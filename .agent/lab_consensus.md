---
description: "Group Majority Consensus Logic for Robust Lab Report Integration"
---

# Group Majority Consensus (Democracia Espacial)

## Context
When associating Lab Reports (Excel) to Spatial Features (QGIS), a naive "row-by-row" approach can lead to errors. Outlier points (GPS errors, typos) might assign a Report ID to the wrong feature if they fall outside the target area, or worse, if they fall into a *neighboring* feature.

## The Problem
- **Input**: Excel file where 1 "Ensayo" (e.g., ID 100) has 5 distinct coordinate rows.
- **Scenario**: 4 points fall correctly in "Cancha A". 1 point (outlier) falls in "Cancha B" or nowhere.
- **Naive Logic**: The outlier row might trigger a partial assignment to Cancha B, or fail silently while the other 4 succeed. This creates data inconsistency.

## The Solution: "Consensus by Group"

Instead of processing each row individually, we process the **Entire Entity (Ensayo)** as a single voting block.

### Algorithm Steps

1.  **Group Data**:
    - Read the entire Excel file first.
    - Group rows by their unique identifier (e.g., `N_Ensayo` or `N_Informe`).
    - *Structure*: `Group_100 = [Row1, Row2, Row3, Row4, Row5]`

2.  **Strict Evaluation (0.5m)**:
    - For each row in the group, perform a **Strict Spatial Query**.
    - **Tolerance**: Reduced from 2.0m to **0.5m** (or user configurable).
    - Checks:
        - `Distance(Point, Feature) < 0.5m`
        - `Date_Match` (Exact date)
        - `Metadata_Match` (Muro, Sector aliases)

3.  **Vote Casting**:
    - Each row "votes" for a Candidate Feature ID.
    - *Example Results for Ensayo 100*:
        - Row 1 -> Cancha_ID_55
        - Row 2 -> Cancha_ID_55
        - Row 3 -> Cancha_ID_55
        - Row 4 -> Cancha_ID_55
        - Row 5 -> Cancha_ID_99 (Wrong!)

4.  **Consensus Decision**:
    - Calculate the Winner: `Cancha_ID_55` (4 votes vs 1).
    - **Threshold**: Optional confidence threshold (e.g., >50% or >60%).
    - If a clear winner exists:
        - Assign `N_Ensayo = 100` to `Cancha_ID_55`.
        - **Log Success**: "Ensayo 100 assigned to Cancha A (Confidence: 80%)".
        - **Log Warning**: "⚠️ Outlier Ignore: Row 5 landed in Cancha B (discarded by majority rule)".

5.  **No Consensus**:
    - If votes are split (e.g., 2 for A, 2 for B), **DO NOT ASSIGN**.
    - Log Critical Error: "❌ Ambiguous Ensayo 100: Split votes between Cancha A and B. Manual review required."

## Implementation Benefits
- **Robustness**: Immune to single-point GPS flukes.
- **Integrity**: Prevents "fragmented" assignments where one Report ID is split across multiple features.
- **Auditability**: Explicitly identifies which points were outliers and ignored.

## Usage in Code
Implement inside `LabReportLoader` class:
1. `_parse_excel_to_groups(path)` -> Returns `Dict[EnsayoID, List[Rows]]`
2. `_resolve_consensus(group, layer)` -> Returns `(WinningFeatureID, Confidence, Outliers)`
3. `_apply_matches(matches, layer)` -> Batch updates QGIS features.
