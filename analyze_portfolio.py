import os
import numpy as np
import pandas as pd
import torch
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(BASE_DIR, "result")
NAV_FILE = os.path.join(RESULT_DIR, "nav_combined.csv")
METRICS_EXCEL = os.path.join(RESULT_DIR, "metrics_summary.xlsx")
METRICS_CSV = os.path.join(RESULT_DIR, "metrics_summary.csv")

def calculate_max_drawdown(nav_series):
    clean_series = nav_series.dropna()
    if len(clean_series) < 2:
        return np.nan
    cum_max = clean_series.cummax()
    drawdown = (clean_series - cum_max) / cum_max
    return drawdown.min()

def calculate_annual_returns(df_nav):
    df_nav.index = pd.to_datetime(df_nav.index)
    years = sorted(df_nav.index.year.unique())
    
    annual_returns = {}
    for ticker in df_nav.columns:
        annual_returns[ticker] = {}
        for y in years:
            df_year = df_nav[ticker][df_nav.index.year == y].dropna()
            if len(df_year) >= 2:
                start_val = df_year.iloc[0]
                end_val = df_year.iloc[-1]
                annual_returns[ticker][f"Return {y}"] = (end_val / start_val) - 1.0
            else:
                annual_returns[ticker][f"Return {y}"] = np.nan
                
    return pd.DataFrame(annual_returns).T

def monte_carlo_simulation_torch(nav_series, num_simulations=100000, days=252):
    clean_nav = nav_series.dropna()
    if len(clean_nav) < 5:
        return np.nan, np.nan, np.nan, np.nan

    returns = clean_nav.pct_change().dropna()
    if len(returns) == 0:
        return np.nan, np.nan, np.nan, np.nan

    mu_daily = float(returns.mean())
    sigma_daily = float(returns.std())
    s0 = float(clean_nav.iloc[-1])

    # PyTorch Hardware Acceleration (CUDA GPU if available, else vectorized CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    # Drift & Volatility parameters
    drift = torch.tensor((mu_daily - 0.5 * sigma_daily**2) * days, dtype=torch.float32, device=device)
    volatility = torch.tensor(sigma_daily * np.sqrt(days), dtype=torch.float32, device=device)

    # Standard normal random numbers shape: (num_simulations,)
    z = torch.randn(num_simulations, dtype=torch.float32, device=device)

    # Simulated final prices S_T
    simulated_st = s0 * torch.exp(drift + volatility * z)

    # Calculate expected return distribution: (S_T - S_0) / S_0
    simulated_returns = (simulated_st - s0) / s0

    mean_exp_ret = float(torch.mean(simulated_returns).cpu().item())
    p5_exp_ret = float(torch.quantile(simulated_returns, 0.05).cpu().item())
    p50_exp_ret = float(torch.quantile(simulated_returns, 0.50).cpu().item())
    p95_exp_ret = float(torch.quantile(simulated_returns, 0.95).cpu().item())

    return mean_exp_ret, p5_exp_ret, p50_exp_ret, p95_exp_ret

def run_portfolio_analysis():
    if not os.path.exists(NAV_FILE):
        print(f"Error: Combined NAV file not found at {NAV_FILE}")
        return

    df_nav = pd.read_csv(NAV_FILE, index_col="Date")
    print(f"Loaded NAV data: {df_nav.shape[0]} rows, {df_nav.shape[1]} tickers.")

    # 1. Calculate Annual Returns per Year
    df_annual = calculate_annual_returns(df_nav)

    # 2. Calculate Daily Returns
    df_returns = df_nav.pct_change()

    # 3. Calculate Volatility & Max Drawdown
    metrics = {}
    
    # Device status log
    device_name = "CUDA GPU" if torch.cuda.is_available() else "PyTorch Vectorized CPU"
    print(f"Running Monte Carlo Simulation (100,000 runs) using: {device_name}...")

    for ticker in df_nav.columns:
        nav_series = df_nav[ticker].dropna()
        ret_series = df_returns[ticker].dropna()

        # Volatility (Annualized)
        vol_annual = ret_series.std() * np.sqrt(252) if len(ret_series) > 1 else np.nan

        # Max Drawdown
        mdd = calculate_max_drawdown(nav_series)

        # Monte Carlo Simulation
        mc_mean, mc_p5, mc_p50, mc_p95 = monte_carlo_simulation_torch(nav_series)

        metrics[ticker] = {
            "Annualized Volatility": vol_annual,
            "Max Drawdown (MDD)": mdd,
            "MC Expected Return (Mean)": mc_mean,
            "MC Expected Return (Median / 50th)": mc_p50,
            "MC VaR 95% (5th Percentile)": mc_p5,
            "MC Upside (95th Percentile)": mc_p95
        }

    df_metrics = pd.DataFrame(metrics).T

    # Combine Annual Returns and Metrics
    df_summary = pd.concat([df_annual, df_metrics], axis=1)

    # Save outputs
    df_summary.to_csv(METRICS_CSV)
    
    with pd.ExcelWriter(METRICS_EXCEL, engine="xlsxwriter") as writer:
        df_summary.to_excel(writer, sheet_name="Summary Metrics")
        df_annual.to_excel(writer, sheet_name="Annual Returns")
        df_metrics.to_excel(writer, sheet_name="Risk & Monte Carlo")

    print(f"\nAnalysis complete! Results saved to:")
    print(f"  - {METRICS_EXCEL}")
    print(f"  - {METRICS_CSV}")
    print("\nSummary Preview:")
    print(df_summary)

if __name__ == "__main__":
    run_portfolio_analysis()
