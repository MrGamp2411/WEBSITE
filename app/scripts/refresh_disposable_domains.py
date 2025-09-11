import argparse
from app.utils.disposable_email import refresh_disposable_cache


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    count = refresh_disposable_cache(force=args.force)
    print(f"Loaded {count} disposable domains")


if __name__ == "__main__":
    main()
