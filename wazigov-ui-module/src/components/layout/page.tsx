import React from "react";
import CountyFinanceOverview from "@/src/components/dashboard/CountyFinanceOverview";
import Sidebar from "@/src/components/layout/Sidebar";

export default function FinancePage() {
  return (
    <div className="flex min-h-screen bg-[#F9F8F4] dark:bg-background">
      {/* Sidebar logic is simplified here for standalone route display */}
      <Sidebar activeTab="finance" setActiveTab={() => {}} />
      
      <main className="flex-1 md:ml-64 p-6 lg:p-12 transition-all duration-300">
        <div className="max-w-6xl mx-auto pt-10">
          <CountyFinanceOverview />
        </div>
      </main>
    </div>
  );
}