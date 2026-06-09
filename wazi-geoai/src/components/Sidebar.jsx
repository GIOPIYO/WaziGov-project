export default function Sidebar() {
  return (
    <div className="sidebar">

      <div className="brand-section">
        <h1>Wazigov</h1>

        <p className="subtitle">
          Public Government Accountability Platform
        </p>
      </div>

      <div className="divider"></div>

      <div className="panel-section">
        <h3>Government Institution</h3>

        <select className="control-input">
          <option>Select Institution</option>
          <option>Office of the Auditor General</option>
          <option>Controller of Budget</option>
        </select>
      </div>

      <div className="panel-section">
        <h3>Report Category</h3>

        <select className="control-input">
          <option>Select Report Type</option>
          <option>County Audit Reports</option>
          <option>National Government Reports</option>
          <option>Project Audit Reports</option>
          <option>Budget Implementation Reports</option>
        </select>
      </div>

      <div className="panel-section">
        <h3>Financial Year</h3>

        <select className="control-input">
          <option>Select Financial Year</option>
          <option>2024 / 2025</option>
          <option>2023 / 2024</option>
          <option>2022 / 2023</option>
          <option>2021 / 2022</option>
        </select>
      </div>

      <div className="divider"></div>

      <div className="citizen-section">

        <h3>Explore Your Area</h3>

        <div className="panel-section">
          <label className="input-label">
            County
          </label>

          <select className="control-input">
            <option>Select County</option>
            <option>Nairobi</option>
            <option>Mombasa</option>
            <option>Kisumu</option>
            <option>Nakuru</option>
          </select>
        </div>

        <div className="panel-section">
          <label className="input-label">
            Ward
          </label>

          <select className="control-input">
            <option>Select Ward</option>
            <option>Westlands</option>
            <option>Kilimani</option>
            <option>Langata</option>
            <option>Kasarani</option>
          </select>
        </div>

        <div className="panel-section">
          <button className="analyze-btn">
            View Ward Insights
          </button>
        </div>

      </div>

      <div className="divider"></div>

      <div className="citizen-section">
  <h3>Public Insights</h3>

  <div className="panel-section">
    <label className="input-label">
      Select Insight
    </label>

    <select className="control-input">
      <option>Select Insight Type</option>

      <option>
        Government-Funded Projects
      </option>

      <option>
        Flagged Audit Issues
      </option>

      <option>
        Delayed Public Projects
      </option>

      <option>
        Budget Allocation & Usage
      </option>

      <option>
        Pending Development Projects
      </option>

      <option>
        High-Risk Spending Areas
      </option>

      <option>
        Procurement Irregularities
      </option>
    </select>
  </div>

  <div className="panel-section">
    <button className="analyze-btn">
      Generate Public Insights
    </button>
  </div>
</div>

    </div>
  )
}