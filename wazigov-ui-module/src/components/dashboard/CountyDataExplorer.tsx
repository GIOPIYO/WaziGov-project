"use client";

import { motion, AnimatePresence } from "motion/react";
import { geoMercator, geoPath } from "d3-geo";
import React, { useState, useMemo } from "react";
import kenyaGeoData from "/workspaces/wazigov-ui-/gadm41_KEN_1.json";

import {
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  MapPin,
  Activity,
  FileText,
  BadgeCent,
} from "lucide-react";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

// --- Types (unchanged) ---
type RiskStatus = "OK" | "FLAGGED" | "CLEAN_AUDIT";
type TriangulationVerdict =
  | "CORROBORATED_PROJECT_RISK"
  | "VERIFIED_COMPLIANT"
  | "PENDING_REVIEW";

interface ProjectData {
  project_id: string;
  county: string;
  financial_year: string;
  project_name: string;
  contract_sum_kshs: number;
  amount_paid_kshs: number;
  implementation_pct: number;
  source_cob: boolean;
  source_oag: boolean;
  dev_threshold_breach: boolean;
  cob_signal: {
    status: RiskStatus;
    dev_pct: number;
    metric: string;
  };
  oag_forensics: {
    status: RiskStatus;
    findings: string[];
    risk_types: string[];
    match_confidence: number;
  };
  triangulation_verdict: TriangulationVerdict;
}

// --- Mock Data (unchanged) ---
const MOCK_DATA: ProjectData[] = [
  {
    project_id: "bari-premises55",
    county: "Baringo",
    financial_year: "2023/2024",
    project_name: "Premises 55 Construction",
    contract_sum_kshs: 50204385.0,
    amount_paid_kshs: 50204385.0,
    implementation_pct: 100.0,
    source_cob: true,
    source_oag: true,
    dev_threshold_breach: false,
    cob_signal: {
      status: "OK",
      dev_pct: 63.0,
      metric: "Development expenditure at 63.0% of total expenditure",
    },
    oag_forensics: {
      status: "FLAGGED",
      findings: [
        "Stalled Completion due to substandard materials used by M/S Apex Builders.",
      ],
      risk_types: ["INCOMPLETE_PROJECT", "PROCUREMENT_BREACH"],
      match_confidence: 88.5,
    },
    triangulation_verdict: "CORROBORATED_PROJECT_RISK",
  },
  {
    project_id: "bari-road-02",
    county: "Baringo",
    financial_year: "2023/2024",
    project_name: "Kabarnet Access Road Upgrade",
    contract_sum_kshs: 120500000.0,
    amount_paid_kshs: 45000000.0,
    implementation_pct: 35.0,
    source_cob: true,
    source_oag: false,
    dev_threshold_breach: true,
    cob_signal: {
      status: "FLAGGED",
      dev_pct: 28.0,
      metric: "Development threshold breach (28.0% < 30% statutory min)",
    },
    oag_forensics: {
      status: "OK",
      findings: ["Ongoing works, within acceptable timelines."],
      risk_types: [],
      match_confidence: 95.0,
    },
    triangulation_verdict: "PENDING_REVIEW",
  },
  {
    project_id: "nai-water-01",
    county: "Nairobi",
    financial_year: "2023/2024",
    project_name: "Embakasi Clean Water Pipeline",
    contract_sum_kshs: 340000000.0,
    amount_paid_kshs: 340000000.0,
    implementation_pct: 100.0,
    source_cob: true,
    source_oag: true,
    dev_threshold_breach: false,
    cob_signal: {
      status: "OK",
      dev_pct: 42.0,
      metric: "Development expenditure at 42.0% of total expenditure",
    },
    oag_forensics: {
      status: "CLEAN_AUDIT",
      findings: ["Project completed to specification. Value for money verified."],
      risk_types: [],
      match_confidence: 99.0,
    },
    triangulation_verdict: "VERIFIED_COMPLIANT",
  },
];

// --- Utilities ---
const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat("en-KE", {
    style: "currency",
    currency: "KES",
    maximumFractionDigits: 0,
  }).format(amount);
};

// --- Subcomponents ---
const ProjectCard = ({ project }: { project: ProjectData }) => {
  const isHighRisk = project.triangulation_verdict === "CORROBORATED_PROJECT_RISK";
  const isCompliant = project.triangulation_verdict === "VERIFIED_COMPLIANT";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      layout
    >
      <Card className="flex flex-col flex-1 overflow-hidden bg-card border rounded-2xl hover:border-foreground/10 transition-colors duration-200 shadow-sm">
        {/* Verdict Banner */}
        <div
          className={`px-5 py-2.5 flex items-center gap-2 border-b ${
            isHighRisk
              ? "bg-rose-50 dark:bg-rose-950/40 border-rose-100 dark:border-rose-900/50 text-rose-700 dark:text-rose-400"
              : isCompliant
              ? "bg-emerald-50 dark:bg-emerald-950/40 border-emerald-100 dark:border-emerald-900/50 text-emerald-700 dark:text-emerald-400"
              : "bg-amber-50 dark:bg-amber-950/40 border-amber-100 dark:border-amber-900/50 text-amber-700 dark:text-amber-400"
          }`}
        >
          {isHighRisk ? (
            <ShieldAlert className="w-4 h-4" />
          ) : isCompliant ? (
            <CheckCircle2 className="w-4 h-4" />
          ) : (
            <Activity className="w-4 h-4" />
          )}
          <span className="text-xs font-bold tracking-wider uppercase">
            {project.triangulation_verdict.replace(/_/g, " ")}
          </span>
        </div>

        <CardHeader className="p-5 pb-0">
          <div className="flex justify-between items-start gap-4">
            <div>
              <CardTitle className="font-semibold text-foreground text-lg leading-tight mb-2">
                {project.project_name}
              </CardTitle>
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground font-medium">
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" /> {project.county}
                </span>
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" /> {project.project_id}
                </span>
                <Badge variant="secondary" className="font-medium pointer-events-none">
                  {project.financial_year}
                </Badge>
              </div>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 flex flex-col gap-6 pt-5">
          {/* Financial Telemetry */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                Contract Sum
              </span>
              <div className="text-base font-semibold text-foreground">
                {formatCurrency(project.contract_sum_kshs)}
              </div>
            </div>
            <div className="space-y-1">
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                Amount Paid
              </span>
              <div className="text-base font-semibold text-foreground">
                {formatCurrency(project.amount_paid_kshs)}
              </div>
            </div>

            <div className="col-span-2 mt-1">
              <div className="flex justify-between text-xs mb-1.5 font-medium">
                <span className="text-muted-foreground">Implementation Progress</span>
                <span className="text-foreground">{project.implementation_pct}%</span>
              </div>
              <div className="w-full bg-muted rounded-full h-1.5 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    project.implementation_pct === 100 ? "bg-emerald-500" : "bg-blue-500"
                  }`}
                  style={{ width: `${project.implementation_pct}%` }}
                />
              </div>
            </div>
          </div>

          {/* Audit Signals Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* COB Signal */}
            <div className="p-3.5 rounded-xl border bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <BadgeCent className="w-3.5 h-3.5" /> CoB Signal
                </span>
                <Badge
                  variant="outline"
                  className={`font-bold uppercase tracking-wider text-[10px] pointer-events-none ${
                    project.cob_signal.status === "OK"
                      ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/30 dark:border-emerald-800 dark:text-emerald-400"
                      : "bg-amber-50 border-amber-200 text-amber-700 dark:bg-amber-900/30 dark:border-amber-800 dark:text-amber-400"
                  }`}
                >
                  {project.cob_signal.status}
                </Badge>
              </div>
              <p className="text-sm font-medium text-foreground leading-snug">
                {project.cob_signal.metric}
              </p>
            </div>

            {/* OAG Forensics */}
            <div className="p-3.5 rounded-xl border bg-muted/50">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> OAG Audit
                </span>
                <Badge
                  variant="outline"
                  className={`font-bold uppercase tracking-wider text-[10px] pointer-events-none ${
                    project.oag_forensics.status === "FLAGGED"
                      ? "bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-900/30 dark:border-rose-800 dark:text-rose-400"
                      : "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-900/30 dark:border-emerald-800 dark:text-emerald-400"
                  }`}
                >
                  {project.oag_forensics.status}
                </Badge>
              </div>
              <p className="text-sm font-medium text-foreground leading-snug line-clamp-2">
                {project.oag_forensics.findings[0]}
              </p>
              {project.oag_forensics.risk_types.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {project.oag_forensics.risk_types.map((risk) => (
                    <Badge
                      variant="secondary"
                      key={risk}
                      className="text-[10px] uppercase font-semibold pointer-events-none"
                    >
                      {risk.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

// Abstracted SVG layout representing a stylized map of Kenya regions
const StylizedKenyaMap = ({
  selectedCounty,
  onSelect,
}: {
  selectedCounty: string;
  onSelect: (c: string) => void;
}) => {
  const width = 400;
  const height = 450;

  // useMemo ensures we only calculate the projection paths once, not on every render
  const { pathGenerator, features } = useMemo(() => {
    // 1. Create a Mercator projection
    // fitSize automatically calculates the perfect scale and center for Kenya!
    const projection = geoMercator().fitSize(
      [width, height],
      kenyaGeoData as any 
    );

    // 2. Create a path generator using that projection
    const generator = geoPath().projection(projection);

    return {
      pathGenerator: generator,
      features: kenyaGeoData.features,
    };
  }, []);

  return (
    <div className="relative w-full aspect-square max-w-[400px] mx-auto">
      <svg
        viewBox={`0 0 400 450`}
        className="w-full h-full drop-shadow-sm filter"
        xmlns="http://www.w3.org/2000/svg"
      >
        {features.map((feature: any) => {
          // The GADM dataset stores the county name in the "NAME_1" property
          const countyName = feature.properties.NAME_1;
          const isSelected = selectedCounty === countyName;
          
          // Generate the SVG 'd' string for this specific county
          const pathD = pathGenerator(feature) || "";

          // Calculate the center point of the county for placing the label
          const centroid = pathGenerator.centroid(feature);
          const labelX = centroid[0];
          const labelY = centroid[1];

          // Determine if we should show a label (optional: you might only want to show labels for selected or active counties if the map gets crowded)
          const hasData = ["Baringo", "Nairobi", "Turkana", "Mombasa", "Kisumu", "Garissa"].includes(countyName);

          return (
            <g
              key={countyName}
              className="group outline-none"
              onClick={() => onSelect(countyName)}
            >
             <path
  d={pathD}
  className={`
    cursor-pointer transition-all duration-300 ease-out outline-none
    /* Crisp borders separating the counties */
    stroke-background dark:stroke-zinc-900 stroke-[1.5px] stroke-linejoin-round
    ${
      isSelected
        ? "fill-blue-500 dark:fill-blue-600"
        : "fill-zinc-100 hover:fill-zinc-200 dark:fill-zinc-800 dark:hover:fill-zinc-700"
    }
  `}
/>
              
              {/* Only render text if valid coordinates exist and we want to highlight it */}
              {!isNaN(labelX) && !isNaN(labelY) && (isSelected || hasData) && (
                <text
                  x={labelX}
                  y={labelY}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className={`
                    text-[9px] font-bold tracking-wide transition-colors duration-200 pointer-events-none select-none
                    ${
                      isSelected
                        ? "fill-white"
                        : "fill-muted-foreground group-hover:fill-foreground"
                    }
                  `}
                >
                  {countyName}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};

// --- Main Container ---
export default function CountyDataExplorer() {
  const [selectedCounty, setSelectedCounty] = useState<string>("Baringo");

  const filteredProjects = MOCK_DATA.filter((p) => p.county === selectedCounty);

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-foreground tracking-tight mb-2">
          Civic Data Explorer
        </h1>
        <p className="text-muted-foreground text-lg max-w-2xl">
          Automated audits and county budget telemetry cross-referencing OAG findings with CoB
          expenditure signals.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12 items-start">
        {/* Left Column: Interactive Map */}
        <div className="lg:col-span-5 flex flex-col gap-6 sticky top-8">
          <div className="bg-muted/50 rounded-3xl border p-6 sm:p-8">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                  <MapPin className="w-5 h-5 text-blue-500" /> Regional Selection
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  Select a region to analyze project telemetry.
                </p>
              </div>
            </div>

            <StylizedKenyaMap selectedCounty={selectedCounty} onSelect={setSelectedCounty} />

            <div className="mt-8 flex justify-center gap-6 text-xs font-semibold text-muted-foreground">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500"></span> Selected
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-muted"></span> Available
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Project Cards */}
        <div className="lg:col-span-7 flex flex-col min-h-[500px]">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-foreground">
              {selectedCounty} County Projects
            </h2>
            <span className="px-3 py-1 bg-muted text-muted-foreground font-semibold text-sm rounded-full">
              {filteredProjects.length} Record{filteredProjects.length !== 1 && "s"}
            </span>
          </div>

          <div className="flex flex-col gap-5">
            <AnimatePresence mode="popLayout">
              {filteredProjects.length > 0 ? (
                filteredProjects.map((project) => (
                  <ProjectCard key={project.project_id} project={project} />
                ))
              ) : (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="w-full py-16 flex flex-col items-center justify-center text-center bg-muted/50 rounded-2xl border border-dashed"
                >
                  <FileText className="w-12 h-12 text-muted-foreground/50 mb-4" />
                  <h3 className="text-foreground font-semibold text-lg mb-1">
                    No Projects Found
                  </h3>
                  <p className="text-muted-foreground text-sm max-w-sm">
                    There is currently no audit or financial telemetry available for the selected
                    region.
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}