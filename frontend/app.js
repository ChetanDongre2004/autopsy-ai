const API_BASE = window.location.origin;

const ALL_TABS = ["review", "test", "audit", "repo", "qa", "dast", "analyze", "deps", "branch", "dashboard"];
const GRID_TABS = ["review", "test", "audit"];

function switchTab(tab) {
    ALL_TABS.forEach(t => {
        const el = document.getElementById(t + "Section");
        if (!el) return;
        el.style.display = t === tab ? (GRID_TABS.includes(t) ? "grid" : "flex") : "none";
    });
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.tab === tab);
    });
    const badgeMap = {
        review: "Code Review", test: "Test Generator", audit: "Security Audit",
        repo: "Repo Intelligence", qa: "QA Scanner", dast: "DAST Simulator",
        analyze: "Code Metrics", deps: "Dependency Scanner", branch: "Branch Compare",
        dashboard: "Health Dashboard"
    };
    document.getElementById("moduleBadge").textContent = badgeMap[tab] || "Autopsy AI";
}

function openExplainModal() { document.getElementById("explainOverlay").classList.add("open"); }
function closeExplainModal() { document.getElementById("explainOverlay").classList.remove("open"); }

async function explainTest(testName, testCodeContext, language) {
    document.getElementById("explainTitle").textContent = testName;
    document.getElementById("explainOneLiner").textContent = "Loading explanation...";
    document.getElementById("explainWhy").textContent = "";
    document.getElementById("explainHow").textContent = "";
    openExplainModal();
    try {
        const res = await fetch(`${API_BASE}/api/test/explain`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ test_code: testCodeContext || testName, language })
        });
        if (!res.ok) throw new Error("API error");
        const data = await res.json();
        document.getElementById("explainOneLiner").textContent = data.oneLiner || "—";
        document.getElementById("explainWhy").textContent = data.whyItMatters || "—";
        document.getElementById("explainHow").textContent = data.howToPass || "—";
    } catch {
        document.getElementById("explainOneLiner").textContent = "Could not load explanation.";
    }
}

function copyTestFile() {
    const block = document.getElementById("testFileBlock");
    if (!block) return;
    navigator.clipboard.writeText(block.textContent).then(() => {
        const btn = document.getElementById("copyBtn");
        if (btn) {
            btn.textContent = "Copied!";
            btn.classList.add("copied");
            setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 2000);
        }
    }).catch(() => alert("Copy failed — please select the code block manually."));
}

function extractTestSnippet(testName, fullTestFile) {
    if (!fullTestFile || !testName) return testName;
    const lines = fullTestFile.split("\n");
    const startIdx = lines.findIndex(l => l.includes(`def ${testName}(`));
    if (startIdx === -1) return testName;
    const snippet = [lines[startIdx]];
    for (let i = startIdx + 1; i < lines.length; i++) {
        if (/^(async )?def /.test(lines[i].trimStart()) && i !== startIdx) break;
        snippet.push(lines[i]);
        if (snippet.length > 30) break;
    }
    return snippet.join("\n");
}

function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function escapeAttr(str) {
    return String(str).replace(/\\/g, "\\\\").replace(/'/g, "\\'").replace(/"/g, "&quot;").replace(/\n/g, "\\n").replace(/\r/g, "");
}

const extMap = { python: "py", javascript: "js", typescript: "ts", html: "html", css: "css", java: "java", cpp: "cpp" };

document.addEventListener("DOMContentLoaded", () => {

    // ── Tab Switching ──
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // ── Explain modal backdrop close ──
    document.getElementById("explainOverlay").addEventListener("click", e => {
        if (e.target === document.getElementById("explainOverlay")) closeExplainModal();
    });

    // ── Theme Toggle ──
    document.getElementById("themeToggle").addEventListener("click", () => {
        const html = document.documentElement;
        const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
        html.setAttribute("data-theme", next);
        document.getElementById("themeToggle").textContent = next === "dark" ? "☀ Light" : "🌙 Dark";
    });


    // ════════════════════════════════════════════════
    //  CODE REVIEWER
    // ════════════════════════════════════════════════

    const w1 = {
        codeInput: document.getElementById("codeInput"),
        langSelect: document.getElementById("languageSelect"),
        analyzeBtn: document.getElementById("analyzeBtn"),
        btnText: document.querySelector(".btn-text"),
        spinner: document.getElementById("w1Spinner"),
        codeDisplay: document.getElementById("codeDisplay"),
        fileName: document.getElementById("fileNameDisplay"),
        resultsWrap: document.getElementById("w1Results"),
        errorBanner: document.getElementById("w1ErrorBanner"),
    };

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

    w1.analyzeBtn.addEventListener("click", async () => {
        const code = w1.codeInput.value.trim();
        const lang = w1.langSelect.value;
        if (!code) { showError(w1.errorBanner, "Please paste some code to analyze."); return; }

        setLoading(w1.analyzeBtn, w1.spinner, w1.btnText, true, "Analyzing...", "Audit Code");
        clearError(w1.errorBanner);
        w1.resultsWrap.innerHTML = shimmer(3);

        try {
            const res = await fetch(`${API_BASE}/api/review/`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, language: lang }),
            });
            if (!res.ok) { let msg = `Server error ${res.status}`; try { const e = await res.json(); msg = e.detail || msg; } catch {} throw new Error(msg); }
            renderW1Results(await res.json());
        } catch (err) {
            showError(w1.errorBanner, err.message);
            w1.resultsWrap.innerHTML = emptyState("🤖", "Paste code and click Audit Code");
        } finally {
            setLoading(w1.analyzeBtn, w1.spinner, w1.btnText, false, "Analyzing...", "Audit Code");
        }
    });

    function renderW1Results(data) {
        const gradeColors = { A: "#22c55e", B: "#3b82f6", C: "#eab308", D: "#f97316", F: "#ef4444" };
        const gc = gradeColors[data.grade] || "#888";
        const issuesHTML = (data.issues?.length > 0)
            ? data.issues.map(i => `<div class="issue-card" data-severity="${i.severity}"><div class="issue-header"><span class="issue-type">${i.type}</span><span class="issue-line">Line ${i.line || "?"}</span></div><div class="issue-desc">${i.description}</div><div class="issue-fix">💡 ${i.suggestion}</div></div>`).join("")
            : `<p style="color:var(--green);font-size:.8rem;">✨ No issues found!</p>`;
        const posHTML = (data.positives?.length > 0)
            ? `<ul class="positives-list">${data.positives.map(p => `<li>${p}</li>`).join("")}</ul>` : "";

        w1.resultsWrap.innerHTML = `
            <div class="score-card"><div class="grade-circle" style="background:${gc}">${data.grade || "?"}</div><div class="score-details"><h2>${data.score || 0}/100</h2><p>${data.summary || "No summary."}</p></div></div>
            <div class="metrics-row"><div class="metric-card red"><div class="metric-value">${data.metrics?.critical || 0}</div><div class="metric-label">Critical</div></div><div class="metric-card yellow"><div class="metric-value">${data.metrics?.warnings || 0}</div><div class="metric-label">Warnings</div></div><div class="metric-card blue"><div class="metric-value">${data.metrics?.info || 0}</div><div class="metric-label">Info</div></div></div>
            <div><div class="section-title">Issues (${data.metrics?.totalIssues || 0})</div>${issuesHTML}</div>
            ${posHTML ? `<div><div class="section-title">Positives</div>${posHTML}</div>` : ""}
            <div class="section-title" style="margin-top:4px;">Fix Time Estimate</div><p style="font-size:.78rem;color:var(--text-2);">⏱ ${data.metrics?.estimatedFixTime || "N/A"}</p>
        `;
    }


    // ════════════════════════════════════════════════
    //  TEST GENERATOR
    // ════════════════════════════════════════════════

    const w2 = {
        codeInput: document.getElementById("testCodeInput"),
        langSelect: document.getElementById("testLanguageSelect"),
        funcInput: document.getElementById("functionNameInput"),
        generateBtn: document.getElementById("generateTestBtn"),
        btnText: document.querySelector(".btn-text-test"),
        spinner: document.getElementById("w2Spinner"),
        codeDisplay: document.getElementById("testCodeDisplay"),
        fileName: document.getElementById("testFileNameDisplay"),
        resultsWrap: document.getElementById("w2Results"),
        errorBanner: document.getElementById("w2ErrorBanner"),
        mockToggle: document.getElementById("includeMocks"),
        fixtureToggle: document.getElementById("includeFixtures"),
    };

    let selectedDepth = "standard";

    function w2UpdateViewer() {
        const lang = w2.langSelect.value.split(" ")[0];
        w2.codeDisplay.className = `language-${lang}`;
        w2.codeDisplay.textContent = w2.codeInput.value || "# Paste your code here...";
        hljs.highlightElement(w2.codeDisplay);
        w2.fileName.textContent = `untitled.${extMap[lang] || lang}`;
    }

    w2.codeInput.addEventListener("input", w2UpdateViewer);
    w2.langSelect.addEventListener("change", w2UpdateViewer);
    w2UpdateViewer();

    document.querySelectorAll(".depth-pill").forEach(pill => {
        pill.addEventListener("click", () => {
            document.querySelectorAll(".depth-pill").forEach(p => p.classList.remove("active"));
            pill.classList.add("active");
            selectedDepth = pill.dataset.depth;
        });
    });

    w2.generateBtn.addEventListener("click", async () => {
        const code = w2.codeInput.value.trim();
        const lang = w2.langSelect.value.split(" ")[0];
        const funcName = w2.funcInput.value.trim();
        if (!code) { showError(w2.errorBanner, "Please paste some code to generate tests for."); return; }

        setLoading(w2.generateBtn, w2.spinner, w2.btnText, true, "Generating...", "Generate Tests");
        clearError(w2.errorBanner);
        w2.resultsWrap.innerHTML = shimmer(5);

        const body = { code, language: lang, test_depth: selectedDepth, include_mocks: w2.mockToggle.checked, include_fixtures: w2.fixtureToggle.checked };
        if (funcName) body.function_name = funcName;

        try {
            const res = await fetch(`${API_BASE}/api/test/`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });
            if (!res.ok) { let msg = `Server error ${res.status}`; try { const e = await res.json(); msg = e.detail || msg; } catch {} throw new Error(msg); }
            renderW2Results(await res.json());
        } catch (err) {
            showError(w2.errorBanner, err.message);
            w2.resultsWrap.innerHTML = emptyState("🧪", "Paste code and click Generate Tests");
        } finally {
            setLoading(w2.generateBtn, w2.spinner, w2.btnText, false, "Generating...", "Generate Tests");
        }
    });

    function renderW2Results(data) {
        const lang = data.language || "python";
        const totalTests = data.totalTests || 0;
        const coverage = data.coverage || "~0%";
        const framework = data.framework || "pytest";
        const pctNum = parseInt(coverage.replace(/\D/g, "")) || 0;

        const typeConfig = { happy_path: { label: "Happy Path", color: "var(--green)" }, edge_case: { label: "Edge Case", color: "var(--yellow)" }, error_case: { label: "Error Case", color: "var(--red)" }, security: { label: "Security", color: "var(--purple)" } };
        const typeCounts = {};
        (data.testCases || []).forEach(tc => { typeCounts[tc.type] = (typeCounts[tc.type] || 0) + 1; });

        const breakdownHTML = Object.entries(typeCounts).length > 0
            ? `<div class="breakdown-row">${Object.entries(typeCounts).map(([type, count]) => { const cfg = typeConfig[type] || { label: type, color: "#888" }; return `<div class="breakdown-pill"><div class="breakdown-dot" style="background:${cfg.color}"></div><span>${cfg.label}</span><strong>${count}</strong></div>`; }).join("")}</div>` : "";

        const funcsHTML = (data.detectedFunctions?.length > 0)
            ? `<div><div class="section-title">Detected Functions</div><div class="func-chips">${data.detectedFunctions.map(f => `<span class="func-chip">${f}()</span>`).join("")}</div></div>` : "";

        const testCasesHTML = (data.testCases || []).map((tc, idx) => {
            const type = tc.type || "happy_path";
            const typeLabels = { happy_path: "Happy Path", edge_case: "Edge Case", error_case: "Error Case", security: "Security" };
            const testSnippet = extractTestSnippet(tc.name, data.testFile || "");
            return `<div class="test-case-card" data-type="${type}" onclick="explainTest('${escapeAttr(tc.name)}','${escapeAttr(testSnippet)}','${lang}')" title="Click for AI explanation"><div class="test-case-header"><span class="test-case-name">${idx + 1}. ${tc.name}</span><span class="type-badge type-${type}">${typeLabels[type] || type}</span></div><div class="test-case-desc">${tc.description}</div><div class="test-io-row"><div class="test-io-chip"><span>In:</span><em>${tc.inputs || "—"}</em></div><div class="test-io-chip"><span>Out:</span><em>${tc.expectedOutput || "—"}</em></div></div></div>`;
        }).join("");

        const testFileHTML = `<div class="test-file-wrap"><div class="test-file-header"><span class="test-file-title">Complete Test File</span><button class="copy-btn" id="copyBtn" onclick="copyTestFile()">Copy</button></div><pre class="test-file-code" id="testFileBlock">${escapeHtml(data.testFile || "")}</pre></div>`;

        w2.resultsWrap.innerHTML = `
            <div class="test-summary-card"><div class="test-count-circle">${totalTests}</div><div class="test-meta"><h2>${totalTests} Test${totalTests !== 1 ? "s" : ""} Generated</h2><p>${data.notes || "—"}</p><div class="test-badges"><span class="test-badge badge-framework">${framework}</span><span class="test-badge badge-coverage">${coverage} coverage</span><span class="test-badge badge-lang">${lang}</span></div></div></div>
            <div class="coverage-bar-wrap"><div class="coverage-bar-label"><span>Estimated Coverage</span><span class="coverage-pct">${coverage}</span></div><div class="coverage-bar-track"><div class="coverage-bar-fill" id="coverageFill" style="width:0%"></div></div></div>
            ${breakdownHTML} ${funcsHTML}
            <div><div class="section-title">Test Cases (${totalTests})</div>${testCasesHTML}</div>
            ${testFileHTML}
            <div class="syntax-check-wrap" id="syntaxCheckWrap"><div class="syntax-check-row"><div class="syntax-dot pending"></div><span class="syntax-message">Checking syntax...</span></div></div>
            <div class="setup-block"><div class="section-title">How to Run</div><pre>${escapeHtml(data.setupInstructions || "pytest tests/ -v")}</pre></div>
            ${(data.missingForFullCoverage?.length > 0) ? `<div><div class="section-title">For 100% Coverage, Also Test</div><ul class="missing-list">${data.missingForFullCoverage.map(m => `<li>${m}</li>`).join("")}</ul></div>` : ""}
        `;

        requestAnimationFrame(() => {
            const fill = document.getElementById("coverageFill");
            if (fill) fill.style.width = `${Math.min(pctNum, 100)}%`;
        });

        if (data.testFile) runSyntaxCheck(data.testFile, data.requestedLanguage || lang);
    }

    async function runSyntaxCheck(testCode, language) {
        const wrap = document.getElementById("syntaxCheckWrap");
        if (!wrap) return;
        try {
            const res = await fetch(`${API_BASE}/api/test/run-check`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ test_code: testCode, language }),
            });
            if (!res.ok) throw new Error();
            const data = await res.json();
            const dotClass = data.valid === true ? "ok" : data.valid === false ? "error" : "pending";
            const funcCount = data.testCount > 0 ? `<span style="color:var(--green);font-size:.72rem;margin-left:auto;">${data.testCount} test functions found</span>` : "";
            wrap.innerHTML = `<div class="syntax-check-row"><div class="syntax-dot ${dotClass}"></div><span class="syntax-message">${data.message || "Check complete"}</span>${funcCount}</div>${(data.warnings || []).map(w => `<div class="syntax-warning">⚠ ${w}</div>`).join("")}${(data.errors || []).map(e => `<div class="syntax-error-msg">✗ ${e}</div>`).join("")}`;
        } catch {
            wrap.innerHTML = `<div class="syntax-check-row"><div class="syntax-dot pending"></div><span class="syntax-message" style="color:var(--text-3)">Syntax check unavailable</span></div>`;
        }
    }


    // ════════════════════════════════════════════════
    //  SECURITY AUDIT
    // ════════════════════════════════════════════════

    const audit = {
        codeInput: document.getElementById("auditCodeInput"),
        langSelect: document.getElementById("auditLanguageSelect"),
        btn: document.getElementById("runAuditBtn"),
        btnText: document.querySelector(".btn-text-audit"),
        spinner: document.getElementById("auditSpinner"),
        codeDisplay: document.getElementById("auditCodeDisplay"),
        fileName: document.getElementById("auditFileNameDisplay"),
        resultsWrap: document.getElementById("auditResults"),
        errorBanner: document.getElementById("auditErrorBanner"),
    };

    function auditUpdateViewer() {
        const lang = audit.langSelect.value;
        audit.codeDisplay.className = `language-${lang}`;
        audit.codeDisplay.textContent = audit.codeInput.value || "# Paste code here...";
        hljs.highlightElement(audit.codeDisplay);
        audit.fileName.textContent = `untitled.${extMap[lang] || lang}`;
    }

    audit.codeInput.addEventListener("input", auditUpdateViewer);
    audit.langSelect.addEventListener("change", auditUpdateViewer);
    auditUpdateViewer();

    audit.btn.addEventListener("click", async () => {
        const code = audit.codeInput.value.trim();
        const lang = audit.langSelect.value;
        if (!code) { showError(audit.errorBanner, "Please paste code to scan."); return; }

        setLoading(audit.btn, audit.spinner, audit.btnText, true, "Scanning...", "Run Security Scan");
        clearError(audit.errorBanner);
        audit.resultsWrap.innerHTML = shimmer(4);

        try {
            const res = await fetch(`${API_BASE}/api/audit/`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code, language: lang }),
            });
            if (!res.ok) { let msg = `Server error ${res.status}`; try { const e = await res.json(); msg = e.detail || msg; } catch {} throw new Error(msg); }
            renderAuditResults(await res.json());
        } catch (err) {
            showError(audit.errorBanner, err.message);
            audit.resultsWrap.innerHTML = emptyState("🛡️", "Paste code and click Run Security Scan");
        } finally {
            setLoading(audit.btn, audit.spinner, audit.btnText, false, "Scanning...", "Run Security Scan");
        }
    });

    function renderAuditResults(data) {
        const stats = data.statistics || { critical: 0, high: 0, medium: 0, low: 0, totalVulnerabilities: 0 };
        const score = data.riskScore ?? 100;
        const level = data.riskLevel ?? "UNKNOWN";
        let scoreColor = score < 30 ? "var(--red)" : score <= 55 ? "var(--orange)" : score <= 75 ? "var(--yellow)" : "var(--green)";

        const vulns = data.vulnerabilities || [];
        let vulnHTML = "";
        if (vulns.length === 0) {
            vulnHTML = `<p style="color:var(--green);font-size:.8rem;margin-top:12px;">✨ No security vulnerabilities detected!</p>`;
        } else {
            vulnHTML = `<div style="margin-top:12px"><div class="section-title">Vulnerabilities (${stats.totalVulnerabilities})</div>${vulns.map(v => {
                const sev = (v.severity || "info").toLowerCase();
                const sc = sev === "critical" ? "var(--red)" : sev === "high" ? "var(--orange)" : sev === "medium" ? "var(--yellow)" : "var(--blue)";
                return `<div class="issue-card" style="border-left-color:${sc};margin-top:6px;"><div class="issue-header"><span class="issue-type" style="color:${sc}">${v.category || "Vulnerability"} ${v.cweId ? '(' + v.cweId + ')' : ''}</span><span class="issue-line">Line ${v.line || "?"}</span></div><div class="issue-desc" style="font-weight:600;">${v.subtype || v.description}</div>${v.evidence ? `<div class="test-file-code" style="padding:6px;margin:4px 0;font-size:.65rem;">${escapeHtml(v.evidence)}</div>` : ""}${v.attackScenario ? `<div class="issue-desc" style="color:var(--text-3);font-size:.7rem;margin-top:4px;"><b>Attack:</b> ${v.attackScenario}</div>` : ""}<div class="issue-fix" style="margin-top:6px;">🛠️ ${v.remediation}</div>${v.secureExample ? `<div class="test-file-code" style="padding:6px;margin:4px 0;font-size:.65rem;background:#121812;color:var(--green);">${escapeHtml(v.secureExample)}</div>` : ""}</div>`;
            }).join("")}</div>`;
        }

        audit.resultsWrap.innerHTML = `
            <div class="score-card" style="border-color:${scoreColor}40;"><div class="grade-circle" style="background:${scoreColor};font-size:1.4rem;">${score}</div><div class="score-details"><h2 style="color:${scoreColor}">${level} RISK</h2><p>${data.executiveSummary || "Scan completed."}</p></div></div>
            <div class="metrics-row"><div class="metric-card red"><div class="metric-value">${stats.critical}</div><div class="metric-label">Critical</div></div><div class="metric-card" style="--metric-color:var(--orange)"><div class="metric-value" style="color:var(--orange)">${stats.high}</div><div class="metric-label">High</div></div><div class="metric-card yellow"><div class="metric-value">${stats.medium}</div><div class="metric-label">Medium</div></div><div class="metric-card blue"><div class="metric-value">${stats.low}</div><div class="metric-label">Low</div></div></div>
            ${vulnHTML}
        `;
    }


    // ════════════════════════════════════════════════
    //  REPO INTELLIGENCE
    // ════════════════════════════════════════════════

    setupFullSection("analyzeRepoBtn", "repoSpinner", ".btn-text-repo", "repoErrorBanner", "repoResults", {
        label: { loading: "Cloning & Analyzing...", idle: "Analyze Repo" },
        validate: () => { const url = document.getElementById("repoUrlInput").value.trim(); if (!url) return "Please enter a GitHub repo URL"; return null; },
        fetch: async () => {
            const url = document.getElementById("repoUrlInput").value.trim();
            const branch = document.getElementById("repoBranchInput").value.trim() || "main";
            return await apiPost("/api/repo/analyze", { repo_url: url, branch });
        },
        render: renderRepoResults,
        emptyIcon: "🔍", emptyMsg: "Analysis failed. Check the URL."
    });

    function renderRepoResults(data) {
        const scan = data.scan || {};
        const analysis = data.analysis || {};
        const topLang = Object.entries(scan.languages || {}).sort((a, b) => b[1] - a[1]);
        const fws = scan.frameworks || [];

        const langsHTML = topLang.map(([l, lines]) => `<span class="fw-chip">${l} <strong>${lines.toLocaleString()}</strong></span>`).join("");
        const fwHTML = fws.map(fw => `<span class="fw-chip">${fw.name} ${fw.version || ""}</span>`).join("") || '<span style="color:var(--text-3);font-size:.78rem;">None detected</span>';
        const filesHTML = (scan.files || []).slice(0, 30).map(f => `<tr><td style="font-family:var(--mono);font-size:.72rem;">${escapeHtml(f.path)}</td><td>${f.language}</td><td>${f.lines}</td><td><span class="fw-chip">${f.role}</span></td></tr>`).join("");

        const scores = analysis.scores || {};
        const scoreBarHTML = Object.entries(scores).map(([key, val]) => {
            const color = val >= 80 ? "var(--green)" : val >= 60 ? "var(--yellow)" : "var(--red)";
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="score-bar-row"><span class="bar-label">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${val}%;background:${color};"></div></div><span class="bar-value">${val}</span></div>`;
        }).join("");

        const recsHTML = (analysis.recommendations || []).map((r, i) => `<div class="issue-card" style="border-left-color:var(--accent);"><div class="issue-header"><span class="issue-type">#${i + 1} ${r.title || ""}</span><span class="issue-line">${r.impact || ""}</span></div><div class="issue-desc">${r.description || ""}</div></div>`).join("");

        document.getElementById("repoResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card"><h3>Repository</h3><p style="font-size:1rem;font-weight:700;color:var(--accent);">${data.repository}</p><p>Branch: ${data.branch} | ${scan.totalFiles || 0} files | ${(scan.totalLines || 0).toLocaleString()} lines</p></div>
                <div class="result-card"><h3>Architecture</h3><p style="font-weight:700;">${(scan.architecture || {}).pattern || "Unknown"}</p><p>${(scan.architecture || {}).description || ""}</p></div>
                <div class="result-card"><h3>Test Coverage</h3><p style="font-size:1.2rem;font-weight:800;color:${(scan.testCoverage || {}).ratio > 50 ? 'var(--green)' : 'var(--yellow)'};">${(scan.testCoverage || {}).ratio || 0}%</p><p>${(scan.testCoverage || {}).testCount || 0} test / ${(scan.testCoverage || {}).sourceCount || 0} source</p></div>
            </div>
            <div class="result-card"><h3>Languages</h3><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">${langsHTML}</div></div>
            <div class="result-card"><h3>Frameworks</h3><div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">${fwHTML}</div></div>
            ${scoreBarHTML ? `<div class="result-card"><h3>Scores</h3><div style="display:flex;flex-direction:column;gap:8px;margin-top:8px;">${scoreBarHTML}</div></div>` : ""}
            ${analysis.techStackSummary ? `<div class="result-card"><h3>Tech Stack</h3><p>${analysis.techStackSummary}</p></div>` : ""}
            ${recsHTML ? `<div class="result-card"><h3>Recommendations</h3>${recsHTML}</div>` : ""}
            <div class="result-card"><h3>File Structure (Top 30)</h3><table class="file-table"><thead><tr><th>Path</th><th>Language</th><th>Lines</th><th>Role</th></tr></thead><tbody>${filesHTML}</tbody></table></div>
        `;
    }


    // ════════════════════════════════════════════════
    //  DEPENDENCY SCANNER
    // ════════════════════════════════════════════════

    setupFullSection("scanDepsBtn", "depsSpinner", ".btn-text-deps", "depsErrorBanner", "depsResults", {
        label: { loading: "Scanning CVEs...", idle: "Scan Deps" },
        validate: () => { if (!document.getElementById("depsManifestInput").value.trim()) return "Please paste manifest content"; return null; },
        fetch: async () => {
            const manifest = document.getElementById("depsManifestInput").value.trim();
            const mType = document.getElementById("depsManifestType").value;
            return await apiPost("/api/dependencies/scan", { manifest_content: manifest, manifest_type: mType });
        },
        render: renderDepsResults,
        emptyIcon: "📦", emptyMsg: "Scan failed. Check your manifest."
    });

    function renderDepsResults(data) {
        const analysis = data.analysis || {};
        const healthScore = analysis.healthScore || 0;
        const scoreColor = healthScore >= 80 ? "var(--green)" : healthScore >= 60 ? "var(--yellow)" : "var(--red)";

        const pkgsHTML = (data.packages || []).map(pkg => {
            const vulnBadge = pkg.vulnerable
                ? `<span style="color:var(--red);font-weight:700;">⚠ ${pkg.vulnCount} vulns</span>`
                : `<span style="color:var(--green);">✓ Secure</span>`;
            const vulnDetails = (pkg.vulnerabilities || []).map(v =>
                `<div style="margin-left:12px;padding:4px 0;font-size:.72rem;border-bottom:1px solid var(--border);"><span style="color:${v.severity === 'critical' ? 'var(--red)' : v.severity === 'high' ? 'var(--orange)' : 'var(--yellow)'};font-weight:700;">${v.severity.toUpperCase()}</span> <span style="color:var(--text-3);margin-left:6px;">${v.cve || v.id}</span><div style="color:var(--text-2);margin-top:2px;">${v.summary}</div>${v.fixedIn ? `<div style="color:var(--green);margin-top:2px;">Fixed in: ${v.fixedIn}</div>` : ""}</div>`
            ).join("");
            return `<tr><td style="font-family:var(--mono);font-size:.75rem;font-weight:600;">${pkg.name}</td><td>${pkg.version}</td><td>${pkg.ecosystem}</td><td>${vulnBadge}${vulnDetails}</td></tr>`;
        }).join("");

        const upgradeHTML = (analysis.upgradeRecommendations || []).map(u =>
            `<div class="issue-card" style="border-left-color:${u.priority === 'high' ? 'var(--red)' : u.priority === 'medium' ? 'var(--yellow)' : 'var(--blue)'}"><div class="issue-header"><span class="issue-type">${u.package}</span><span class="issue-line">${u.current} → ${u.recommended}</span></div><div class="issue-desc">${u.reason}</div>${u.breakingChanges ? '<div style="color:var(--orange);font-size:.72rem;">⚠ May include breaking changes</div>' : ''}</div>`
        ).join("");

        document.getElementById("depsResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${scoreColor}40;margin:8px auto;"><div class="score-num" style="color:${scoreColor};">${healthScore}</div><div class="score-label">Health</div></div></div>
                <div class="result-card"><h3>Summary</h3><div class="metrics-row" style="margin-top:8px;"><div class="metric-card red"><div class="metric-value">${data.criticalCount || 0}</div><div class="metric-label">Critical</div></div><div class="metric-card yellow"><div class="metric-value">${data.totalVulnerabilities || 0}</div><div class="metric-label">Total Vulns</div></div><div class="metric-card blue"><div class="metric-value">${data.totalPackages || 0}</div><div class="metric-label">Packages</div></div></div></div>
                <div class="result-card"><h3>Manifest</h3><p>${data.manifestType || "auto"}</p><p style="margin-top:4px;">${analysis.summary || ""}</p></div>
            </div>
            ${upgradeHTML ? `<div class="result-card"><h3>Upgrade Recommendations</h3>${upgradeHTML}</div>` : ""}
            <div class="result-card"><h3>All Packages</h3><table class="file-table"><thead><tr><th>Package</th><th>Version</th><th>Ecosystem</th><th>Status</th></tr></thead><tbody>${pkgsHTML}</tbody></table></div>
        `;
    }


    // ════════════════════════════════════════════════
    //  BRANCH COMPARE
    // ════════════════════════════════════════════════

    setupFullSection("compareBranchBtn", "branchSpinner", ".btn-text-branch", "branchErrorBanner", "branchResults", {
        label: { loading: "Comparing...", idle: "Compare" },
        validate: () => {
            const url = document.getElementById("branchRepoUrl").value.trim();
            const head = document.getElementById("headBranchInput").value.trim();
            if (!url || !head) return "Enter repo URL and head branch"; return null;
        },
        fetch: async () => {
            const url = document.getElementById("branchRepoUrl").value.trim();
            const base = document.getElementById("baseBranchInput").value.trim() || "main";
            const head = document.getElementById("headBranchInput").value.trim();
            return await apiPost("/api/branch/compare", { repo_url: url, base_branch: base, head_branch: head });
        },
        render: renderBranchResults,
        emptyIcon: "🔀", emptyMsg: "Comparison failed."
    });

    function renderBranchResults(data) {
        const analysis = data.analysis || {};
        const verdict = analysis.verdict || "NEEDS_REVIEW";
        const changedFiles = data.changedFiles || [];
        const commits = data.commits || [];
        const issues = analysis.issues || [];

        const filesHTML = changedFiles.map(f => {
            const sc = { added: "var(--green)", modified: "var(--yellow)", deleted: "var(--red)" };
            return `<tr><td style="font-family:var(--mono);font-size:.72rem;">${escapeHtml(f.path)}</td><td><span style="color:${sc[f.status] || 'var(--text-3)'};font-weight:700;">${f.status}</span></td></tr>`;
        }).join("");

        const commitsHTML = commits.slice(0, 15).map(c =>
            `<div style="display:flex;gap:8px;align-items:baseline;padding:4px 0;border-bottom:1px solid var(--border);font-size:.76rem;"><span style="font-family:var(--mono);color:var(--accent);font-size:.72rem;">${c.hash}</span><span style="flex:1;">${escapeHtml(c.message)}</span><span style="color:var(--text-3);font-size:.68rem;white-space:nowrap;">${c.author}</span></div>`
        ).join("");

        const issuesHTML = issues.map(issue => {
            const sc = { critical: "var(--red)", high: "var(--orange)", medium: "var(--yellow)", low: "var(--blue)" };
            return `<div class="issue-card" style="border-left-color:${sc[issue.severity] || 'var(--border)'}"><div class="issue-header"><span class="issue-type">${issue.type || "issue"}</span><span class="issue-line" style="color:${sc[issue.severity] || 'var(--text-3)'};font-weight:700;">${(issue.severity || "").toUpperCase()}</span></div><div class="issue-desc">${issue.description || ""}</div>${issue.file ? `<div style="font-family:var(--mono);font-size:.68rem;color:var(--text-3);margin:2px 0;">${issue.file}</div>` : ""}${issue.suggestion ? `<div class="issue-fix">Fix: ${issue.suggestion}</div>` : ""}</div>`;
        }).join("");

        document.getElementById("branchResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;"><div class="verdict-badge verdict-${verdict}">${verdict.replace(/_/g, " ")}</div><p style="margin-top:8px;">${analysis.summary || ""}</p></div>
                <div class="result-card"><h3>Changes</h3><div class="metrics-row" style="margin-top:8px;"><div class="metric-card blue"><div class="metric-value">${changedFiles.length}</div><div class="metric-label">Files</div></div><div class="metric-card"><div class="metric-value">${commits.length}</div><div class="metric-label">Commits</div></div><div class="metric-card red"><div class="metric-value">${issues.length}</div><div class="metric-label">Issues</div></div></div></div>
            </div>
            ${issuesHTML ? `<div class="result-card"><h3>Issues (${issues.length})</h3>${issuesHTML}</div>` : '<div class="result-card"><h3>Issues</h3><p style="color:var(--green);">No issues found</p></div>'}
            ${(analysis.positives || []).length ? `<div class="result-card"><h3>Positives</h3><ul class="positives-list">${analysis.positives.map(p => `<li>${p}</li>`).join("")}</ul></div>` : ""}
            ${commitsHTML ? `<div class="result-card"><h3>Commits (${commits.length})</h3>${commitsHTML}</div>` : ""}
            ${filesHTML ? `<div class="result-card"><h3>Changed Files</h3><table class="file-table"><thead><tr><th>File</th><th>Status</th></tr></thead><tbody>${filesHTML}</tbody></table></div>` : ""}
            ${(analysis.testingRecommendations || []).length ? `<div class="result-card"><h3>Testing Recommendations</h3><ul class="missing-list">${analysis.testingRecommendations.map(t => `<li>${t}</li>`).join("")}</ul></div>` : ""}
        `;
    }


    // ════════════════════════════════════════════════
    //  HEALTH DASHBOARD
    // ════════════════════════════════════════════════

    setupFullSection("generateDashboardBtn", "dashboardSpinner", ".btn-text-dashboard", "dashboardErrorBanner", "dashboardResults", {
        label: { loading: "Analyzing Full Repo...", idle: "Generate Dashboard" },
        validate: () => { if (!document.getElementById("dashboardRepoUrl").value.trim()) return "Enter a GitHub repo URL"; return null; },
        fetch: async () => {
            const url = document.getElementById("dashboardRepoUrl").value.trim();
            const branch = document.getElementById("dashboardBranchInput").value.trim() || "main";
            return await apiPost("/api/dashboard/generate", { repo_url: url, branch });
        },
        render: renderDashboard,
        emptyIcon: "📊", emptyMsg: "Dashboard generation failed."
    });

    function renderDashboard(data) {
        const scores = data.scores || {};
        const repoInfo = data.repoInfo || {};
        const overall = data.overallScore || 0;
        const grade = data.grade || "?";
        const gc = { A: "var(--green)", B: "var(--blue)", C: "var(--yellow)", D: "var(--orange)", F: "var(--red)" }[grade] || "var(--text-3)";

        const scoreBarHTML = Object.entries(scores).map(([key, val]) => {
            const color = val >= 80 ? "var(--green)" : val >= 60 ? "var(--yellow)" : "var(--red)";
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="score-bar-row"><span class="bar-label">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${val}%;background:${color};"></div></div><span class="bar-value">${val}</span></div>`;
        }).join("");

        const breakdown = data.issueBreakdown || {};
        const fileRisks = (data.fileRisks || []).slice(0, 10).map(f => {
            const color = f.severity === 'high' ? 'var(--red)' : f.severity === 'medium' ? 'var(--yellow)' : 'var(--blue)';
            return `<div class="issue-card" style="border-left-color:${color};"><div class="issue-header"><span class="issue-type" style="font-family:var(--mono);text-transform:none;">${f.file}</span><span class="issue-line" style="color:${color};font-weight:700;">${f.score}/100</span></div><div class="issue-desc">${(f.issues || []).join(", ")}</div></div>`;
        }).join("");

        const recsHTML = (data.topRecommendations || []).map((r, i) =>
            `<div class="issue-card" style="border-left-color:var(--accent);"><div class="issue-header"><span class="issue-type">#${i + 1} ${r.title}</span><span class="issue-line">Impact: ${r.impact} | Effort: ${r.effort}</span></div><div class="issue-desc">${r.description}</div></div>`
        ).join("");

        const categoryHTML = Object.entries(data.categoryDetails || {}).map(([key, cat]) => {
            const label = key.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase());
            return `<div class="result-card"><h3>${label} — ${cat.score}/100</h3>${(cat.findings || []).map(f => `<p style="margin-bottom:4px;">• ${f}</p>`).join("")}${(cat.recommendations || []).map(r => `<p style="color:var(--green);margin-bottom:4px;">→ ${r}</p>`).join("")}</div>`;
        }).join("");

        const techDebt = data.techDebt || {};
        const langsHTML = Object.entries(repoInfo.languages || {}).map(([l, lines]) => `<span class="fw-chip">${l}: ${lines.toLocaleString()}</span>`).join("");

        document.getElementById("dashboardResults").innerHTML = `
            <div class="results-grid" style="grid-template-columns:200px 1fr 1fr;">
                <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${gc};"><div class="score-num" style="color:${gc};">${overall}</div><div class="score-label">Grade ${grade}</div></div></div>
                <div class="result-card"><h3>Repo Info</h3><p style="font-weight:700;color:var(--accent);">${repoInfo.name || ""}</p><p>${repoInfo.totalFiles || 0} files | ${(repoInfo.totalLines || 0).toLocaleString()} lines</p><p>Tests: ${repoInfo.testFiles || 0} / Sources: ${repoInfo.sourceFiles || 0} (${repoInfo.testRatio || 0}%)</p><div style="margin-top:6px;">${langsHTML}</div></div>
                <div class="result-card"><h3>Issue Breakdown</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(4,1fr);"><div class="metric-card red"><div class="metric-value">${breakdown.critical || 0}</div><div class="metric-label">Critical</div></div><div class="metric-card" style="color:var(--orange);"><div class="metric-value" style="color:var(--orange);">${breakdown.high || 0}</div><div class="metric-label">High</div></div><div class="metric-card yellow"><div class="metric-value">${breakdown.medium || 0}</div><div class="metric-label">Medium</div></div><div class="metric-card blue"><div class="metric-value">${breakdown.low || 0}</div><div class="metric-label">Low</div></div></div></div>
            </div>
            <div class="result-card"><h3>Score Breakdown</h3><div style="display:flex;flex-direction:column;gap:8px;margin-top:8px;">${scoreBarHTML}</div></div>
            ${data.summary ? `<div class="result-card"><h3>Executive Summary</h3><p>${data.summary}</p></div>` : ""}
            ${categoryHTML ? `<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;">${categoryHTML}</div>` : ""}
            ${fileRisks ? `<div class="result-card"><h3>Riskiest Files</h3>${fileRisks}</div>` : ""}
            ${recsHTML ? `<div class="result-card"><h3>Top Recommendations</h3>${recsHTML}</div>` : ""}
            ${techDebt.description ? `<div class="result-card"><h3>Technical Debt</h3><p><strong>${techDebt.level || "Unknown"}</strong> — Est. ${techDebt.estimatedHours || "?"} hours</p><p style="margin-top:4px;">${techDebt.description}</p></div>` : ""}
        `;
    }


    // ════════════════════════════════════════════════
    //  QA SCANNER
    // ════════════════════════════════════════════════

    setupFullSection("scanQaBtn", "qaSpinner", ".btn-text-qa", "qaErrorBanner", "qaResults", {
        label: { loading: "Scanning...", idle: "Scan Coverage" },
        validate: () => { if (!document.getElementById("qaRepoUrl").value.trim()) return "Enter a repo URL"; return null; },
        fetch: async () => {
            const url = document.getElementById("qaRepoUrl").value.trim();
            const branch = document.getElementById("qaBranch").value.trim() || "main";
            const autoGen = document.getElementById("qaAutoGenerate").checked;
            return await apiPost("/api/qa/scan", { repo_url: url, branch, auto_generate: autoGen, max_generate: 5 });
        },
        render: renderQaResults,
        emptyIcon: "🧬", emptyMsg: "Scan failed."
    });

    function renderQaResults(data) {
        const covColor = data.coveragePercent >= 70 ? "var(--green)" : data.coveragePercent >= 40 ? "var(--yellow)" : "var(--red)";
        const mapHTML = (data.coverageMap || []).slice(0, 40).map(f => {
            const sc = { covered: "var(--green)", missing: "var(--red)", empty: "var(--yellow)" };
            return `<tr><td style="font-family:var(--mono);font-size:.72rem;">${escapeHtml(f.path)}</td><td>${f.language}</td><td><span style="color:${sc[f.status] || 'var(--text-3)'};font-weight:700;">${f.status.toUpperCase()}</span></td><td style="font-size:.72rem;color:var(--text-3);">${f.testFile || '--'}</td></tr>`;
        }).join("");

        const genHTML = (data.generatedTests || []).filter(g => !g.error).map(g =>
            `<div class="result-card"><h3>${escapeHtml(g.sourceFile)}</h3><p>${g.framework} | ${g.testCount || 0} tests | ${g.coverage || 'N/A'}</p><pre class="test-file-code" style="max-height:200px;">${escapeHtml(g.testFile || '')}</pre></div>`
        ).join("");

        document.getElementById("qaResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${covColor};"><div class="score-num" style="color:${covColor};">${data.coveragePercent}%</div><div class="score-label">Coverage</div></div></div>
                <div class="result-card"><h3>Test Coverage</h3><div class="metrics-row" style="margin-top:8px;"><div class="metric-card blue"><div class="metric-value">${data.coveredFiles || 0}</div><div class="metric-label">Covered</div></div><div class="metric-card red"><div class="metric-value">${data.missingTests || 0}</div><div class="metric-label">Missing</div></div><div class="metric-card yellow"><div class="metric-value">${data.emptyTests || 0}</div><div class="metric-label">Empty</div></div></div></div>
                <div class="result-card"><h3>Files</h3><p>${data.totalSourceFiles || 0} source / ${data.totalTestFiles || 0} test</p><p style="margin-top:4px;">Frameworks: ${(data.frameworks || []).join(', ') || 'N/A'}</p></div>
            </div>
            <div class="result-card"><h3>Coverage Map</h3><table class="file-table"><thead><tr><th>Source</th><th>Lang</th><th>Status</th><th>Test File</th></tr></thead><tbody>${mapHTML}</tbody></table></div>
            ${genHTML ? '<div class="result-card"><h3>Auto-Generated Tests</h3>' + genHTML + '</div>' : ''}
        `;
    }


    // ════════════════════════════════════════════════
    //  DAST SIMULATOR
    // ════════════════════════════════════════════════

    setupFullSection("runDastBtn", "dastSpinner", ".btn-text-dast", "dastErrorBanner", "dastResults", {
        label: { loading: "Scanning...", idle: "Discover & Attack" },
        validate: () => { if (!document.getElementById("dastCodeInput").value.trim()) return "Paste API/server code"; return null; },
        fetch: async () => {
            const code = document.getElementById("dastCodeInput").value.trim();
            const lang = document.getElementById("dastLangSelect").value;
            return await apiPost("/api/dast/scan", { code, language: lang });
        },
        render: renderDastResults,
        emptyIcon: "💥", emptyMsg: "DAST scan failed."
    });

    function renderDastResults(data) {
        const sev = data.severityCounts || {};
        const analysis = data.analysis || {};

        const epsHTML = (data.endpoints || []).map(ep =>
            `<tr><td style="font-family:var(--mono);font-size:.72rem;">${ep.methods.join(',')} ${escapeHtml(ep.path)}</td><td>Line ${ep.line}</td><td>${ep.hasBody ? 'Yes' : 'No'}</td></tr>`
        ).join("");

        const scenariosHTML = (data.attackScenarios || []).slice(0, 20).map(s => {
            const sc = { critical: "var(--red)", high: "var(--orange)", medium: "var(--yellow)", low: "var(--blue)" };
            return `<div class="issue-card" style="border-left-color:${sc[s.severity] || 'var(--border)'}"><div class="issue-header"><span class="issue-type">${s.attackType}</span><span class="issue-line" style="color:${sc[s.severity]};font-weight:700;">${s.severity.toUpperCase()}</span></div><div class="issue-desc">${s.description}</div><div style="font-size:.72rem;color:var(--text-3);margin-top:2px;">Endpoint: ${s.endpoint} | Vector: ${s.vector}</div><div class="issue-fix">Expected: ${s.expectedBehavior}</div></div>`;
        }).join("");

        document.getElementById("dastResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card"><h3>Endpoints</h3><p style="font-size:1.5rem;font-weight:800;color:var(--accent);">${data.totalEndpoints || 0}</p><p>API endpoints discovered</p></div>
                <div class="result-card"><h3>Attack Scenarios</h3><p style="font-size:1.5rem;font-weight:800;color:var(--orange);">${data.totalScenarios || 0}</p></div>
                <div class="result-card"><h3>Severity</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(4,1fr);"><div class="metric-card red"><div class="metric-value">${sev.critical || 0}</div><div class="metric-label">Critical</div></div><div class="metric-card" style="color:var(--orange);"><div class="metric-value" style="color:var(--orange);">${sev.high || 0}</div><div class="metric-label">High</div></div><div class="metric-card yellow"><div class="metric-value">${sev.medium || 0}</div><div class="metric-label">Medium</div></div><div class="metric-card blue"><div class="metric-value">${sev.low || 0}</div><div class="metric-label">Low</div></div></div></div>
            </div>
            ${analysis.summary ? `<div class="result-card"><h3>Risk Assessment</h3><p style="font-weight:700;color:var(--red);">${analysis.overallRisk || ''} — Score: ${analysis.riskScore || 'N/A'}/100</p><p style="margin-top:4px;">${analysis.summary}</p></div>` : ''}
            ${epsHTML ? `<div class="result-card"><h3>Discovered Endpoints</h3><table class="file-table"><thead><tr><th>Endpoint</th><th>Line</th><th>Body</th></tr></thead><tbody>${epsHTML}</tbody></table></div>` : ''}
            <div class="result-card"><h3>Attack Scenarios</h3>${scenariosHTML || '<p style="color:var(--green);">No attack scenarios</p>'}</div>
        `;
    }


    // ════════════════════════════════════════════════
    //  CODE METRICS
    // ════════════════════════════════════════════════

    setupFullSection("runAnalyzeBtn", "analyzeSpinner", ".btn-text-analyze", "analyzeErrorBanner", "analyzeResults", {
        label: { loading: "Analyzing...", idle: "Full Analysis" },
        validate: () => { if (!document.getElementById("analyzeCodeInput").value.trim()) return "Paste code to analyze"; return null; },
        fetch: async () => {
            const code = document.getElementById("analyzeCodeInput").value.trim();
            const lang = document.getElementById("analyzeLangSelect").value;
            return await apiPost("/api/analyze/full-analysis", { code, language: lang });
        },
        render: renderAnalyzeResults,
        emptyIcon: "📐", emptyMsg: "Analysis failed."
    });

    function renderAnalyzeResults(data) {
        const fm = data.fileMetrics || {};
        const gc = { A: "var(--green)", B: "var(--blue)", C: "var(--yellow)", D: "var(--orange)", F: "var(--red)" }[data.grade] || "var(--text-3)";

        const cxHTML = (data.complexity || []).map(c => {
            const rc = { low: "var(--green)", moderate: "var(--yellow)", high: "var(--orange)", very_high: "var(--red)" };
            return `<tr><td style="font-family:var(--mono);font-size:.75rem;">${c.function}</td><td style="color:${rc[c.rating]};font-weight:700;">${c.complexity}</td><td>${c.rating}</td><td>Line ${c.line}</td></tr>`;
        }).join("");

        const dcHTML = (data.deadCode || []).map(d => `<div class="issue-card" style="border-left-color:var(--yellow);"><div class="issue-header"><span class="issue-type">${d.type.replace(/_/g, ' ')}</span>${d.line ? `<span class="issue-line">Line ${d.line}</span>` : ''}</div><div class="issue-desc">${d.description}</div>${d.fix ? `<div class="issue-fix">${d.fix}</div>` : ''}</div>`).join("");

        const lintHTML = (data.lintIssues || []).map(l => `<div class="issue-card" style="border-left-color:var(--blue);"><div class="issue-header"><span class="issue-type">${l.rule || ''}</span>${l.line ? `<span class="issue-line">Line ${l.line}</span>` : ''}</div><div class="issue-desc">${l.message}</div></div>`).join("");

        const dupHTML = (data.duplications || []).map(d => `<div class="issue-card" style="border-left-color:var(--purple);"><div class="issue-header"><span class="issue-type">Duplicate Block</span><span class="issue-line">Lines ${d.line1} & ${d.line2}</span></div><div class="issue-desc" style="font-family:var(--mono);font-size:.72rem;">${escapeHtml(d.snippet)}</div></div>`).join("");

        document.getElementById("analyzeResults").innerHTML = `
            <div class="results-grid">
                <div class="result-card" style="text-align:center;"><div class="score-ring" style="border-color:${gc};"><div class="score-num" style="color:${gc};">${data.score}</div><div class="score-label">Grade ${data.grade}</div></div></div>
                <div class="result-card"><h3>File Metrics</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(3,1fr);"><div class="metric-card"><div class="metric-value">${fm.totalLines || 0}</div><div class="metric-label">Lines</div></div><div class="metric-card"><div class="metric-value">${fm.functions || 0}</div><div class="metric-label">Functions</div></div><div class="metric-card"><div class="metric-value">${fm.classes || 0}</div><div class="metric-label">Classes</div></div></div><p style="font-size:.75rem;margin-top:8px;">Code: ${fm.codeLines || 0} | Comments: ${fm.commentLines || 0} (${fm.commentRatio || 0}%) | Blank: ${fm.blankLines || 0} | Nesting: ${fm.maxNesting || 0}</p></div>
                <div class="result-card"><h3>Summary</h3><div class="metrics-row" style="margin-top:8px;grid-template-columns:repeat(3,1fr);"><div class="metric-card"><div class="metric-value">${data.averageComplexity || 0}</div><div class="metric-label">Avg Complexity</div></div><div class="metric-card"><div class="metric-value">${data.duplicationCount || 0}</div><div class="metric-label">Duplications</div></div><div class="metric-card red"><div class="metric-value">${data.totalIssues || 0}</div><div class="metric-label">Issues</div></div></div></div>
            </div>
            ${cxHTML ? `<div class="result-card"><h3>Cyclomatic Complexity</h3><table class="file-table"><thead><tr><th>Function</th><th>Complexity</th><th>Rating</th><th>Location</th></tr></thead><tbody>${cxHTML}</tbody></table></div>` : ''}
            ${dcHTML ? `<div class="result-card"><h3>Dead Code (${data.deadCode.length})</h3>${dcHTML}</div>` : ''}
            ${lintHTML ? `<div class="result-card"><h3>Lint Issues (${data.lintIssues.length})</h3>${lintHTML}</div>` : ''}
            ${dupHTML ? `<div class="result-card"><h3>Duplication (${data.duplications.length})</h3>${dupHTML}</div>` : ''}
        `;
    }

}); // end DOMContentLoaded


// ═══════════════════════════════════════════════
//  SHARED HELPERS
// ═══════════════════════════════════════════════

function showError(banner, msg) { banner.textContent = `⚠ ${msg}`; banner.classList.add("visible"); }
function clearError(banner) { banner.classList.remove("visible"); }

function setLoading(btn, spinner, btnText, on, loadingLabel, idleLabel) {
    btn.disabled = on;
    spinner.classList.toggle("visible", on);
    btnText.textContent = on ? loadingLabel : idleLabel;
}

function shimmer(count) {
    return Array.from({ length: count }, (_, i) => `<div class="shimmer" style="height:${60 + i * 10}px;${i ? 'margin-top:8px;' : ''}"></div>`).join("");
}

function emptyState(icon, msg) {
    return `<div class="empty-state"><div class="empty-icon">${icon}</div><p>${msg}</p></div>`;
}

async function apiPost(endpoint, body) {
    const res = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
    });
    if (!res.ok) {
        let msg = `Server error ${res.status}`;
        try { const e = await res.json(); msg = e.detail || msg; } catch { try { msg = await res.text(); } catch {} }
        throw new Error(msg);
    }
    return await res.json();
}

function setupFullSection(btnId, spinnerId, btnTextSel, errBannerId, resultsId, opts) {
    const btn = document.getElementById(btnId);
    const spinner = document.getElementById(spinnerId);
    const btnText = document.querySelector(btnTextSel);
    const errBanner = document.getElementById(errBannerId);
    const results = document.getElementById(resultsId);

    btn.addEventListener("click", async () => {
        const validationErr = opts.validate();
        if (validationErr) { showError(errBanner, validationErr); return; }
        clearError(errBanner);
        setLoading(btn, spinner, btnText, true, opts.label.loading, opts.label.idle);
        results.innerHTML = shimmer(3);

        try {
            const data = await opts.fetch();
            opts.render(data);
        } catch (err) {
            showError(errBanner, err.message);
            results.innerHTML = emptyState(opts.emptyIcon || "❌", opts.emptyMsg || "Operation failed.");
        } finally {
            setLoading(btn, spinner, btnText, false, opts.label.loading, opts.label.idle);
        }
    });
}
