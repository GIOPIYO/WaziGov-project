// components/analytics-grid.tsx
"use client";
import React, { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Banknote, AlertOctagon, TrendingUp, TrendingDown, Loader2, Target, Activity } from "lucide-react";

export default function AnalyticsGrid() {
  const [data, setData] = useState({
    totalBudget: 0,
    flaggedCount: 0,
    totalProjects: 0,
    avgImplementation: 0,
    loading: true,
    error: false,
  });

  useEffect(() => {
    async function fetchStats() {
      try {
        // Fetch up to 1000 projects to calculate aggregate stats
        const res = await fetch("http://localhost:8000/projects?limit=1000");
        if (!res.ok) throw new Error("Failed to fetch");
        const projects = await res.json();

        let totalBudget = 0;
        let flaggedCount = 0;
        let totalProjects = projects.length;
        let totalImplementation = 0;
        let validImplementationCount = 0;

        projects.forEach((p: any) => {
          if (p.contract_sum_kshs) totalBudget += p.contract_sum_kshs;
          if (
            p.oag_status === "FLAGGED" ||
            p.triangulation_verdict === "CORROBORATED_PROJECT_RISK"
          ) {
            flaggedCount += 1;
          }
          if (p.implementation_pct !== undefined && p.implementation_pct !== null) {
            totalImplementation += p.implementation_pct;
            validImplementationCount += 1;
          }
        });

        const avgImplementation = validImplementationCount > 0 ? totalImplementation / validImplementationCount : 0;

        setData({
          totalBudget,
          flaggedCount,
          totalProjects,
          avgImplementation,
          loading: false,
          error: false,
        });
      } catch (err) {
        console.error(err);
        setData((prev) => ({ ...prev, loading: false, error: true }));
      }
    }

    fetchStats();
  }, []);

  const formatCurrencyCompact = (amount: number) => {
    if (amount >= 1e9) return `KES ${(amount / 1e9).toFixed(1)}B`;
    if (amount >= 1e6) return `KES ${(amount / 1e6).toFixed(1)}M`;
    return `KES ${amount.toLocaleString()}`;
  };

  const metrics = [
    {
      title: "Projects Monitored",
      value: data.loading ? "..." : data.totalProjects.toLocaleString(),
      change: "Active in DB",
      trendStatus: "good",
      trendIcon: "up",
      timeframe: "from current records",
      icon: Target,
    },
    {
      title: "Total Budget Tracked",
      value: data.loading ? "..." : formatCurrencyCompact(data.totalBudget),
      change: "Live DB sync",
      trendStatus: "good",
      trendIcon: "up",
      timeframe: "from current records",
      icon: Banknote,
    },
    {
      title: "Avg. Implementation",
      value: data.loading ? "..." : `${data.avgImplementation.toFixed(1)}%`,
      change: "Reported Progress",
      trendStatus: "good",
      trendIcon: "up",
      timeframe: "across all projects",
      icon: Activity,
    },
    {
      title: "Flagged Inconsistencies",
      value: data.loading ? "..." : data.flaggedCount.toString(),
      change: "Needs review",
      trendStatus: "bad",
      trendIcon: "down",
      timeframe: "detected issues",
      icon: AlertOctagon,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
      {metrics.map((metric, idx) => (
        <Card
          key={idx}
          className="bg-white border border-zinc-200 shadow-sm rounded-2xl transition-all duration-300 hover:shadow-md hover:border-[#C5A059]/30 cursor-pointer"
        >
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm font-semibold text-zinc-500 tracking-wider uppercase">
              {metric.title}
            </CardTitle>
            <div className="w-9 h-9 rounded-lg bg-zinc-100 flex items-center justify-center">
              {data.loading ? (
                <Loader2 className="w-4 h-4 text-zinc-400 animate-spin" />
              ) : (
                <metric.icon className="w-4 h-4 text-[#C5A059]" />
              )}
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-[#1a1a1a] font-['Playfair_Display']">
              {metric.value}
            </div>
            <p className="text-xs text-zinc-500 mt-2 flex items-center gap-1 font-medium">
              <span
                className={`inline-flex items-center gap-0.5 ${
                  metric.trendStatus === "good"
                    ? "text-emerald-600"
                    : "text-rose-600"
                }`}
              >
                {metric.trendIcon === "up" ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                {metric.change}
              </span>{" "}
              {metric.timeframe}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}