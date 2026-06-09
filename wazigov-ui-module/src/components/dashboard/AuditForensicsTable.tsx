import React from "react";
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

// --- Mock Data (unchanged) ---
const FLAGGED_PROJECTS = [
  {
    project_id: "bari-premises55",
    county: "Baringo",
    project_name: "Premises 55 Construction",
    risk_type: "INCOMPLETE_PROJECT",
    match_confidence: 88.5,
  },
  {
    project_id: "kia-drainage-22",
    county: "Kiambu",
    project_name: "Thika CBD Drainage Phase 2",
    risk_type: "PROCUREMENT_BREACH",
    match_confidence: 94.2,
  },
  {
    project_id: "mom-bridge-05",
    county: "Mombasa",
    project_name: "Nyali Footbridge Repair",
    risk_type: "GHOST_PROJECT",
    match_confidence: 98.0,
  },
  {
    project_id: "nak-market-01",
    county: "Nakuru",
    project_name: "Naivasha Main Market Sheds",
    risk_type: "BUDGET_DISCREPANCY",
    match_confidence: 82.7,
  },
];

export default function AuditForensicsTable() {
  return (
    <div className="w-full overflow-x-auto rounded-xl border bg-card shadow-sm">
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
              Confidence
            </TableHead>
            <TableHead className="font-semibold text-muted-foreground text-right">
              Action
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {FLAGGED_PROJECTS.map((project) => (
            <TableRow
              key={project.project_id}
              className="hover:bg-muted/50 transition-colors duration-200"
            >
              <TableCell>
                <div className="flex flex-col">
                  <span className="font-medium text-foreground line-clamp-1">
                    {project.project_name}
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
                  {project.risk_type.replace(/_/g, " ")}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-medium">
                <span
                  className={
                    project.match_confidence > 90
                      ? "text-rose-600 dark:text-rose-400"
                      : "text-amber-600 dark:text-amber-400"
                  }
                >
                  {project.match_confidence.toFixed(1)}%
                </span>
              </TableCell>
              <TableCell className="text-right">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs"
                >
                  View Details
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}