"""
个人财务仪表板 — 记账·分类·预算·趋势分析

纯 Python + 终端可视化，无需数据库，JSON 持久化存储。

知识点:
  1. 复式记账思想: 收入/支出/转账
  2. 预算管理: 分类预算 + 超支告警
  3. 趋势分析: 月度汇总 + 环比增长
  4. 数据持久化: JSON 文件存储
  5. 终端可视化: ASCII 图表
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from collections import defaultdict, Counter


# ── 数据模型 ──
CATEGORIES_EXPENSE = ["🍔 餐饮", "🏠 房租", "🚇 交通", "📱 通讯", "🛒 购物", "🎬 娱乐",
                       "❤️ 医疗", "📚 学习", "🧴 日用", "💳 其他"]
CATEGORIES_INCOME = ["💰 工资", "📈 理财", "🎁 红包", "其他收入"]


@dataclass
class Transaction:
    date: str       # "2026-07-03"
    amount: float    # 正=收入, 负=支出
    category: str    # 分类
    note: str = ""   # 备注
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = datetime.now().strftime("%Y%m%d%H%M%S%f")


class FinanceDashboard:
    def __init__(self, data_file: str = "finance.json"):
        self.data_file = Path(data_file)
        self.transactions: List[Transaction] = []
        self.budgets: dict = {}  # {"🍔 餐饮": 3000, ...}
        self._load()

    def _load(self):
        if self.data_file.exists():
            d = json.loads(self.data_file.read_text(encoding="utf-8"))
            self.transactions = [Transaction(**t) for t in d.get("transactions", [])]
            self.budgets = d.get("budgets", {})

    def save(self):
        self.data_file.write_text(json.dumps({
            "transactions": [asdict(t) for t in self.transactions],
            "budgets": self.budgets,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, date: str, amount: float, category: str, note: str = ""):
        self.transactions.append(Transaction(date, amount, category, note))
        self.save()

    def monthly_summary(self, ym: str = "") -> dict:
        """月度汇总: 收入/支出/结余/分类明细"""
        if not ym:
            ym = datetime.now().strftime("%Y-%m")

        income = sum(t.amount for t in self.transactions
                     if t.date.startswith(ym) and t.amount > 0)
        expense = sum(abs(t.amount) for t in self.transactions
                      if t.date.startswith(ym) and t.amount < 0)

        cat_exp = defaultdict(float)
        for t in self.transactions:
            if t.date.startswith(ym) and t.amount < 0:
                cat_exp[t.category] += abs(t.amount)

        return {
            "month": ym, "income": round(income, 2), "expense": round(expense, 2),
            "balance": round(income - expense, 2),
            "categories": dict(sorted(cat_exp.items(), key=lambda x: x[1], reverse=True)),
        }

    def trend(self, months: int = 6) -> List[dict]:
        """近N个月趋势"""
        results = []
        now = datetime.now()
        for i in range(months - 1, -1, -1):
            ym = (now.replace(day=1) - timedelta(days=i * 31)).strftime("%Y-%m")
            results.append(self.monthly_summary(ym))
        return results

    def budget_check(self, ym: str = "") -> dict:
        """预算检查"""
        summary = self.monthly_summary(ym)
        alerts = {}
        for cat, budget in self.budgets.items():
            spent = summary["categories"].get(cat, 0)
            pct = spent / budget if budget > 0 else 0
            status = "🔴" if pct > 1 else "🟡" if pct > 0.8 else "🟢"
            alerts[cat] = {"budget": budget, "spent": round(spent, 2), "pct": round(pct * 100), "status": status}
        return alerts

    def report(self):
        """生成完整财务报告"""
        print("=" * 55)
        print("💰 个人财务仪表板")
        print("=" * 55)

        # 当月
        now_ym = datetime.now().strftime("%Y-%m")
        s = self.monthly_summary(now_ym)
        print(f"\n📅 {now_ym} 月度报告")
        print(f"   ┌─────────────┬──────────┐")
        print(f"   │ 收入         │ ¥{s['income']:>8,.1f} │")
        print(f"   │ 支出         │ ¥{s['expense']:>8,.1f} │")
        print(f"   │ 结余         │ ¥{s['balance']:>8,.1f} │")
        print(f"   └─────────────┴──────────┘")

        # 分类明细
        print(f"\n📊 支出分类:")
        max_cat = max((len(k) for k in s["categories"]), default=10)
        max_amt = max(s["categories"].values()) if s["categories"] else 1
        for cat, amt in s["categories"].items():
            bar = "█" * int(amt / max_amt * 20) if max_amt > 0 else ""
            print(f"   {cat:<{max_cat+2}} ¥{amt:>8,.1f}  {bar}")

        # 预算
        if self.budgets:
            print(f"\n🎯 预算执行:")
            alerts = self.budget_check()
            for cat, info in alerts.items():
                print(f"   {info['status']} {cat}: ¥{info['spent']:,.0f}/{info['budget']:,.0f} ({info['pct']}%)")

        # 趋势
        print(f"\n📈 近6月趋势:")
        trend = self.trend(6)
        max_exp = max(s["expense"] for s in trend) if trend else 1
        for s in trend:
            bar = "█" * int(s["expense"] / max_exp * 25) if max_exp > 0 else ""
            print(f"   {s['month']} 开销 ¥{s['expense']:>8,.1f} {bar}")

        print(f"\n💡 提示: 设置预算: dashboard.set_budget('🍔 餐饮', 3000)")


# ── Demo ──
def main():
    import random
    db = FinanceDashboard()

    # 生成演示数据
    if not db.transactions:
        cat_weights = [
            ("🍔 餐饮", 0.25, 15, 80), ("🏠 房租", 0.20, 2000, 3000),
            ("🚇 交通", 0.10, 5, 50), ("🛒 购物", 0.15, 20, 500),
            ("🎬 娱乐", 0.10, 30, 200), ("📚 学习", 0.08, 10, 100),
            ("🧴 日用", 0.07, 10, 100), ("其他", 0.05, 5, 200),
        ]
        for m in range(6):
            ym = (datetime.now().replace(day=1) - timedelta(days=m * 31))
            for cat, prob, lo, hi in cat_weights:
                if random.random() < prob * 5:  # 平均5笔/月/分类
                    db.add(ym.strftime("%Y-%m-") + f"{random.randint(1,28):02d}",
                           -random.uniform(lo, hi), cat, "demo")
            # 每月一笔工资
            db.add(ym.strftime("%Y-%m-10"), 15000 + random.uniform(-500, 1000), "💰 工资", "月薪")

        db.budgets = {"🍔 餐饮": 3000, "🛒 购物": 2500, "🎬 娱乐": 1500}
        db.save()

    db.report()


if __name__ == "__main__":
    main()
