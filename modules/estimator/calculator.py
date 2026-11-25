"""
Household Energy and Electricity Bill Calculation Engine.
Implements validated, multi-method appliance consumption calculations
and BESCOM LT-1 domestic tariff billing rules with financial precision.
"""

from typing import Any, Dict, List, Optional, Tuple


def calculate_appliance_energy(
    calculation_method: str,
    quantity: int = 1,
    rated_watt: Optional[float] = None,
    daily_hours: Optional[float] = None,
    days_per_month: int = 30,
    annual_kwh: Optional[float] = None,
    kwh_per_cycle: Optional[float] = None,
    cycles_per_month: Optional[float] = None,
    custom_monthly_kwh: Optional[float] = None,
    standby_enabled: bool = False,
    standby_watt: float = 0.0,
    daily_standby_hours: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculates monthly and daily energy consumption (in kWh) for an appliance
    according to its specific physical calculation method.

    Validation rules:
    - quantity must be >= 1
    - days_per_month must be between 1 and 31
    - daily_hours must be between 0.0 and 24.0
    - wattages and kWh ratings must be non-negative
    """
    # 1. Input sanitization & validation
    qty = max(1, int(quantity))
    days = max(1, min(31, int(days_per_month)))
    active_daily_kwh = 0.0
    standby_monthly_kwh = 0.0

    method = (calculation_method or "rated_wattage").lower()

    if method == "annual_kwh":
        # BEE Star Rating: rating represents annual normalized energy use
        annual_val = max(0.0, float(annual_kwh or 0.0))
        # Daily = Annual kWh / 365 * quantity
        active_daily_kwh = (annual_val * qty) / 365.0
        active_monthly_kwh = active_daily_kwh * days

    elif method == "kwh_per_cycle":
        # Cyclic batch appliances (e.g. washing machines)
        cycle_val = max(0.0, float(kwh_per_cycle or 0.0))
        cycles = max(0.0, float(cycles_per_month if cycles_per_month is not None else days))
        active_monthly_kwh = cycle_val * qty * cycles
        active_daily_kwh = active_monthly_kwh / days if days > 0 else 0.0

    elif method == "user_supplied":
        # Custom user-provided monthly kWh
        custom_val = max(0.0, float(custom_monthly_kwh or 0.0))
        active_monthly_kwh = custom_val * qty
        active_daily_kwh = active_monthly_kwh / days if days > 0 else 0.0

    else:
        # Default: rated_wattage
        watt_val = max(0.0, float(rated_watt or 0.0))
        hrs_val = max(0.0, min(24.0, float(daily_hours or 0.0)))
        active_daily_kwh = (watt_val * qty * hrs_val) / 1000.0
        active_monthly_kwh = active_daily_kwh * days

    # 2. Standby consumption (calculated only if explicitly enabled)
    if standby_enabled and standby_watt > 0 and daily_standby_hours > 0:
        std_hrs = max(0.0, min(24.0, float(daily_standby_hours)))
        std_watt = max(0.0, float(standby_watt))
        standby_daily_kwh = (std_watt * qty * std_hrs) / 1000.0
        standby_monthly_kwh = standby_daily_kwh * days
    else:
        standby_daily_kwh = 0.0

    total_monthly_kwh = round(active_monthly_kwh + standby_monthly_kwh, 3)
    total_daily_kwh = round(active_daily_kwh + standby_daily_kwh, 3)

    return {
        "active_monthly_kwh": round(active_monthly_kwh, 3),
        "standby_monthly_kwh": round(standby_monthly_kwh, 3),
        "monthly_kwh": total_monthly_kwh,
        "daily_kwh": total_daily_kwh,
        "calculation_method": method,
        "quantity": qty,
        "days_per_month": days,
    }


def calculate_household_summary(
    appliances: List[Dict[str, Any]],
    energy_rate_per_kwh: float = 5.80,
) -> Dict[str, Any]:
    """
    Aggregates consumption across a list of configured household appliances.
    Computes total daily kWh, monthly kWh, individual shares, and variable energy costs.
    """
    total_monthly_kwh = 0.0
    total_daily_kwh = 0.0
    total_quantity = 0
    appliance_results = []

    for item in appliances:
        # Resolve effective power/energy specifications safely across custom and default aliases
        eff_watt = item.get("custom_watt")
        if eff_watt is None:
            eff_watt = item.get("rated_watt") if item.get("rated_watt") is not None else item.get("default_watt")

        eff_annual = item.get("custom_annual_kwh")
        if eff_annual is None:
            eff_annual = item.get("annual_kwh") if item.get("annual_kwh") is not None else item.get("default_annual_kwh")

        eff_cycle = item.get("custom_kwh_per_cycle")
        if eff_cycle is None:
            eff_cycle = item.get("kwh_per_cycle") if item.get("kwh_per_cycle") is not None else item.get("default_kwh_per_cycle")

        res = calculate_appliance_energy(
            calculation_method=item.get("calculation_method", "rated_wattage"),
            quantity=item.get("quantity", 1),
            rated_watt=eff_watt,
            daily_hours=item.get("daily_hours"),
            days_per_month=item.get("days_per_month", 30),
            annual_kwh=eff_annual,
            kwh_per_cycle=eff_cycle,
            cycles_per_month=item.get("cycles_per_month"),
            custom_monthly_kwh=item.get("custom_monthly_kwh"),
            standby_enabled=bool(item.get("standby_enabled", 0)),
            standby_watt=float(item.get("standby_watt", 0.0)),
            daily_standby_hours=float(item.get("daily_standby_hours", 0.0)),
        )

        monthly_kwh = res["monthly_kwh"]
        variable_cost = round(monthly_kwh * energy_rate_per_kwh, 2)
        qty = res["quantity"]

        total_monthly_kwh += monthly_kwh
        total_daily_kwh += res["daily_kwh"]
        total_quantity += qty

        appliance_results.append({
            **item,
            "monthly_kwh": monthly_kwh,
            "daily_kwh": res["daily_kwh"],
            "variable_cost": variable_cost,
        })

    # Calculate percentage shares mathematically consistent to 100%
    for item in appliance_results:
        if total_monthly_kwh > 0:
            share = round((item["monthly_kwh"] / total_monthly_kwh) * 100, 2)
        else:
            share = 0.0
        item["share_percent"] = share

    # Sort descending by monthly kWh
    appliance_results.sort(key=lambda x: x["monthly_kwh"], reverse=True)

    highest_consumer = appliance_results[0] if appliance_results else None

    return {
        "total_monthly_kwh": round(total_monthly_kwh, 2),
        "total_daily_kwh": round(total_daily_kwh, 2),
        "total_appliance_units": total_quantity,
        "appliance_count": len(appliances),
        "total_variable_cost": round(total_monthly_kwh * energy_rate_per_kwh, 2),
        "appliances": appliance_results,
        "highest_consumer": highest_consumer,
    }


def calculate_bescom_bill(
    total_monthly_kwh: float,
    sanctioned_load_kw: float = 3.0,
    base_rate_paise: int = 580,          # ₹5.80 / kWh
    fixed_charge_rate_paise: int = 15000, # ₹150.00 / kW / month
    duty_percent: float = 9.0,           # 9.0% on energy charges
) -> Dict[str, Any]:
    """
    Computes an estimated monthly electricity bill according to verified BESCOM LT-1 specifications:
    - Variable Energy Charge: Total kWh × ₹5.80
    - Fixed Charge: Sanctioned Load (kW) × ₹150.00
    - Electricity Duty: 9% of Variable Energy Charge
    - Total Estimated Bill = Energy Charge + Fixed Charge + Duty
    """
    kwh = max(0.0, float(total_monthly_kwh))
    load_kw = max(0.5, float(sanctioned_load_kw))

    # Calculate in integer paise to avoid IEEE 754 floating-point drift
    energy_charge_paise = round(kwh * base_rate_paise)
    fixed_charge_paise = round(load_kw * fixed_charge_rate_paise)
    duty_paise = round(energy_charge_paise * (duty_percent / 100.0))

    total_net_paise = energy_charge_paise + fixed_charge_paise + duty_paise

    return {
        "total_kwh": round(kwh, 2),
        "sanctioned_load_kw": round(load_kw, 1),
        "energy_rate_inr": base_rate_paise / 100.0,
        "fixed_charge_rate_inr": fixed_charge_rate_paise / 100.0,
        "duty_percent": duty_percent,
        "energy_charge_inr": round(energy_charge_paise / 100.0, 2),
        "fixed_charge_inr": round(fixed_charge_paise / 100.0, 2),
        "duty_inr": round(duty_paise / 100.0, 2),
        "total_bill_inr": round(total_net_paise / 100.0, 2),
        # Integer paise values for SQLite storage
        "energy_charge_paise": energy_charge_paise,
        "fixed_charge_paise": fixed_charge_paise,
        "duty_paise": duty_paise,
        "net_payable_paise": total_net_paise,
    }
