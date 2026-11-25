"""
Calculation-Based Household Energy Insights Engine.
Generates deterministic, mathematically sound household energy savings insights
based exclusively on the user's configured appliances and operating hours.
"""

from typing import Any, Dict, List, Optional


def generate_household_insights(
    appliances: List[Dict[str, Any]],
    energy_rate_inr: float = 5.80,
) -> List[Dict[str, str]]:
    """
    Analyzes configured household appliances to generate actionable,
    quantifiable observations and hypothetical reduction calculations.
    """
    if not appliances:
        return []

    insights = []
    total_kwh = sum(a.get("monthly_kwh", 0.0) for a in appliances)
    if total_kwh <= 0:
        return []

    # 1. Top Consumer Identification
    sorted_by_kwh = sorted(appliances, key=lambda x: x.get("monthly_kwh", 0.0), reverse=True)
    top_app = sorted_by_kwh[0]
    top_name = top_app.get("label") or top_app.get("spec_name") or "Top Appliance"
    top_kwh = top_app.get("monthly_kwh", 0.0)

    if top_kwh > 0:
        top_share = round((top_kwh / total_kwh) * 100, 1)
        top_cost = round(top_kwh * energy_rate_inr, 2)
        insights.append({
            "type": "top_consumer",
            "title": f"Primary Energy Driver: {top_name}",
            "message": (
                f"<strong>{top_name}</strong> accounts for <strong>{top_share}%</strong> of your estimated monthly energy use "
                f"({top_kwh:,.1f} kWh, contributing ₹{top_cost:,.2f} in variable charges)."
            ),
            "icon": "⚡",
        })

    # 2. Air Conditioner Specific Analysis
    ac_items = [
        a for a in appliances
        if "air conditioner" in (a.get("spec_name") or "").lower() or "ac" in (a.get("label") or "").lower()
    ]
    if ac_items:
        ac_kwh = sum(a.get("monthly_kwh", 0.0) for a in ac_items)
        if ac_kwh > 0:
            ac_share = round((ac_kwh / total_kwh) * 100, 1)

            # Hypothetical 2-hour daily runtime reduction calculation
            ac_reduction_kwh = 0.0
            for ac in ac_items:
                method = ac.get("calculation_method", "rated_wattage")
                qty = ac.get("quantity", 1)
                hrs = ac.get("daily_hours", 0.0)
                days = ac.get("days_per_month", 30)
                watt = ac.get("custom_watt") or ac.get("default_watt") or ac.get("rated_watt") or 1400

                if method == "rated_wattage" and hrs > 0:
                    hours_to_cut = min(2.0, hrs)
                    ac_reduction_kwh += (watt * qty * hours_to_cut * days) / 1000.0

            saved_cost = round(ac_reduction_kwh * energy_rate_inr, 2)

            insights.append({
                "type": "ac_reduction",
                "title": "Air Conditioning Optimization",
                "message": (
                    f"Air conditioning represents <strong>{ac_share}%</strong> of your monthly consumption ({ac_kwh:,.1f} kWh). "
                    f"Reducing AC runtime by <strong>2 hours per day</strong> would save an estimated "
                    f"<strong>{ac_reduction_kwh:,.1f} kWh/month</strong> (saving ₹{saved_cost:,.2f}/month on variable energy charges)."
                ),
                "icon": "❄️",
            })

    # 3. Water Heater / Geyser Analysis
    geyser_items = [
        a for a in appliances
        if any(k in (a.get("spec_name") or "").lower() or k in (a.get("label") or "").lower() for k in ["geyser", "water heater"])
    ]
    if geyser_items:
        g_kwh = sum(a.get("monthly_kwh", 0.0) for a in geyser_items)
        if g_kwh > 0:
            g_share = round((g_kwh / total_kwh) * 100, 1)
            insights.append({
                "type": "water_heating",
                "title": "Water Heating Load",
                "message": (
                    f"Water heating accounts for <strong>{g_share}%</strong> ({g_kwh:,.1f} kWh) of your bill. "
                    f"Because geysers draw high wattage (1.5 kW - 2.0 kW), setting timers or limiting pre-heat durations "
                    f"directly caps peak morning demand."
                ),
                "icon": "🚿",
            })

    # 4. Overall Baseline Efficiency Observation
    if len(appliances) >= 3 and not insights:
        insights.append({
            "type": "general_baseline",
            "title": "Consumption Distribution",
            "message": (
                f"Your configured appliances yield a balanced baseline load of <strong>{total_kwh:,.1f} kWh</strong> per month. "
                f"Total estimated variable energy charge is ₹{total_kwh * energy_rate_inr:,.2f} at ₹{energy_rate_inr:.2f}/kWh."
            ),
            "icon": "💡",
        })

    return insights
