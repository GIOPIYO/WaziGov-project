"use client";
import React, { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, ChevronDown, ChevronUp } from "lucide-react";
import { motion } from "motion/react";

const ProjectDetails = ({ project }: { project: any }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const findings = project.oag_findings || [];
  const hasFindings = findings.length > 0;
  
  const isLong = findings.length > 1 || (findings[0] && findings[0].length > 150);

  return (
    <div className="p-5 text-sm text-muted-foreground space-y-4">
      <div>
        <strong className="text-foreground block mb-2 text-xs uppercase tracking-wider">Detailed Findings</strong>
        {hasFindings ? (
          <div className="space-y-2">
            <ul className="list-disc pl-5 space-y-1.5 marker:text-muted-foreground/50">
              {findings.map((finding: string, idx: number) => (
                <li 
                  key={idx} 
                  className={`leading-relaxed ${!isExpanded && idx === 0 ? "line-clamp-2" : ""} ${!isExpanded && idx > 0 ? "hidden" : ""}`}
                >
                  {finding}
                </li>
              ))}
            </ul>
            {isLong && (
              <button
                onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                className="text-xs font-semibold text-blue-600 dark:text-blue-400 hover:underline focus:outline-none"
              >
                {isExpanded ? "Show Less" : "Read More..."}
              </button>
            )}
          </div>
        ) : (
          <p>No specific OAG findings recorded for this project.</p>
        )}
      </div>
      <div className="flex flex-wrap gap-x-8 gap-y-2 border-t pt-3 mt-3">
        <p>Contract Sum: <strong className="text-foreground">{project.contract_sum_kshs ? `KES ${project.contract_sum_kshs.toLocaleString()}` : "N/A"}</strong></p>
        <p>Implementation: <strong className="text-foreground">{project.implementation_pct !== undefined && project.implementation_pct !== null ? `${project.implementation_pct}%` : "N/A"}</strong></p>
      </div>
    </div>
  );
};

export default function AuditForensicsTable() {
  const [flaggedProjects, setFlaggedProjects] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedProject, setExpandedProject] = useState<string | null>(null);

  useEffect(() => {
    async function fetchFlagged() {
      try {
        const res = await fetch("http://localhost:8000/projects?limit=1000");
        if (!res.ok) throw new Error("Failed to fetch");
        const allProjects = await res.json();

        // Filter projects that are flagged or high risk
        const flagged = allProjects
          .filter(
            (p: any) =>
              p.oag_status === "FLAGGED" ||
              p.triangulation_verdict === "CORROBORATED_PROJECT_RISK"
          )
          .sort((a: any, b: any) => (b.oag_match_confidence || 0) - (a.oag_match_confidence || 0))
          .slice(0, 10); // show top 10 highest confidence issues

        setFlaggedProjects(flagged);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchFlagged();
  }, []);

  const toggleDetails = (projectId: string) => {
    setExpandedProject(expandedProject === projectId ? null : projectId);
  };

  return (
    <div className="w-full overflow-x-auto rounded-xl border bg-card shadow-sm relative min-h-[200px]">
      <Table>
        <TableHeader className="bg-muted/50">
          <TableRow className="hover:bg-transparent">
            <TableHead className="font-semibold text-muted-foreground">
              Project / ID
            </TableHead>
            <TableHead className="font-semibold text-muted-foreground">
              County
            </TableHead>
            <TableHead className="font-semibold text-muted-foreground">
              Risk Type
            </TableHead>
            <TableHead className="font-semibold text-muted-foreground text-right">
              Action
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {loading ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center py-10">
                <div className="flex flex-col items-center justify-center text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin mb-2" />
                  Fetching forensic data...
                </div>
              </TableCell>
            </TableRow>
          ) : flaggedProjects.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center py-10 text-muted-foreground">
                No flagged projects found.
              </TableCell>
            </TableRow>
          ) : (
            flaggedProjects.map((project) => {
              // Extract the first risk type or fallback to status
              const riskType = 
                (project.oag_risk_types && project.oag_risk_types.length > 0) 
                  ? project.oag_risk_types[0] 
                  : (project.triangulation_verdict || project.oag_status || "FLAGGED");

              const isExpanded = expandedProject === project.project_id;

              return (
                <React.Fragment key={project.project_id}>
                  <TableRow
                    className="hover:bg-muted/50 transition-colors duration-200 cursor-pointer"
                    onClick={() => toggleDetails(project.project_id)}
                  >
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-foreground line-clamp-1">
                          {project.project_name ? project.project_name.replace(/(?:\s+[\d.,]+)+\s*$/, "") : "Unknown Project"}
                        </span>
                        <span className="text-xs text-muted-foreground whitespace-nowrap mt-0.5">
                          {project.project_id}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium text-foreground whitespace-nowrap">
                      {project.county}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant="outline"
                        className="bg-rose-50 border-rose-200 text-rose-700 dark:bg-rose-900/30 dark:border-rose-800 dark:text-rose-400 font-semibold tracking-wider text-[10px] uppercase whitespace-nowrap pointer-events-none"
                      >
                        {riskType.replace(/_/g, " ")}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 text-xs flex items-center gap-1 ml-auto"
                      >
                        {isExpanded ? "Hide Details" : "View Details"}
                        {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                      </Button>
                    </TableCell>
                  </TableRow>
                  {isExpanded && (
                    <TableRow className="bg-muted/20 hover:bg-muted/20">
                      <TableCell colSpan={4} className="p-0 border-b">
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          className="overflow-hidden"
                        >
                          <ProjectDetails project={project} />
                        </motion.div>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              );
            })
          )}
        </TableBody>
      </Table>
    </div>
  );
}