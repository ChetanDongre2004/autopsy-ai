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

const API_BASE = "https://autopsy-ai.onrender.com";


// ═══════════════════════════════════════════════════════
//  WEEK SWITCHING
// ═══════════════════════════════════════════════════════

function switchTab(tab) {
    document.getElementById("reviewSection").style.display = tab === "review" ? "grid" : "none";
    document.getElementById("testSection").style.display = tab === "test" ? "grid" : "none";
    document.getElementById("auditSection").style.display = tab === "audit" ? "grid" : "none";

    document.getElementById("tabReview").classList.toggle("active", tab === "review");
    document.getElementById("tabTest").classList.toggle("active", tab === "test");
    document.getElementById("tabAudit").classList.toggle("active", tab === "audit");

    const badgeMap = {
        review: "Code Reviewer",
        test: "Test Generator",
        audit: "Security Audit"
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