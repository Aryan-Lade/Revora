import {
  ArrowDownRight,
  ArrowUpRight,
  CircleDollarSign,
  CreditCard,
  TrendingUp,
  Wallet,
} from "lucide-react";

const revenueData = {
  totalRevenue: 1248500,
  recoveredRevenue: 482650,
  revenueAtRisk: 318400,
  lostRevenue: 96750,
  previousRevenue: 1126400,
  previousRecovered: 391200,
  previousAtRisk: 352100,
};

const formatCurrency = (value) => {
  if (value >= 10000000) {
    return `₹${(value / 10000000).toFixed(2)}Cr`;
  }

  if (value >= 100000) {
    return `₹${(value / 100000).toFixed(2)}L`;
  }

  if (value >= 1000) {
    return `₹${(value / 1000).toFixed(1)}K`;
  }

  return `₹${value.toLocaleString("en-IN")}`;
};

const calculatePercentage = (current, previous) => {
  if (!previous) return 0;

  return ((current - previous) / previous) * 100;
};

const getPercentageColor = (value, inverse = false) => {
  const positive = inverse ? value < 0 : value > 0;

  return positive
    ? "text-emerald-400"
    : value === 0
      ? "text-slate-400"
      : "text-red-400";
};

const RevenueOverview = () => {
  const revenueGrowth = calculatePercentage(
    revenueData.totalRevenue,
    revenueData.previousRevenue
  );

  const recoveryGrowth = calculatePercentage(
    revenueData.recoveredRevenue,
    revenueData.previousRecovered
  );

  const riskChange = calculatePercentage(
    revenueData.revenueAtRisk,
    revenueData.previousAtRisk
  );

  const recoveryRate =
    revenueData.totalRevenue > 0
      ? (revenueData.recoveredRevenue / revenueData.totalRevenue) * 100
      : 0;

  const cards = [
    {
      title: "Total Revenue",
      value: formatCurrency(revenueData.totalRevenue),
      change: revenueGrowth,
      icon: CircleDollarSign,
      description: "Processed revenue",
      iconBg: "bg-blue-500/10",
      iconColor: "text-blue-400",
    },
    {
      title: "Recovered Revenue",
      value: formatCurrency(revenueData.recoveredRevenue),
      change: recoveryGrowth,
      icon: Wallet,
      description: "Revenue recovered by Revora",
      iconBg: "bg-emerald-500/10",
      iconColor: "text-emerald-400",
    },
    {
      title: "Revenue At Risk",
      value: formatCurrency(revenueData.revenueAtRisk),
      change: riskChange,
      inverse: true,
      icon: TrendingUp,
      description: "Requires intervention",
      iconBg: "bg-amber-500/10",
      iconColor: "text-amber-400",
    },
    {
      title: "Recovery Rate",
      value: `${recoveryRate.toFixed(1)}%`,
      change: recoveryGrowth,
      icon: CreditCard,
      description: "Recovery efficiency",
      iconBg: "bg-violet-500/10",
      iconColor: "text-violet-400",
    },
  ];

  return (
    <section className="w-full">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-white">
            Revenue Overview
          </h2>

          <p className="mt-1 text-sm text-slate-400">
            Monitor revenue performance and recovery impact
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.6)]" />

          <span className="text-xs font-medium text-slate-400">
            Live data
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => {
          const Icon = card.icon;

          const changeColor = getPercentageColor(
            card.change,
            card.inverse
          );

          const isPositive = card.inverse
            ? card.change < 0
            : card.change > 0;

          return (
            <div
              key={card.title}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-[#111827] p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/20 hover:bg-[#151e2d]"
            >
              <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-white/[0.02] blur-2xl transition-all duration-300 group-hover:bg-white/[0.04]" />

              <div className="relative">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-400">
                      {card.title}
                    </p>

                    <h3 className="mt-3 text-2xl font-bold tracking-tight text-white">
                      {card.value}
                    </h3>
                  </div>

                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl ${card.iconBg}`}
                  >
                    <Icon
                      size={19}
                      strokeWidth={2}
                      className={card.iconColor}
                    />
                  </div>
                </div>

                <div className="mt-5 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    {isPositive ? (
                      <ArrowUpRight
                        size={15}
                        className={changeColor}
                      />
                    ) : (
                      <ArrowDownRight
                        size={15}
                        className={changeColor}
                      />
                    )}

                    <span
                      className={`text-xs font-semibold ${changeColor}`}
                    >
                      {Math.abs(card.change).toFixed(1)}%
                    </span>

                    <span className="text-xs text-slate-500">
                      vs last period
                    </span>
                  </div>
                </div>

                <p className="mt-2 text-xs text-slate-500">
                  {card.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-2xl border border-white/10 bg-[#111827] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">
                Recovery Impact
              </p>

              <p className="mt-2 text-lg font-semibold text-white">
                {formatCurrency(revenueData.recoveredRevenue)}
              </p>
            </div>

            <div className="rounded-xl bg-emerald-500/10 p-2.5">
              <Wallet
                size={18}
                className="text-emerald-400"
              />
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                Recovered from at-risk revenue
              </span>

              <span className="font-medium text-emerald-400">
                {revenueData.revenueAtRisk > 0
                  ? (
                      (revenueData.recoveredRevenue /
                        revenueData.revenueAtRisk) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </span>
            </div>

            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-emerald-400 transition-all duration-700"
                style={{
                  width: `${Math.min(
                    (revenueData.recoveredRevenue /
                      Math.max(revenueData.revenueAtRisk, 1)) *
                      100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#111827] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">
                Revenue Exposure
              </p>

              <p className="mt-2 text-lg font-semibold text-white">
                {formatCurrency(revenueData.revenueAtRisk)}
              </p>
            </div>

            <div className="rounded-xl bg-amber-500/10 p-2.5">
              <TrendingUp
                size={18}
                className="text-amber-400"
              />
            </div>
          </div>

          <div className="mt-5">
            <div className="mb-2 flex items-center justify-between text-xs">
              <span className="text-slate-500">
                At-risk vs total revenue
              </span>

              <span className="font-medium text-amber-400">
                {revenueData.totalRevenue > 0
                  ? (
                      (revenueData.revenueAtRisk /
                        revenueData.totalRevenue) *
                      100
                    ).toFixed(1)
                  : 0}
                %
              </span>
            </div>

            <div className="h-2 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-amber-400 transition-all duration-700"
                style={{
                  width: `${Math.min(
                    (revenueData.revenueAtRisk /
                      Math.max(revenueData.totalRevenue, 1)) *
                      100,
                    100
                  )}%`,
                }}
              />
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-white/10 bg-[#111827] p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-slate-400">
                Net Revenue Health
              </p>

              <p className="mt-2 text-lg font-semibold text-white">
                {formatCurrency(
                  revenueData.totalRevenue -
                    revenueData.revenueAtRisk -
                    revenueData.lostRevenue
                )}
              </p>
            </div>

            <div className="rounded-xl bg-blue-500/10 p-2.5">
              <CircleDollarSign
                size={18}
                className="text-blue-400"
              />
            </div>
          </div>

          <div className="mt-5 flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-800">
              <div
                className="h-full rounded-full bg-blue-400 transition-all duration-700"
                style={{
                  width: `${Math.min(
                    ((revenueData.totalRevenue -
                      revenueData.revenueAtRisk) /
                      Math.max(revenueData.totalRevenue, 1)) *
                      100,
                    100
                  )}%`,
                }}
              />
            </div>

            <span className="text-xs font-medium text-blue-400">
              {(
                ((revenueData.totalRevenue -
                  revenueData.revenueAtRisk) /
                  Math.max(revenueData.totalRevenue, 1)) *
                100
              ).toFixed(1)}
              %
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default RevenueOverview;