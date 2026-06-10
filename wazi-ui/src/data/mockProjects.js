// Realistic mock database of public projects in Kenya
// Comprising county-level infrastructure, health, water, education, and agriculture initiatives.
// Integrates real-life OAG audit report findings, AI-simplified summaries, and simulated citizen feedback.

export const mockProjects = [
  {
    id: "PROJ-2026-NBO-001",
    title: "Nairobi County Green Park Terminus Expansion",
    sector: "Infrastructure",
    county: "Nairobi",
    ward: "Central Business District",
    budget: 1850000000, // 1.85 Billion KES
    spent: 2100000000,  // Overspent by 250M
    status: "Suspended",
    progress: 85,
    startDate: "2024-03-15",
    expectedEndDate: "2025-12-20",
    oagOpinion: "Adverse", // Critical OAG findings
    implementationAgency: "Nairobi Metropolitan Services (NMS) & County Executive",
    auditorGeneralQueries: [
      {
        id: "Q-101",
        issue: "Over-expenditure without Supplementary Budget Approval",
        amount: 250000000,
        severity: "High",
        description: "The project has incurred expenditures exceeding the approved budget of KES 1.85 Billion by KES 250 Million. No supplementary budget approvals or authority files were presented to audit to support this variation."
      },
      {
        id: "Q-102",
        issue: "Undelivered Digital Passenger Information Systems",
        amount: 45000000,
        severity: "Medium",
        description: "A payment of KES 45 Million was made to a third-party vendor for smart digital display boards. Visual inspection on 2026-02-10 revealed that no display boards were installed, and the contractor had abandoned the site."
      }
    ],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON THE NAIROBI GREEN PARK TERMINUS UPGRADE PROJECT FOR THE YEAR ENDED 30 JUNE 2025

1. Over-expenditure and Budget Variations
Audit inspection of project accounts revealed that the total expenditure stood at KES 2,100,000,000 against a contract sum of KES 1,850,000,000, resulting in an unapproved over-expenditure of KES 250,000,000. No documentation was provided to prove that the relevant county executive committee or the County Assembly approved these variations. This violates Section 135 of the Public Finance Management Act, 2012.

2. Equipment Paid for but Not Delivered
A sum of KES 45,000,000 was disbursed under voucher no. V-9988 for 'Digital Smart Screens and Passenger Tracking Systems'. Visual audits and site visitations on 10 February 2026 revealed that none of the equipment had been supplied, installed, or configured. Management has not offered any satisfactory explanation or initiated recovery processes from the contractor.

3. Failure of Concrete Works and Structural Defects
Site reviews indicated substantial cracking along the southern exit ramp concrete pavements. Structural integrity assessments indicate the concrete mixture did not meet the standard class C25 specification as contracted, which could lead to early failure under heavy bus loads.

Conclusion
In view of the unapproved variations, payment for non-existent IT systems, and poor workmanship on the ramps, I am unable to confirm that the public obtained value for money. Consequently, I issue an Adverse Opinion on the project financial reporting and implementation integrity.`,
    aiSummary: "The government originally budgeted KES 1.85 Billion, but actually spent KES 2.1 Billion (KES 250 Million over budget) without the legally required approvals from the County Assembly. Furthermore, the Auditor General found that KES 45 Million was paid for digital signs that were never delivered, and the concrete exit ramp is already cracking because of poor building materials.",
    milestones: [
      { date: "2024-01-10", label: "Project Approved & Tendering Opened", status: "completed" },
      { date: "2024-03-15", label: "Construction Commenced", status: "completed" },
      { date: "2024-11-30", label: "Audit Visit by OAG Inspectors", status: "completed" },
      { date: "2025-06-30", label: "OAG Adverse Audit Report Issued", status: "completed" },
      { date: "2026-01-15", label: "Works Halted / Senate Committee Inquiry", status: "active" }
    ],
    citizenReports: [
      {
        id: "CR-1",
        author: "Karanja M.",
        date: "2026-05-10",
        rating: 2,
        comment: "This place has been abandoned for months now. Busses are parking on dirt because the concrete pavement has massive sinkholes. Complete waste of tax money!",
        image: "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Verified Anomaly"
      },
      {
        id: "CR-2",
        author: "Amina O.",
        date: "2026-05-24",
        rating: 1,
        comment: "No sign of the digital boards they claimed to install. It is just empty wire pipes sticking out of the concrete.",
        image: null,
        verificationStatus: "Verified Anomaly"
      }
    ]
  },
  {
    id: "PROJ-2026-MSA-002",
    title: "Mombasa Sub-County Hospital Maternity Wing",
    sector: "Health",
    county: "Mombasa",
    ward: "Changamwe",
    budget: 450000000, // 450 Million KES
    spent: 442000000,
    status: "Complete",
    progress: 100,
    startDate: "2024-05-01",
    expectedEndDate: "2025-10-30",
    oagOpinion: "Clean", // Unqualified
    implementationAgency: "Mombasa County Department of Health Services",
    auditorGeneralQueries: [],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON THE CONSTRUCTION OF CHANGAMWE SUB-COUNTY HOSPITAL MATERNITY WING FOR THE YEAR ENDED 30 JUNE 2025

1. Execution and Delivery of Works
We conducted financial and physical audits on the construction of the 120-bed capacity maternity wing. Review of construction documents, including bills of quantities, payment certificates, and certificate of practical completion, confirmed that works were executed in accordance with technical specifications and standards.

2. Equipment Installation and Commissioning
Visual audit on 15 November 2025 confirmed that specialized medical gas pipelines, newborn incubators, ultra-sound equipment, and maternity beds have been successfully installed and commissioned. The unit is currently operating at full capacity.

3. Value for Money Assessment
The project was completed within budget, representing a minor cost saving of KES 8,000,000. High public utility was verified, as the center now handles an average of 40 births daily, alleviating congestion at Coast General Teaching and Referral Hospital.

Conclusion
Based on the audit procedures performed, the funds allocated for this project were applied efficiently and in compliance with the public procurement guidelines. I issue an Unqualified (Clean) Opinion.`,
    aiSummary: "The 120-bed maternity hospital wing was completed within the planned budget of KES 450 Million, actually saving KES 8 Million! The Auditor General verified that all the high-end equipment like incubators and oxygen pipelines are installed and functioning. The center is already delivering 40 babies a day, successfully relieving congestion in Mombasa.",
    milestones: [
      { date: "2024-04-05", label: "Contract Awarded", status: "completed" },
      { date: "2024-05-01", label: "Groundbreaking Ceremony", status: "completed" },
      { date: "2025-08-15", label: "Building Works Concluded", status: "completed" },
      { date: "2025-10-10", label: "Medical Equipment Installed & Commissioned", status: "completed" },
      { date: "2025-11-01", label: "Official Opening to the Public", status: "completed" }
    ],
    citizenReports: [
      {
        id: "CR-3",
        author: "Fatma S.",
        date: "2026-04-02",
        rating: 5,
        comment: "Excellent facility. My sister delivered here last month. The doctors are helpful, the wards are clean and spacious, and they have reliable solar backup power. Truly a blessing!",
        image: "https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Citizen Confirmed"
      }
    ]
  },
  {
    id: "PROJ-2026-KIS-003",
    title: "Kisumu Lakefront Sewerage & Sanitation Line",
    sector: "Water & Sanitation",
    county: "Kisumu",
    ward: "Kisumu Central",
    budget: 920000000, // 920 Million KES
    spent: 890000000,
    status: "In Progress",
    progress: 72,
    startDate: "2024-09-01",
    expectedEndDate: "2026-08-30",
    oagOpinion: "Qualified", // Minor discrepancies but not adverse
    implementationAgency: "Lake Victoria South Water Works Development Agency",
    auditorGeneralQueries: [
      {
        id: "Q-301",
        issue: "Unsupported Excavation Disposal Fees",
        amount: 32000000,
        severity: "Low",
        description: "A payment of KES 32 Million for disposal of excavated rock and soil in Kisumu West lacked supporting landfill receipt certificates or environmental disposal permits from NEMA."
      }
    ],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON KISUMU LAKEFRONT SANITATION INFRASTRUCTURE PROJECT FOR THE YEAR ENDED 30 JUNE 2025

1. Status of Project Implementation
A physical audit of the sewerage line expansion in Kisumu Central Ward indicated that approximately 14 kilometers out of the planned 20 kilometers of trunk line have been laid, representing a physical completion of 70%.

2. Environmental Mitigation and Earthworks Claims
The contractor charged a sum of KES 32,000,000 for 'haulage and rock waste disposal to designated municipal dumping sites'. However, management did not provide landfill dumping receipts, waste management logs, or NEMA transport permits to verify that the waste was disposed of lawfully. 

3. Compliance with Local Labour Regulations
Audit reviews of employee rosters indicated that the contractor maintained the 70% local hiring quota as stipulated in the contract, and wages were fully documented and paid on time.

Conclusion
Except for the unsupported disposal fees of KES 32 Million, the financial records and project works conform to guidelines in all material respects. I therefore issue a Qualified Opinion on this project.`,
    aiSummary: "The project is currently 72% complete and has laid 14km of sewerage lines. Overall it is on track, but the Auditor General has flagged KES 32 Million paid for removing dug-up soil because there are no landfill receipts or environmental permits proving the soil was actually disposed of safely.",
    milestones: [
      { date: "2024-07-20", label: "Tender Awarded to Sino-Lake JV", status: "completed" },
      { date: "2024-09-01", label: "Excavation Works Started", status: "completed" },
      { date: "2025-05-15", label: "Auditor Site Inspection", status: "completed" },
      { date: "2026-03-01", label: "Main Treatment Connection Completed", status: "completed" },
      { date: "2026-08-30", label: "Target Project Commissioning Date", status: "pending" }
    ],
    citizenReports: [
      {
        id: "CR-4",
        author: "Ochieng J.",
        date: "2026-05-18",
        rating: 4,
        comment: "They are currently digging along the lakeshore road, which has caused heavy traffic, but the workers are on-site daily and speed is good. Excited to finally get modern sewer lines here.",
        image: "https://images.unsplash.com/photo-1504307651254-35680f356dfd?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Citizen Confirmed"
      }
    ]
  },
  {
    id: "PROJ-2026-TUR-004",
    title: "Turkana Solar-Powered Borehole Water Project",
    sector: "Water & Sanitation",
    county: "Turkana",
    ward: "Lodwar Town",
    budget: 120000000, // 120 Million KES
    spent: 120000000,
    status: "Suspended",
    progress: 40,
    startDate: "2025-01-10",
    expectedEndDate: "2025-09-30",
    oagOpinion: "Adverse", // Critical OAG findings
    implementationAgency: "Turkana County Water & Irrigation Department",
    auditorGeneralQueries: [
      {
        id: "Q-401",
        issue: "Non-functional Solar Inverters and Pumps",
        amount: 58000000,
        severity: "High",
        description: "A total of KES 58 Million was spent on importing and installing high-capacity solar inverters and water pumps. However, audit tests revealed that the inverters were defective second-hand models that failed within 2 weeks of installation. The pumps are currently idle."
      },
      {
        id: "Q-402",
        issue: "Unexplained Project Stoppage and Abandonment",
        amount: 62000000,
        severity: "High",
        description: "Although the contractor was paid KES 120 Million (100% of the total budget), only 4 of the planned 10 boreholes have been drilled. The contractor closed the Lodwar site office in September 2025 and has not responded to inquiries."
      }
    ],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON THE SOLAR-POWERED BOREHOLES IN LODWAR TOWN WARD FOR THE YEAR ENDED 31 DECEMBER 2025

1. Full Payment for Half-Done Works
A review of the bank statements and ledger records shows the contractor was paid the full contract sum of KES 120,000,000 by 15 August 2025. However, physical audits of the water points showed that only 4 boreholes were drilled and fitted, against the contractual target of 10 boreholes. The remaining 6 locations have not seen any mobilization or work.

2. Supply of Defective and Substandard Equipment
Technical audits of the 4 installed solar stations revealed that the pumps are not discharging water. Log books indicate the systems failed 14 days after commissioning. The solar panels are generic models with low wattage outputs, failing to match the tender specification for German-made high-density photovoltaic cells. 

3. Site Abandonment
At the time of our audit in November 2025, no workers or machinery were present. The main contractor has vanished, leaving the community without water despite the complete budget absorption.

Conclusion
The citizens of Lodwar did not receive any value from this KES 120 Million investment. I conclude that public funds were lost through procurement fraud and poor supervision. I issue an Adverse Opinion.`,
    aiSummary: "The government paid the contractor 100% of the budget (KES 120 Million), but the contractor only drilled 4 out of the 10 planned water boreholes and then completely abandoned the project. To make matters worse, the solar panels and pumps they did install are second-hand and broke down after only 2 weeks, leaving the Lodwar community with zero water.",
    milestones: [
      { date: "2025-01-02", label: "Tender Award & Mobilization", status: "completed" },
      { date: "2025-03-10", label: "First 2 Boreholes Drilled", status: "completed" },
      { date: "2025-08-15", label: "100% Budget Cleared and Paid", status: "completed" },
      { date: "2025-09-30", label: "Contractor Closed Site & Left Lodwar", status: "completed" },
      { date: "2025-11-20", label: "Audit Inspection Confirms Defect & Stoppage", status: "completed" }
    ],
    citizenReports: [
      {
        id: "CR-5",
        author: "Lokuruka E.",
        date: "2026-03-15",
        rating: 1,
        comment: "This is a crime against our people. We have to walk 15km to the river while this KES 120M water project sits here rusting in the sun. The solar panels are completely covered in dust and the pump is dead.",
        image: "https://images.unsplash.com/photo-1547970894-3b192936de15?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Verified Anomaly"
      }
    ]
  },
  {
    id: "PROJ-2026-KBU-005",
    title: "Kiambu Early Childhood Development Centers (ECDE)",
    sector: "Education",
    county: "Kiambu",
    ward: "Kabete",
    budget: 280000000, // 280 Million KES
    spent: 280000000,
    status: "Complete",
    progress: 100,
    startDate: "2024-02-01",
    expectedEndDate: "2025-04-30",
    oagOpinion: "Qualified", // Minor bookkeeping queries
    implementationAgency: "Kiambu County Department of Education & Social Services",
    auditorGeneralQueries: [
      {
        id: "Q-501",
        issue: "Missing Assets Registry and Equipment Inventories",
        amount: 15000000,
        severity: "Low",
        description: "School desks, early-learning tablets, and play items valued at KES 15 Million were not registered in the county assets tracker or individual school registers."
      }
    ],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON THE KIAMBU EARLY CHILDHOOD DEVELOPMENT CENTERS CONSTRUCTION PROJECT FOR THE YEAR ENDED 30 JUNE 2025

1. Execution of Works and Commissioning
Audit visits to 12 new ECDE classrooms across Kabete Ward verified that the building envelopes, restrooms, and administrative blocks were built to standard, fully painted, and fitted with child-friendly playing facilities. The classrooms are currently populated by students.

2. Equipment and Instructional Material Audits
While KES 15,000,000 was spent on learning aids, school desks, and outdoor playgrounds, these items were not entered into the master assets logs or individual school ledger templates. We could not verify if all desks paid for reached the respective centers due to poor tracking.

Conclusion
The classroom construction is highly successful and represents good value for the money. However, management must address the weak inventory tracking for student furniture and learning aids. I issue a Qualified Opinion on account of inventory record gaps.`,
    aiSummary: "The classrooms were successfully built and are now full of children, proving to be a highly useful project! However, the Auditor General flagged that KES 15 Million worth of kids' desks, toys, and tablets were never entered into the schools' inventory books, making it hard to verify if every single desk bought actually made it to the classrooms.",
    milestones: [
      { date: "2024-01-15", label: "Contracts Signed for 12 Sites", status: "completed" },
      { date: "2024-02-01", label: "Construction Commencement", status: "completed" },
      { date: "2025-01-20", label: "Buildings Completed and Handed Over", status: "completed" },
      { date: "2025-03-01", label: "Schools Populated and Active", status: "completed" },
      { date: "2025-06-10", label: "Inventory Audit Conducted", status: "completed" }
    ],
    citizenReports: [
      {
        id: "CR-6",
        author: "Wanjiku N.",
        date: "2026-05-02",
        rating: 5,
        comment: "My twin children go here. The classrooms are bright, they have beautiful play slides outside, and clean toilets. A massive upgrade from the old mabati structure we used to have!",
        image: "https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Citizen Confirmed"
      }
    ]
  },
  {
    id: "PROJ-2026-NBO-006",
    title: "Nairobi Smart Street Lighting Grid Phase II",
    sector: "Infrastructure",
    county: "Nairobi",
    ward: "Kasarani",
    budget: 340000000, // 340 Million KES
    spent: 340000000,
    status: "Complete",
    progress: 100,
    startDate: "2024-07-01",
    expectedEndDate: "2025-05-30",
    oagOpinion: "Disclaimer", // Serious audit blockage (no records provided)
    implementationAgency: "Nairobi County Department of Public Works",
    auditorGeneralQueries: [
      {
        id: "Q-601",
        issue: "Total Denial of Access to Supporting Vouchers & Logs",
        amount: 340000000,
        severity: "High",
        description: "The management failed to present any payment vouchers, procurement journals, material delivery notes, or electricity contract agreements for the entire KES 340 Million budget."
      }
    ],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON THE NAIROBI SMART STREET LIGHTING GRID PHASE II FOR THE YEAR ENDED 30 JUNE 2025

1. Total Denial and Limitation of Audit Scope
Management failed to present any ledger reports, tendering journals, bids evaluation summaries, pay vouchers, or cashbooks supporting the expenditure of KES 340,000,000. Under Section 9(1) of the Public Audit Act, 2015, the Auditor-General is entitled to full access to all books and records. The absolute failure to provide evidence constitutes a severe limitation of audit scope.

2. Verification of Physical Assets
We attempted to conduct sample walk-along verifications of 'smart solar streetlights' listed in the project outline. While streetlights exist in Kasarani, we could not confirm if these were built under this project phase, or if they were constructed by private developers or under a separate Rural Electrification program.

Conclusion
Due to the absolute refusal of the department to provide any records, receipts, or contracts, I have been unable to obtain sufficient appropriate audit evidence to provide an opinion on the project. I therefore issue a Disclaimer of Opinion.`,
    aiSummary: "The Auditor General could not audit this KES 340 Million project because the County Department of Public Works refused to show any financial files, receipts, contracts, or bank statements. Even though streetlights are standing in Kasarani, there is zero paper proof that they were actually funded by this budget or who got paid for them.",
    milestones: [
      { date: "2024-06-15", label: "Tender Advertised", status: "completed" },
      { date: "2024-07-01", label: "Project Mobilization", status: "completed" },
      { date: "2025-05-30", label: "Physical Completion Claimed", status: "completed" },
      { date: "2025-09-12", label: "Audit Site Visit (Denied files)", status: "completed" },
      { date: "2025-12-18", label: "Disclaimer of Audit Opinion Issued", status: "completed" }
    ],
    citizenReports: [
      {
        id: "CR-7",
        author: "Mwangi J.",
        date: "2026-04-20",
        rating: 3,
        comment: "We have streetlights on our road now and it is much safer at night! But why is the county hiding the papers? If the job was done, just show the public where the KES 340 Million went.",
        image: "https://images.unsplash.com/photo-1517486808906-6ca8b3f04846?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Citizen Confirmed"
      }
    ]
  },
  {
    id: "PROJ-2026-KIS-007",
    title: "Kisumu Avocado Processing Plant & Cold Storage",
    sector: "Agriculture",
    county: "Kisumu",
    ward: "Muhoroni",
    budget: 520000000, // 520 Million KES
    spent: 310000000,
    status: "In Progress",
    progress: 55,
    startDate: "2025-02-10",
    expectedEndDate: "2026-10-15",
    oagOpinion: "Clean", // Clean progress audit
    implementationAgency: "Kisumu County Department of Agriculture & Livestock",
    auditorGeneralQueries: [],
    oagReportText: `REPORT OF THE AUDITOR-GENERAL ON KISUMU MUHORONI AVOCADO VALUE-ADDITION FACILITY FOR THE PERIOD ENDING 31 DECEMBER 2025

1. Financial Allocation and Expenditure Review
Our audit verified that out of the KES 520,000,000 total budget, KES 310,000,000 has been disbursed and spent in line with the work schedule. All payments are supported by valid certificates of work done, architectural records, and material receipt notes.

2. Progress of Infrastructure Setup
Physical site inspections on 15 November 2025 confirmed that the main factory building foundation, steel framework, and roofing structures are completed. Installation of cold storage panels is currently underway.

Conclusion
The project is progressing in an orderly, efficient manner. Financial ledger records are well-kept and transparency standards are met. I issue an Unqualified (Clean) opinion for this ongoing phase.`,
    aiSummary: "This KES 520 Million project is currently 55% complete. KES 310 Million has been spent so far, and the Auditor General confirmed that every single cent has proper receipts, steel purchase records, and building progress certificates. The factory shell and roof are completed, and cold storage installation is currently on schedule.",
    milestones: [
      { date: "2025-01-05", label: "Tender Awarded", status: "completed" },
      { date: "2025-02-10", label: "Groundbreaking", status: "completed" },
      { date: "2025-08-30", label: "Foundation & Steel Framework Complete", status: "completed" },
      { date: "2025-11-15", label: "OAG Progress Inspection", status: "completed" },
      { date: "2026-10-15", label: "Scheduled Commissioning", status: "pending" }
    ],
    citizenReports: [
      {
        id: "CR-8",
        author: "Anyango R.",
        date: "2026-05-15",
        rating: 4,
        comment: "The factory walls are up and it looks huge! Farmers in Muhoroni are really counting on this to store our avocados. Hope they finish it on time.",
        image: "https://images.unsplash.com/photo-1595974482597-4b8da8879bc5?auto=format&fit=crop&w=600&q=80",
        verificationStatus: "Citizen Confirmed"
      }
    ]
  }
];
