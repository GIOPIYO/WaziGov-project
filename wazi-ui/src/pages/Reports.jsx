import React from 'react';
import { FilePlus, Download, Clock } from 'lucide-react';

export default function Reports() {
  return (
    <div>
      <h1 className="page-title">Financial Reports</h1>
      
      {/* -- Report Generation -- */}
      <div className="report-generation-section">
        <h2>Generate a New Report</h2>
        <p>Create a customized financial report based on your selected criteria.</p>
        <button className="btn-primary">
          <FilePlus size={18} />
          <span>Generate New Report</span>
        </button>
      </div>

      {/* -- Recent Reports -- */}
      <div className="recent-reports-section">
        <h2>Recent Reports</h2>
        <div className="report-list">
          {/* Placeholder for recent reports */}
          {[...Array(3)].map((_, i) => (
            <div key={i} className="report-item-placeholder">
              <div className="report-info">
                <p className="report-name">Q3 Financial Summary</p>
                <p className="report-date">Generated on: {new Date().toLocaleDateString()}</p>
              </div>
              <button className="btn-secondary">
                <Download size={16} />
                <span>Download</span>
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* -- Report Templates -- */}
      <div className="report-templates-section">
        <h2>Report Templates</h2>
        <div className="template-list">
          {/* Placeholder for report templates */}
          {[...Array(2)].map((_, i) => (
            <div key={i} className="template-item-placeholder">
              <p className="template-name">Annual General Report</p>
              <p className="template-description">A comprehensive summary of all financial activities over the past year.</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
