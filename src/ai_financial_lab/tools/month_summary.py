from ai_financial_lab.data.fake_financial_data import FINANCIAL_DATA

def get_month_summary() -> dict:
    income = FINANCIAL_DATA["income"]
    fixed_expenses = FINANCIAL_DATA["fixed_expenses"]
    variable_expenses = FINANCIAL_DATA["variable_expenses"]
    investment_goal = FINANCIAL_DATA["investment_goal"]

    total_expenses = fixed_expenses + variable_expenses

    margin_before_investment = income - total_expenses

    free_margin = (margin_before_investment - investment_goal)

    return {
        "income": income,
        "fixed_expenses": fixed_expenses,
        "variable_expenses": variable_expenses,
        "total_expenses": total_expenses,
        "investment_goal": investment_goal,
        "margin_before_investment": margin_before_investment,
        "free_margin": free_margin,
    }
