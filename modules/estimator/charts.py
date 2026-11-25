"""
Household Energy Analytics Visualizations.
Renders the 5 required personal household charts:
1. Appliance-wise Energy Consumption (Donut Chart)
2. Appliance-wise Electricity Cost (Donut Chart)
3. Appliance Consumption Comparison (Monthly kWh Bar Chart)
4. Daily Consumption Breakdown (Daily kWh Bar Chart)
5. Monthly Bill Cost Structure Breakdown (Component Bar Chart)
"""

from typing import Any, Dict, List
import matplotlib.pyplot as plt
import numpy as np

# Professional green-and-white SaaS styling constants
SURFACE_WHITE = "#ffffff"
PRIMARY_EMERALD = "#059669"
BORDER_GRAY = "#e2ece5"
DARK_SLATE = "#0f172a"
MUTED_SLATE = "#64748b"

# Balanced color palette for appliance slices
PALETTE = [
    "#059669", "#10b981", "#3b82f6", "#6366f1", "#8b5cf6",
    "#ec4899", "#f59e0b", "#14b8a6", "#06b6d4", "#f97316",
    "#84cc16", "#a855f7", "#64748b"
]


def _apply_theme(fig: plt.Figure, ax: plt.Axes) -> None:
    """Applies clean consistent light theme to chart."""
    fig.patch.set_facecolor(SURFACE_WHITE)
    ax.set_facecolor(SURFACE_WHITE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#cbd5e1")
    ax.spines["bottom"].set_color("#cbd5e1")
    ax.tick_params(colors=MUTED_SLATE, labelsize=9)


def plot_appliance_kwh_donut(appliances: List[Dict[str, Any]]) -> plt.Figure:
    """Renders a donut chart of appliance percentage contribution to monthly kWh."""
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    fig.patch.set_facecolor(SURFACE_WHITE)

    if not appliances:
        ax.text(0.5, 0.5, "No appliances configured", ha="center", va="center", color=MUTED_SLATE)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    # Group small appliances into 'Other' if more than 7 items
    valid_items = [a for a in appliances if a.get("monthly_kwh", 0) > 0]
    if not valid_items:
        ax.text(0.5, 0.5, "0 kWh estimated consumption", ha="center", va="center", color=MUTED_SLATE)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    labels = []
    sizes = []
    for a in valid_items[:7]:
        name = a.get("label") or a.get("spec_name") or a.get("appliance_name_snapshot") or "Appliance"
        labels.append(name)
        sizes.append(a.get("monthly_kwh", 0))

    if len(valid_items) > 7:
        other_kwh = sum(a.get("monthly_kwh", 0) for a in valid_items[7:])
        if other_kwh > 0:
            labels.append("Other Appliances")
            sizes.append(other_kwh)

    colors = PALETTE[:len(sizes)]
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
        textprops={"fontsize": 8.5, "color": DARK_SLATE},
        wedgeprops={"width": 0.42, "edgecolor": SURFACE_WHITE, "linewidth": 2},
    )

    for at in autotexts:
        at.set_fontsize(8)
        at.set_weight("bold")
        at.set_color("#ffffff")

    ax.set_title("Appliance Energy Consumption Share (% kWh)", fontsize=11, fontweight="bold", color=DARK_SLATE, pad=12)
    fig.tight_layout()
    return fig


def plot_appliance_cost_donut(appliances: List[Dict[str, Any]]) -> plt.Figure:
    """Renders a donut chart of appliance variable energy cost contribution."""
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    fig.patch.set_facecolor(SURFACE_WHITE)

    valid_items = [a for a in appliances if a.get("variable_cost", 0) > 0 or a.get("monthly_kwh", 0) > 0]
    if not valid_items:
        ax.text(0.5, 0.5, "No variable cost data", ha="center", va="center", color=MUTED_SLATE)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    labels = []
    sizes = []
    for a in valid_items[:7]:
        name = a.get("label") or a.get("spec_name") or a.get("appliance_name_snapshot") or "Appliance"
        cost = a.get("variable_cost") if a.get("variable_cost") is not None else round(a.get("monthly_kwh", 0) * 5.80, 2)
        labels.append(name)
        sizes.append(cost)

    if len(valid_items) > 7:
        other_cost = sum(
            a.get("variable_cost") if a.get("variable_cost") is not None else round(a.get("monthly_kwh", 0) * 5.80, 2)
            for a in valid_items[7:]
        )
        if other_cost > 0:
            labels.append("Other Appliances")
            sizes.append(other_cost)

    colors = PALETTE[:len(sizes)]
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
        textprops={"fontsize": 8.5, "color": DARK_SLATE},
        wedgeprops={"width": 0.42, "edgecolor": SURFACE_WHITE, "linewidth": 2},
    )

    for at in autotexts:
        at.set_fontsize(8)
        at.set_weight("bold")
        at.set_color("#ffffff")

    ax.set_title("Appliance Variable Cost Share (%)", fontsize=11, fontweight="bold", color=DARK_SLATE, pad=12)
    fig.tight_layout()
    return fig


def plot_appliance_kwh_bar(appliances: List[Dict[str, Any]]) -> plt.Figure:
    """Renders horizontal bar chart comparing monthly kWh across appliances."""
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    _apply_theme(fig, ax)

    if not appliances:
        ax.text(0.5, 0.5, "No appliances configured", ha="center", va="center", color=MUTED_SLATE)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    # Sort ascending for horizontal bar chart (top consumers appear on top)
    sorted_items = sorted(appliances, key=lambda x: x.get("monthly_kwh", 0), reverse=False)[-10:]
    names = [a.get("label") or a.get("spec_name") or a.get("appliance_name_snapshot") or "Appliance" for a in sorted_items]
    kwh_values = [a.get("monthly_kwh", 0) for a in sorted_items]

    bars = ax.barh(names, kwh_values, color=PRIMARY_EMERALD, height=0.6, edgecolor="#047857", alpha=0.9)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(
            f" {width:,.1f} kWh",
            xy=(width, bar.get_y() + bar.get_height() / 2),
            xytext=(4, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=8.5,
            color=DARK_SLATE,
            fontweight="bold",
        )

    max_val = max(kwh_values) if kwh_values else 100
    ax.set_xlim(0, max_val * 1.25)
    ax.set_title("Monthly Energy Consumption Comparison (kWh)", fontsize=11, fontweight="bold", color=DARK_SLATE, pad=12)
    ax.set_xlabel("Monthly Consumption (kWh)", fontsize=9.5, color=DARK_SLATE, labelpad=6)
    ax.grid(axis="x", linestyle="--", alpha=0.5, color=BORDER_GRAY)
    fig.tight_layout()
    return fig


def plot_daily_consumption_bar(appliances: List[Dict[str, Any]]) -> plt.Figure:
    """Renders vertical bar chart of estimated daily kWh per appliance."""
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    _apply_theme(fig, ax)

    sorted_items = sorted(appliances, key=lambda x: x.get("daily_kwh", 0), reverse=True)[:8]
    if not sorted_items:
        ax.text(0.5, 0.5, "No daily consumption data", ha="center", va="center", color=MUTED_SLATE)
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    names = [a.get("label") or a.get("spec_name") or a.get("appliance_name_snapshot") or "Appliance" for a in sorted_items]
    daily_values = [a.get("daily_kwh", 0) for a in sorted_items]

    bars = ax.bar(names, daily_values, color="#3b82f6", width=0.55, edgecolor="#1d4ed8", alpha=0.88)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"{height:.2f} k",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color=DARK_SLATE,
            fontweight="bold",
        )

    max_h = max(daily_values) if daily_values else 10
    ax.set_ylim(0, max_h * 1.25)
    ax.set_title("Daily Energy Consumption Breakdown (kWh/day)", fontsize=11, fontweight="bold", color=DARK_SLATE, pad=12)
    ax.set_ylabel("Daily Consumption (kWh)", fontsize=9.5, color=DARK_SLATE, labelpad=6)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=BORDER_GRAY)
    ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    return fig


def plot_cost_breakdown_bar(bill_dict: Dict[str, Any]) -> plt.Figure:
    """Renders a stacked/grouped bar chart illustrating the BESCOM LT-1 bill component breakdown."""
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    _apply_theme(fig, ax)

    components = ["Energy Charge", "Fixed Charge", "Electricity Duty"]
    values = [
        bill_dict.get("energy_charge_inr", 0.0),
        bill_dict.get("fixed_charge_inr", 0.0),
        bill_dict.get("duty_inr", 0.0),
    ]
    colors = ["#059669", "#f59e0b", "#6366f1"]

    bars = ax.bar(components, values, color=colors, width=0.5, edgecolor=SURFACE_WHITE, alpha=0.9)

    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            f"₹{height:,.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color=DARK_SLATE,
            fontweight="bold",
        )

    max_v = max(values) if values and max(values) > 0 else 100
    ax.set_ylim(0, max_v * 1.25)
    ax.set_title("Monthly Electricity Bill Component Breakdown (₹)", fontsize=11, fontweight="bold", color=DARK_SLATE, pad=12)
    ax.set_ylabel("Amount (₹)", fontsize=9.5, color=DARK_SLATE, labelpad=6)
    ax.grid(axis="y", linestyle="--", alpha=0.5, color=BORDER_GRAY)
    fig.tight_layout()
    return fig
