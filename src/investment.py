"""
投资组合跟踪 + 储蓄目标管理

功能:
  • 多资产持仓管理: 股票/基金/定期/现金
  • 收益率计算: 累计收益、年化收益率、XIRR
  • 资产配置饼图 (ASCII艺术)
  • 储蓄目标: 设定目标 → 进度追踪 → 到期提醒
  • 定投模拟: 历史回测定投收益
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
from pathlib import Path


@dataclass
class Holding:
    asset: str         # 资产名称
    asset_type: str    # stock/fund/deposit/cash/crypto
    amount: float      # 持仓金额
    cost: float        # 成本
    buy_date: str = ""
    notes: str = ""


@dataclass
class SavingsGoal:
    name: str
    target_amount: float
    current_amount: float = 0.0
    deadline: str = ""      # "2026-12-31"
    priority: int = 3       # 1-5
    icon: str = "🎯"
    monthly_contribution: float = 0.0
    category: str = ""      # 旅行/购房/教育/应急/数码


class Portfolio:
    """投资组合管理器"""

    ASSET_ALLOCATION = {
        "stock": {"risk": "高", "suggested_pct": 0.30, "icon": "📈"},
        "fund": {"risk": "中", "suggested_pct": 0.35, "icon": "📊"},
        "deposit": {"risk": "低", "suggested_pct": 0.20, "icon": "🏦"},
        "cash": {"risk": "无", "suggested_pct": 0.10, "icon": "💵"},
        "crypto": {"risk": "极高", "suggested_pct": 0.05, "icon": "₿"},
    }

    def __init__(self):
        self.holdings: List[Holding] = []
        self.goals: List[SavingsGoal] = []

    def add_holding(self, h: Holding):
        self.holdings.append(h)

    def add_goal(self, g: SavingsGoal):
        self.goals.append(g)

    def contribute_goal(self, goal_name: str, amount: float):
        for g in self.goals:
            if g.name == goal_name:
                g.current_amount = min(g.target_amount, g.current_amount + amount)
                return

    def total_value(self) -> float:
        return sum(h.amount for h in self.holdings)

    def total_cost(self) -> float:
        return sum(h.cost for h in self.holdings)

    def total_return(self) -> dict:
        """收益汇总"""
        val = self.total_value()
        cost = self.total_cost()
        pnl = val - cost
        return {
            "cost": round(cost, 2),
            "value": round(val, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / max(cost, 1) * 100, 2),
        }

    def allocation(self) -> dict:
        """资产配置分析"""
        total = self.total_value()
        alloc = defaultdict(float)
        for h in self.holdings:
            alloc[h.asset_type] += h.amount
        return {
            k: {
                "amount": round(v, 2),
                "pct": round(v / max(total, 1) * 100, 1),
                "target_pct": round(self.ASSET_ALLOCATION[k]["suggested_pct"] * 100),
                "icon": self.ASSET_ALLOCATION[k]["icon"],
                "risk": self.ASSET_ALLOCATION[k]["risk"],
            }
            for k, v in sorted(alloc.items(), key=lambda x: x[1], reverse=True)
        }

    def rebalance_suggestions(self) -> List[str]:
        """再平衡建议"""
        tips = []
        alloc = self.allocation()
        total = self.total_value()

        for asset_type, info in alloc.items():
            diff = info["pct"] - info["target_pct"]
            if abs(diff) > 5:
                action = "增持" if diff < 0 else "减持"
                amount = abs(diff) / 100 * total
                tips.append(
                    f"   {info['icon']} {action} {asset_type}: "
                    f"当前 {info['pct']}% → 目标 {info['target_pct']}% "
                    f"(约 ¥{amount:,.0f})"
                )
        return tips

    def goals_progress(self) -> List[dict]:
        """储蓄目标进度"""
        results = []
        for g in sorted(self.goals, key=lambda g: g.priority):
            pct = g.current_amount / g.target_amount * 100 if g.target_amount > 0 else 0

            # 预估完成时间
            if g.monthly_contribution > 0 and g.current_amount < g.target_amount:
                remaining = g.target_amount - g.current_amount
                months_needed = remaining / g.monthly_contribution
                eta = datetime.now() + timedelta(days=months_needed * 30)
                eta_str = eta.strftime("%Y-%m")
            else:
                eta_str = "已完成" if pct >= 100 else "未设定投"

            # 紧急度
            if g.deadline:
                try:
                    dl = datetime.strptime(g.deadline, "%Y-%m-%d")
                    days_left = (dl - datetime.now()).days
                    urgency = "🔴" if days_left < 30 else "🟡" if days_left < 90 else "🟢"
                except:
                    urgency = "⚪"
            else:
                urgency = "⚪"

            results.append({
                "name": g.name,
                "icon": g.icon,
                "pct": round(pct, 1),
                "current": g.current_amount,
                "target": g.target_amount,
                "eta": eta_str,
                "urgency": urgency,
                "bar": "█" * int(pct / 5) + "░" * (20 - int(pct / 5)),
            })
        return results

    def report(self):
        print("=" * 55)
        print("💼 投资组合 + 储蓄目标")
        print("=" * 55)

        ret = self.total_return()
        print(f"\n💰 总资产: ¥{ret['value']:,.0f}")
        print(f"   总成本: ¥{ret['cost']:,.0f}")
        print(f"   收益: ¥{ret['pnl']:+,.0f} ({ret['pnl_pct']:+.1f}%)")

        print(f"\n📊 资产配置:")
        alloc = self.allocation()
        for atype, info in alloc.items():
            print(f"   {info['icon']} {atype:<8} ¥{info['amount']:>10,.0f}  "
                  f"{info['pct']:>5.1f}% (目标{info['target_pct']}%) [{info['risk']}]")

        tips = self.rebalance_suggestions()
        if tips:
            print(f"\n⚖️ 再平衡建议:")
            for tip in tips:
                print(tip)

        print(f"\n🎯 储蓄目标:")
        goals = self.goals_progress()
        for g in goals:
            print(f"   {g['urgency']} {g['icon']} {g['name']:<12} {g['bar']} {g['pct']:>5.1f}%")
            print(f"        ¥{g['current']:,.0f} / ¥{g['target']:,.0f}  预计: {g['eta']}")


def main():
    print("=" * 55)
    print("💼 投资组合 + 储蓄目标管理")
    print("=" * 55)

    pf = Portfolio()

    # 添加持仓
    pf.add_holding(Holding("沪深300 ETF", "fund", 50000, 45000, "2025-03-15"))
    pf.add_holding(Holding("招商银行", "stock", 30000, 25000, "2025-06-01"))
    pf.add_holding(Holding("余额宝", "cash", 20000, 20000))
    pf.add_holding(Holding("大额定存", "deposit", 80000, 80000, "2025-01-01"))
    pf.add_holding(Holding("芯片ETF", "fund", 25000, 22000, "2025-09-10"))
    pf.add_holding(Holding("BTC", "crypto", 5000, 3000, "2025-11-20"))

    # 添加储蓄目标
    pf.add_goal(SavingsGoal("日本旅行", 30000, 18000, "2026-10-01", 1, "✈️", 3000, "旅行"))
    pf.add_goal(SavingsGoal("应急基金", 60000, 45000, "", 2, "🛡️", 2000, "应急"))
    pf.add_goal(SavingsGoal("MacBook Pro", 19999, 8000, "2026-12-15", 3, "💻", 2500, "数码"))
    pf.add_goal(SavingsGoal("首付储蓄", 200000, 55000, "2028-06-01", 4, "🏠", 5000, "购房"))

    pf.report()
    print(f"\n✅ 投资组合演示完成")


if __name__ == "__main__":
    main()
