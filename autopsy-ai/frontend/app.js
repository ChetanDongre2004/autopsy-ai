/*
  Autopsy AI - Premium Vanilla JS Frontend
  Handles code submission, syntax highlighting, and dynamic UI rendering.
*/

document.addEventListener("DOMContentLoaded", () => {
    // --- DOM Elements ---
    const themeToggle = document.getElementById("themeToggle");
    const codeInput = document.getElementById("codeInput");
    const languageSelect = document.getElementById("languageSelect");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const btnText = document.querySelector(".btn-text");
    const loader = document.querySelector(".loader");
    
    const codeDisplay = document.getElementById("codeDisplay");
    
    // UI Panel Elements
    const initialState = document.getElementById("initialState");
    const resultsState = document.getElementById("resultsState");
    
    const gradeDisplay = document.getElementById("gradeDisplay");
    const scoreDisplay = document.getElementById("scoreDisplay");
    const summaryDisplay = document.getElementById("summaryDisplay");
    
    const metricCritical = document.getElementById("metricCritical");
    const metricWarning = document.getElementById("metricWarning");
    const metricInfo = document.getElementById("metricInfo");
    
    const issueCount = document.getElementById("issueCount");
    const issuesContainer = document.getElementById("issuesContainer");
    
    const positivesContainer = document.getElementById("positivesContainer");

    // --- Theme Toggle ---
    themeToggle.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", newTheme);
    });

    // --- Real-time Code Highlighting ---
    codeInput.addEventListener("input", updateCodeViewer);
    languageSelect.addEventListener("change", updateCodeViewer);

    function updateCodeViewer() {
        const code = codeInput.value || "# Paste your messy code here...";
        const lang = languageSelect.value;
        
        // Update language class for highlight.js
        codeDisplay.className = `language-${lang}`;
        
        // Escape HTML to prevent injection
        codeDisplay.textContent = code;
        
        // Trigger highlight
        hljs.highlightElement(codeDisplay);
    }

    // Initialize highlight for the default example code
    updateCodeViewer();

    // --- Analysis Submit ---
    analyzeBtn.addEventListener("click", async () => {
        const code = codeInput.value.trim();
        const lang = languageSelect.value;

        if (!code) {
            alert("⚠️ Please paste some code to analyze.");
            return;
        }

        // Set Loading State
        btnText.textContent = "Analyzing...";
        loader.classList.remove("hidden");
        analyzeBtn.disabled = true;
        
        // Hide previous results
        initialState.classList.add("hidden");
        resultsState.classList.add("hidden");

        try {
            // Note: Update URL if hosted elsewhere. Defaults to FastAPI backend.
            const response = await fetch("https://autopsy-ai.onrender.com/api/review/", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code: code, language: lang })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Server Error");
            }

            const data = await response.json();
            renderResults(data);
        } catch (error) {
            console.error("API Error:", error);
            alert("❌ Analysis Failed: \n" + error.message);
            // Reset to initial state on hard failure
            initialState.classList.remove("hidden");
        } finally {
            // Reset Loading State
            btnText.textContent = "Audit Code";
            loader.classList.add("hidden");
            analyzeBtn.disabled = false;
        }
    });

    // --- Render Results to UI ---
    function renderResults(data) {
        // Show the results section
        resultsState.classList.remove("hidden");
        
        // 1. Score & Grade
        scoreDisplay.textContent = `${data.score}/100`;
        summaryDisplay.textContent = data.summary;
        gradeDisplay.textContent = data.grade;
        
        // Set distinct colors based on grade
        const gradeMap = {
            "A": "var(--grade-a)",
            "B": "var(--grade-b)",
            "C": "var(--grade-c)",
            "D": "var(--grade-d)",
            "F": "var(--grade-f)"
        };
        gradeDisplay.style.backgroundColor = gradeMap[data.grade] || "var(--text-muted)";
        
        // 2. Metrics
        metricCritical.textContent = data.metrics.critical || 0;
        metricWarning.textContent = data.metrics.warnings || 0;
        metricInfo.textContent = data.metrics.info || 0;
        issueCount.textContent = data.metrics.totalIssues || 0;

        // 3. Render Issues
        issuesContainer.innerHTML = "";
        if (data.issues && data.issues.length > 0) {
            data.issues.forEach(issue => {
                const card = document.createElement("div");
                card.className = "issue-card";
                card.setAttribute("data-severity", issue.severity); // "critical", "warning", "info"

                // Title bar with line number
                const header = document.createElement("div");
                header.className = "issue-header";
                header.innerHTML = `
                    <span class="issue-type">${issue.type}</span>
                    <span class="issue-line">Line: ${issue.line || '?'}</span>
                `;

                // Description
                const desc = document.createElement("div");
                desc.className = "issue-desc";
                desc.textContent = issue.description;

                // Fixing Suggestion
                const suggestion = document.createElement("div");
                suggestion.className = "issue-suggestion";
                suggestion.innerHTML = `<strong>Fix:</strong> ${issue.suggestion}`;

                card.appendChild(header);
                card.appendChild(desc);
                card.appendChild(suggestion);
                issuesContainer.appendChild(card);
            });
        } else {
            issuesContainer.innerHTML = `<p style="color:var(--grade-a); font-size: 0.9rem;">✨ Exceptional! No issues found.</p>`;
        }

        // 4. Render Positives
        positivesContainer.innerHTML = "";
        if (data.positives && data.positives.length > 0) {
            data.positives.forEach(msg => {
                const li = document.createElement("li");
                li.textContent = msg;
                positivesContainer.appendChild(li);
            });
        }
    }
});
