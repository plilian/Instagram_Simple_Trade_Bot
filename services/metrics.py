import pandas as pd

def calculate_rsi(df: pd.DataFrame, length: int = 14) -> pd.Series | None:

    if df.empty or "close" not in df.columns:
        return None

    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=length - 1, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, min_periods=length).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    if rsi.isnull().all():
        return None

    return rsi

def calculate_volatility(df: pd.DataFrame) -> float | None:

    if df.empty or "close" not in df.columns:
        return None

    returns = df['close'].pct_change().dropna()
    if returns.empty:
        return None

    volatility = returns.std() * (252 ** 0.5)
    return volatility * 100

def calculate_risk_reward(
    entry: float, stop: float, target: float
) -> tuple[float | None, float | None, float | None, str]:

    risk = None
    reward = None
    position_type = "نامعتبر"

    if target > entry > stop:
        risk = entry - stop
        reward = target - entry
        position_type = "long"
    elif stop > entry > target:
        risk = stop - entry
        reward = entry - target
        position_type = "short"

    if risk is None or reward is None or risk == 0:
        return (None, risk, reward, position_type)

    rr_ratio = reward / risk
    return (rr_ratio, risk, reward, position_type)
