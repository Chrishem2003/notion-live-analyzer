from __future__ import annotations

import argparse

from .orchestrator import SovereignBrain


def main():

    parser = argparse.ArgumentParser(
        description="Sovereign Intelligence CLI"
    )

    parser.add_argument(
        "prompt",
        nargs="?",
        help="Problem to solve",
    )

    parser.add_argument(
        "--provider",
        default=None,
    )

    parser.add_argument(
        "--model",
        default=None,
    )

    args = parser.parse_args()

    if not args.prompt:

        print(
            "Usage: python -m sovereign_intelligence "
            "\"your problem\""
        )

        raise SystemExit(1)

    brain = SovereignBrain()

    result = brain.solve(
        args.prompt,
        provider=args.provider,
        model=args.model,
    )

    print()
    print(result.answer)
    print()

    if result.verification:

        print(
            f"Verification confidence: "
            f"{result.verification.confidence:.2f}"
        )


if __name__ == "__main__":
    main()