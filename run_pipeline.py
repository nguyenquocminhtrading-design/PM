import os
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Dragon Capital Fund Scraping & Quantitative Portfolio Analysis Pipeline")
    parser.add_argument("--scrape", action="store_true", help="Run Selenium Web Scraper to download Excel files")
    parser.add_argument("--extract", action="store_true", help="Run NAV extraction across downloaded Excel files")
    parser.add_argument("--analyze", action="store_true", help="Run Quantitative Metrics & PyTorch Monte Carlo Simulation")
    parser.add_argument("--all", action="store_true", help="Run full pipeline: extract NAV and analyze portfolio")

    args = parser.parse_args()

    # If no flags passed, default to running extraction + analysis
    if not (args.scrape or args.extract or args.analyze or args.all):
        args.all = True

    if args.scrape:
        print("=== STEP 1: Running Web Scraper ===")
        import main as scraper_module
        scraper = scraper_module.DragonCapitalScraper()
        scraper.run()

    if args.extract or args.all:
        print("\n=== STEP 2: Running NAV Extraction ===")
        import extract_nav
        extract_nav.process_all_files()

    if args.analyze or args.all:
        print("\n=== STEP 3: Running Quantitative Analysis & Monte Carlo Simulation ===")
        import analyze_portfolio
        analyze_portfolio.run_portfolio_analysis()

if __name__ == "__main__":
    main()
