/*
  Autopsy AI — app.js
  ===================
  Full implementation for Week 1 (Code Review) and Week 2 (Test Generator).

  ARCHITECTURE:
  - switchWeek()        — toggles between the two feature tabs
  - Week 1 section      — code reviewer logic
  - Week 2 section      — test generator logic with:
      • depth selection
      • toggle options (mocks, fixtures)
      • renderTestResults()   — builds the full results UI
      • renderBreakdown()     — pie-like counts by test type
      • renderTestCases()     — individual test case cards
      • renderTestFile()      — syntax-highlighted test code block
      • renderSyntaxCheck()   — live syntax validation via /api/test/run-check
      • explainTest()         — modal explanation via /api/test/explain
      • copyTestFile()        — clipboard copy with visual feedback

  BASE URL:
  All API calls go to http://localhost:8000 by default.
  Change this once in one place and everything updates.
*/

const API_BASE = window.location.origin;


// ═══════════════════════════════════════════════════════
//  WEEK SWITCHING
// ═══════════════════════════════════════════════════════

const ALL_TABS = ["review", "test", "audit", "repo", "qa", "dast", "analyze", "deps", "branch", "dashboard"];
const GRID_TABS = ["review", "test", "audit"];

function switchTab(tab) {
    ALL_TABS.forEach(t => {
        const el = document.getElementById(t + "Section");
        if (!el) return;
        if (t === tab) {
            el.style.display = GRID_TABS.includes(t) ? "grid" : "flex";
        } else {
            el.style.display = "none";
        }
    });

    ALL_TABS.forEach(t => {
        const btn = document.getElementById("tab" + t.charAt(0).toUpperCase() + t.slice(1));
        if (btn) btn.classList.toggle("active", t === tab);
    });

    const badgeMap = {
        review: "Code Reviewer",
        test: "Test Generator",
        audit: "Security Audit",
        repo: "Repo Intelligence",
        qa: "QA Scanner",
        dast: "DAST Simulator",
        analyze: "Code Metrics",
        deps: "Dependency Scanner",
        branch: "Branch Compare",
        dashboard: "Health Dashboard"
    };
    document.getElementById("moduleBadge").textContent = badgeMap[tab] || "Autopsy AI";
}


// ═══════════════════════════════════════════════════════
//  EXPLAIN MODAL — shared between week 2 test cards
// ═══════════════════════════════════════════════════════

let currentExplainTestCode = "";  // Store for the modal's test code

function openExplainModal() {
    document.getElementById("explainOverlay").classList.add("open");
}

function closeExplainModal() {
    document.getElementById("explainOverlay").classList.remove("open");
}

// Close on backdrop click
document.getElementById("explainOverlay").addEventListener("click", e => {
    if (e.target === document.getElementById("explainOverlay")) closeExplainModal();
});

async function explainTest(testName, testCodeContext, language) {
    // Pre-populate modal with loading state
    document.getElementById("explainTitle").textContent = testName;
    document.getElementById("explainOneLiner").textContent = "Loading explanation...";
    document.getElementById("explainWhy").textContent = "";
    document.getElementById("explainHow").textContent = "";
    openExplainModal();

    try {
        const res = await fetch(`${API_BASE}/api/test/explain`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ test_code: testCodeContext || testName, language })
        });

        if (!res.ok) throw new Error("API error");
        const data = await res.json();

        document.getElementById("explainOneLiner").textContent = data.oneLiner   || "—";
        document.getElementById("explainWhy").textContent      = data.whyItMatters || "—";
        document.getElementById("explainHow").textContent      = data.howToPass   || "—";

    } catch (err) {
        document.getElementById("explainOneLiner").textContent = "Could not load explanation. Make sure the backend is running.";
    }
}


// ═══════════════════════════════════════════════════════
//  MAIN — DOM READY
// ═══════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {

    // ── Theme Toggle ──────────────────────────────────
    const themeBtn = document.getElementById("themeToggle");
    themeBtn.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme");
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        themeBtn.textContent = next === "dark" ? "☀ Light" : "🌙 Dark";
    });


    // ════════════════════════════════════════════════════════
    //  CODE REVIEWER
    // ════════════════════════════════════════════════════════

    const w1 = {
        codeInput:   document.getElementById("codeInput"),
        langSelect:  document.getElementById("languageSelect"),
        analyzeBtn:  document.getElementById("analyzeBtn"),
        btnText:     document.querySelector(".btn-text"),
        spinner:     document.getElementById("w1Spinner"),
        codeDisplay: document.getElementById("codeDisplay"),
        fileName:    document.getElementById("fileNameDisplay"),
        resultsWrap: document.getElementById("w1Results"),
        emptyState:  document.getElementById("w1EmptyState"),
        errorBanner: document.getElementById("w1ErrorBanner"),
    };

    const extMap = { python:"py", javascript:"js", typescript:"ts", html:"html", css:"css", java:"java", cpp:"cpp" };

    function w1UpdateViewer() {
        const lang = w1.langSelect.value;
        w1.codeDisplay.className = `language-${lang}`;
        w1.codeDisplay.textContent = w1.codeInput.value || "# Paste your code here...";
        hljs.highlightElement(w1.codeDisplay);
        w1.fileName.textContent = `untitled.${extMap[lang] || lang}`;
    }

    w1.codeInput.addEventListener("input", w1UpdateViewer);
    w1.langSelect.addEventListener("change", w1UpdateViewer);
    w1UpdateViewer();

    // ── Analyze button ──
    w1.analyzeBtn.addEventListener("click", async () => {
        const code = w1.codeInput.value.trim();
        const lang = w1.langSelect.value;

        if (!code) { showW1Error("Please paste some code to analyze."); return; }

        w1SetLoading(true);
        clearW1Error();
        renderW1Loading();

        try {
            const res = await fetch(`${API_BASE}/api/review/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, language: lang }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Server error ${res.status}`);
            }

            renderW1Results(await res.json());

        } catch (err) {
            showW1Error(err.message);
            renderW1Empty();
        } finally {
            w1SetLoading(false);
        }
    });

    function w1SetLoading(on) {
        w1.analyzeBtn.disabled = on;
        w1.spinner.classList.toggle("visible", on);
        w1.btnText.textContent = on ? "Analyzing..." : "Audit Code";
    }

    function showW1Error(msg) {
        w1.errorBanner.textContent = `⚠ ${msg}`;
        w1.errorBanner.classList.add("visible");
    }
    function clearW1Error() { w1.errorBanner.classList.remove("visible"); }

    function renderW1Loading() {
        w1.resultsWrap.innerHTML = `
            <div class="shimmer" style="height:80px;"></div>
            <div class="shimmer" style="height:52px;margin-top:8px;"></div>
            <div class="shimmer" style="height:52px;margin-top:8px;"></div>
        `;
    }

    function renderW1Empty() {
        w1.resultsWrap.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🤖</div>
                <p>Paste code on the left and click Audit Code</p>
            </div>`;
    }

    function renderW1Results(data) {
        const gradeColors = {
            A: "#22c55e", B: "#3b82f6", C: "#eab308", D: "#f97316", F: "#ef4444"
        };
        const gradeColor = gradeColors[data.grade] || "#888";

        // Issues HTML
        const issuesHTML = (data.issues?.length > 0)
            ? data.issues.map(issue => `
                <div class="issue-card" data-severity="${issue.severity}">
                    <div class="issue-header">
                        <span class="issue-type">${issue.type}</span>
                        <span class="issue-line">Line ${issue.line || "?"}</span>
                    </div>
                    <div class="issue-desc">${issue.description}</div>
                    <div class="issue-fix">💡 ${issue.suggestion}</div>
                </div>`).join("")
            : `<p style="color:var(--green);font-size:0.8rem;">✨ No issues found!</p>`;

        // Positives HTML
        const positivesHTML = (data.positives?.length > 0)
            ? `<ul class="positives-list">${data.positives.map(p => `<li>${p}</li>`).join("")}</ul>`
            : `<p style="color:var(--text-muted);font-size:0.78rem;">—</p>`;

        w1.resultsWrap.innerHTML = `
            <div class="score-card">
                <div class="grade-circle" style="background:${gradeColor}">${data.grade || "?"}</div>
                <div class="score-details">
                    <h2>${data.score || 0}/100</h2>
                    <p>${data.summary || "No summary."}</p>
                </div>
            </div>

            <div class="metrics-row">
                <div class="metric-card red">
                    <div class="metric-value">${data.metrics?.critical || 0}</div>
                    <div class="metric-label">Critical</div>
                </div>
                <div class="metric-card yellow">
                    <div class="metric-value">${data.metrics?.warnings || 0}</div>
                    <div class="metric-label">Warnings</div>
                </div>
                <div class="metric-card blue">
                    <div class="metric-value">${data.metrics?.info || 0}</div>
                    <div class="metric-label">Info</div>
                </div>
            </div>

            <div>
                <div class="section-title">Issues (${data.metrics?.totalIssues || 0})</div>
                ${issuesHTML}
            </div>

            <div>
                <div class="section-title">Positives</div>
                ${positivesHTML}
            </div>

            <div class="section-title" style="margin-top:4px;">Fix Time Estimate</div>
            <p style="font-size:0.78rem;color:var(--text-secondary);">
                ⏱ ${data.metrics?.estimatedFixTime || "N/A"}
            </p>
        `;
    }


    // ════════════════════════════════════════════════════════
    //  TEST GENERATOR
    // ════════════════════════════════════════════════════════

    const w2 = {
        codeInput:   document.getElementById("testCodeInput"),
        langSelect:  document.getElementById("testLanguageSelect"),
        funcInput:   document.getElementById("functionNameInput"),
        generateBtn: document.getElementById("generateTestBtn"),
        btnText:     document.querySelector(".btn-text-test"),
        spinner:     document.getElementById("w2Spinner"),
        codeDisplay: document.getElementById("testCodeDisplay"),
        fileName:    document.getElementById("testFileNameDisplay"),
        resultsWrap: document.getElementById("w2Results"),
        emptyState:  document.getElementById("w2EmptyState"),
        errorBanner: document.getElementById("w2ErrorBanner"),
        mockToggle:  document.getElementById("includeMocks"),
        fixtureToggle: document.getElementById("includeFixtures"),
    };

    // State
    let selectedDepth = "standard";
    let lastTestResults = null; // cached for syntax check and copy

    // Language → file extension map
    const testExtMap = { python:"py", javascript:"js", typescript:"ts", java:"java" };

    function w2UpdateViewer() {
        const lang = w2.langSelect.value.split(" ")[0]; // "python" from "python → pytest"
        w2.codeDisplay.className = `language-${lang}`;
        w2.codeDisplay.textContent = w2.codeInput.value || "# Paste your code here...";
        hljs.highlightElement(w2.codeDisplay);
        w2.fileName.textContent = `untitled.${testExtMap[lang] || lang}`;
    }

    w2.codeInput.addEventListener("input", w2UpdateViewer);
    w2.langSelect.addEventListener("change", w2UpdateViewer);
    w2UpdateViewer();

    // ── Depth pill selection ──
    document.querySelectorAll(".depth-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            document.querySelectorAll(".depth-pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            selectedDepth = pill.dataset.depth;
        });
    });

    // ── Generate Tests button ──
    w2.generateBtn.addEventListener("click", async () => {
        const code = w2.codeInput.value.trim();
        const lang = w2.langSelect.value.split(" ")[0];
        const funcName = w2.funcInput.value.trim();

        if (!code) { showW2Error("Please paste some code to generate tests for."); return; }

        w2SetLoading(true);
        clearW2Error();
        renderW2Loading();

        const body = {
            code,
            language: lang,
            test_depth: selectedDepth,
            include_mocks: w2.mockToggle.checked,
            include_fixtures: w2.fixtureToggle.checked,
        };
        if (funcName) body.function_name = funcName;

        try {
            const res = await fetch(`${API_BASE}/api/test/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Server error ${res.status}`);
            }

            const data = await res.json();
            lastTestResults = data;
            renderW2Results(data);

        } catch (err) {
            showW2Error(err.message);
            renderW2Empty();
        } finally {
            w2SetLoading(false);
        }
    });

    function w2SetLoading(on) {
        w2.generateBtn.disabled = on;
        w2.spinner.classList.toggle("visible", on);
        w2.btnText.textContent = on ? "Generating..." : "Generate Tests";
    }

    function showW2Error(msg) {
        w2.errorBanner.textContent = `⚠ ${msg}`;
        w2.errorBanner.classList.add("visible");
    }
    function clearW2Error() { w2.errorBanner.classList.remove("visible"); }

    function renderW2Loading() {
        w2.resultsWrap.innerHTML = `
            <div class="shimmer" style="height:90px;"></div>
            <div class="shimmer" style="height:40px;margin-top:8px;"></div>
            <div class="shimmer" style="height:60px;margin-top:8px;"></div>
            <div class="shimmer" style="height:60px;margin-top:8px;"></div>
            <div class="shimmer" style="height:60px;margin-top:8px;"></div>
        `;
    }

    function renderW2Empty() {
        w2.resultsWrap.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🧪</div>
                <p>Paste code on the left and click Generate Tests</p>
            </div>`;
    }

    // ─────────────────────────────────────────────────────────
    //  MAIN RENDER — assembles all sub-sections
    // ─────────────────────────────────────────────────────────
    function renderW2Results(data) {
        const lang = data.language || "python";
        const totalTests = data.totalTests || 0;
        const coverage   = data.coverage   || "~0%";
        const framework  = data.framework  || "pytest";

        // ── 1. Summary card ──────────────────────────────────
        const summaryHTML = `
            <div class="test-summary-card">
                <div class="test-count-circle">${totalTests}</div>
                <div class="test-meta">
                    <h2>${totalTests} Test${totalTests !== 1 ? "s" : ""} Generated</h2>
                    <p>${data.notes || "—"}</p>
                    <div class="test-badges">
                        <span class="test-badge badge-framework">${framework}</span>
                        <span class="test-badge badge-coverage">${coverage} coverage</span>
                        <span class="test-badge badge-lang">${lang}</span>
                    </div>
                </div>
            </div>`;

        // ── 2. Coverage bar ──────────────────────────────────
        const pctNum = parseInt(coverage.replace(/\D/g, "")) || 0;
        const coverageHTML = `
            <div class="coverage-bar-wrap">
                <div class="coverage-bar-label">
                    <span>Estimated Coverage</span>
                    <span class="coverage-pct">${coverage}</span>
                </div>
                <div class="coverage-bar-track">
                    <div class="coverage-bar-fill" id="coverageFill" style="width:0%"></div>
                </div>
            </div>`;

        // ── 3. Type breakdown ────────────────────────────────
        const typeConfig = {
            happy_path:  { label: "Happy Path",  color: "var(--green)",  bg: "var(--green-dim)" },
            edge_case:   { label: "Edge Case",   color: "var(--yellow)", bg: "var(--yellow-dim)" },
            error_case:  { label: "Error Case",  color: "var(--red)",    bg: "var(--red-dim)" },
            security:    { label: "Security",    color: "var(--purple)", bg: "var(--purple-dim)" },
        };

        const typeCounts = {};
        (data.testCases || []).forEach(tc => {
            typeCounts[tc.type] = (typeCounts[tc.type] || 0) + 1;
        });

        const breakdownHTML = Object.entries(typeCounts).length > 0
            ? `<div class="breakdown-row">
                ${Object.entries(typeCounts).map(([type, count]) => {
                    const cfg = typeConfig[type] || { label: type, color: "#888", bg: "#88880a" };
                    return `<div class="breakdown-pill">
                        <div class="breakdown-dot" style="background:${cfg.color}"></div>
                        <span>${cfg.label}</span>
                        <strong>${count}</strong>
                    </div>`;
                }).join("")}
               </div>`
            : "";

        // ── 4. Detected functions ─────────────────────────────
        const funcsHTML = (data.detectedFunctions?.length > 0)
            ? `<div>
                <div class="section-title">Detected Functions</div>
                <div class="func-chips">
                    ${data.detectedFunctions.map(f => `<span class="func-chip">${f}()</span>`).join("")}
                </div>
               </div>`
            : "";

        // ── 5. Test cases ─────────────────────────────────────
        const testCasesHTML = renderTestCases(data.testCases || [], data.testFile || "", lang);

        // ── 6. Test file ──────────────────────────────────────
        const testFileHTML = renderTestFile(data.testFile || "", data.requestedLanguage || lang);

        // ── 7. Syntax check section ───────────────────────────
        // This renders a pending state and then triggers the API call
        const syntaxCheckHTML = `
            <div class="syntax-check-wrap" id="syntaxCheckWrap">
                <div class="syntax-check-row">
                    <div class="syntax-dot pending"></div>
                    <span class="syntax-message">Checking syntax...</span>
                </div>
            </div>`;

        // ── 8. Setup instructions ─────────────────────────────
        const setupHTML = `
            <div class="setup-block">
                <div class="section-title">⚡ How to Run</div>
                <pre>${escapeHtml(data.setupInstructions || "pytest tests/ -v")}</pre>
            </div>`;

        // ── 9. Missing coverage ───────────────────────────────
        const missingHTML = (data.missingForFullCoverage?.length > 0)
            ? `<div>
                <div class="section-title">For 100% Coverage, Also Test</div>
                <ul class="missing-list">
                    ${data.missingForFullCoverage.map(m => `<li>${m}</li>`).join("")}
                </ul>
               </div>`
            : "";

        // ── Assemble all sections ──────────────────────────────
        w2.resultsWrap.innerHTML = `
            ${summaryHTML}
            ${coverageHTML}
            ${breakdownHTML}
            ${funcsHTML}
            <div>
                <div class="section-title">Test Cases (${totalTests})</div>
                ${testCasesHTML}
            </div>
            ${testFileHTML}
            ${syntaxCheckHTML}
            ${setupHTML}
            ${missingHTML}
        `;

        // Animate coverage bar after render
        requestAnimationFrame(() => {
            const fill = document.getElementById("coverageFill");
            if (fill) fill.style.width = `${Math.min(pctNum, 100)}%`;
        });

        // Trigger async syntax check
        if (data.testFile) {
            runSyntaxCheck(data.testFile, data.requestedLanguage || lang);
        }
    }

    // ─────────────────────────────────────────────────────────
    //  RENDER TEST CASES — individual expandable cards
    // ─────────────────────────────────────────────────────────
    function renderTestCases(testCases, fullTestFile, language) {
        if (!testCases.length) {
            return `<p style="font-size:0.78rem;color:var(--text-muted);">No test cases returned.</p>`;
        }

        return testCases.map((tc, idx) => {
            const type = tc.type || "happy_path";
            const typeLabels = {
                happy_path: "Happy Path",
                edge_case:  "Edge Case",
                error_case: "Error Case",
                security:   "Security",
            };
            const typeLabel = typeLabels[type] || type.replace(/_/g, " ");

            // Try to extract this test's code snippet from the full test file
            // by searching for the function name
            const testSnippet = extractTestSnippet(tc.name, fullTestFile);

            return `
                <div class="test-case-card" data-type="${type}" 
                     onclick="explainTest('${escapeAttr(tc.name)}', '${escapeAttr(testSnippet)}', '${language}')"
                     title="Click to get an AI explanation of this test">
                    <div class="test-case-header">
                        <span class="test-case-name">${idx + 1}. ${tc.name}</span>
                        <span class="type-badge type-${type}">${typeLabel}</span>
                    </div>
                    <div class="test-case-desc">${tc.description}</div>
                    <div class="test-io-row">
                        <div class="test-io-chip"><span>Input:</span><em>${tc.inputs || "—"}</em></div>
                        <div class="test-io-chip"><span>Expects:</span><em>${tc.expectedOutput || "—"}</em></div>
                        ${tc.complexity ? `<div class="test-io-chip"><span>Complexity:</span><em>${tc.complexity}</em></div>` : ""}
                    </div>
                    <div style="font-size:0.68rem;color:var(--text-muted);margin-top:4px;">💡 Click for AI explanation</div>
                </div>`;
        }).join("");
    }

    // ─────────────────────────────────────────────────────────
    //  RENDER TEST FILE — code block with copy button
    // ─────────────────────────────────────────────────────────
    function renderTestFile(testFileContent, language) {
        const escaped = escapeHtml(testFileContent);
        return `
            <div class="test-file-wrap">
                <div class="test-file-header">
                    <span class="test-file-title">📄 Complete Test File</span>
                    <button class="copy-btn" id="copyBtn" onclick="copyTestFile()">Copy</button>
                </div>
                <pre class="test-file-code" id="testFileBlock">${escaped}</pre>
            </div>`;
    }

    // ─────────────────────────────────────────────────────────
    //  SYNTAX CHECK — calls /api/test/run-check async
    // ─────────────────────────────────────────────────────────
    async function runSyntaxCheck(testCode, language) {
        const wrap = document.getElementById("syntaxCheckWrap");
        if (!wrap) return;

        try {
            const res = await fetch(`${API_BASE}/api/test/run-check`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ test_code: testCode, language }),
            });

            if (!res.ok) throw new Error();
            const data = await res.json();

            const dotClass = data.valid === true ? "ok" : data.valid === false ? "error" : "pending";
            const msg = data.message || "Check complete";
            const warningsHTML = (data.warnings || []).map(w =>
                `<div class="syntax-warning">⚠ ${w}</div>`).join("");
            const errorsHTML = (data.errors || []).map(e =>
                `<div class="syntax-error-msg">✗ ${e}</div>`).join("");
            const funcCount = data.testCount > 0
                ? `<span style="color:var(--green);font-size:0.72rem;margin-left:auto;">${data.testCount} test functions found</span>`
                : "";

            wrap.innerHTML = `
                <div class="syntax-check-row">
                    <div class="syntax-dot ${dotClass}"></div>
                    <span class="syntax-message">${msg}</span>
                    ${funcCount}
                </div>
                ${warningsHTML}
                ${errorsHTML}
            `;
        } catch (err) {
            const wrap = document.getElementById("syntaxCheckWrap");
            if (wrap) wrap.innerHTML = `
                <div class="syntax-check-row">
                    <div class="syntax-dot pending"></div>
                    <span class="syntax-message" style="color:var(--text-muted)">Syntax check unavailable</span>
                </div>`;
        }
    }


    // ════════════════════════════════════════════════════════
    //  SECURITY AUDIT
    // ════════════════════════════════════════════════════════
    const audit = {
        codeInput:   document.getElementById("auditCodeInput"),
        langSelect:  document.getElementById("auditLanguageSelect"),
        analyzeBtn:  document.getElementById("runAuditBtn"),
        btnText:     document.querySelector(".btn-text-audit"),
        spinner:     document.getElementById("auditSpinner"),
        codeDisplay: document.getElementById("auditCodeDisplay"),
        fileName:    document.getElementById("auditFileNameDisplay"),
        resultsWrap: document.getElementById("auditResults"),
        emptyState:  document.getElementById("auditEmptyState"),
        errorBanner: document.getElementById("auditErrorBanner"),
    };

    function auditUpdateViewer() {
        const lang = audit.langSelect.value;
        audit.codeDisplay.className = `language-${lang}`;
        audit.codeDisplay.textContent = audit.codeInput.value || "# Paste your code here...";
        hljs.highlightElement(audit.codeDisplay);
        audit.fileName.textContent = `untitled.${extMap[lang] || lang}`;
    }

    audit.codeInput.addEventListener("input", auditUpdateViewer);
    audit.langSelect.addEventListener("change", auditUpdateViewer);

    audit.analyzeBtn.addEventListener("click", async () => {
        const code = audit.codeInput.value.trim();
        const lang = audit.langSelect.value;

        if (!code) { showAuditError("Please paste some code to scan."); return; }

        auditSetLoading(true);
        clearAuditError();
        renderAuditLoading();

        try {
            const res = await fetch(`${API_BASE}/api/audit/`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, language: lang }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || `Server error ${res.status}`);
            }

            renderAuditResults(await res.json());

        } catch (err) {
            showAuditError(err.message);
            renderAuditEmpty();
        } finally {
            auditSetLoading(false);
        }
    });

    function auditSetLoading(on) {
        audit.analyzeBtn.disabled = on;
        audit.spinner.classList.toggle("visible", on);
        audit.btnText.textContent = on ? "Scanning..." : "Run Security Scan";
    }

    function showAuditError(msg) {
        audit.errorBanner.textContent = `⚠ ${msg}`;
        audit.errorBanner.classList.add("visible");
    }
    function clearAuditError() { audit.errorBanner.classList.remove("visible"); }

    function renderAuditLoading() {
        audit.resultsWrap.innerHTML = `
            <div class="shimmer" style="height:100px;"></div>
            <div class="shimmer" style="height:60px;margin-top:8px;"></div>
            <div class="shimmer" style="height:150px;margin-top:8px;"></div>
            <div class="shimmer" style="height:150px;margin-top:8px;"></div>
        `;
    }

    function renderAuditEmpty() {
        audit.resultsWrap.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon" style="filter:none;">🛡️</div>
                <p>Paste code on the left and click Run Security Scan</p>
            </div>`;
    }
    
    function renderAuditResults(data) {
        const stats = data.statistics || { critical:0, high:0, medium:0, low:0, totalVulnerabilities:0 };
        const score = data.riskScore ?? 100;
        const level = data.riskLevel ?? "UNKNOWN";
        
        let scoreColor = "var(--green)";
        if (score < 30) scoreColor = "var(--red)";
        else if (score <= 55) scoreColor = "var(--orange)";
        else if (score <= 75) scoreColor = "var(--yellow)";
        
        const summaryHTML = `
            <div class="score-card" style="border-color:${scoreColor}40;">
                <div class="grade-circle" style="background:${scoreColor}; font-size:1.4rem;">${score}</div>
                <div class="score-details">
                    <h2 style="color:${scoreColor}">${level} RISK</h2>
                    <p>${data.executiveSummary || "Scan completed."}</p>
                </div>
            </div>
            <div class="metrics-row">
                <div class="metric-card red">
                    <div class="metric-value">${stats.critical}</div>
                    <div class="metric-label">Critical</div>
                </div>
                <div class="metric-card" style="color:var(--orange)">
                    <div class="metric-value">${stats.high}</div>
                    <div class="metric-label">High</div>
                </div>
                <div class="metric-card yellow">
                    <div class="metric-value">${stats.medium}</div>
                    <div class="metric-label">Medium</div>
                </div>
                <div class="metric-card blue">
                    <div class="metric-value">${stats.low}</div>
                    <div class="metric-label">Low</div>
                </div>
            </div>
        `;
        
        let vulnHTML = "";
        const vulns = data.vulnerabilities || [];
        if (vulns.length === 0) {
            vulnHTML = `<p style="color:var(--green);font-size:0.8rem;margin-top:12px;">✨ No obvious security vulnerabilities detected!</p>`;
        } else {
            vulnHTML = vulns.map(v => {
                const sevLevel = (v.severity || "info").toLowerCase();
                let stripColor = "var(--blue)";
                if (sevLevel === "critical") stripColor = "var(--red)";
                else if (sevLevel === "high") stripColor = "var(--orange)";
                else if (sevLevel === "medium" || sevLevel === "warning") stripColor = "var(--yellow)";
                
                return `
                <div class="issue-card" style="border-left-color:${stripColor}; margin-top:8px;">
                    <div class="issue-header">
                        <span class="issue-type" style="color:${stripColor}">${v.category || "Vulnerability"} ${v.cweId ? '('+v.cweId+')' : ''}</span>
                        <span class="issue-line">Line ${v.line || "?"}</span>
                    </div>
                    <div class="issue-desc" style="font-weight:600;">${v.subtype || v.description}</div>
                    ${v.evidence ? `<div class="test-file-code" style="padding:6px; margin:4px 0; font-size:0.65rem;">${escapeHtml(v.evidence)}</div>` : ""}
                    ${v.attackScenario ? `<div class="issue-desc" style="color:var(--text-muted); font-size:0.7rem; margin-top:4px;"><b>Attack Scenario:</b> ${v.attackScenario}</div>` : ""}
                    <div class="issue-fix" style="margin-top:6px;">🛠️ ${v.remediation}</div>
                    ${v.secureExample ? `<div class="test-file-code" style="padding:6px; margin:4px 0; font-size:0.65rem; background:#121812; color:var(--green);">${escapeHtml(v.secureExample)}</div>` : ""}
                </div>`;
            }).join("");
            vulnHTML = `<div style="margin-top:16px"><div class="section-title">Vulnerabilities (${stats.totalVulnerabilities})</div>${vulnHTML}</div>`;
        }

        audit.resultsWrap.innerHTML = summaryHTML + vulnHTML;
    }

    // ════════════════════════════════════════════════════════
    //  REPO INTELLIGENCE
    // ════════════════════════════════════════════════════════

    const repoBtn = document.getElementById("analyzeRepoBtn");
    const repoSpinner = document.getElementById("repoSpinner");
    const repoBtnText = document.querySelector(".btn-text-repo");

    repoBtn.addEventListener("click", async () => {
        const url = document.getElementById("repoUrlInput").value.trim();
        const branch = document.getElementById("repoBranchInput").value.trim() || "main";
        const errBanner = document.getElementById("repoErrorBanner");
        const results = document.getElementById("repoResults");

        if (!url) { errBanner.textContent = "Please enter a GitHub repo URL"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");

        repoBtn.disabled = true;
        repoSpinner.classList.add("visible");
        repoBtnText.textContent = "Cloning & Analyzing...";
        results.innerHTML = '<div class="shimmer" style="height:100px;"></div><div class="shimmer" style="height:60px;margin-top:8px;"></div><div class="shimmer" style="height:200px;margin-top:8px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/repo/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_url: url, branch })
            });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Failed"); }
            renderRepoResults(await res.json());
        } catch (err) {
            errBanner.textContent = `Error: ${err.message}`;
            errBanner.classList.add("visible");
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Analysis failed. Check the URL and try again.</p></div>';
        } finally {
            repoBtn.disabled = false;
            repoSpinner.classList.remove("visible");
            repoBtnText.textContent = "Analyze Repository";
        }
    });

    function renderRepoResults(data) {
        const scan = data.scan || {};
        const analysis = data.analysis || {};
        const langs = scan.languages || {};
        const topLang = Object.entries(langs).sort((a,b) => b[1]-a[1]);
        const fws = scan.frameworks || [];

        const langsHTML = topLang.map(([l, lines]) =>
            `<span class="fw-chip">${l} <strong>${lines.toLocaleString()} lines</strong></span>`
        ).join("");

        const fwHTML = fws.map(fw =>
            `<span class="fw-chip">${fw.name} ${fw.version || ""}</span>`
        ).join("") || '<span style="color:var(--text-muted);font-size:0.78rem;">None detected</span>';

        const filesHTML = (scan.files || []).slice(0, 30).map(f =>
            `<tr><td style="font-family:var(--font-code);font-size:0.72rem;">${escapeHtml(f.path)}</td><td>${f.language}</td><td>${f.lines}</td><td><span class="fw-chip">${f.role}</span></td></tr>`
        ).join("");

        const scores = analysis.scores || {};
        const scoreBarHTML = Object.entries(scores).map(([key, val]) => {
            const color = val >= 80 ? "var(--green)" : val >= 60 ? "var(--yellow)" : "var(--red)";
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="score-bar-row"><span class="bar-label">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${val}%;background:${color};"></div></div><span class="bar-value">${val}</span></div>`;
        }).join("");

        const recsHTML = (analysis.recommendations || []).map((r, i) =>
            `<div class="issue-card" style="border-left-color:var(--accent);"><div class="issue-header"><span class="issue-type">#${i+1} ${r.title || ""}</span><span class="issue-line">${r.impact || ""}</span></div><div class="issue-desc">${r.description || ""}</div></div>`
        ).join("");

        document.getElementById("repoResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card"><h3>Repository</h3><p style="font-size:1rem;font-weight:700;color:var(--accent);">${data.repository}</p><p>Branch: ${data.branch} | ${scan.totalFiles || 0} files | ${(scan.totalLines||0).toLocaleString()} lines</p></div>
                <div class="result-card"><h3>Architecture</h3><p style="font-weight:700;color:var(--text-primary);">${(scan.architecture||{}).pattern||"Unknown"}</p><p>${(scan.architecture||{}).description||""}</p></div>
                <div class="result-card"><h3>Test Coverage</h3><p style="font-size:1.2rem;font-weight:800;color:${(scan.testCoverage||{}).ratio > 50 ? 'var(--green)':'var(--yellow)'};">${(scan.testCoverage||{}).ratio||0}%</p><p>${(scan.testCoverage||{}).testCount||0} test files / ${(scan.testCoverage||{}).sourceCount||0} source files</p></div>
            </div>
            <div class="result-card"><h3>Languages</h3><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">${langsHTML}</div></div>
            <div class="result-card"><h3>Frameworks & Tools</h3><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">${fwHTML}</div></div>
            ${scoreBarHTML ? `<div class="result-card"><h3>Scores</h3><div style="display:flex;flex-direction:column;gap:8px;margin-top:8px;">${scoreBarHTML}</div></div>` : ""}
            ${analysis.techStackSummary ? `<div class="result-card"><h3>Tech Stack Analysis</h3><p>${analysis.techStackSummary}</p></div>` : ""}
            ${recsHTML ? `<div class="result-card"><h3>Recommendations</h3>${recsHTML}</div>` : ""}
            <div class="result-card"><h3>File Structure (Top 30)</h3><table class="file-table"><thead><tr><th>Path</th><th>Language</th><th>Lines</th><th>Role</th></tr></thead><tbody>${filesHTML}</tbody></table></div>
        `;
    }


    // ════════════════════════════════════════════════════════
    //  DEPENDENCY SCANNER
    // ════════════════════════════════════════════════════════

    const depsBtn = document.getElementById("scanDepsBtn");
    const depsSpinner = document.getElementById("depsSpinner");
    const depsBtnText = document.querySelector(".btn-text-deps");

    depsBtn.addEventListener("click", async () => {
        const manifest = document.getElementById("depsManifestInput").value.trim();
        const mType = document.getElementById("depsManifestType").value;
        const errBanner = document.getElementById("depsErrorBanner");
        const results = document.getElementById("depsResults");

        if (!manifest) { errBanner.textContent = "Please paste manifest content"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");

        depsBtn.disabled = true;
        depsSpinner.classList.add("visible");
        depsBtnText.textContent = "Scanning CVEs...";
        results.innerHTML = '<div class="shimmer" style="height:80px;"></div><div class="shimmer" style="height:200px;margin-top:8px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/dependencies/scan`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ manifest_content: manifest, manifest_type: mType })
            });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Failed"); }
            renderDepsResults(await res.json());
        } catch (err) {
            errBanner.textContent = `Error: ${err.message}`;
            errBanner.classList.add("visible");
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Scan failed. Check your manifest content.</p></div>';
        } finally {
            depsBtn.disabled = false;
            depsSpinner.classList.remove("visible");
            depsBtnText.textContent = "Scan Dependencies";
        }
    });

    function renderDepsResults(data) {
        const analysis = data.analysis || {};
        const healthScore = analysis.healthScore || 0;
        const scoreColor = healthScore >= 80 ? "var(--green)" : healthScore >= 60 ? "var(--yellow)" : "var(--red)";

        const pkgsHTML = (data.packages || []).map(pkg => {
            const vulnBadge = pkg.vulnerable
                ? `<span style="color:var(--red);font-weight:700;">⚠ ${pkg.vulnCount} vulnerabilities</span>`
                : `<span style="color:var(--green);">✓ Secure</span>`;
            const vulnDetails = (pkg.vulnerabilities || []).map(v =>
                `<div style="margin-left:12px;padding:4px 0;font-size:0.72rem;border-bottom:1px solid var(--border-subtle);">
                    <span style="color:${v.severity==='critical'?'var(--red)':v.severity==='high'?'var(--orange)':'var(--yellow)'};font-weight:700;">${v.severity.toUpperCase()}</span>
                    <span style="color:var(--text-muted);margin-left:6px;">${v.cve || v.id}</span>
                    <div style="color:var(--text-secondary);margin-top:2px;">${v.summary}</div>
                    ${v.fixedIn ? `<div style="color:var(--green);margin-top:2px;">Fixed in: ${v.fixedIn}</div>` : ""}
                </div>`
            ).join("");

            return `<tr>
                <td style="font-family:var(--font-code);font-size:0.75rem;font-weight:600;">${pkg.name}</td>
                <td>${pkg.version}</td>
                <td>${pkg.ecosystem}</td>
                <td>${vulnBadge}${vulnDetails}</td>
            </tr>`;
        }).join("");

        const upgradeHTML = (analysis.upgradeRecommendations || []).map(u =>
            `<div class="issue-card" style="border-left-color:${u.priority==='high'?'var(--red)':u.priority==='medium'?'var(--yellow)':'var(--blue)'};">
                <div class="issue-header"><span class="issue-type">${u.package}</span><span class="issue-line">${u.current} → ${u.recommended}</span></div>
                <div class="issue-desc">${u.reason}</div>
                ${u.breakingChanges ? '<div style="color:var(--orange);font-size:0.72rem;">⚠ May include breaking changes</div>' : ''}
            </div>`
        ).join("");

        document.getElementById("depsResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;">
                    <div class="score-ring" style="border-color:${scoreColor}40;margin:8px auto;">
                        <div class="score-num" style="color:${scoreColor};">${healthScore}</div>
                        <div class="score-label">Health</div>
                    </div>
                </div>
                <div class="result-card"><h3>Summary</h3>
                    <div class="metrics-row" style="margin-top:8px;">
                        <div class="metric-card red"><div class="metric-value">${data.criticalCount || 0}</div><div class="metric-label">Critical</div></div>
                        <div class="metric-card yellow"><div class="metric-value">${data.totalVulnerabilities || 0}</div><div class="metric-label">Total Vulns</div></div>
                        <div class="metric-card blue"><div class="metric-value">${data.totalPackages || 0}</div><div class="metric-label">Packages</div></div>
                    </div>
                </div>
                <div class="result-card"><h3>Manifest</h3><p>${data.manifestType || "auto"}</p><p style="margin-top:4px;">${analysis.summary || ""}</p></div>
            </div>
            ${upgradeHTML ? `<div class="result-card"><h3>Upgrade Recommendations</h3>${upgradeHTML}</div>` : ""}
            <div class="result-card"><h3>All Packages</h3><table class="file-table"><thead><tr><th>Package</th><th>Version</th><th>Ecosystem</th><th>Status</th></tr></thead><tbody>${pkgsHTML}</tbody></table></div>
        `;
    }


    // ════════════════════════════════════════════════════════
    //  BRANCH COMPARE
    // ════════════════════════════════════════════════════════

    const branchBtn = document.getElementById("compareBranchBtn");
    const branchSpinner = document.getElementById("branchSpinner");
    const branchBtnText = document.querySelector(".btn-text-branch");

    branchBtn.addEventListener("click", async () => {
        const url = document.getElementById("branchRepoUrl").value.trim();
        const base = document.getElementById("baseBranchInput").value.trim() || "main";
        const head = document.getElementById("headBranchInput").value.trim();
        const errBanner = document.getElementById("branchErrorBanner");
        const results = document.getElementById("branchResults");

        if (!url || !head) { errBanner.textContent = "Please enter repo URL and head branch name"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");

        branchBtn.disabled = true;
        branchSpinner.classList.add("visible");
        branchBtnText.textContent = "Comparing...";
        results.innerHTML = '<div class="shimmer" style="height:80px;"></div><div class="shimmer" style="height:200px;margin-top:8px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/branch/compare`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_url: url, base_branch: base, head_branch: head })
            });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Failed"); }
            renderBranchResults(await res.json());
        } catch (err) {
            errBanner.textContent = `Error: ${err.message}`;
            errBanner.classList.add("visible");
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Comparison failed. Check repo URL and branch names.</p></div>';
        } finally {
            branchBtn.disabled = false;
            branchSpinner.classList.remove("visible");
            branchBtnText.textContent = "Compare Branches";
        }
    });

    function renderBranchResults(data) {
        const analysis = data.analysis || {};
        const verdict = analysis.verdict || "NEEDS_REVIEW";
        const changedFiles = data.changedFiles || [];
        const commits = data.commits || [];
        const issues = analysis.issues || [];

        const filesHTML = changedFiles.map(f => {
            const statusColors = { added: "var(--green)", modified: "var(--yellow)", deleted: "var(--red)" };
            return `<tr><td style="font-family:var(--font-code);font-size:0.72rem;">${escapeHtml(f.path)}</td><td><span style="color:${statusColors[f.status]||'var(--text-muted)'};font-weight:700;">${f.status}</span></td></tr>`;
        }).join("");

        const commitsHTML = commits.slice(0, 15).map(c =>
            `<div style="display:flex;gap:8px;align-items:baseline;padding:4px 0;border-bottom:1px solid var(--border-subtle);font-size:0.76rem;">
                <span style="font-family:var(--font-code);color:var(--accent);font-size:0.72rem;">${c.hash}</span>
                <span style="color:var(--text-primary);flex:1;">${escapeHtml(c.message)}</span>
                <span style="color:var(--text-muted);font-size:0.68rem;white-space:nowrap;">${c.author}</span>
            </div>`
        ).join("");

        const issuesHTML = issues.map(issue => {
            const sevColors = { critical: "var(--red)", high: "var(--orange)", medium: "var(--yellow)", low: "var(--blue)" };
            return `<div class="issue-card" style="border-left-color:${sevColors[issue.severity]||'var(--border)'};">
                <div class="issue-header">
                    <span class="issue-type">${issue.type || "issue"}</span>
                    <span class="issue-line" style="color:${sevColors[issue.severity]||'var(--text-muted)'};font-weight:700;">${(issue.severity||"").toUpperCase()}</span>
                </div>
                <div class="issue-desc">${issue.description || ""}</div>
                ${issue.file ? `<div style="font-family:var(--font-code);font-size:0.68rem;color:var(--text-muted);margin:2px 0;">${issue.file}</div>` : ""}
                ${issue.impact ? `<div style="font-size:0.72rem;color:var(--orange);margin-top:2px;">Impact: ${issue.impact}</div>` : ""}
                ${issue.suggestion ? `<div class="issue-fix">Fix: ${issue.suggestion}</div>` : ""}
            </div>`;
        }).join("");

        const positivesHTML = (analysis.positives || []).map(p => `<li>${p}</li>`).join("");

        document.getElementById("branchResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;">
                    <div class="verdict-badge verdict-${verdict}">${verdict.replace(/_/g, " ")}</div>
                    <p style="margin-top:8px;">${analysis.summary || ""}</p>
                </div>
                <div class="result-card"><h3>Changes</h3>
                    <div class="metrics-row" style="margin-top:8px;">
                        <div class="metric-card blue"><div class="metric-value">${changedFiles.length}</div><div class="metric-label">Files</div></div>
                        <div class="metric-card"><div class="metric-value">${commits.length}</div><div class="metric-label">Commits</div></div>
                        <div class="metric-card red"><div class="metric-value">${issues.length}</div><div class="metric-label">Issues</div></div>
                    </div>
                </div>
            </div>
            ${issuesHTML ? `<div class="result-card"><h3>Issues Found (${issues.length})</h3>${issuesHTML}</div>` : '<div class="result-card"><h3>Issues</h3><p style="color:var(--green);">No issues found in this diff</p></div>'}
            ${positivesHTML ? `<div class="result-card"><h3>Positives</h3><ul class="positives-list">${positivesHTML}</ul></div>` : ""}
            ${commitsHTML ? `<div class="result-card"><h3>Commits (${commits.length})</h3>${commitsHTML}</div>` : ""}
            ${filesHTML ? `<div class="result-card"><h3>Changed Files</h3><table class="file-table"><thead><tr><th>File</th><th>Status</th></tr></thead><tbody>${filesHTML}</tbody></table></div>` : ""}
            ${(analysis.testingRecommendations||[]).length ? `<div class="result-card"><h3>Testing Recommendations</h3><ul class="missing-list">${analysis.testingRecommendations.map(t=>`<li>${t}</li>`).join("")}</ul></div>` : ""}
        `;
    }


    // ════════════════════════════════════════════════════════
    //  HEALTH DASHBOARD
    // ════════════════════════════════════════════════════════

    const dashBtn = document.getElementById("generateDashboardBtn");
    const dashSpinner = document.getElementById("dashboardSpinner");
    const dashBtnText = document.querySelector(".btn-text-dashboard");

    dashBtn.addEventListener("click", async () => {
        const url = document.getElementById("dashboardRepoUrl").value.trim();
        const branch = document.getElementById("dashboardBranchInput").value.trim() || "main";
        const errBanner = document.getElementById("dashboardErrorBanner");
        const results = document.getElementById("dashboardResults");

        if (!url) { errBanner.textContent = "Please enter a GitHub repo URL"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");

        dashBtn.disabled = true;
        dashSpinner.classList.add("visible");
        dashBtnText.textContent = "Analyzing Full Repo...";
        results.innerHTML = '<div class="shimmer" style="height:120px;"></div><div class="shimmer" style="height:80px;margin-top:8px;"></div><div class="shimmer" style="height:200px;margin-top:8px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/dashboard/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo_url: url, branch })
            });
            if (!res.ok) { const e = await res.json(); throw new Error(e.detail || "Failed"); }
            renderDashboard(await res.json());
        } catch (err) {
            errBanner.textContent = `Error: ${err.message}`;
            errBanner.classList.add("visible");
            results.innerHTML = '<div class="empty-state"><div class="empty-icon">❌</div><p>Dashboard generation failed.</p></div>';
        } finally {
            dashBtn.disabled = false;
            dashSpinner.classList.remove("visible");
            dashBtnText.textContent = "Generate Dashboard";
        }
    });

    function renderDashboard(data) {
        const scores = data.scores || {};
        const repoInfo = data.repoInfo || {};
        const overall = data.overallScore || 0;
        const grade = data.grade || "?";
        const gradeColors = { A: "var(--green)", B: "var(--blue)", C: "var(--yellow)", D: "var(--orange)", F: "var(--red)" };
        const overallColor = gradeColors[grade] || "var(--text-muted)";

        const scoreBarHTML = Object.entries(scores).map(([key, val]) => {
            const color = val >= 80 ? "var(--green)" : val >= 60 ? "var(--yellow)" : "var(--red)";
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="score-bar-row"><span class="bar-label">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${val}%;background:${color};"></div></div><span class="bar-value">${val}</span></div>`;
        }).join("");

        const breakdown = data.issueBreakdown || {};
        const fileRisks = (data.fileRisks || []).slice(0, 10);
        const fileRisksHTML = fileRisks.map(f => {
            const color = f.severity==='high' ? 'var(--red)' : f.severity==='medium' ? 'var(--yellow)' : 'var(--blue)';
            return `<div class="issue-card" style="border-left-color:${color};">
                <div class="issue-header"><span class="issue-type" style="font-family:var(--font-code);text-transform:none;">${f.file}</span><span class="issue-line" style="color:${color};font-weight:700;">${f.score}/100</span></div>
                <div class="issue-desc">${(f.issues||[]).join(", ")}</div>
            </div>`;
        }).join("");

        const recsHTML = (data.topRecommendations || []).map((r, i) =>
            `<div class="issue-card" style="border-left-color:var(--accent);">
                <div class="issue-header"><span class="issue-type">#${i+1} ${r.title}</span><span class="issue-line">Impact: ${r.impact} | Effort: ${r.effort}</span></div>
                <div class="issue-desc">${r.description}</div>
            </div>`
        ).join("");

        const categoryHTML = Object.entries(data.categoryDetails || {}).map(([key, cat]) => {
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="result-card">
                <h3>${label} — ${cat.score}/100</h3>
                ${(cat.findings||[]).map(f => `<p style="margin-bottom:4px;">• ${f}</p>`).join("")}
                ${(cat.recommendations||[]).map(r => `<p style="color:var(--green);margin-bottom:4px;">→ ${r}</p>`).join("")}
            </div>`;
        }).join("");

        const techDebt = data.techDebt || {};
        const langsHTML = Object.entries(repoInfo.languages || {}).map(([l, lines]) =>
            `<span class="fw-chip">${l}: ${lines.toLocaleString()}</span>`
        ).join("");

        document.getElementById("dashboardResults").innerHTML = `
            <div class="results-grid" style="grid-template-columns: 200px 1fr 1fr;">
                <div class="result-card" style="text-align:center;">
                    <div class="score-ring" style="border-color:${overallColor};">
                        <div class="score-num" style="color:${overallColor};">${overall}</div>
                        <div class="score-label">Grade ${grade}</div>
                    </div>
                </div>
                <div class="result-card"><h3>Repo Info</h3>
                    <p style="font-weight:700;color:var(--accent);">${repoInfo.name || ""}</p>
                    <p>${repoInfo.totalFiles || 0} files | ${(repoInfo.totalLines||0).toLocaleString()} lines</p>
                    <p>Tests: ${repoInfo.testFiles||0} / Sources: ${repoInfo.sourceFiles||0} (${repoInfo.testRatio||0}%)</p>
                    <div style="margin-top:6px;">${langsHTML}</div>
                </div>
                <div class="result-card"><h3>Issue Breakdown</h3>
                    <div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(4,1fr);">
                        <div class="metric-card red"><div class="metric-value">${breakdown.critical||0}</div><div class="metric-label">Critical</div></div>
                        <div class="metric-card" style="color:var(--orange);"><div class="metric-value">${breakdown.high||0}</div><div class="metric-label">High</div></div>
                        <div class="metric-card yellow"><div class="metric-value">${breakdown.medium||0}</div><div class="metric-label">Medium</div></div>
                        <div class="metric-card blue"><div class="metric-value">${breakdown.low||0}</div><div class="metric-label">Low</div></div>
                    </div>
                </div>
            </div>
            <div class="result-card"><h3>Score Breakdown</h3><div style="display:flex;flex-direction:column;gap:8px;margin-top:8px;">${scoreBarHTML}</div></div>
            ${data.summary ? `<div class="result-card"><h3>Executive Summary</h3><p>${data.summary}</p></div>` : ""}
            ${categoryHTML ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">${categoryHTML}</div>` : ""}
            ${fileRisksHTML ? `<div class="result-card"><h3>Riskiest Files</h3>${fileRisksHTML}</div>` : ""}
            ${recsHTML ? `<div class="result-card"><h3>Top Recommendations</h3>${recsHTML}</div>` : ""}
            ${techDebt.description ? `<div class="result-card"><h3>Technical Debt</h3><p><strong>${techDebt.level || "Unknown"}</strong> — Est. ${techDebt.estimatedHours || "?"} hours</p><p style="margin-top:4px;">${techDebt.description}</p></div>` : ""}
        `;
    }


    // ════════════════════════════════════════════════════════
    //  QA SCANNER
    // ════════════════════════════════════════════════════════
    document.getElementById("scanQaBtn").addEventListener("click", async () => {
        const url = document.getElementById("qaRepoUrl").value.trim();
        const branch = document.getElementById("qaBranch").value.trim() || "main";
        const autoGen = document.getElementById("qaAutoGenerate").checked;
        const errBanner = document.getElementById("qaErrorBanner");
        const results = document.getElementById("qaResults");
        const btn = document.getElementById("scanQaBtn");
        const spinner = document.getElementById("qaSpinner");
        const btnText = document.querySelector(".btn-text-qa");

        if (!url) { errBanner.textContent = "Enter a repo URL"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");
        btn.disabled = true; spinner.classList.add("visible"); btnText.textContent = "Scanning...";
        results.innerHTML = '<div class="shimmer" style="height:80px;"></div><div class="shimmer" style="height:200px;margin-top:8px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/qa/scan`, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({repo_url:url,branch,auto_generate:autoGen,max_generate:5}) });
            if (!res.ok) { const e=await res.json(); throw new Error(e.detail||"Failed"); }
            const data = await res.json();
            const covColor = data.coveragePercent >= 70 ? "var(--green)" : data.coveragePercent >= 40 ? "var(--yellow)" : "var(--red)";

            const mapHTML = (data.coverageMap||[]).slice(0,40).map(f => {
                const sc = {covered:"var(--green)",missing:"var(--red)",empty:"var(--yellow)"};
                return `<tr><td style="font-family:var(--font-code);font-size:0.72rem;">${escapeHtml(f.path)}</td><td>${f.language}</td><td><span style="color:${sc[f.status]||'var(--text-muted)'};font-weight:700;">${f.status.toUpperCase()}</span></td><td style="font-size:0.72rem;color:var(--text-muted);">${f.testFile||'--'}</td></tr>`;
            }).join("");

            const genHTML = (data.generatedTests||[]).map(g => g.error ? '' :
                `<div class="result-card"><h3>${escapeHtml(g.sourceFile)}</h3><p>${g.framework} | ${g.testCount||0} tests | ${g.coverage||'N/A'}</p><pre class="test-file-code" style="max-height:200px;">${escapeHtml(g.testFile||'')}</pre></div>`
            ).join("");

            results.innerHTML = `
                <div class="results-grid">
                    <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${covColor};"><div class="score-num" style="color:${covColor};">${data.coveragePercent}%</div><div class="score-label">Coverage</div></div></div>
                    <div class="result-card"><h3>Test Coverage</h3><div class="metrics-row" style="margin-top:8px;"><div class="metric-card blue"><div class="metric-value">${data.coveredFiles||0}</div><div class="metric-label">Covered</div></div><div class="metric-card red"><div class="metric-value">${data.missingTests||0}</div><div class="metric-label">Missing</div></div><div class="metric-card yellow"><div class="metric-value">${data.emptyTests||0}</div><div class="metric-label">Empty</div></div></div></div>
                    <div class="result-card"><h3>Files</h3><p>${data.totalSourceFiles||0} source files<br>${data.totalTestFiles||0} test files</p><p style="margin-top:4px;">Frameworks: ${(data.frameworks||[]).join(', ')||'N/A'}</p></div>
                </div>
                <div class="result-card"><h3>Coverage Map</h3><table class="file-table"><thead><tr><th>Source File</th><th>Lang</th><th>Status</th><th>Test File</th></tr></thead><tbody>${mapHTML}</tbody></table></div>
                ${genHTML ? '<div class="result-card"><h3>Auto-Generated Tests</h3>'+genHTML+'</div>' : ''}
            `;
        } catch (err) { errBanner.textContent=err.message; errBanner.classList.add("visible"); results.innerHTML='<div class="empty-state"><div class="empty-icon">❌</div><p>Scan failed</p></div>'; }
        finally { btn.disabled=false; spinner.classList.remove("visible"); btnText.textContent="Scan Test Coverage"; }
    });


    // ════════════════════════════════════════════════════════
    //  DAST SIMULATOR
    // ════════════════════════════════════════════════════════
    document.getElementById("runDastBtn").addEventListener("click", async () => {
        const code = document.getElementById("dastCodeInput").value.trim();
        const lang = document.getElementById("dastLangSelect").value;
        const errBanner = document.getElementById("dastErrorBanner");
        const results = document.getElementById("dastResults");
        const btn = document.getElementById("runDastBtn");
        const spinner = document.getElementById("dastSpinner");
        const btnText = document.querySelector(".btn-text-dast");

        if (!code) { errBanner.textContent="Paste API/server code"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");
        btn.disabled=true; spinner.classList.add("visible"); btnText.textContent="Scanning...";
        results.innerHTML='<div class="shimmer" style="height:200px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/dast/scan`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({code,language:lang}) });
            if (!res.ok) { const e=await res.json(); throw new Error(e.detail||"Failed"); }
            const data = await res.json();
            const sev = data.severityCounts||{};
            const analysis = data.analysis||{};

            const epsHTML = (data.endpoints||[]).map(ep =>
                `<tr><td style="font-family:var(--font-code);font-size:0.72rem;">${ep.methods.join(',')} ${escapeHtml(ep.path)}</td><td>Line ${ep.line}</td><td>${ep.hasBody?'Yes':'No'}</td></tr>`
            ).join("");

            const scenariosHTML = (data.attackScenarios||[]).slice(0,20).map(s => {
                const sc = {critical:"var(--red)",high:"var(--orange)",medium:"var(--yellow)",low:"var(--blue)"};
                return `<div class="issue-card" style="border-left-color:${sc[s.severity]||'var(--border)'};">
                    <div class="issue-header"><span class="issue-type">${s.attackType}</span><span class="issue-line" style="color:${sc[s.severity]};font-weight:700;">${s.severity.toUpperCase()}</span></div>
                    <div class="issue-desc">${s.description}</div>
                    <div style="font-size:0.72rem;color:var(--text-muted);margin-top:2px;">Endpoint: ${s.endpoint} | Vector: ${s.vector}</div>
                    <div class="issue-fix">Expected: ${s.expectedBehavior}</div>
                </div>`;
            }).join("");

            results.innerHTML = `
                <div class="results-grid">
                    <div class="result-card"><h3>Endpoints</h3><p style="font-size:1.5rem;font-weight:800;color:var(--accent);">${data.totalEndpoints||0}</p><p>API endpoints discovered</p></div>
                    <div class="result-card"><h3>Attack Scenarios</h3><p style="font-size:1.5rem;font-weight:800;color:var(--orange);">${data.totalScenarios||0}</p></div>
                    <div class="result-card"><h3>Severity</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(4,1fr);"><div class="metric-card red"><div class="metric-value">${sev.critical||0}</div><div class="metric-label">Critical</div></div><div class="metric-card" style="color:var(--orange);"><div class="metric-value">${sev.high||0}</div><div class="metric-label">High</div></div><div class="metric-card yellow"><div class="metric-value">${sev.medium||0}</div><div class="metric-label">Medium</div></div><div class="metric-card blue"><div class="metric-value">${sev.low||0}</div><div class="metric-label">Low</div></div></div></div>
                </div>
                ${analysis.summary ? `<div class="result-card"><h3>Risk Assessment</h3><p style="font-weight:700;color:var(--red);">${analysis.overallRisk||''} — Score: ${analysis.riskScore||'N/A'}/100</p><p style="margin-top:4px;">${analysis.summary}</p></div>` : ''}
                ${epsHTML ? `<div class="result-card"><h3>Discovered Endpoints</h3><table class="file-table"><thead><tr><th>Endpoint</th><th>Line</th><th>Body</th></tr></thead><tbody>${epsHTML}</tbody></table></div>` : ''}
                <div class="result-card"><h3>Attack Scenarios</h3>${scenariosHTML||'<p style="color:var(--green);">No attack scenarios generated</p>'}</div>
            `;
        } catch (err) { errBanner.textContent=err.message; errBanner.classList.add("visible"); results.innerHTML='<div class="empty-state"><div class="empty-icon">❌</div><p>DAST scan failed</p></div>'; }
        finally { btn.disabled=false; spinner.classList.remove("visible"); btnText.textContent="Discover & Attack"; }
    });


    // ════════════════════════════════════════════════════════
    //  CODE METRICS / FULL ANALYSIS
    // ════════════════════════════════════════════════════════
    document.getElementById("runAnalyzeBtn").addEventListener("click", async () => {
        const code = document.getElementById("analyzeCodeInput").value.trim();
        const lang = document.getElementById("analyzeLangSelect").value;
        const errBanner = document.getElementById("analyzeErrorBanner");
        const results = document.getElementById("analyzeResults");
        const btn = document.getElementById("runAnalyzeBtn");
        const spinner = document.getElementById("analyzeSpinner");
        const btnText = document.querySelector(".btn-text-analyze");

        if (!code) { errBanner.textContent="Paste code to analyze"; errBanner.classList.add("visible"); return; }
        errBanner.classList.remove("visible");
        btn.disabled=true; spinner.classList.add("visible"); btnText.textContent="Analyzing...";
        results.innerHTML='<div class="shimmer" style="height:200px;"></div>';

        try {
            const res = await fetch(`${API_BASE}/api/analyze/full-analysis`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({code,language:lang}) });
            if (!res.ok) { const e=await res.json(); throw new Error(e.detail||"Failed"); }
            const data = await res.json();
            const fm = data.fileMetrics||{};
            const gradeColors = {A:"var(--green)",B:"var(--blue)",C:"var(--yellow)",D:"var(--orange)",F:"var(--red)"};
            const gc = gradeColors[data.grade]||"var(--text-muted)";

            const cxHTML = (data.complexity||[]).map(c => {
                const rc = {low:"var(--green)",moderate:"var(--yellow)",high:"var(--orange)",very_high:"var(--red)"};
                return `<tr><td style="font-family:var(--font-code);font-size:0.75rem;">${c.function}</td><td style="color:${rc[c.rating]};font-weight:700;">${c.complexity}</td><td>${c.rating}</td><td>Line ${c.line}</td></tr>`;
            }).join("");

            const dcHTML = (data.deadCode||[]).map(d =>
                `<div class="issue-card" style="border-left-color:var(--yellow);"><div class="issue-header"><span class="issue-type">${d.type.replace(/_/g,' ')}</span>${d.line?`<span class="issue-line">Line ${d.line}</span>`:''}</div><div class="issue-desc">${d.description}</div>${d.fix?`<div class="issue-fix">${d.fix}</div>`:''}</div>`
            ).join("");

            const lintHTML = (data.lintIssues||[]).map(l =>
                `<div class="issue-card" style="border-left-color:var(--blue);"><div class="issue-header"><span class="issue-type">${l.rule||''}</span>${l.line?`<span class="issue-line">Line ${l.line}</span>`:''}</div><div class="issue-desc">${l.message}</div></div>`
            ).join("");

            const dupHTML = (data.duplications||[]).map(d =>
                `<div class="issue-card" style="border-left-color:var(--purple);"><div class="issue-header"><span class="issue-type">Duplicate Block</span><span class="issue-line">Lines ${d.line1} & ${d.line2}</span></div><div class="issue-desc" style="font-family:var(--font-code);font-size:0.72rem;">${escapeHtml(d.snippet)}</div></div>`
            ).join("");

            results.innerHTML = `
                <div class="results-grid">
                    <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${gc};"><div class="score-num" style="color:${gc};">${data.score}</div><div class="score-label">Grade ${data.grade}</div></div></div>
                    <div class="result-card"><h3>File Metrics</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(3,1fr);"><div class="metric-card"><div class="metric-value">${fm.totalLines||0}</div><div class="metric-label">Total Lines</div></div><div class="metric-card"><div class="metric-value">${fm.functions||0}</div><div class="metric-label">Functions</div></div><div class="metric-card"><div class="metric-value">${fm.classes||0}</div><div class="metric-label">Classes</div></div></div><p style="font-size:0.75rem;margin-top:8px;">Code: ${fm.codeLines||0} | Comments: ${fm.commentLines||0} (${fm.commentRatio||0}%) | Blank: ${fm.blankLines||0} | Max Nesting: ${fm.maxNesting||0}</p></div>
                    <div class="result-card"><h3>Summary</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(3,1fr);"><div class="metric-card"><div class="metric-value">${data.averageComplexity||0}</div><div class="metric-label">Avg Complexity</div></div><div class="metric-card"><div class="metric-value">${data.duplicationCount||0}</div><div class="metric-label">Duplications</div></div><div class="metric-card red"><div class="metric-value">${data.totalIssues||0}</div><div class="metric-label">Issues</div></div></div></div>
                </div>
                ${cxHTML ? `<div class="result-card"><h3>Cyclomatic Complexity</h3><table class="file-table"><thead><tr><th>Function</th><th>Complexity</th><th>Rating</th><th>Location</th></tr></thead><tbody>${cxHTML}</tbody></table></div>` : ''}
                ${dcHTML ? `<div class="result-card"><h3>Dead Code (${data.deadCode.length})</h3>${dcHTML}</div>` : ''}
                ${lintHTML ? `<div class="result-card"><h3>Lint Issues (${data.lintIssues.length})</h3>${lintHTML}</div>` : ''}
                ${dupHTML ? `<div class="result-card"><h3>Code Duplication (${data.duplications.length})</h3>${dupHTML}</div>` : ''}
            `;
        } catch (err) { errBanner.textContent=err.message; errBanner.classList.add("visible"); results.innerHTML='<div class="empty-state"><div class="empty-icon">❌</div><p>Analysis failed</p></div>'; }
        finally { btn.disabled=false; spinner.classList.remove("visible"); btnText.textContent="Full Analysis"; }
    });


    // ─────────────────────────────────────────────────────────
    //  INIT — trigger viewers on load
    // ─────────────────────────────────────────────────────────
    w1UpdateViewer();
    w2UpdateViewer();
    auditUpdateViewer();

}); // end DOMContentLoaded


// ═══════════════════════════════════════════════════════
//  GLOBAL UTILITIES — called from inline onclick attrs
// ═══════════════════════════════════════════════════════

function copyTestFile() {
    const block = document.getElementById("testFileBlock");
    if (!block) return;

    navigator.clipboard.writeText(block.textContent || block.innerText).then(() => {
        const btn = document.getElementById("copyBtn");
        if (btn) {
            btn.textContent = "✓ Copied!";
            btn.classList.add("copied");
            setTimeout(() => {
                btn.textContent = "Copy";
                btn.classList.remove("copied");
            }, 2000);
        }
    }).catch(() => {
        alert("Copy failed — please manually select the code block.");
    });
}

function closeExplainModal() {
    document.getElementById("explainOverlay").classList.remove("open");
}


// ═══════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════

/**
 * Extracts a single test function's code from the full test file string.
 * This lets us send just the relevant test to the /explain endpoint.
 *
 * Strategy: find "def test_name(" then grab lines until the next "def " at the same indent.
 */
function extractTestSnippet(testName, fullTestFile) {
    if (!fullTestFile || !testName) return testName;

    const lines = fullTestFile.split("\n");
    const startIdx = lines.findIndex(l => l.includes(`def ${testName}(`));
    if (startIdx === -1) return testName;

    const snippet = [lines[startIdx]];
    for (let i = startIdx + 1; i < lines.length; i++) {
        const line = lines[i];
        // Stop when we hit the next def at the same or outer indentation level
        if (/^def |^    def |^async def |^    async def /.test(line) && i !== startIdx) break;
        snippet.push(line);
        if (snippet.length > 30) break; // Cap to avoid huge payloads
    }
    return snippet.join("\n");
}

/** Safely escape HTML for display in innerHTML */
function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/** Safely escape a string for use in an HTML attribute value */
function escapeAttr(str) {
    return String(str)
        .replace(/\\/g, "\\\\")
        .replace(/'/g, "\\'")
        .replace(/"/g, "&quot;")
        .replace(/\n/g, "\\n")
        .replace(/\r/g, "");
}