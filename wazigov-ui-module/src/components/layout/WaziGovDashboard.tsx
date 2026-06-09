"use client";

import React, { useState, useEffect } from "react";
import { Playfair_Display, Inter } from "next/font/google";
import { Search, Sun, Moon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CountyDataExplorer from "@/src/components/dashboard/CountyDataExplorer";
import Sidebar from "@/src/components/layout/Sidebar";
import AnalyticsGrid from "@/src/components/dashboard/AnalyticsGrid";
import AuditForensicsTable from "@/src/components/dashboard/AuditForensicsTable";

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
      <Sidebar />

      {/* Main Container */}
      <div className="flex-1 md:ml-64 flex flex-col min-h-screen transition-all duration-300 w-full relative">
        {/* Top Header */}
        <header className="fixed top-0 right-0 left-0 md:left-64 h-16 bg-card/80 backdrop-blur-md border-b z-30 pl-16 pr-6 md:px-8 flex items-center justify-between transition-all duration-300">
          {/* Search */}
          <div className="relative w-full max-w-md hidden sm:flex items-center">
            <Search className="absolute left-4 w-4 h-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search projects, audits, or counties..."
              className="pl-10 bg-muted/50 border-input h-10 w-full rounded-full focus-visible:ring-1 focus-visible:ring-ring focus-visible:ring-offset-0 transition-all shadow-sm"
            />
          </div>

          {/* Mobile Search */}
          <div className="sm:hidden flex items-center">
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

            {/* Profile – uses accent colour */}
            <div className="w-9 h-9 rounded-full bg-accent/20 border border-accent/40 flex items-center justify-center text-accent font-bold text-sm cursor-pointer shadow-sm">
              OG
            </div>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 pt-24 pb-12 px-6 lg:px-12 overflow-x-hidden">
          <Tabs defaultValue="detailed-analytics" className="w-full max-w-6xl mx-auto">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-6 mb-8">
              <div className="space-y-1.5">
                <h1 className={`text-3xl font-bold text-foreground tracking-tight ${playfair.className}`}>
                  WaziGov Intelligence
                </h1>
                <p className="text-sm text-muted-foreground max-w-lg">
                  Real‑time county budget telemetry cross‑referenced with OAG findings and CoB expenditure signals.
                </p>
              </div>

              <TabsList className="bg-muted p-1 rounded-xl h-auto self-start sm:self-auto border">
                <TabsTrigger
                  value="overview-summary"
                  className="rounded-lg px-4 py-2 text-sm font-medium data-[state=active]:bg-card data-[state=active]:text-accent data-[state=active]:shadow-sm transition-all"
                >
                  Overview Summary
                </TabsTrigger>
                <TabsTrigger
                  value="detailed-analytics"
                  className="rounded-lg px-4 py-2 text-sm font-medium data-[state=active]:bg-card data-[state=active]:text-accent data-[state=active]:shadow-sm transition-all"
                >
                  Detailed Analytics
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="overview-summary" className="mt-0 outline-none animate-in fade-in-50 duration-500 flex flex-col gap-6">
              <AnalyticsGrid />
              <div>
                <h3 className={`text-xl font-bold text-foreground mb-4 ${playfair.className}`}>
                  Audit Forensics
                </h3>
                <AuditForensicsTable />
              </div>
            </TabsContent>

            <TabsContent value="detailed-analytics" className="mt-0 outline-none animate-in fade-in-50 duration-500">
              <div className="bg-card rounded-3xl shadow-sm border overflow-hidden">
                <CountyDataExplorer />
              </div>
            </TabsContent>
          </Tabs>
        </main>
      </div>
    </div>
  );
}