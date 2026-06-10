"use client";

import React, { useState, useMemo, useEffect } from "react";
import { 
  TrendingUp, 
  Wallet, 
  PieChart, 
  Search, 
  Info,
  ArrowUpRight,
  Banknote,
  Target,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertTriangle
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "../../../components/ui/card";
import { Input } from "../../../components/ui/input";
import { Playfair_Display } from "next/font/google";

const playfair = Playfair_Display({ subsets: ["latin"], weight: ["700"] });

interface CountyFinance {
  county_name: string;
  fiscal_year: string;
  executive_budget_kshs: number;
  assembly_budget_kshs: number;
  total_budget_kshs: number;
  budgeted_revenue_kshs: number;
  actual_revenue_kshs: number;
  revenue_achievement_pct: string;
  executive_expenditure_kshs: number;
  assembly_expenditure_kshs: number;
  total_expenditure_kshs: number;
}

const formatCurrency = (val: number | string) => {
  const num = typeof val === "string" ? parseFloat(val.replace(/,/g, "")) : val;
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(num || 0);
};

const MetricCard = ({ title, value, subtext, icon: Icon, color }: any) => (
  <Card className="overflow-hidden border-none shadow-sm bg-card transition-all hover:shadow-md">
    <CardContent className="p-6">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">{title}</p>
          <h3 className={`text-2xl font-bold text-foreground ${playfair.className}`}>{value}</h3>
          <p className="text-[10px] text-muted-foreground mt-1 font-medium">{subtext}</p>
        </div>
        <div className={`p-2.5 rounded-xl ${color}`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </CardContent>
  </Card>
);

interface CountyFinanceOverviewProps {
  onViewProjects?: (countyName: string) => void;
}

export default function CountyFinanceOverview({ onViewProjects }: CountyFinanceOverviewProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [expandedCounty, setExpandedCounty] = useState<string | null>(null);
  const [finances, setFinances] = useState<CountyFinance[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchFinances() {
      setLoading(true);
      setError(null);
      try {
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${baseUrl}/finances`);
        if (!res.ok) throw new Error("Failed to fetch finance data");
        const data = await res.json();
        setFinances(data);
      } catch (err: any) {
        console.error(err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchFinances();
  }, []);

  // Process summary stats for the national overview
  const summary = useMemo(() => {
    const totalBudget = finances.reduce((acc, curr) => acc + (Number(curr.total_budget_kshs) || 0), 0);
    const totalExp = finances.reduce((acc, curr) => acc + (Number(curr.total_expenditure_kshs) || 0), 0);
    
    return {
      totalBudget,
      totalExp,
      countiesCount: finances.length
    };
  }, [finances]);

  // Merge and filter data for the individual county cards
  const countyMetrics = useMemo(() => {
    return finances
      .filter(c => c.county_name.toLowerCase().includes(searchTerm.toLowerCase()))
      .map(c => ({
        name: c.county_name,
        totalBudget: Number(c.total_budget_kshs) || 0,
        totalExpenditure: Number(c.total_expenditure_kshs) || 0,
        revenueAchievement: c.revenue_achievement_pct || "0%",
        actualRevenue: Number(c.actual_revenue_kshs) || 0,
        budgetedRevenue: Number(c.budgeted_revenue_kshs) || 0,
        execBudget: Number(c.executive_budget_kshs) || 0,
        assembBudget: Number(c.assembly_budget_kshs) || 0,
        execExp: Number(c.executive_expenditure_kshs) || 0,
        assembExp: Number(c.assembly_expenditure_kshs) || 0,
        fiscalYear: c.fiscal_year
      }));
  }, [finances, searchTerm]);

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Header section with Search */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className={`text-3xl font-bold text-foreground tracking-tight ${playfair.className}`}>Citizen Budget Portal</h2>
          <p className="text-sm text-muted-foreground mt-1">Transparent tracking of how public funds are allocated and utilized.</p>
        </div>
        <div className="relative w-full md:w-80">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            placeholder="Search your county..." 
            className="pl-10 rounded-full bg-card shadow-sm border-input"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {/* National Totals Section */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard 
          title="Total National Budget" 
          value={formatCurrency(summary.totalBudget)} 
          subtext="Approved allocations across all counties"
          icon={Wallet}
          color="bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400"
        />
        <MetricCard 
          title="Total Expenditure" 
          value={formatCurrency(summary.totalExp)} 
          subtext="Actual cumulative spending across reporting counties"
          icon={TrendingUp}
          color="bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400"
        />
        <MetricCard 
          title="Reporting Counties" 
          value={summary.countiesCount} 
          subtext="Active financial performance datasets"
          icon={PieChart}
          color="bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400"
        />
      </div>

      {/* Contextual Educational Note */}
      <div className="bg-[#C5A059]/10 border border-[#C5A059]/20 rounded-2xl p-4 flex gap-3 items-center text-sm text-[#8a6d3b] dark:text-[#C5A059]">
        <div className="p-1.5 rounded-full bg-[#C5A059]/20 shrink-0">
          <Info className="w-4 h-4" />
        </div>
        <p>Public financial records help track how public funds are distributed between <b>legislative oversight</b> and <b>executive implementation</b>.</p>
      </div>

      {/* Interactive County Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {loading ? (
          <div className="col-span-full py-20 flex flex-col items-center justify-center text-center">
            <Loader2 className="h-8 w-8 animate-spin text-[#C5A059] mb-4" />
            <p className="text-muted-foreground font-medium italic">Fetching latest financial telemetry...</p>
          </div>
        ) : error ? (
          <div className="col-span-full py-20 flex flex-col items-center justify-center text-center text-rose-500 bg-rose-50/50 rounded-3xl border border-dashed border-rose-200">
            <AlertTriangle className="w-12 h-12 mb-4" />
            <h3 className="text-lg font-bold">Connection Error</h3>
            <p className="text-sm max-w-xs">Unable to reach the budget server. Please verify the API is active.</p>
          </div>
        ) : countyMetrics.length === 0 ? (
          <div className="col-span-full text-center py-20 border-2 border-dashed rounded-3xl bg-muted/20">
            <p className="text-muted-foreground font-medium">No counties match your search criteria.</p>
          </div>
        ) : (
          <AnimatePresence mode="popLayout">
          {countyMetrics.map((county) => (
            <motion.div
              key={county.name}
              layout
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={{ duration: 0.2 }}
            >
              <Card 
                onClick={() => setExpandedCounty(expandedCounty === county.name ? null : county.name)}
                className={`h-full border-none shadow-sm hover:shadow-md transition-all bg-card overflow-hidden group cursor-pointer ring-1 ring-foreground/5 ${
                  expandedCounty === county.name ? "ring-[#C5A059]/50 shadow-lg" : ""
                }`}
              >
                <div className="h-1.5 w-full bg-muted">
                </div>
                <CardHeader className="pb-2">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className={`text-xl font-bold ${playfair.className}`}>{county.name}</CardTitle>
                      <CardDescription className="text-xs uppercase tracking-widest">Fiscal Year {county.fiscalYear}</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Finance Breakdown */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1.5">
                        <Banknote className="w-3.5 h-3.5" /> Approved Budget
                      </span>
                      <p className="font-semibold text-foreground">{formatCurrency(county.totalBudget)}</p>
                    </div>
                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1.5">
                        <ArrowUpRight className="w-3.5 h-3.5" /> Actual Spent
                      </span>
                      <p className="font-semibold text-foreground">{formatCurrency(county.totalExpenditure)}</p>
                    </div>
                  </div>

                  {/* Revenue Achievement Indicator */}
                  <div className="pt-4 border-t border-border/50">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-[10px] uppercase font-bold text-muted-foreground flex items-center gap-1.5">
                        <Target className="w-3.5 h-3.5" /> Local Revenue Collection
                      </span>
                      <span className={`text-xs font-bold ${parseInt(county.revenueAchievement) >= 100 ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {county.revenueAchievement} of Target
                      </span>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-1000 ${parseInt(county.revenueAchievement) >= 100 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                          style={{ width: `${Math.min(parseInt(county.revenueAchievement), 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-muted-foreground whitespace-nowrap">
                        {formatCurrency(county.actualRevenue)}
                      </span>
                    </div>
                  </div>

                  {/* Expanded Details Section */}
                  <AnimatePresence>
                    {expandedCounty === county.name && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="pt-6 border-t border-dashed space-y-4">
                          <h4 className="text-xs font-bold uppercase tracking-widest text-[#C5A059]">Budget Allocation Breakdown</h4>
                          
                          <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-3">
                              <p className="text-[10px] font-bold text-muted-foreground uppercase">County Executive</p>
                              <div className="space-y-1">
                                <p className="text-[10px] text-muted-foreground">Allocation</p>
                                <p className="text-sm font-medium">{formatCurrency(county.execBudget)}</p>
                              </div>
                              <div className="space-y-1">
                                <p className="text-[10px] text-muted-foreground">Actual Spent</p>
                                <p className="text-sm font-medium text-emerald-600">
                                  {formatCurrency(county.execExp)}
                                </p>
                              </div>
                            </div>

                            <div className="space-y-3">
                              <p className="text-[10px] font-bold text-muted-foreground uppercase">County Assembly</p>
                              <div className="space-y-1">
                                <p className="text-[10px] text-muted-foreground">Allocation</p>
                                <p className="text-sm font-medium">{formatCurrency(county.assembBudget)}</p>
                              </div>
                              <div className="space-y-1">
                                <p className="text-[10px] text-muted-foreground">Actual Spent</p>
                                <p className="text-sm font-medium text-amber-600">
                                  {formatCurrency(county.assembExp)}
                                </p>
                              </div>
                            </div>
                          </div>

                          <div className="bg-muted/30 p-3 rounded-lg flex items-center justify-between">
                            <span className="text-[10px] font-bold text-muted-foreground">INTERACTIVE ANALYSIS</span>
                            <span 
                              className="text-[10px] font-bold text-[#C5A059] flex items-center gap-1 cursor-pointer hover:underline"
                              onClick={(e) => {
                                e.stopPropagation();
                                onViewProjects?.(county.name);
                              }}
                            >
                              View Detailed Projects <ArrowUpRight className="w-3 h-3" />
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  <div className="flex justify-center pt-2">
                    {expandedCounty === county.name ? (
                      <ChevronUp className="w-4 h-4 text-muted-foreground/40" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-muted-foreground/40 group-hover:text-[#C5A059] transition-colors" />
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}