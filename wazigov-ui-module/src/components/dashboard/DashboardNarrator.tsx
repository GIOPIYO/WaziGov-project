"use client";

import React from "react";
import { Volume2, VolumeX } from "lucide-react";
import { useScreenReader } from "@/hooks/useScreenReader";

// Explicit TypeScript shape for the project data elements coming from your screen state
interface ProjectData {
  id: string;
  title: string;
  county: string;
  year: string;
  contractSum?: string;
  amountPaid?: string;
  progress?: number;
  cobStatus?: string;
  cobDetail?: string;
  oagStatus?: string;
  oagDetail?: string;
}

interface DashboardNarratorProps {
  activeCounty: string;
  projects: ProjectData[];
}

export default function DashboardNarrator({ activeCounty, projects }: DashboardNarratorProps) {
  const { speak, stop, isSpeaking } = useScreenReader();

  const handleNarrateData = () => {
    if (!projects || projects.length === 0) {
      speak(`There are currently no active project metrics recorded for ${activeCounty} County.`);
      return;
    }

    // Build the structural introductory phrase dynamically
    let narrative = `Displaying telemetry summary for ${activeCounty} County, containing ${projects.length} project records. `;

    // Parse every real object inside your live active state array
    projects.forEach((project, idx) => {
      narrative += `Item ${idx + 1}: ${project.title}. `;
      
      if (project.contractSum) {
        // Humanize currency markings so they read as spoken phrases instead of raw characters
        const formattedSum = project.contractSum
          .replace("Ksh", "Kenyan Shillings")
          .replace("KES", "Kenyan Shillings");
        narrative += `The designated contract sum is ${formattedSum}. `;
      }

      if (project.progress !== undefined) {
        narrative += `Current execution implementation is at ${project.progress} percent. `;
      }

      // Automatically evaluate state warning flags and parse details natively if flagged
      if (project.oagStatus === "FLAGGED") {
        narrative += `Warning. This project profile reflects a verified project risk indicator from the Office of the Auditor General. Observation note indicates: ${project.oagDetail || "Stalled completion due to substandard materials used."} `;
      }

      narrative += " "; // Structural brief pause between mapped list files
    });

    speak(narrative);
  };

  return (
    <div className="flex items-center justify-end">
      {!isSpeaking ? (
        <button
          onClick={handleNarrateData}
          className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-zinc-900 border border-zinc-800 text-white hover:bg-zinc-800 transition shadow-sm active:scale-95"
          aria-label={`Read summary for ${activeCounty}`}
        >
          <Volume2 className="w-4 h-4 text-[#C5A059]" />
          Listen to {activeCounty} Overview
        </button>
      ) : (
        <button
          onClick={stop}
          className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2.5 rounded-xl bg-rose-600 border border-rose-700 text-white hover:bg-rose-700 transition shadow-sm animate-pulse"
          aria-label="Stop playback narration"
        >
          <VolumeX className="w-4 h-4" />
          Stop Audio Narrator
        </button>
      )}
    </div>
  );
}