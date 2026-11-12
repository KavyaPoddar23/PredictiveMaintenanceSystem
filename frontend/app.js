
const API_BASE = "/api/v1";

let machinePredictions = [];

const tableBody = document.getElementById("machineTable");
const loadingMessage = document.getElementById("loadingMessage");
const errorMessage = document.getElementById("errorMessage");
const searchInput = document.getElementById("searchInput");
const riskFilter = document.getElementById("riskFilter");


async function fetchJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || `Request failed: ${response.status}`);
    }

    return response.json();
}


async function loadDashboard() {
    loadingMessage.classList.remove("hidden");
    errorMessage.classList.add("hidden");

    try {
        const [summary, fleet] = await Promise.all([
            fetchJSON(`${API_BASE}/fleet/summary`),
            fetchJSON(`${API_BASE}/fleet/predictions`)
        ]);

        machinePredictions = fleet.predictions || [];

        document.getElementById("totalMachines").textContent =
            summary.total_machines;

        document.getElementById("highRiskMachines").textContent =
            summary.high_risk_machines;

        document.getElementById("averageProbability").textContent =
            `${(summary.average_failure_probability * 100).toFixed(1)}%`;

        const distribution = summary.risk_distribution;

        document.getElementById("criticalMachines").textContent =
            distribution.CRITICAL;

        document.getElementById("criticalCount").textContent =
            distribution.CRITICAL;

        document.getElementById("highCount").textContent =
            distribution.HIGH;

        document.getElementById("mediumCount").textContent =
            distribution.MEDIUM;

        document.getElementById("lowCount").textContent =
            distribution.LOW;

        document.getElementById("lastUpdated").textContent =
            `Loaded: ${new Date().toLocaleString()}`;

        renderTable();

    } catch (error) {
        errorMessage.textContent =
            `Unable to load dashboard: ${error.message}`;

        errorMessage.classList.remove("hidden");
        tableBody.innerHTML = "";
    } finally {
        loadingMessage.classList.add("hidden");
    }
}


function renderTable() {
    const searchTerm = searchInput.value.trim().toLowerCase();
    const selectedRisk = riskFilter.value;

    const filtered = machinePredictions
        .filter(machine => {
            const matchesSearch =
                machine.machine_id.toLowerCase().includes(searchTerm) ||
                machine.machine_name.toLowerCase().includes(searchTerm);

            const matchesRisk =
                selectedRisk === "ALL" ||
                machine.risk_level === selectedRisk;

            return matchesSearch && matchesRisk;
        })
        .sort((a, b) =>
            b.failure_probability - a.failure_probability
        );

    tableBody.innerHTML = "";

    if (filtered.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7">No matching machines found.</td>
            </tr>
        `;
        return;
    }

    filtered.forEach(machine => {
        const row = document.createElement("tr");

        const probability =
            (machine.failure_probability * 100).toFixed(2);

        const cells = [
            machine.machine_id,
            machine.machine_name,
            machine.machine_type,
            machine.criticality,
            `${probability}%`,
            machine.risk_level
        ];

        cells.forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "--";
            row.appendChild(cell);
        });

        const actionCell = document.createElement("td");
        const button = document.createElement("button");

        button.className = "view-button";
        button.textContent = "View Details";

        button.addEventListener("click", () => {
            showMachineDetails(machine.machine_id);
        });

        actionCell.appendChild(button);
        row.appendChild(actionCell);

        const riskCell = row.children[5];
        const badge = document.createElement("span");

        badge.className = `risk-badge ${machine.risk_level}`;
        badge.textContent = machine.risk_level;

        riskCell.textContent = "";
        riskCell.appendChild(badge);

        tableBody.appendChild(row);
    });
}


async function showMachineDetails(machineId) {
    const panel = document.getElementById("detailPanel");
    const details = document.getElementById("machineDetails");

    panel.classList.remove("hidden");
    details.textContent = "Loading machine details...";

    try {
        const machine = await fetchJSON(
            `${API_BASE}/predictions/${encodeURIComponent(machineId)}`
        );

        details.innerHTML = "";

        const fields = [
            ["Machine ID", machine.machine_id],
            ["Machine Name", machine.machine_name],
            ["Machine Type", machine.machine_type],
            ["Criticality", machine.criticality],
            ["Failure Probability",
                `${(machine.failure_probability * 100).toFixed(2)}%`],
            ["Risk Level", machine.risk_level],
            ["Recommended Action", machine.recommended_action],
            ["Snapshot Timestamp", machine.snapshot_timestamp],
            ["Prediction Horizon",
                `${machine.prediction_horizon_hours} hours`],
            ["Model Version", machine.model_version]
        ];

        fields.forEach(([label, value]) => {
            const item = document.createElement("div");
            item.className = "detail-row";

            const strong = document.createElement("strong");
            strong.textContent = `${label}: `;

            const span = document.createElement("span");
            span.textContent = value ?? "--";

            item.appendChild(strong);
            item.appendChild(span);
            details.appendChild(item);
        });

        const heading = document.createElement("h4");
        heading.textContent = "Important Features";
        details.appendChild(heading);

        const featureList = document.createElement("ul");
        featureList.className = "feature-list";

        (machine.important_features || []).forEach(feature => {
            const item = document.createElement("li");

            const observed = feature.observed_value === null
                ? "Unavailable"
                : Number(feature.observed_value).toFixed(3);

            item.textContent =
                `${feature.feature}: ${observed} ` +
                `(global importance: ${Number(
                    feature.global_importance
                ).toFixed(4)})`;

            featureList.appendChild(item);
        });

        details.appendChild(featureList);

        const note = document.createElement("p");
        note.textContent = machine.explanation_note;
        details.appendChild(note);

        panel.scrollIntoView({ behavior: "smooth" });

    } catch (error) {
        details.textContent =
            `Unable to load machine details: ${error.message}`;
    }
}


searchInput.addEventListener("input", renderTable);
riskFilter.addEventListener("change", renderTable);

document.getElementById("refreshButton").addEventListener(
    "click",
    loadDashboard
);

document.getElementById("closeDetails").addEventListener(
    "click",
    () => {
        document.getElementById("detailPanel").classList.add("hidden");
    }
);


loadDashboard();
