// components/analytics-grid.tsx
"use client";
import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Banknote, Target, AlertOctagon, TrendingUp, TrendingDown } from "lucide-react";

export default function AnalyticsGrid() {
  const metrics = [
    {
      title: "Total Budget Tracked",
      value: "KES 142.5B",
      change: "+12.4%",
      trendStatus: "good",
      trendIcon: "up",
      timeframe: "from last quarter",
      icon: Banknote,
    },
    {
      title: "Extraction Accuracy Coefficient",
      value: "98.2%",
      change: "+1.2%",
      trendStatus: "good",
      trendIcon: "up",
      timeframe: "from last quarter",
      icon: Target,
    },
    {
      title: "Flagged Inconsistencies",
      value: "342",
      change: "-5.4%",
      trendStatus: "good",
      trendIcon: "down",
      timeframe: "from last quarter",
      icon: AlertOctagon,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
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
              <metric.icon className="w-4 h-4 text-[#C5A059]" />
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