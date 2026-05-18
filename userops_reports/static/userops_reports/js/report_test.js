(function () {
    "use strict";

    const API_BASE_URL = "/userops/api";
    const state = {
        activeView: "overview",
        metrics: {},
        courses: [],
        clusters: [],
        asms: [],
        learnerResults: [],
        currentRows: [],
        currentColumns: [],
        sort: {
            courses: { key: "total_enrollments", dir: "desc" },
            clusters: { key: "assigned_courses", dir: "desc" },
            asms: { key: "assigned_courses", dir: "desc" },
        },
    };

    const colors = {
        completed: "#168a52",
        progress: "#c47a0a",
        notStarted: "#c2413a",
    };

    const els = {};

    function byId(id) {
        return document.getElementById(id);
    }

    function bindElements() {
        [
            "dateRange", "startDate", "endDate", "refreshBtn", "exportBtn", "noticeRegion",
            "kpiCourses", "kpiCoursesSub", "kpiAssignments", "kpiCompleted", "kpiCompletionRate",
            "kpiInProgress", "kpiNotStarted", "kpiDealers", "kpiClusters", "kpiAsms",
            "statusDonut", "statusLegend", "topCourses", "clusterBars", "attentionList",
            "courseFilter", "clusterFilter", "asmFilter", "coursesTable", "clustersTable",
            "asmsTable", "learnerSearch", "learnerSearchBtn", "learnerResults",
            "detailDrawer", "drawerKicker", "drawerTitle", "drawerBody", "drawerClose",
            "drawerScrim",
        ].forEach(function (id) {
            els[id] = byId(id);
        });
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    function formatNumber(value) {
        return Number(value || 0).toLocaleString("en-IN");
    }

    function asNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function clampPercent(value) {
        return Math.max(0, Math.min(100, asNumber(value)));
    }

    function formatPercent(value) {
        const numeric = clampPercent(value);
        return `${numeric.toFixed(numeric % 1 === 0 ? 0 : 1)}%`;
    }

    function formatDate(value) {
        if (!value) {
            return "N/A";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return "N/A";
        }
        return date.toLocaleDateString("en-IN", { year: "numeric", month: "short", day: "numeric" });
    }

    function completionRate(completed, total) {
        const denominator = asNumber(total);
        if (!denominator) {
            return 0;
        }
        return (asNumber(completed) / denominator) * 100;
    }

    function courseNotStarted(course) {
        return Math.max(
            0,
            asNumber(course.total_enrollments) -
                asNumber(course.passed_count || course.certificates_issued) -
                asNumber(course.in_progress_count)
        );
    }

    function dateQueryString() {
        const params = new URLSearchParams();
        const range = els.dateRange.value || "all";
        params.set("date_range", range);
        if (range === "custom") {
            if (els.startDate.value) {
                params.set("start_date", els.startDate.value);
            }
            if (els.endDate.value) {
                params.set("end_date", els.endDate.value);
            }
        }
        return `?${params.toString()}`;
    }

    function apiUrl(path, includeDates) {
        return `${API_BASE_URL}${path}${includeDates ? dateQueryString() : ""}`;
    }

    async function fetchJson(path, label, includeDates) {
        const response = await fetch(apiUrl(path, includeDates), {
            credentials: "same-origin",
            headers: { Accept: "application/json" },
        });
        if (!response.ok) {
            throw new Error(`${label} returned ${response.status}`);
        }
        return response.json();
    }

    async function loadResource(path, label, includeDates) {
        try {
            return { ok: true, label, data: await fetchJson(path, label, includeDates) };
        } catch (error) {
            return { ok: false, label, error };
        }
    }

    function showNotice(message, type) {
        const item = document.createElement("div");
        item.className = `notice ${type || ""}`.trim();
        item.textContent = message;
        els.noticeRegion.appendChild(item);
    }

    function clearNotices() {
        els.noticeRegion.innerHTML = "";
    }

    async function loadAllData() {
        clearNotices();
        showNotice("Loading report data...", "");
        setBusy(true);

        const results = await Promise.all([
            loadResource("/dashboard-metrics", "Dashboard metrics", true),
            loadResource("/courses/overview", "Courses overview", true),
            loadResource("/cluster-performance", "Cluster performance", true),
            loadResource("/asm-overview", "ASM overview", true),
        ]);

        clearNotices();
        results.forEach(function (result) {
            if (!result.ok) {
                showNotice(`${result.label} failed: ${result.error.message}`, "error");
                return;
            }
            if (result.label === "Dashboard metrics") {
                state.metrics = result.data || {};
            }
            if (result.label === "Courses overview") {
                state.courses = (result.data && result.data.courses) || [];
            }
            if (result.label === "Cluster performance") {
                state.clusters = (result.data && result.data.clusters) || [];
            }
            if (result.label === "ASM overview") {
                state.asms = (result.data && result.data.asms) || [];
            }
        });

        if (results.some(function (result) { return result.ok; })) {
            showNotice("Report data loaded. Some sections may use cached values if an API failed.", "success");
        }

        renderAll();
        setBusy(false);
    }

    function setBusy(isBusy) {
        els.refreshBtn.disabled = isBusy;
        els.refreshBtn.textContent = isBusy ? "Loading" : "Refresh";
    }

    function renderAll() {
        renderKpis();
        renderOverview();
        renderCoursesTable();
        renderClustersTable();
        renderAsmsTable();
        refreshCurrentExportRows();
    }

    function renderKpis() {
        const totalCourses = state.courses.length;
        const assignments = asNumber(state.metrics.total_assigned_courses);
        const completed = asNumber(state.metrics.total_completed);
        const inProgress = asNumber(state.metrics.total_in_progress);
        const notStarted = asNumber(state.metrics.total_not_started);

        els.kpiCourses.textContent = formatNumber(totalCourses);
        els.kpiCoursesSub.textContent = `${formatNumber(totalCourses)} course rows`;
        els.kpiAssignments.textContent = formatNumber(assignments);
        els.kpiCompleted.textContent = formatNumber(completed);
        els.kpiCompletionRate.textContent = `${formatPercent(completionRate(completed, assignments))} completion`;
        els.kpiInProgress.textContent = formatNumber(inProgress);
        els.kpiNotStarted.textContent = formatNumber(notStarted);
        els.kpiDealers.textContent = formatNumber(state.metrics.total_dealers);
        els.kpiClusters.textContent = formatNumber(state.metrics.total_clusters || state.clusters.length);
        els.kpiAsms.textContent = formatNumber(state.metrics.total_asms || state.asms.length);
    }

    function renderOverview() {
        renderStatusDonut();
        renderTopCourses();
        renderClusterBars();
        renderAttentionList();
    }

    function renderStatusDonut() {
        const completed = asNumber(state.metrics.total_completed);
        const inProgress = asNumber(state.metrics.total_in_progress);
        const notStarted = asNumber(state.metrics.total_not_started);
        const total = completed + inProgress + notStarted;

        if (!total) {
            els.statusDonut.style.background = "#e5eaf0";
        } else {
            const completedDeg = (completed / total) * 360;
            const progressDeg = completedDeg + (inProgress / total) * 360;
            els.statusDonut.style.background = [
                `conic-gradient(${colors.completed} 0deg ${completedDeg}deg`,
                `${colors.progress} ${completedDeg}deg ${progressDeg}deg`,
                `${colors.notStarted} ${progressDeg}deg 360deg)`,
            ].join(", ");
        }

        els.statusLegend.innerHTML = [
            legendRow("green", "Completed", completed, total),
            legendRow("amber", "In progress", inProgress, total),
            legendRow("red", "Not started", notStarted, total),
        ].join("");
    }

    function legendRow(colorClass, label, value, total) {
        return `
            <div class="legend-row">
                <span class="swatch ${colorClass}"></span>
                <span>${escapeHtml(label)}</span>
                <strong>${formatNumber(value)} (${formatPercent(completionRate(value, total))})</strong>
            </div>
        `;
    }

    function renderTopCourses() {
        const rows = state.courses
            .slice()
            .sort(function (a, b) { return asNumber(b.total_enrollments) - asNumber(a.total_enrollments); })
            .slice(0, 6);

        if (!rows.length) {
            els.topCourses.innerHTML = emptyState("No course data available.");
            return;
        }

        els.topCourses.innerHTML = rows.map(function (course) {
            const rate = completionRate(course.certificates_issued || course.passed_count, course.total_enrollments);
            return `
                <div class="stack-item">
                    <div>
                        <button type="button" data-course="${escapeHtml(course.course_id)}">${escapeHtml(course.course_name || course.course_id)}</button>
                        <div class="stack-meta">${formatNumber(course.total_enrollments)} learners</div>
                    </div>
                    <span class="pill green">${formatPercent(rate)}</span>
                </div>
            `;
        }).join("");
    }

    function renderClusterBars() {
        const rows = state.clusters
            .slice()
            .sort(function (a, b) { return asNumber(b.assigned_courses) - asNumber(a.assigned_courses); })
            .slice(0, 8);

        if (!rows.length) {
            els.clusterBars.innerHTML = emptyState("No cluster data available.");
            return;
        }

        els.clusterBars.innerHTML = rows.map(function (cluster) {
            const value = clampPercent(cluster.avg_progress);
            return `
                <div class="bar-item">
                    <div class="bar-head">
                        <button type="button" data-cluster="${escapeHtml(cluster.cluster)}">${escapeHtml(cluster.cluster || "Unassigned")}</button>
                        <span>${formatPercent(value)}</span>
                    </div>
                    <div class="bar-track"><span class="bar-fill" style="width:${value}%"></span></div>
                    <div class="stack-meta">${formatNumber(cluster.assigned_courses)} assigned, ${formatNumber(cluster.total_users)} dealers</div>
                </div>
            `;
        }).join("");
    }

    function renderAttentionList() {
        const rows = state.courses
            .map(function (course) {
                return Object.assign({}, course, { not_started_count: courseNotStarted(course) });
            })
            .sort(function (a, b) { return asNumber(b.not_started_count) - asNumber(a.not_started_count); })
            .filter(function (course) { return asNumber(course.not_started_count) > 0; })
            .slice(0, 6);

        if (!rows.length) {
            els.attentionList.innerHTML = emptyState("No not-started courses in the current data.");
            return;
        }

        els.attentionList.innerHTML = rows.map(function (course) {
            return `
                <div class="stack-item">
                    <div>
                        <button type="button" data-course="${escapeHtml(course.course_id)}">${escapeHtml(course.course_name || course.course_id)}</button>
                        <div class="stack-meta">${formatNumber(course.total_enrollments)} total learners</div>
                    </div>
                    <span class="pill red">${formatNumber(course.not_started_count)} not started</span>
                </div>
            `;
        }).join("");
    }

    function emptyState(message) {
        return `<div class="empty-state">${escapeHtml(message)}</div>`;
    }

    function filteredRows(rows, query, fields) {
        const term = String(query || "").trim().toLowerCase();
        if (!term) {
            return rows.slice();
        }
        return rows.filter(function (row) {
            return fields.some(function (field) {
                return String(row[field] || "").toLowerCase().includes(term);
            });
        });
    }

    function sortRows(rows, sortState) {
        return rows.slice().sort(function (a, b) {
            const aValue = a[sortState.key];
            const bValue = b[sortState.key];
            const aNumber = Number(aValue);
            const bNumber = Number(bValue);
            let comparison;
            if (Number.isFinite(aNumber) && Number.isFinite(bNumber)) {
                comparison = aNumber - bNumber;
            } else {
                comparison = String(aValue || "").localeCompare(String(bValue || ""));
            }
            return sortState.dir === "asc" ? comparison : -comparison;
        });
    }

    function renderCoursesTable() {
        const rows = sortRows(
            filteredRows(state.courses, els.courseFilter.value, ["course_name", "course_id"]),
            state.sort.courses
        );
        if (!rows.length) {
            els.coursesTable.innerHTML = rowEmpty(6, "No courses match the current filters.");
            return;
        }
        els.coursesTable.innerHTML = rows.map(function (course) {
            const completed = asNumber(course.certificates_issued || course.passed_count);
            const rate = completionRate(completed, course.total_enrollments);
            return `
                <tr class="clickable" data-course="${escapeHtml(course.course_id)}">
                    <td>
                        <strong>${escapeHtml(course.course_name || "Untitled course")}</strong>
                        <div class="muted">${escapeHtml(course.course_id || "")}</div>
                    </td>
                    <td>${formatNumber(course.total_enrollments)}</td>
                    <td>${formatNumber(completed)}</td>
                    <td>${formatNumber(course.in_progress_count)}</td>
                    <td class="progress-cell">${progressMarkup(rate)}</td>
                    <td>${formatDate(course.last_activity)}</td>
                </tr>
            `;
        }).join("");
    }

    function renderClustersTable() {
        const rows = sortRows(
            filteredRows(state.clusters, els.clusterFilter.value, ["cluster"]),
            state.sort.clusters
        );
        if (!rows.length) {
            els.clustersTable.innerHTML = rowEmpty(7, "No clusters match the current filters.");
            return;
        }
        els.clustersTable.innerHTML = rows.map(function (cluster) {
            return `
                <tr class="clickable" data-cluster="${escapeHtml(cluster.cluster)}">
                    <td><strong>${escapeHtml(cluster.cluster || "Unassigned")}</strong></td>
                    <td>${formatNumber(cluster.total_users)}</td>
                    <td>${formatNumber(cluster.assigned_courses)}</td>
                    <td>${formatNumber(cluster.completed_courses)}</td>
                    <td>${formatNumber(cluster.in_progress)}</td>
                    <td>${formatNumber(cluster.not_started)}</td>
                    <td class="progress-cell">${progressMarkup(cluster.avg_progress)}</td>
                </tr>
            `;
        }).join("");
    }

    function renderAsmsTable() {
        const rows = sortRows(
            filteredRows(state.asms, els.asmFilter.value, ["name"]),
            state.sort.asms
        );
        if (!rows.length) {
            els.asmsTable.innerHTML = rowEmpty(7, "No ASMs match the current filters.");
            return;
        }
        els.asmsTable.innerHTML = rows.map(function (asm) {
            return `
                <tr class="clickable" data-asm="${escapeHtml(asm.name)}">
                    <td><strong>${escapeHtml(asm.name || "Unassigned")}</strong></td>
                    <td>${formatNumber(asm.dealers)}</td>
                    <td>${formatNumber(asm.assigned_courses)}</td>
                    <td>${formatNumber(asm.completed_courses)}</td>
                    <td>${formatNumber(asm.in_progress)}</td>
                    <td>${formatNumber(asm.not_started)}</td>
                    <td class="progress-cell">${progressMarkup(asm.avg_progress)}</td>
                </tr>
            `;
        }).join("");
    }

    function progressMarkup(value) {
        const numeric = clampPercent(value);
        const color = numeric >= 70 ? "green" : numeric >= 35 ? "amber" : "red";
        return `
            <span class="pill ${color}">${formatPercent(numeric)}</span>
            <div class="mini-track"><span class="mini-fill" style="width:${numeric}%"></span></div>
        `;
    }

    function rowEmpty(colspan, message) {
        return `<tr><td colspan="${colspan}">${emptyState(message)}</td></tr>`;
    }

    function switchView(viewName) {
        state.activeView = viewName;
        document.querySelectorAll(".tab").forEach(function (tab) {
            tab.classList.toggle("is-active", tab.dataset.view === viewName);
        });
        document.querySelectorAll(".view").forEach(function (view) {
            view.classList.toggle("is-active", view.id === `${viewName}View`);
        });
        refreshCurrentExportRows();
    }

    function refreshCurrentExportRows() {
        if (state.activeView === "courses") {
            state.currentRows = sortRows(filteredRows(state.courses, els.courseFilter.value, ["course_name", "course_id"]), state.sort.courses);
            state.currentColumns = [
                ["course_name", "Course"],
                ["course_id", "Course ID"],
                ["total_enrollments", "Enrollments"],
                ["certificates_issued", "Completed"],
                ["in_progress_count", "In Progress"],
                ["avg_grade", "Average Grade"],
                ["last_activity", "Last Activity"],
            ];
        } else if (state.activeView === "clusters") {
            state.currentRows = sortRows(filteredRows(state.clusters, els.clusterFilter.value, ["cluster"]), state.sort.clusters);
            state.currentColumns = [
                ["cluster", "Cluster"],
                ["total_users", "Dealers"],
                ["assigned_courses", "Assigned"],
                ["completed_courses", "Completed"],
                ["in_progress", "In Progress"],
                ["not_started", "Not Started"],
                ["avg_progress", "Average Progress"],
            ];
        } else if (state.activeView === "asms") {
            state.currentRows = sortRows(filteredRows(state.asms, els.asmFilter.value, ["name"]), state.sort.asms);
            state.currentColumns = [
                ["name", "ASM"],
                ["dealers", "Dealers"],
                ["assigned_courses", "Assigned"],
                ["completed_courses", "Completed"],
                ["in_progress", "In Progress"],
                ["not_started", "Not Started"],
                ["avg_progress", "Average Progress"],
            ];
        } else if (state.activeView === "learners") {
            state.currentRows = state.learnerResults.slice();
            state.currentColumns = [
                ["username", "Username"],
                ["dealer_name", "Dealer"],
                ["dealer_id", "Dealer ID"],
                ["cluster", "Cluster"],
                ["asm", "ASM"],
                ["rsm", "RSM"],
                ["courses_assigned", "Courses Assigned"],
                ["courses_completed", "Courses Completed"],
                ["avg_progress", "Average Progress"],
            ];
        } else {
            state.currentRows = state.courses.slice();
            state.currentColumns = [
                ["course_name", "Course"],
                ["total_enrollments", "Enrollments"],
                ["certificates_issued", "Completed"],
                ["avg_grade", "Average Grade"],
            ];
        }
    }

    async function openCourseDetails(courseId) {
        openDrawer("Course", courseId, loadingMarkup("Loading course details"));
        const [courseResult, learnersResult] = await Promise.all([
            loadResource(`/course/${encodeURIComponent(courseId)}`, "Course detail", true),
            loadResource(`/course/${encodeURIComponent(courseId)}/learners`, "Course learners", true),
        ]);

        const course = courseResult.ok ? courseResult.data : {};
        const learners = learnersResult.ok && learnersResult.data ? learnersResult.data.learners || [] : [];
        const detailName = course.course_name || courseId;

        els.drawerTitle.textContent = detailName;
        els.drawerBody.innerHTML = [
            detailStats([
                ["Enrollments", course.total_enrollments],
                ["Completed", course.certificates_issued || course.passed_count],
                ["In progress", course.in_progress_count],
                ["Average grade", formatPercent(course.avg_grade)],
            ]),
            drawerSection("Learners", learnersTable(learners)),
        ].join("");
    }

    async function openClusterDetails(clusterName) {
        openDrawer("Cluster", clusterName, loadingMarkup("Loading cluster details"));
        const result = await loadResource(`/asm-performance/${encodeURIComponent(clusterName)}`, "Cluster detail", true);
        if (!result.ok) {
            els.drawerBody.innerHTML = emptyState(result.error.message);
            return;
        }
        const data = result.data || {};
        const dealers = data.dealers || [];
        els.drawerBody.innerHTML = [
            detailStats([
                ["Dealers", data.totals && data.totals.dealers],
                ["Assigned", data.totals && data.totals.assigned_courses],
                ["Completed", data.totals && data.totals.completed_courses],
                ["Average progress", formatPercent(data.totals && data.totals.avg_progress)],
            ]),
            drawerSection("Dealers", dealersTable(dealers)),
        ].join("");
    }

    async function openAsmDetails(asmName) {
        openDrawer("ASM", asmName, loadingMarkup("Loading ASM details"));
        const result = await loadResource(`/asm-dealers/${encodeURIComponent(asmName)}`, "ASM detail", true);
        if (!result.ok) {
            els.drawerBody.innerHTML = emptyState(result.error.message);
            return;
        }
        const data = result.data || {};
        els.drawerBody.innerHTML = [
            detailStats([
                ["Dealers", data.totals && data.totals.dealers],
                ["Assigned", data.totals && data.totals.assigned_courses],
                ["Completed", data.totals && data.totals.completed_courses],
                ["Average progress", formatPercent(data.totals && data.totals.avg_progress)],
            ]),
            drawerSection("Clusters", clusterMiniList(data.clusters || [])),
            drawerSection("Dealers", dealersTable(data.dealers || [])),
        ].join("");
    }

    async function openUserDetails(userId) {
        openDrawer("Learner", `User ${userId}`, loadingMarkup("Loading learner details"));
        const result = await loadResource(`/user-id/${encodeURIComponent(userId)}`, "Learner detail", false);
        if (!result.ok) {
            els.drawerBody.innerHTML = emptyState(result.error.message);
            return;
        }
        const user = result.data || {};
        els.drawerTitle.textContent = user.dealer_name || user.username || `User ${userId}`;
        els.drawerBody.innerHTML = [
            detailStats([
                ["Assigned", user.total_courses_assigned],
                ["Completed", user.courses_completed],
                ["In progress", user.courses_in_progress],
                ["Overall progress", formatPercent(user.overall_progress)],
            ]),
            drawerSection("Profile", profileGrid(user)),
            drawerSection("Courses", userCoursesTable(user.courses || [])),
        ].join("");
    }

    function openDrawer(kicker, title, body) {
        els.drawerKicker.textContent = kicker;
        els.drawerTitle.textContent = title || "Details";
        els.drawerBody.innerHTML = body || "";
        els.detailDrawer.classList.add("is-open");
        els.drawerScrim.classList.add("is-open");
        els.detailDrawer.setAttribute("aria-hidden", "false");
    }

    function closeDrawer() {
        els.detailDrawer.classList.remove("is-open");
        els.drawerScrim.classList.remove("is-open");
        els.detailDrawer.setAttribute("aria-hidden", "true");
    }

    function loadingMarkup(message) {
        return `<div class="loading-inline">${escapeHtml(message)}...</div>`;
    }

    function detailStats(items) {
        return `
            <div class="detail-grid">
                ${items.map(function (item) {
                    return `
                        <div class="detail-stat">
                            <span>${escapeHtml(item[0])}</span>
                            <strong>${escapeHtml(item[1] == null ? "0" : item[1])}</strong>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    function drawerSection(title, body) {
        return `
            <section class="drawer-section">
                <h3>${escapeHtml(title)}</h3>
                ${body}
            </section>
        `;
    }

    function profileGrid(user) {
        const fields = [
            ["Username", user.username],
            ["Email", user.email],
            ["Dealer ID", user.dealer_id],
            ["Cluster", user.cluster],
            ["ASM", user.asm],
            ["RSM", user.rsm],
            ["Champion", user.champion_name],
            ["Mobile", user.champion_mobile],
            ["Role", user.role],
            ["Brand", user.brand],
        ];
        return `
            <div class="detail-grid">
                ${fields.map(function (field) {
                    return `
                        <div class="detail-stat">
                            <span>${escapeHtml(field[0])}</span>
                            <strong>${escapeHtml(field[1] || "N/A")}</strong>
                        </div>
                    `;
                }).join("")}
            </div>
        `;
    }

    function learnersTable(learners) {
        if (!learners.length) {
            return emptyState("No learners found for this course.");
        }
        return tableMarkup(
            ["Learner", "Dealer ID", "Cluster", "ASM", "Status", "Grade"],
            learners.slice(0, 200).map(function (learner) {
                return [
                    escapeHtml(learner.dealer_name || learner.username),
                    escapeHtml(learner.dealer_id || "N/A"),
                    escapeHtml(learner.cluster || "N/A"),
                    escapeHtml(learner.asm || "N/A"),
                    escapeHtml(learner.status || learner.completion_status || "N/A"),
                    formatPercent(learner.grade || learner.percent_grade),
                ];
            })
        );
    }

    function dealersTable(dealers) {
        if (!dealers.length) {
            return emptyState("No dealers found.");
        }
        return tableMarkup(
            ["Dealer", "ID", "Cluster", "Assigned", "Completed", "Average"],
            dealers.slice(0, 200).map(function (dealer) {
                return [
                    escapeHtml(dealer.dealer_name || dealer.username),
                    escapeHtml(dealer.dealer_id || "N/A"),
                    escapeHtml(dealer.cluster || "N/A"),
                    formatNumber(dealer.courses_assigned),
                    formatNumber(dealer.completed_courses),
                    formatPercent(dealer.avg_progress),
                ];
            })
        );
    }

    function userCoursesTable(courses) {
        if (!courses.length) {
            return emptyState("No enrolled courses found.");
        }
        return tableMarkup(
            ["Course", "Status", "Grade", "Enrollment", "Certificate"],
            courses.map(function (course) {
                return [
                    escapeHtml(course.course_name || course.course_id),
                    escapeHtml(course.status || "N/A"),
                    formatPercent(course.grade),
                    formatDate(course.enrollment_date),
                    course.certificate_issued ? "Yes" : "No",
                ];
            })
        );
    }

    function clusterMiniList(clusters) {
        if (!clusters.length) {
            return emptyState("No cluster distribution found.");
        }
        return clusters.map(function (cluster) {
            return `
                <div class="bar-item">
                    <div class="bar-head">
                        <strong>${escapeHtml(cluster.name || "Unassigned")}</strong>
                        <span>${formatPercent(cluster.avg_progress)}</span>
                    </div>
                    <div class="bar-track"><span class="bar-fill" style="width:${clampPercent(cluster.avg_progress)}%"></span></div>
                    <div class="stack-meta">${formatNumber(cluster.dealers)} dealers, ${formatNumber(cluster.assigned_courses)} assigned</div>
                </div>
            `;
        }).join("");
    }

    function tableMarkup(headers, rows) {
        return `
            <div class="table-wrap">
                <table>
                    <thead><tr>${headers.map(function (header) { return `<th>${escapeHtml(header)}</th>`; }).join("")}</tr></thead>
                    <tbody>
                        ${rows.map(function (row) {
                            return `<tr>${row.map(function (cell) { return `<td>${cell}</td>`; }).join("")}</tr>`;
                        }).join("")}
                    </tbody>
                </table>
            </div>
        `;
    }

    async function performLearnerSearch() {
        const query = els.learnerSearch.value.trim();
        if (query.length < 2) {
            els.learnerResults.innerHTML = emptyState("Type at least 2 characters to search.");
            state.learnerResults = [];
            refreshCurrentExportRows();
            return;
        }
        els.learnerResults.innerHTML = loadingMarkup("Searching learners");
        const result = await loadResource(`/search?query=${encodeURIComponent(query)}`, "Learner search", false);
        if (!result.ok) {
            els.learnerResults.innerHTML = emptyState(result.error.message);
            state.learnerResults = [];
            refreshCurrentExportRows();
            return;
        }
        state.learnerResults = (result.data && result.data.users) || [];
        refreshCurrentExportRows();
        if (!state.learnerResults.length) {
            els.learnerResults.innerHTML = emptyState("No learners found.");
            return;
        }
        els.learnerResults.innerHTML = state.learnerResults.map(function (user) {
            return `
                <article class="result-card">
                    <button type="button" data-user="${escapeHtml(user.user_id)}">${escapeHtml(user.dealer_name || user.username)}</button>
                    <div class="result-meta">
                        <span class="pill">${escapeHtml(user.username || "N/A")}</span>
                        <span class="pill">${escapeHtml(user.dealer_id || "N/A")}</span>
                        <span class="pill">${escapeHtml(user.cluster || "N/A")}</span>
                        <span class="pill green">${formatPercent(user.avg_progress)}</span>
                    </div>
                    <div class="muted">${formatNumber(user.courses_completed)} of ${formatNumber(user.courses_assigned)} courses completed</div>
                </article>
            `;
        }).join("");
    }

    function exportCsv() {
        refreshCurrentExportRows();
        if (!state.currentRows.length) {
            showNotice("No rows available to export for the current view.", "error");
            return;
        }
        const header = state.currentColumns.map(function (col) { return csvCell(col[1]); }).join(",");
        const lines = state.currentRows.map(function (row) {
            return state.currentColumns.map(function (col) {
                return csvCell(row[col[0]]);
            }).join(",");
        });
        const blob = new Blob([[header].concat(lines).join("\n")], { type: "text/csv;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `userops-${state.activeView}-${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
    }

    function csvCell(value) {
        const text = String(value == null ? "" : value);
        return `"${text.replace(/"/g, '""')}"`;
    }

    function updateCustomDateVisibility() {
        const show = els.dateRange.value === "custom";
        document.querySelectorAll(".custom-date").forEach(function (field) {
            field.classList.toggle("is-hidden", !show);
        });
    }

    function setSort(viewName, key) {
        const sortState = state.sort[viewName];
        if (!sortState) {
            return;
        }
        if (sortState.key === key) {
            sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
        } else {
            sortState.key = key;
            sortState.dir = "desc";
        }
        if (viewName === "courses") {
            renderCoursesTable();
        }
        if (viewName === "clusters") {
            renderClustersTable();
        }
        if (viewName === "asms") {
            renderAsmsTable();
        }
        refreshCurrentExportRows();
    }

    function attachEvents() {
        document.querySelectorAll(".tab").forEach(function (tab) {
            tab.addEventListener("click", function () {
                switchView(tab.dataset.view);
            });
        });

        document.querySelectorAll("[data-jump]").forEach(function (button) {
            button.addEventListener("click", function () {
                switchView(button.dataset.jump);
            });
        });

        els.dateRange.addEventListener("change", function () {
            updateCustomDateVisibility();
            loadAllData();
        });
        els.startDate.addEventListener("change", loadAllData);
        els.endDate.addEventListener("change", loadAllData);
        els.refreshBtn.addEventListener("click", loadAllData);
        els.exportBtn.addEventListener("click", exportCsv);

        els.courseFilter.addEventListener("input", function () {
            renderCoursesTable();
            refreshCurrentExportRows();
        });
        els.clusterFilter.addEventListener("input", function () {
            renderClustersTable();
            refreshCurrentExportRows();
        });
        els.asmFilter.addEventListener("input", function () {
            renderAsmsTable();
            refreshCurrentExportRows();
        });

        els.learnerSearchBtn.addEventListener("click", performLearnerSearch);
        els.learnerSearch.addEventListener("keydown", function (event) {
            if (event.key === "Enter") {
                performLearnerSearch();
            }
        });

        document.addEventListener("click", function (event) {
            const sortButton = event.target.closest("[data-sort]");
            if (sortButton) {
                const view = sortButton.closest(".view");
                if (view && view.id === "coursesView") {
                    setSort("courses", sortButton.dataset.sort);
                }
                if (view && view.id === "clustersView") {
                    setSort("clusters", sortButton.dataset.sort);
                }
                if (view && view.id === "asmsView") {
                    setSort("asms", sortButton.dataset.sort);
                }
                return;
            }

            const courseTarget = event.target.closest("[data-course]");
            if (courseTarget) {
                openCourseDetails(courseTarget.dataset.course);
                return;
            }

            const clusterTarget = event.target.closest("[data-cluster]");
            if (clusterTarget) {
                openClusterDetails(clusterTarget.dataset.cluster);
                return;
            }

            const asmTarget = event.target.closest("[data-asm]");
            if (asmTarget) {
                openAsmDetails(asmTarget.dataset.asm);
                return;
            }

            const userTarget = event.target.closest("[data-user]");
            if (userTarget) {
                openUserDetails(userTarget.dataset.user);
            }
        });

        els.drawerClose.addEventListener("click", closeDrawer);
        els.drawerScrim.addEventListener("click", closeDrawer);
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeDrawer();
            }
        });
    }

    function init() {
        bindElements();
        attachEvents();
        updateCustomDateVisibility();
        els.learnerResults.innerHTML = emptyState("Search results will appear here.");
        loadAllData();
    }

    init();
}());
