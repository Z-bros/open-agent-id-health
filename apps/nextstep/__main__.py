"""Honest prebuild placeholder; no planning/queries are implemented."""
import argparse

def main():
    parser = argparse.ArgumentParser(description="TB-NextStep — planned bounded verification app")
    parser.parse_args()
    parser.exit(2, "Not implemented: bounded verification planner begins during the official build window.\n")

if __name__ == "__main__":
    main()
