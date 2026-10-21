"""Honest prebuild placeholder; no evidence explanation/inference is implemented."""
import argparse

def main():
    parser = argparse.ArgumentParser(description="TB-CaseLens — planned evidence explanation app")
    parser.parse_args()
    parser.exit(2, "Not implemented: explanation agent begins during the official build window.\n")

if __name__ == "__main__":
    main()
