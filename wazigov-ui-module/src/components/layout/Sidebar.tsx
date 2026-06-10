"use client";

import React, { useState } from "react";
import {
  LayoutDashboard,
  Map,
  Wallet,
  ShieldAlert,
  Menu,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

const navItems = [
  { name: "Overview", icon: LayoutDashboard, id: "overview" },
  { name: "County Explorer", icon: Map, id: "explorer" },
  { name: "Finance Portal", icon: Wallet, id: "finance" },
  { name: "Audit Forensics", icon: ShieldAlert, id: "audit" },
];

interface SidebarProps {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

export default function Sidebar({ activeTab, setActiveTab }: SidebarProps) {
  const [isMobileOpen, setIsMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle button – uses card background */}
      <div className="md:hidden fixed top-3 left-4 z-50">
        <Button
          variant="outline"
          size="icon"
          onClick={() => setIsMobileOpen(!isMobileOpen)}
          className="bg-card/80 backdrop-blur-md border shadow-sm"
        >
          {isMobileOpen ? (
            <X className="w-5 h-5" />
          ) : (
            <Menu className="w-5 h-5" />
          )}
          <span className="sr-only">Toggle Sidebar</span>
        </Button>
      </div>

      {/* Mobile overlay – semi‑transparent foreground */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-foreground/20 backdrop-blur-sm z-40 md:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-screen w-64 border-r bg-card z-40 transition-transform duration-300 ease-in-out md:translate-x-0 ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Logo area */}
        <div className="flex h-16 items-center px-6 border-b mt-14 md:mt-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-accent flex items-center justify-center shadow-sm">
              <span className="text-accent-foreground font-black text-sm tracking-tighter">
                WG
              </span>
            </div>
            <span className="font-bold text-xl text-foreground tracking-tight">
              WaziGov
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex flex-col gap-2 p-4 mt-2">
          {navItems.map((item) => {
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  setActiveTab(item.id);
                  setIsMobileOpen(false);
                }}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 cursor-pointer text-left w-full ${
                  isActive
                    ? "bg-muted text-foreground font-semibold shadow-sm"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground font-medium"
                }`}
              >
                <item.icon className="w-5 h-5 shrink-0" />
                <span className="text-sm">{item.name}</span>
              </button>
            );
          })}
        </nav>
      </aside>
    </>
  );
}