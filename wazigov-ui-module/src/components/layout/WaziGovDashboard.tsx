"use client";

import React, { useState, useEffect } from "react";
import { Playfair_Display, Inter } from "next/font/google";
import { Search, Sun, Moon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import CountyDataExplorer from "@/src/components/dashboard/CountyDataExplorer";
import Sidebar from "@/src/components/layout/Sidebar";
import AnalyticsGrid from "@/src/components/dashboard/AnalyticsGrid";
import AuditForensicsTable from "@/src/components/dashboard/AuditForensicsTable";
import CountyFinanceOverview from "@/src/components/dashboard/CountyFinanceOverview";

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
  style: ["normal", "italic"],
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
});

export default function WaziGovDashboard() {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [searchQuery, setSearchQuery] = useState("");

  useEffect(() => {
    const isDark = document.documentElement.classList.contains("dark");
    setIsDarkMode(isDark);
  }, []);

  const toggleTheme = () => {
    if (isDarkMode) {
      document.documentElement.classList.remove("dark");
      setIsDarkMode(false);
    } else {
      document.documentElement.classList.add("dark");
      setIsDarkMode(true);
    }
  };

  return (
    <div className={`flex min-h-screen bg-background ${inter.className}`}>
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

      {/* Main Container */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen transition-all duration-300 w-full relative">
        {/* Top Header */}
        <header className="fixed top-0 right-0 left-0 md:left-64 h-16 bg-card/80 backdrop-blur-md border-b z-30 pl-16 pr-6 md:px-8 flex items-center justify-between transition-all duration-300">
          {/* Search */}
          <div className={`relative w-full max-w-md hidden sm:flex items-center transition-opacity duration-300 ${activeTab === "explorer" ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
            <Search className="absolute left-4 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search projects, audits, or counties..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-muted/50 border-input h-10 w-full rounded-full focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-0 transition-all shadow-sm"
            />
          </div>

          {/* Mobile Search */}
          <div className={`sm:hidden flex items-center transition-opacity duration-300 ${activeTab === "explorer" ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
            <Button variant="ghost" size="icon" className="rounded-full">
              <Search className="w-5 h-5" />
            </Button>
          </div>

          <div className="flex items-center gap-4">
            {/* Theme Toggle */}
            <Button
              variant="outline"
              size="icon"
              onClick={toggleTheme}
              className="rounded-full border"
            >
              {isDarkMode ? (
                <Moon className="w-[1.2rem] h-[1.2rem]" />
              ) : (
                <Sun className="w-[1.2rem] h-[1.2rem]" />
              )}
              <span className="sr-only">Toggle theme</span>
            </Button>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 pt-24 pb-12 px-6 lg:px-12 overflow-x-hidden">
          <div className="w-full max-w-6xl mx-auto flex flex-col gap-6">
            <div className="space-y-1.5 mb-2">
              <h1 className={`text-3xl font-bold text-foreground tracking-tight ${playfair.className}`}>
                WaziGov Intelligence
              </h1>
              <p className="text-sm text-muted-foreground max-w-lg">
                Real‑time county budget telemetry cross‑referenced with OAG findings and CoB expenditure signals.
              </p>
            </div>

            {activeTab === "overview" && (
              <div className="animate-in fade-in-50 duration-500 flex flex-col gap-6">
                <AnalyticsGrid />
                <div>
                  <h3 className={`text-xl font-bold text-foreground mb-4 ${playfair.className}`}>
                    High-Risk Project Watchlist
                  </h3>
                  <AuditForensicsTable />
                </div>
              </div>
            )}

            {activeTab === "explorer" && (
              <div className="bg-card rounded-3xl shadow-sm border overflow-hidden animate-in fade-in-50 duration-500">
                <CountyDataExplorer searchQuery={searchQuery} />
              </div>
            )}

            {activeTab === "finance" && (
              <CountyFinanceOverview />
            )}

            {activeTab === "audit" && (
              <div className="animate-in fade-in-50 duration-500">
                <h3 className={`text-xl font-bold text-foreground mb-4 ${playfair.className}`}>
                  Detailed Audit Forensics
                </h3>
                <AuditForensicsTable />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}