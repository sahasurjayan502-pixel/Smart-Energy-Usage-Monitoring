"""
Visualizations for Historical Electricity Analytics Dashboard.
Builds Matplotlib and Seaborn figures with clean modern SaaS styling,
cohesive emerald-slate color palette, clear labels, and graceful empty-state handling.
"""

from typing import Optional, List
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Design constants for SaaS visual hierarchy
PRIMARY_EMERALD = "#059669"
ACCENT_GREEN = "#10b981"
DARK_SLATE = "#1e293b"
MUTED_SLATE = "#64748b"
BORDER_GRAY = "#e2ece5"
SURFACE_WHITE = "#ffffff"


def _apply_saas_theme(fig: plt.Figure, ax: plt.Axes) -> None:
    """Applies a consistent clean light SaaS visual theme to figures and axes."""
    fig.patch.set_facecolor(SURFACE_WHITE)
    ax.set_facecolor(SURFACE_WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["bottom"].set_linewidth(1.0)
    ax.tick_params(colors=MUTED_SLATE, labelsize=9.5)


def _create_empty_figure(message: str = "No data available for selected filters.") -> plt.Figure:
    """Helper to generate an informative placeholder figure when DataFrame is empty."""
    fig, ax = plt.subplots(figsize=(8, 4))
    _apply_saas_theme(fig, ax)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12, color=MUTED_SLATE, fontweight="bold")
    ax.set_axis_off()
    fig.tight_layout()
    return fig


def plot_energy_overview(df: pd.DataFrame, months: Optional[List[int]] = None) -> plt.Figure:
    """
    Renders the modern Energy Overview chart matching the UI design reference:
    Emerald line plot with circular markers, soft gradient area fill, and formatted latest value pill.
    """
    if df.empty:
        return _create_empty_figure()

    data = df if months is None else df[df["month"].isin(months)]
    if data.empty:
        return _create_empty_figure()

    monthly_data = data.groupby("month")["electricity_bill"].mean().reset_index().sort_values("month")

    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    _apply_saas_theme(fig, ax)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    x_labels = [month_names[m - 1] for m in monthly_data["month"]]
    x_positions = list(range(len(monthly_data)))
    y_values = monthly_data["electricity_bill"].values

    # Plot smooth line and points
    ax.plot(
        x_positions,
        y_values,
        marker="o",
        linewidth=2.8,
        markersize=6.5,
        color=PRIMARY_EMERALD,
        markerfacecolor=PRIMARY_EMERALD,
        markeredgecolor="#ffffff",
        markeredgewidth=1.5,
        zorder=4,
    )

    # Soft area fill below the line
    ax.fill_between(
        x_positions,
        y_values,
        color="#a7f3d0",
        alpha=0.35,
        zorder=3,
    )

    # Annotate latest data point with a clean badge if data points exist
    if len(x_positions) > 0:
        last_x = x_positions[-1]
        last_y = y_values[-1]
        ax.annotate(
            f"₹{last_y:,.0f}",
            xy=(last_x, last_y),
            xytext=(0, 14),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            fontweight="bold",
            color="#ffffff",
            bbox=dict(boxstyle="round,pad=0.35,rounding_size=0.4", fc=PRIMARY_EMERALD, ec="none", alpha=0.95),
            zorder=5,
        )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels, fontsize=9.5, color=DARK_SLATE, fontweight="bold")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda val, pos: f"{int(val/1000)}k" if val >= 1000 else f"{int(val)}"))
    ax.grid(True, linestyle="--", alpha=0.5, color=BORDER_GRAY, zorder=1)
    ax.set_ylabel("Average Bill (₹)", fontsize=10, color=MUTED_SLATE, labelpad=8)

    # Padding on y axis
    min_y = min(y_values) * 0.85 if len(y_values) > 0 else 0
    max_y = max(y_values) * 1.15 if len(y_values) > 0 else 5000
    ax.set_ylim(bottom=max(0, min_y), top=max_y)

    fig.tight_layout()
    return fig


def plot_avg_bill_by_city(df: pd.DataFrame) -> plt.Figure:
    """Renders a sorted horizontal bar chart of average electricity bills by city."""
    if df.empty:
        return _create_empty_figure()

    city_data = (
        df.groupby("city")["electricity_bill"]
        .mean()
        .reset_index()
        .sort_values(by="electricity_bill", ascending=True)
    )

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    _apply_saas_theme(fig, ax)

    bars = ax.barh(
        city_data["city"],
        city_data["electricity_bill"],
        color=PRIMARY_EMERALD,
        edgecolor="#047857",
        height=0.65,
        alpha=0.92,
    )

    ax.set_title("Average Electricity Bill by City (₹)", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.set_xlabel("Average Bill (₹)", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.set_ylabel("City", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.grid(axis="x", linestyle="--", alpha=0.5, color=BORDER_GRAY)

    # Annotate bar values cleanly
    for bar in bars:
        width = bar.get_width()
        ax.annotate(
            f" ₹{width:,.0f}",
            xy=(width, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8.5,
            color=DARK_SLATE,
            fontweight="bold",
        )

    # Add right margin padding for label readability
    max_val = city_data["electricity_bill"].max()
    ax.set_xlim(0, max_val * 1.15)

    fig.tight_layout()
    return fig


def plot_monthly_bill_trends(df: pd.DataFrame) -> plt.Figure:
    """Renders a line plot showing monthly trend of average electricity bills."""
    if df.empty:
        return _create_empty_figure()

    monthly_data = df.groupby("month")["electricity_bill"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    _apply_saas_theme(fig, ax)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    ax.plot(
        monthly_data["month"],
        monthly_data["electricity_bill"],
        marker="o",
        linewidth=2.4,
        markersize=6,
        color=PRIMARY_EMERALD,
        label="Monthly Mean Bill",
    )
    ax.fill_between(
        monthly_data["month"],
        monthly_data["electricity_bill"],
        color=PRIMARY_EMERALD,
        alpha=0.1,
    )

    ax.set_title("Monthly Electricity Bill Trend Across Cities", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.set_xlabel("Month", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.set_ylabel("Average Bill (₹)", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_names, fontsize=9.5)
    ax.grid(True, linestyle="--", alpha=0.5, color=BORDER_GRAY)
    ax.legend(loc="upper right", frameon=True, facecolor=SURFACE_WHITE, edgecolor=BORDER_GRAY, fontsize=9)

    fig.tight_layout()
    return fig


def plot_bill_distribution(df: pd.DataFrame) -> plt.Figure:
    """Renders histogram and KDE showing distribution of electricity bills."""
    if df.empty:
        return _create_empty_figure()

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    _apply_saas_theme(fig, ax)

    sns.histplot(
        df["electricity_bill"],
        kde=True,
        bins=32,
        color=PRIMARY_EMERALD,
        edgecolor=SURFACE_WHITE,
        line_kws={"linewidth": 2.2, "color": "#064e3b"},
        alpha=0.65,
        ax=ax,
    )

    mean_val = df["electricity_bill"].mean()
    median_val = df["electricity_bill"].median()

    ax.axvline(mean_val, color="#e11d48", linestyle="--", linewidth=1.6, label=f"Mean: ₹{mean_val:,.0f}")
    ax.axvline(median_val, color="#2563eb", linestyle=":", linewidth=1.8, label=f"Median: ₹{median_val:,.0f}")

    ax.set_title("Distribution of Electricity Bills (₹)", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.set_xlabel("Electricity Bill (₹)", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.set_ylabel("Frequency", fontsize=10.5, color=DARK_SLATE, labelpad=8)
    ax.legend(loc="upper right", frameon=True, facecolor=SURFACE_WHITE, edgecolor=BORDER_GRAY, fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.5, color=BORDER_GRAY)

    fig.tight_layout()
    return fig


def plot_hours_vs_bill(df: pd.DataFrame, max_points: int = 3000) -> plt.Figure:
    """
    Renders scatter plot of MonthlyHours versus ElectricityBill.
    Illustrates the underlying dataset identity (Bill = Hours × Rate).
    """
    if df.empty:
        return _create_empty_figure()

    # Subsample if dataset is large to maintain smooth interactive UI
    sample_df = df.sample(min(len(df), max_points), random_state=42) if len(df) > max_points else df

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    _apply_saas_theme(fig, ax)

    scatter = ax.scatter(
        sample_df["monthly_hours"],
        sample_df["electricity_bill"],
        c=sample_df["tariff_rate"],
        cmap="viridis",
        alpha=0.65,
        s=20,
        edgecolor="none",
    )

    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.outline.set_color(BORDER_GRAY)
    cbar.ax.tick_params(colors=MUTED_SLATE, labelsize=8.5)
    cbar.set_label("Tariff Rate (₹/kWh)", fontsize=9.5, color=DARK_SLATE, labelpad=8)

    ax.set_title("Monthly Hours vs Electricity Bill (Direct Identity)", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.set_xlabel("Monthly Hours", fontsize=10.5, fontweight="medium", color=DARK_SLATE, labelpad=8)
    ax.set_ylabel("Electricity Bill (₹)", fontsize=10.5, fontweight="medium", color=DARK_SLATE, labelpad=8)
    ax.grid(True, linestyle="--", alpha=0.5, color=BORDER_GRAY)

    fig.tight_layout()
    return fig


def plot_tariff_distribution(df: pd.DataFrame) -> plt.Figure:
    """Renders bar plot of discrete tariff rates present in the dataset."""
    if df.empty:
        return _create_empty_figure()

    tariff_counts = df["tariff_rate"].value_counts().sort_index().reset_index()
    tariff_counts.columns = ["tariff_rate", "count"]

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    _apply_saas_theme(fig, ax)

    bars = ax.bar(
        tariff_counts["tariff_rate"].astype(str),
        tariff_counts["count"],
        color="#3b82f6",
        edgecolor="#1d4ed8",
        width=0.58,
        alpha=0.9,
    )

    ax.set_title("Frequency of Discrete Tariff Rates (₹/kWh)", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.set_xlabel("Tariff Rate (₹/kWh)", fontsize=10.5, fontweight="medium", color=DARK_SLATE, labelpad=8)
    ax.set_ylabel("Record Count", fontsize=10.5, fontweight="medium", color=DARK_SLATE, labelpad=8)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=BORDER_GRAY)
    ax.tick_params(axis="x", rotation=45)

    fig.tight_layout()
    return fig


def plot_correlation_heatmap(df: pd.DataFrame) -> plt.Figure:
    """Renders correlation heatmap of numerical variables."""
    if df.empty:
        return _create_empty_figure()

    numeric_cols = [
        "monthly_hours",
        "tariff_rate",
        "electricity_bill",
        "fan",
        "refrigerator",
        "air_conditioner",
        "television",
        "monitor",
    ]
    available_cols = [c for c in numeric_cols if c in df.columns]

    corr = df[available_cols].corr()

    fig, ax = plt.subplots(figsize=(8, 6.2))
    fig.patch.set_facecolor(SURFACE_WHITE)
    ax.set_facecolor(SURFACE_WHITE)

    # Readable clean labels
    label_mapping = {
        "monthly_hours": "Hours",
        "tariff_rate": "Tariff",
        "electricity_bill": "Bill (₹)",
        "fan": "Fan",
        "refrigerator": "Fridge",
        "air_conditioner": "AC",
        "television": "TV",
        "monitor": "Monitor",
    }
    annot_cols = [label_mapping.get(c, c) for c in available_cols]

    sns.heatmap(
        corr,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        vmin=-1,
        vmax=1,
        linewidths=0.75,
        linecolor=SURFACE_WHITE,
        cbar_kws={"shrink": 0.8, "pad": 0.03},
        xticklabels=annot_cols,
        yticklabels=annot_cols,
        annot_kws={"size": 9, "fontweight": "medium"},
        ax=ax,
    )

    ax.set_title("Feature Correlation Matrix", fontsize=12, fontweight="bold", color=DARK_SLATE, pad=14)
    ax.tick_params(axis="x", rotation=45, colors=DARK_SLATE, labelsize=9.5)
    ax.tick_params(axis="y", rotation=0, colors=DARK_SLATE, labelsize=9.5)

    fig.tight_layout()
    return fig
