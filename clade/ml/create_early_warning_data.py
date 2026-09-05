from pathlib import Path

import pandas as pd


INPUT_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "careedge_training_data.csv"
)

OUTPUT_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "careedge_early_warning_data.csv"
)


SAMPLES_PER_EVENT = 250
SAMPLE_RATE = 50


def label_fall_sequence(group):
    """
    Label a 250-sample simulated fall sequence according
    to the phases defined in FallMotionSimulator.

    Timeline at 50 Hz:
        0.00 - 1.50 s : pre_fall
        1.50 - 2.25 s : fall_transition
        2.25 - 2.75 s : fall
        2.75 - 3.50 s : post_fall
        3.50 - 5.00 s : post_fall
    """

    group = group.sort_values("timestamp").reset_index(drop=True)

    labels = []

    for sample_index in range(len(group)):

        progress = sample_index / max(
            SAMPLES_PER_EVENT - 1,
            1
        )

        if progress < 0.30:
            label = "pre_fall"

        elif progress < 0.45:
            label = "fall_transition"

        elif progress < 0.55:
            label = "fall"

        else:
            label = "post_fall"

        labels.append(label)

    group["early_warning_event"] = labels

    return group


def main():

    print("=" * 70)
    print("CAREEDGE — EARLY WARNING DATA PREPARATION")
    print("=" * 70)

    print()
    print("Input:")
    print(INPUT_FILE)

    # ---------------------------------------------------------
    # Load existing simulation dataset
    # ---------------------------------------------------------
    df = pd.read_csv(INPUT_FILE)

    print()
    print("Raw dataset:", df.shape)

    # ---------------------------------------------------------
    # Only fall episodes need early-warning relabeling.
    # All other events remain normal medical events.
    # ---------------------------------------------------------
    output_parts = []

    for (patient_id, event), group in df.groupby(
        ["patient_id", "event"],
        sort=False
    ):

        group = group.copy()

        if event == "fall":
            group = label_fall_sequence(group)
        else:
            group["early_warning_event"] = "normal"

        output_parts.append(group)

    result = pd.concat(
        output_parts,
        ignore_index=True
    )

    # ---------------------------------------------------------
    # Shuffle records so the output has the same structure
    # as the original training dataset.
    # ---------------------------------------------------------
    result = result.sample(
        frac=1,
        random_state=42
    ).reset_index(drop=True)

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------
    result.to_csv(
        OUTPUT_FILE,
        index=False
    )

    print()
    print("Generated dataset:", result.shape)

    print()
    print("Early-warning labels:")
    print(
        result["early_warning_event"]
        .value_counts()
        .sort_index()
    )

    print()
    print("Saved to:")
    print(OUTPUT_FILE)

    print()
    print("=" * 70)
    print("EARLY WARNING DATA PREPARATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()