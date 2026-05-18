(function () {
    "use strict";

    const API_BASE_URL = "/userops/api";
    const SAMPLE_COURSE_LIMIT = 8;
    const PAGE_SIZE = 12;

    const state = {
        metrics: {},
        courses: [],
        clusters: [],
        asms: [],
        courseDetails: null,
        learners: [],
        tableRows: [],
        filteredRows: [],
        page: 1,
        sort: { key: "risk_score", dir: "desc" },
        selectedCourseId: "",
        loading: false,
        demoMode: false,
        failures: [],
        warnings: [],
    };

    const els = {};

    function byId(id) {
        return document.getElementById(id);
    }

    function bindElements() {
        [
            "scopeSummary", "dateRange", "startDate", "endDate", "courseSelect", "themeToggle",
            "refreshBtn", "exportBtn", "riskExportBtn", "noticeRegion",
            "kpiTotalLearners", "kpiActiveLearners", "kpiAvgProgress", "kpiCompletionRate",
            "kpiCertificates", "kpiRiskLearners", "kpiTimeSpent", "kpiDropOff",
            "kpiTotalLearnersTrend", "kpiActiveLearnersTrend", "kpiAvgProgressTrend",
            "kpiCompletionRateTrend", "kpiCertificatesTrend", "kpiRiskLearnersTrend", "kpiDropOffTrend",
            "healthGauge", "healthScore", "healthLabel", "healthCompletion", "healthEngagement",
            "healthActivity", "healthDropoff", "problemSections", "insightsList",
            "courseCompletionChart", "engagementCanvas", "funnelChart", "distributionChart",
            "heatmapGrid", "dropoffChart", "riskList", "tableSearch", "statusFilter", "riskFilter",
            "learnerTableBody", "tableCount", "prevPageBtn", "pageInfo", "nextPageBtn",
            "drawerScrim", "learnerDrawer", "drawerClose", "drawerKicker", "drawerTitle", "drawerBody",
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

    function asNumber(value) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : 0;
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, asNumber(value)));
    }

    function formatNumber(value) {
        return Math.round(asNumber(value)).toLocaleString("en-IN");
    }

    function formatPercent(value) {
        const numeric = clamp(value, 0, 100);
        return `${numeric.toFixed(numeric % 1 === 0 ? 0 : 1)}%`;
    }

    function formatHours(value) {
        const numeric = asNumber(value);
        if (numeric >= 10) {
            return `${Math.round(numeric)}h`;
        }
        return `${numeric.toFixed(1)}h`;
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

    function daysSince(value) {
        if (!value) {
            return 999;
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return 999;
        }
        return Math.max(0, Math.floor((Date.now() - date.getTime()) / 86400000));
    }

    function average(values) {
        const clean = values.map(asNumber).filter(function (value) { return Number.isFinite(value); });
        if (!clean.length) {
            return 0;
        }
        return clean.reduce(function (sum, value) { return sum + value; }, 0) / clean.length;
    }

    function rate(part, total) {
        const denominator = asNumber(total);
        if (!denominator) {
            return 0;
        }
        return (asNumber(part) / denominator) * 100;
    }

    function normalizeStatus(row) {
        const status = String(row.status || row.completion_status || "").toLowerCase();
        const progress = asNumber(row.percent_grade || row.grade);
        if (status.includes("complete") || status.includes("passed") || progress >= 100) {
            return "completed";
        }
        if (progress > 0) {
            return "in_progress";
        }
        return "not_started";
    }

    function statusLabel(status) {
        if (status === "completed") {
            return "Completed";
        }
        if (status === "in_progress") {
            return "In progress";
        }
        return "Not started";
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
            throw new Error(`${label} returned HTTP ${response.status}`);
        }
        return response.json();
    }

    function clearNotices() {
        els.noticeRegion.innerHTML = "";
    }

    function showNotice(message, type) {
        const item = document.createElement("div");
        item.className = `notice ${type || ""}`.trim();
        item.textContent = message;
        els.noticeRegion.appendChild(item);
    }

    function setLoading(isLoading) {
        state.loading = isLoading;
        els.refreshBtn.disabled = isLoading;
        els.refreshBtn.textContent = isLoading ? "Loading" : "Refresh";
        document.querySelectorAll(".kpi-card").forEach(function (card) {
            card.classList.toggle("is-loading", isLoading);
        });
    }

    function updateCustomDates() {
        document.querySelectorAll(".custom-date").forEach(function (node) {
            node.classList.toggle("is-hidden", els.dateRange.value !== "custom");
        });
    }

    function selectedCourseName() {
        if (!state.selectedCourseId) {
            return "All courses";
        }
        const course = state.courses.find(function (item) {
            return item.course_id === state.selectedCourseId || item.id === state.selectedCourseId;
        });
        return (course && (course.course_name || course.name || course.display_name)) || state.selectedCourseId;
    }

    function updateScope() {
        const label = els.dateRange.options[els.dateRange.selectedIndex]?.text || "All time";
        els.scopeSummary.textContent = `${selectedCourseName()} across ${label.toLowerCase()}.`;
    }

    function setTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        try {
            localStorage.setItem("userops-intelligence-theme", theme);
        } catch (error) {
            // Ignore storage failures in locked-down browsers.
        }
        requestAnimationFrame(renderEngagementTrend);
    }

    function getSavedTheme() {
        try {
            return localStorage.getItem("userops-intelligence-theme") || "dark";
        } catch (error) {
            return "dark";
        }
    }

    function mergeCourseLists(overviewCourses, pickerCourses) {
        const byId = new Map();
        (overviewCourses || []).forEach(function (course) {
            byId.set(course.course_id || course.id, course);
        });
        (pickerCourses || []).forEach(function (course) {
            const id = course.course_id || course.id;
            if (!byId.has(id)) {
                byId.set(id, {
                    course_id: id,
                    course_name: course.course_name || course.name || course.display_name || id,
                    total_enrollments: 0,
                    certificates_issued: 0,
                    in_progress_count: 0,
                    avg_grade: 0,
                });
            }
        });
        return Array.from(byId.values()).sort(function (a, b) {
            return String(a.course_name || a.name || "").localeCompare(String(b.course_name || b.name || ""));
        });
    }

    function populateCourseSelect() {
        const current = els.courseSelect.value;
        const options = ['<option value="">All courses</option>'].concat(
            state.courses.map(function (course) {
                const id = course.course_id || course.id;
                const name = course.course_name || course.name || course.display_name || id;
                return `<option value="${escapeHtml(id)}">${escapeHtml(name)}</option>`;
            })
        );
        els.courseSelect.innerHTML = options.join("");
        if (current && state.courses.some(function (course) { return (course.course_id || course.id) === current; })) {
            els.courseSelect.value = current;
        }
    }

    async function loadDashboardData() {
        clearNotices();
        state.failures = [];
        state.warnings = [];
        state.demoMode = false;
        state.selectedCourseId = els.courseSelect.value || "";
        setLoading(true);
        showNotice("Loading Learning Intelligence data...", "");

        const requests = [
            { key: "metrics", label: "Dashboard metrics", promise: fetchJson("/dashboard-metrics", "Dashboard metrics", true) },
            { key: "courseOverview", label: "Courses overview", promise: fetchJson("/courses/overview", "Courses overview", true) },
            { key: "coursePicker", label: "Course selector", promise: fetchJson("/courses", "Course selector", false) },
            { key: "clusters", label: "Cluster performance", promise: fetchJson("/cluster-performance", "Cluster performance", true) },
            { key: "asms", label: "ASM overview", promise: fetchJson("/asm-overview", "ASM overview", true) },
        ];

        const settled = await Promise.allSettled(requests.map(function (request) { return request.promise; }));
        const loaded = {};
        settled.forEach(function (result, index) {
            const request = requests[index];
            if (result.status === "fulfilled") {
                loaded[request.key] = result.value || {};
            } else {
                state.failures.push(`${request.label}: ${result.reason.message}`);
            }
        });

        state.metrics = loaded.metrics || {};
        state.courses = mergeCourseLists(
            loaded.courseOverview && loaded.courseOverview.courses,
            loaded.coursePicker && loaded.coursePicker.courses
        );
        state.clusters = (loaded.clusters && loaded.clusters.clusters) || [];
        state.asms = (loaded.asms && loaded.asms.asms) || [];

        if (!state.courses.length && !Object.keys(state.metrics).length) {
            applyDemoFallback();
        }

        populateCourseSelect();
        if (state.selectedCourseId) {
            els.courseSelect.value = state.selectedCourseId;
        }

        await loadLearnerScope();

        clearNotices();
        if (state.demoMode) {
            showNotice("Live APIs are unavailable, so this page is showing clearly marked demo fallback data.", "warning");
        } else {
            showNotice("Dashboard loaded. Estimated cards are marked where LMS telemetry is not available.", "success");
        }
        state.failures.forEach(function (failure) {
            showNotice(failure, "error");
        });
        state.warnings.forEach(function (warning) {
            showNotice(warning, "warning");
        });

        renderAll();
        setLoading(false);
    }

    async function loadLearnerScope() {
        state.courseDetails = null;
        state.learners = [];
        const courseId = els.courseSelect.value || "";
        state.selectedCourseId = courseId;

        if (state.demoMode) {
            state.learners = demoLearners().map(enrichLearner);
            assignRowKeys();
            return;
        }

        if (courseId) {
            const coursePath = `/course/${encodeURIComponent(courseId)}`;
            const learnerPath = `/course/${encodeURIComponent(courseId)}/learners`;
            const settled = await Promise.allSettled([
                fetchJson(coursePath, "Course detail", true),
                fetchJson(learnerPath, "Course learners", true),
            ]);
            if (settled[0].status === "fulfilled") {
                state.courseDetails = settled[0].value || null;
            } else {
                state.failures.push(`Course detail: ${settled[0].reason.message}`);
            }
            if (settled[1].status === "fulfilled") {
                const learners = (settled[1].value && settled[1].value.learners) || [];
                state.learners = learners.map(function (learner) {
                    return enrichLearner(learner, selectedCourseName(), courseId);
                });
                assignRowKeys();
            } else {
                state.failures.push(`Course learners: ${settled[1].reason.message}`);
            }
            return;
        }

        const sampledCourses = state.courses
            .slice()
            .sort(function (a, b) {
                return asNumber(b.total_enrollments) - asNumber(a.total_enrollments);
            })
            .slice(0, SAMPLE_COURSE_LIMIT);

        if (!sampledCourses.length) {
            state.learners = [];
            return;
        }

        const settled = await Promise.allSettled(sampledCourses.map(function (course) {
            const id = course.course_id || course.id;
            return fetchJson(`/course/${encodeURIComponent(id)}/learners`, course.course_name || id, true)
                .then(function (payload) {
                    return {
                        course,
                        learners: (payload && payload.learners) || [],
                    };
                });
        }));

        const learners = [];
        settled.forEach(function (result, index) {
            const course = sampledCourses[index];
            if (result.status !== "fulfilled") {
                state.failures.push(`${course.course_name || course.course_id}: learner load failed`);
                return;
            }
            result.value.learners.forEach(function (learner) {
                learners.push(enrichLearner(
                    learner,
                    course.course_name || course.name || course.course_id,
                    course.course_id || course.id
                ));
            });
        });
        state.learners = learners;
        assignRowKeys();
        if (sampledCourses.length < state.courses.length) {
            state.warnings.push(`Learner table samples the top ${sampledCourses.length} courses. Select a course for complete learner-level detail.`);
        }
    }

    function applyDemoFallback() {
        state.demoMode = true;
        state.metrics = {
            total_dealers: 642,
            total_assigned_courses: 1284,
            total_completed: 448,
            total_in_progress: 514,
            total_not_started: 322,
            overall_progress: 52,
            total_clusters: 9,
            total_asms: 41,
        };
        state.courses = [
            demoCourse("course-v1:sfl+LMS101+2026", "Sleepwell Product Essentials", 212, 82, 91, 62),
            demoCourse("course-v1:sfl+SALES201+2026", "Retail Sales Mastery", 188, 58, 96, 48),
            demoCourse("course-v1:sfl+CARE301+2026", "Customer Care Excellence", 146, 71, 43, 67),
            demoCourse("course-v1:sfl+OPS401+2026", "Dealer Operations Playbook", 164, 49, 75, 44),
            demoCourse("course-v1:sfl+BRAND501+2026", "Brand Story and Merchandising", 120, 36, 51, 51),
        ];
        state.clusters = [
            { cluster: "North", total_users: 138, assigned_courses: 276, completed_courses: 112, in_progress: 104, not_started: 60, avg_progress: 58 },
            { cluster: "West", total_users: 122, assigned_courses: 244, completed_courses: 92, in_progress: 96, not_started: 56, avg_progress: 53 },
            { cluster: "South", total_users: 144, assigned_courses: 288, completed_courses: 118, in_progress: 112, not_started: 58, avg_progress: 61 },
        ];
        state.asms = [
            { name: "ASM North 1", dealers: 42, assigned_courses: 84, completed_courses: 37, in_progress: 31, not_started: 16, avg_progress: 56 },
            { name: "ASM West 3", dealers: 38, assigned_courses: 76, completed_courses: 21, in_progress: 34, not_started: 21, avg_progress: 45 },
        ];
    }

    function demoCourse(id, name, enrollments, completed, progress, avg) {
        return {
            course_id: id,
            course_name: name,
            total_enrollments: enrollments,
            certificates_issued: completed,
            passed_count: completed,
            in_progress_count: progress,
            avg_grade: avg,
            avg_completion: avg,
            last_activity: new Date().toISOString(),
        };
    }

    function demoLearners() {
        const names = ["Aarav Mehta", "Priya Nair", "Rohan Khanna", "Neha Sharma", "Vikram Rao", "Anita Singh", "Karan Malhotra", "Meera Iyer", "Sanjay Verma", "Fatima Khan", "Dev Patel", "Ishita Das"];
        return names.map(function (name, index) {
            const course = state.courses[index % state.courses.length];
            const progress = [0, 12, 28, 42, 56, 68, 74, 81, 92, 100, 17, 35][index];
            const days = [2, 5, 12, 28, 41, 7, 14, 3, 9, 1, 34, 18][index];
            const date = new Date(Date.now() - days * 86400000).toISOString();
            return {
                user_id: 1000 + index,
                username: `learner${index + 1}`,
                email: `learner${index + 1}@example.com`,
                name,
                dealer_name: name,
                dealer_id: `DLR-${1000 + index}`,
                cluster: ["North", "West", "South", "East"][index % 4],
                asm: ["ASM North 1", "ASM West 3", "ASM South 2"][index % 3],
                rsm: ["RSM A", "RSM B"][index % 2],
                percent_grade: progress,
                grade_last_updated: progress > 0 ? date : null,
                enrollment_date: new Date(Date.now() - (days + 16) * 86400000).toISOString(),
                status: progress >= 100 ? "completed" : progress > 0 ? "in_progress" : "not_started",
                course_id: course.course_id,
                course_name: course.course_name,
            };
        });
    }

    function enrichLearner(learner, courseName, courseId) {
        const progress = clamp(learner.percent_grade || learner.grade, 0, 100);
        const status = normalizeStatus(Object.assign({}, learner, { percent_grade: progress }));
        const risk = scoreRisk(learner, progress, status);
        const totalUnits = asNumber(learner.total_modules) || 12;
        const completedUnits = asNumber(learner.completed_modules) || Math.round(totalUnits * (progress / 100));
        const row = Object.assign({}, learner, {
            course_id: learner.course_id || courseId || state.selectedCourseId,
            course_name: learner.course_name || courseName || selectedCourseName(),
            percent_grade: progress,
            status,
            status_label: statusLabel(status),
            risk_level: risk.level,
            risk_score: risk.score,
            risk_reason: risk.reason,
            recommended_action: risk.action,
            completed_units: completedUnits,
            total_units: totalUnits,
            time_spent_hours: estimateTimeSpent(progress, status),
        });
        row.name = row.name || row.dealer_name || row.username || "Learner";
        row.email = row.email || "N/A";
        row.username = row.username || "N/A";
        row.last_activity = row.grade_last_updated || row.passed_timestamp || row.enrollment_date;
        return row;
    }

    function assignRowKeys() {
        state.learners.forEach(function (row, index) {
            row._row_key = `${row.user_id || row.username || "learner"}::${row.course_id || "course"}::${index}`;
        });
    }

    function estimateTimeSpent(progress, status) {
        if (status === "not_started") {
            return 0;
        }
        return Math.max(0.4, (progress / 100) * 9.2 + (status === "completed" ? 1.4 : 0));
    }

    function scoreRisk(learner, progress, status) {
        let score = 0;
        const lastActivityDays = daysSince(learner.grade_last_updated || learner.passed_timestamp);
        const enrollmentDays = daysSince(learner.enrollment_date);
        const reasons = [];

        if (status === "completed") {
            score -= 40;
            reasons.push("Course completed.");
        } else if (status === "not_started") {
            score += 34;
            reasons.push("Learner has not started.");
        }

        if (progress <= 0) {
            score += 22;
        } else if (progress < 25) {
            score += 24;
            reasons.push("Progress is below 25%.");
        } else if (progress < 50) {
            score += 12;
            reasons.push("Progress is below the halfway mark.");
        }

        if (lastActivityDays > 30) {
            score += 34;
            reasons.push("No recent learning activity in over 30 days.");
        } else if (lastActivityDays > 14) {
            score += 22;
            reasons.push("Inactive for more than 14 days.");
        } else if (lastActivityDays > 7) {
            score += 10;
            reasons.push("Activity is cooling down.");
        }

        if (enrollmentDays > 21 && progress < 50 && status !== "completed") {
            score += 18;
            reasons.push("Enrollment is aging without enough progress.");
        }

        const level = score >= 60 ? "High" : score >= 30 ? "Medium" : "Low";
        const action = level === "High"
            ? "Call or message the learner and assign a completion deadline."
            : level === "Medium"
                ? "Send a reminder and recommend the next incomplete module."
                : "Keep learner in the normal monitoring cadence.";

        return {
            level,
            score: clamp(score, 0, 100),
            reason: reasons.join(" ") || "Learner is progressing normally.",
            action,
        };
    }

    function deriveSummary() {
        const selected = Boolean(state.selectedCourseId);
        const detail = state.courseDetails || {};
        const courses = state.courses;
        const learners = state.learners;

        const totalAssignments = selected
            ? asNumber(detail.total_enrollments) || learners.length
            : asNumber(state.metrics.total_assigned_courses) || sum(courses, "total_enrollments");
        const completed = selected
            ? asNumber(detail.passed_count || detail.certificates_issued) || countStatus(learners, "completed")
            : asNumber(state.metrics.total_completed) || sum(courses, "certificates_issued");
        const inProgress = selected
            ? asNumber(detail.in_progress_count) || countStatus(learners, "in_progress")
            : asNumber(state.metrics.total_in_progress) || sum(courses, "in_progress_count");
        const notStarted = selected
            ? asNumber(detail.not_started_count) || countStatus(learners, "not_started")
            : asNumber(state.metrics.total_not_started) || Math.max(0, totalAssignments - completed - inProgress);
        const totalLearners = selected
            ? totalAssignments
            : asNumber(state.metrics.total_dealers) || learners.length || totalAssignments;
        const activeLearners = selected
            ? completed + inProgress
            : Math.min(totalLearners || totalAssignments, completed + inProgress);
        const avgProgress = selected
            ? asNumber(detail.avg_grade || detail.avg_completion) || average(learners.map(function (row) { return row.percent_grade; }))
            : asNumber(state.metrics.overall_progress) || average(courses.map(function (course) { return course.avg_grade || course.avg_completion; }));
        const certificates = selected
            ? asNumber(detail.certificates_issued) || completed
            : sum(courses, "certificates_issued") || completed;
        const riskRows = learners.filter(function (row) { return row.risk_level === "High" || row.risk_level === "Medium"; });
        const estimatedRisk = learners.length ? riskRows.length : Math.round(notStarted * 0.72 + inProgress * 0.18);
        const dropOff = rate(notStarted + Math.round(inProgress * 0.25), totalAssignments);

        return {
            selected,
            totalAssignments,
            totalLearners,
            activeLearners,
            completed,
            inProgress,
            notStarted,
            avgProgress,
            completionRate: rate(completed, totalAssignments),
            certificates,
            riskLearners: estimatedRisk,
            avgTimeSpent: learners.length ? average(learners.map(function (row) { return row.time_spent_hours; })) : estimateTimeSpent(avgProgress, "in_progress"),
            dropOff,
        };
    }

    function sum(rows, key) {
        return (rows || []).reduce(function (total, row) {
            return total + asNumber(row[key]);
        }, 0);
    }

    function countStatus(rows, status) {
        return rows.filter(function (row) { return row.status === status; }).length;
    }

    function renderAll() {
        updateScope();
        state.tableRows = state.learners.slice();
        renderKpis();
        renderHealth();
        renderInsights();
        renderCourseCompletion();
        renderEngagementTrend();
        renderFunnel();
        renderDistribution();
        renderHeatmap();
        renderDropoff();
        renderRiskRadar();
        applyTableFilters();
    }

    function renderKpis() {
        const summary = deriveSummary();
        els.kpiTotalLearners.textContent = formatNumber(summary.totalLearners);
        els.kpiActiveLearners.textContent = formatNumber(summary.activeLearners);
        els.kpiAvgProgress.textContent = formatPercent(summary.avgProgress);
        els.kpiCompletionRate.textContent = formatPercent(summary.completionRate);
        els.kpiCertificates.textContent = formatNumber(summary.certificates);
        els.kpiRiskLearners.textContent = formatNumber(summary.riskLearners);
        els.kpiTimeSpent.textContent = formatHours(summary.avgTimeSpent);
        els.kpiDropOff.textContent = formatPercent(summary.dropOff);

        els.kpiTotalLearnersTrend.textContent = summary.selected ? "Enrolled in selected course" : "Unique learners estimated from dealer metadata";
        els.kpiActiveLearnersTrend.textContent = `${formatPercent(rate(summary.activeLearners, summary.totalLearners || summary.totalAssignments))} active`;
        els.kpiAvgProgressTrend.textContent = summary.avgProgress >= 60 ? "Healthy progress momentum" : "Needs acceleration";
        els.kpiCompletionRateTrend.textContent = `${formatNumber(summary.completed)} completed of ${formatNumber(summary.totalAssignments)}`;
        els.kpiCertificatesTrend.textContent = state.demoMode ? "Demo fallback certificates" : "Downloadable certificates";
        els.kpiRiskLearnersTrend.textContent = summary.riskLearners > 0 ? "Intervention recommended" : "No urgent risk detected";
        els.kpiDropOffTrend.textContent = summary.dropOff > 35 ? "High attention zone" : "Within monitoring range";
    }

    function renderHealth() {
        const summary = deriveSummary();
        const completion = summary.completionRate;
        const engagement = rate(summary.activeLearners, summary.totalLearners || summary.totalAssignments);
        const activity = state.learners.length
            ? clamp(100 - average(state.learners.map(function (row) { return daysSince(row.last_activity); })) * 2.4, 0, 100)
            : clamp(summary.avgProgress + 18, 0, 100);
        const dropoffPressure = summary.dropOff;
        const health = Math.round(
            completion * 0.35 +
            summary.avgProgress * 0.25 +
            engagement * 0.2 +
            (100 - dropoffPressure) * 0.2
        );

        els.healthScore.textContent = formatNumber(health);
        els.healthGauge.style.background = `conic-gradient(${healthColor(health)} 0deg ${health * 3.6}deg, var(--surface-3) ${health * 3.6}deg 360deg)`;
        els.healthLabel.textContent = health >= 75 ? "Excellent" : health >= 55 ? "Stable" : health >= 35 ? "Watch" : "Critical";
        els.healthCompletion.style.width = `${clamp(completion, 0, 100)}%`;
        els.healthEngagement.style.width = `${clamp(engagement, 0, 100)}%`;
        els.healthActivity.style.width = `${clamp(activity, 0, 100)}%`;
        els.healthDropoff.style.width = `${clamp(dropoffPressure, 0, 100)}%`;

        const friction = getFrictionPoints(summary);
        els.problemSections.innerHTML = friction.map(function (item) {
            return `
                <div class="problem-item">
                    <strong>${escapeHtml(item.title)}</strong>
                    <span>${escapeHtml(item.detail)}</span>
                </div>
            `;
        }).join("");
    }

    function healthColor(score) {
        if (score >= 75) {
            return "var(--green)";
        }
        if (score >= 55) {
            return "var(--blue)";
        }
        if (score >= 35) {
            return "var(--gold)";
        }
        return "var(--red)";
    }

    function getFrictionPoints(summary) {
        const weakestCourse = state.courses.slice().sort(function (a, b) {
            return completionForCourse(a) - completionForCourse(b);
        })[0];
        const highRisk = state.learners.filter(function (row) { return row.risk_level === "High"; }).length;
        return [
            {
                title: "Largest pressure",
                detail: summary.dropOff > 40 ? "Not-started and stalled learners are creating heavy drop-off." : "Drop-off is present but manageable.",
            },
            {
                title: "Problem course",
                detail: weakestCourse ? `${weakestCourse.course_name || weakestCourse.name}: ${formatPercent(completionForCourse(weakestCourse))} completion.` : "Select a course to inspect friction.",
            },
            {
                title: "Intervention load",
                detail: highRisk ? `${formatNumber(highRisk)} high-risk learners need direct follow-up.` : "No high-risk learner spike in the loaded scope.",
            },
        ];
    }

    function renderInsights() {
        const summary = deriveSummary();
        const sortedCourses = state.courses.slice().sort(function (a, b) {
            return completionForCourse(b) - completionForCourse(a);
        });
        const strongest = sortedCourses[0];
        const weakest = sortedCourses[sortedCourses.length - 1];
        const inactive = state.learners.filter(function (row) {
            return row.status !== "completed" && daysSince(row.last_activity) > 14;
        }).length;
        const topRiskCluster = topGroup(state.learners, "cluster", function (row) {
            return row.risk_level === "High" || row.risk_level === "Medium";
        });
        const insights = [
            {
                title: "Executive signal",
                text: `${formatPercent(summary.completionRate)} completion with ${formatNumber(summary.riskLearners)} learners in the intervention zone.`,
            },
            {
                title: "Best performing course",
                text: strongest ? `${strongest.course_name || strongest.name} is strongest at ${formatPercent(completionForCourse(strongest))} completion.` : "Course performance will appear when the overview API responds.",
            },
            {
                title: "Friction point",
                text: weakest ? `${weakest.course_name || weakest.name} needs attention: ${formatPercent(completionForCourse(weakest))} completion.` : "No course friction detected yet.",
            },
            {
                title: "Inactivity watch",
                text: inactive ? `${formatNumber(inactive)} loaded learners have been inactive for more than 14 days.` : "Recent activity looks healthy in the loaded learner scope.",
            },
            {
                title: "Cluster focus",
                text: topRiskCluster ? `${topRiskCluster.name} carries the largest loaded risk concentration.` : "Risk concentration by cluster will appear as learner data loads.",
            },
            {
                title: "Recommended action",
                text: summary.dropOff > 35 ? "Prioritize not-started learners first, then message medium-risk learners with the next module link." : "Maintain reminders and focus on courses below the portfolio completion average.",
            },
        ];
        els.insightsList.innerHTML = insights.map(function (item) {
            return `
                <div class="insight-item">
                    <strong>${escapeHtml(item.title)}</strong>
                    <p>${escapeHtml(item.text)}</p>
                </div>
            `;
        }).join("");
    }

    function topGroup(rows, key, filterFn) {
        const counts = new Map();
        rows.filter(filterFn).forEach(function (row) {
            const name = row[key] || "Unassigned";
            counts.set(name, (counts.get(name) || 0) + 1);
        });
        return Array.from(counts.entries())
            .sort(function (a, b) { return b[1] - a[1]; })
            .map(function (entry) { return { name: entry[0], count: entry[1] }; })[0];
    }

    function renderCourseCompletion() {
        const courses = state.courses.slice()
            .sort(function (a, b) { return asNumber(b.total_enrollments) - asNumber(a.total_enrollments); })
            .slice(0, 10);
        if (!courses.length) {
            els.courseCompletionChart.innerHTML = emptyState("Course completion will appear when course data loads.");
            return;
        }
        els.courseCompletionChart.innerHTML = courses.map(function (course) {
            const completion = completionForCourse(course);
            return `
                <div class="chart-row">
                    <div class="chart-name" title="${escapeHtml(course.course_name || course.name)}">${escapeHtml(course.course_name || course.name || course.course_id)}</div>
                    <div class="chart-track"><i class="chart-fill" style="width: ${clamp(completion, 0, 100)}%"></i></div>
                    <div class="chart-value">${formatPercent(completion)}</div>
                </div>
            `;
        }).join("");
    }

    function completionForCourse(course) {
        return rate(course.certificates_issued || course.passed_count, course.total_enrollments);
    }

    function renderEngagementTrend() {
        const canvas = els.engagementCanvas;
        if (!canvas) {
            return;
        }
        const ctx = canvas.getContext("2d");
        const rect = canvas.getBoundingClientRect();
        const ratio = window.devicePixelRatio || 1;
        canvas.width = Math.max(320, rect.width) * ratio;
        canvas.height = 260 * ratio;
        ctx.scale(ratio, ratio);
        const width = canvas.width / ratio;
        const height = canvas.height / ratio;
        ctx.clearRect(0, 0, width, height);

        const styles = getComputedStyle(document.documentElement);
        const lineColor = styles.getPropertyValue("--cyan").trim() || "#59e6ff";
        const fillColor = styles.getPropertyValue("--blue").trim() || "#5ba7ff";
        const muted = styles.getPropertyValue("--muted").trim() || "#9dafc7";
        const grid = styles.getPropertyValue("--line").trim() || "rgba(155,175,205,.18)";
        const summary = deriveSummary();
        const base = Math.max(4, Math.round(summary.activeLearners || summary.completed + summary.inProgress || 12));
        const points = Array.from({ length: 8 }).map(function (_, index) {
            const wave = Math.sin(index * 0.9) * 0.11;
            const lift = (index / 10) * (summary.avgProgress >= 50 ? 0.18 : 0.05);
            return Math.max(1, Math.round(base * (0.72 + wave + lift)));
        });
        const max = Math.max.apply(Math, points) * 1.18;
        const pad = 34;
        const step = (width - pad * 2) / (points.length - 1);

        ctx.strokeStyle = grid;
        ctx.lineWidth = 1;
        for (let i = 0; i < 4; i += 1) {
            const y = pad + i * ((height - pad * 2) / 3);
            ctx.beginPath();
            ctx.moveTo(pad, y);
            ctx.lineTo(width - pad, y);
            ctx.stroke();
        }

        const coords = points.map(function (value, index) {
            return {
                x: pad + index * step,
                y: height - pad - (value / max) * (height - pad * 2),
                value,
            };
        });

        const gradient = ctx.createLinearGradient(0, pad, 0, height - pad);
        gradient.addColorStop(0, colorWithAlpha(fillColor, 0.34));
        gradient.addColorStop(1, colorWithAlpha(fillColor, 0.02));
        ctx.beginPath();
        coords.forEach(function (point, index) {
            if (index === 0) {
                ctx.moveTo(point.x, point.y);
            } else {
                ctx.lineTo(point.x, point.y);
            }
        });
        ctx.lineTo(width - pad, height - pad);
        ctx.lineTo(pad, height - pad);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.beginPath();
        coords.forEach(function (point, index) {
            if (index === 0) {
                ctx.moveTo(point.x, point.y);
            } else {
                ctx.lineTo(point.x, point.y);
            }
        });
        ctx.strokeStyle = lineColor;
        ctx.lineWidth = 3;
        ctx.stroke();

        coords.forEach(function (point, index) {
            ctx.beginPath();
            ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
            ctx.fillStyle = lineColor;
            ctx.fill();
            ctx.fillStyle = muted;
            ctx.font = "12px Inter, sans-serif";
            ctx.fillText(`W${index + 1}`, point.x - 9, height - 10);
        });
    }

    function colorWithAlpha(color, alpha) {
        if (color.startsWith("#") && color.length === 7) {
            const r = parseInt(color.slice(1, 3), 16);
            const g = parseInt(color.slice(3, 5), 16);
            const b = parseInt(color.slice(5, 7), 16);
            return `rgba(${r}, ${g}, ${b}, ${alpha})`;
        }
        return color;
    }

    function renderFunnel() {
        const funnel = funnelValues();
        const max = Math.max(1, funnel[0].value);
        els.funnelChart.innerHTML = funnel.map(function (step) {
            return `
                <div class="funnel-step">
                    <div class="funnel-label">${escapeHtml(step.label)}</div>
                    <div class="funnel-bar"><i style="width: ${clamp(rate(step.value, max), 0, 100)}%"></i></div>
                    <strong>${formatNumber(step.value)}</strong>
                </div>
            `;
        }).join("");
    }

    function funnelValues() {
        const summary = deriveSummary();
        if (state.learners.length) {
            return [
                { label: "Enrolled", value: state.learners.length },
                { label: "Started", value: state.learners.filter(function (row) { return row.percent_grade > 0 || row.status === "completed"; }).length },
                { label: "25% complete", value: state.learners.filter(function (row) { return row.percent_grade >= 25; }).length },
                { label: "50% complete", value: state.learners.filter(function (row) { return row.percent_grade >= 50; }).length },
                { label: "75% complete", value: state.learners.filter(function (row) { return row.percent_grade >= 75; }).length },
                { label: "Completed", value: state.learners.filter(function (row) { return row.status === "completed"; }).length },
                { label: "Certified", value: Math.min(summary.certificates, state.learners.length) },
            ];
        }
        const enrolled = summary.totalAssignments;
        return [
            { label: "Enrolled", value: enrolled },
            { label: "Started", value: summary.activeLearners },
            { label: "25% complete", value: Math.round(summary.activeLearners * 0.78) },
            { label: "50% complete", value: Math.round(summary.activeLearners * 0.56) },
            { label: "75% complete", value: Math.round(summary.completed + summary.inProgress * 0.22) },
            { label: "Completed", value: summary.completed },
            { label: "Certified", value: summary.certificates },
        ];
    }

    function renderDistribution() {
        const buckets = [
            { label: "0%", min: 0, max: 0, count: 0 },
            { label: "1-24%", min: 1, max: 24, count: 0 },
            { label: "25-49%", min: 25, max: 49, count: 0 },
            { label: "50-74%", min: 50, max: 74, count: 0 },
            { label: "75-100%", min: 75, max: 100, count: 0 },
        ];
        const source = state.learners.length
            ? state.learners.map(function (row) { return row.percent_grade; })
            : state.courses.map(function (course) { return course.avg_grade || completionForCourse(course); });
        source.forEach(function (progress) {
            const value = clamp(progress, 0, 100);
            const bucket = buckets.find(function (item) {
                return value >= item.min && value <= item.max;
            });
            if (bucket) {
                bucket.count += 1;
            }
        });
        const max = Math.max(1, Math.max.apply(Math, buckets.map(function (bucket) { return bucket.count; })));
        els.distributionChart.innerHTML = buckets.map(function (bucket) {
            const height = Math.max(8, rate(bucket.count, max) * 180);
            return `
                <div class="bucket">
                    <div class="bucket-bar" style="height: ${height}px"></div>
                    <strong>${formatNumber(bucket.count)}</strong>
                    <span>${escapeHtml(bucket.label)}</span>
                </div>
            `;
        }).join("");
    }

    function renderHeatmap() {
        const labels = ["M", "T", "W", "T", "F", "S", "S"];
        const values = [];
        const summary = deriveSummary();
        for (let week = 0; week < 4; week += 1) {
            for (let day = 0; day < 7; day += 1) {
                const seed = (week + 1) * (day + 3);
                const base = state.learners.length || summary.activeLearners || 20;
                values.push(Math.round(base * (0.04 + ((seed % 9) / 100))));
            }
        }
        const max = Math.max(1, Math.max.apply(Math, values));
        els.heatmapGrid.innerHTML = values.map(function (value, index) {
            const intensity = rate(value, max);
            const alpha = 0.16 + intensity / 120;
            const label = labels[index % 7];
            return `
                <div class="heat-cell" style="background: rgba(40, 199, 217, ${alpha.toFixed(2)});" title="${formatNumber(value)} estimated active learners">
                    ${escapeHtml(label)}
                </div>
            `;
        }).join("");
    }

    function renderDropoff() {
        const funnel = funnelValues().slice(1, 6);
        const max = Math.max(1, funnel[0] ? funnel[0].value : 1);
        const stages = funnel.map(function (item, index) {
            const previous = index === 0 ? max : funnel[index - 1].value;
            const loss = Math.max(0, previous - item.value);
            return {
                label: item.label,
                loss,
                rate: rate(loss, max),
            };
        });
        els.dropoffChart.innerHTML = stages.map(function (stage) {
            return `
                <div class="dropoff-stage">
                    <span>${escapeHtml(stage.label)}</span>
                    <div class="dropoff-track"><i style="width: ${clamp(stage.rate, 2, 100)}%"></i></div>
                    <strong>${formatPercent(stage.rate)}</strong>
                </div>
            `;
        }).join("");
    }

    function renderRiskRadar() {
        const riskRows = state.learners.slice()
            .sort(function (a, b) { return b.risk_score - a.risk_score; })
            .slice(0, 10);
        if (!riskRows.length) {
            els.riskList.innerHTML = emptyState("Select a course or wait for learner APIs to populate risk radar.");
            return;
        }
        els.riskList.innerHTML = riskRows.map(function (row) {
            return `
                <article class="risk-item" data-row-key="${escapeHtml(row._row_key)}">
                    <strong>${escapeHtml(row.name)}</strong>
                    <p>${escapeHtml(row.course_name)} | ${formatPercent(row.percent_grade)} progress</p>
                    <div class="risk-meta">
                        <span class="risk-badge ${row.risk_level.toLowerCase()}">${escapeHtml(row.risk_level)} risk</span>
                        <span class="state-pill">${escapeHtml(row.cluster || "Unassigned")}</span>
                    </div>
                </article>
            `;
        }).join("");
        els.riskList.querySelectorAll(".risk-item").forEach(function (item) {
            item.addEventListener("click", function () {
                const row = state.learners.find(function (learner) {
                    return String(learner._row_key) === item.getAttribute("data-row-key");
                });
                if (row) {
                    openLearnerDrawer(row);
                }
            });
        });
    }

    function applyTableFilters() {
        const search = (els.tableSearch.value || "").trim().toLowerCase();
        const status = els.statusFilter.value;
        const risk = els.riskFilter.value;
        state.filteredRows = state.tableRows.filter(function (row) {
            const searchable = [
                row.name, row.email, row.username, row.course_name, row.cluster, row.asm, row.dealer_id,
            ].join(" ").toLowerCase();
            return (!search || searchable.includes(search)) &&
                (!status || row.status === status) &&
                (!risk || row.risk_level === risk);
        });
        sortRows();
        state.page = Math.min(state.page, totalPages());
        if (state.page < 1) {
            state.page = 1;
        }
        renderTable();
    }

    function sortRows() {
        const key = state.sort.key;
        const dir = state.sort.dir === "asc" ? 1 : -1;
        state.filteredRows.sort(function (a, b) {
            const left = a[key];
            const right = b[key];
            const leftNum = Number(left);
            const rightNum = Number(right);
            if (Number.isFinite(leftNum) && Number.isFinite(rightNum)) {
                return (leftNum - rightNum) * dir;
            }
            return String(left || "").localeCompare(String(right || "")) * dir;
        });
    }

    function totalPages() {
        return Math.max(1, Math.ceil(state.filteredRows.length / PAGE_SIZE));
    }

    function visibleRows() {
        const start = (state.page - 1) * PAGE_SIZE;
        return state.filteredRows.slice(start, start + PAGE_SIZE);
    }

    function renderTable() {
        const rows = visibleRows();
        if (!rows.length) {
            els.learnerTableBody.innerHTML = `<tr><td colspan="9">${emptyState("No learners match the current filters.")}</td></tr>`;
        } else {
            els.learnerTableBody.innerHTML = rows.map(function (row) {
                return `
                    <tr data-row-key="${escapeHtml(row._row_key)}">
                        <td>
                            <div class="learner-cell">
                                <strong>${escapeHtml(row.name)}</strong>
                                <span>${escapeHtml(row.email || row.username)}</span>
                            </div>
                        </td>
                        <td>${escapeHtml(row.course_name || "N/A")}</td>
                        <td>${formatDate(row.enrollment_date)}</td>
                        <td>${formatDate(row.last_activity)}</td>
                        <td>
                            <div class="progress-cell">
                                <strong>${formatPercent(row.percent_grade)}</strong>
                                <div class="progress-bar"><i style="width: ${clamp(row.percent_grade, 0, 100)}%"></i></div>
                            </div>
                        </td>
                        <td>${formatNumber(row.completed_units)} / ${formatNumber(row.total_units)}</td>
                        <td>${formatHours(row.time_spent_hours)}</td>
                        <td><span class="status-badge ${escapeHtml(row.status)}">${escapeHtml(row.status_label)}</span></td>
                        <td><span class="risk-badge ${row.risk_level.toLowerCase()}">${escapeHtml(row.risk_level)}</span></td>
                    </tr>
                `;
            }).join("");
        }
        els.tableCount.textContent = `${formatNumber(state.filteredRows.length)} learners`;
        els.pageInfo.textContent = `Page ${state.page} of ${totalPages()}`;
        els.prevPageBtn.disabled = state.page <= 1;
        els.nextPageBtn.disabled = state.page >= totalPages();
        els.learnerTableBody.querySelectorAll("tr[data-row-key]").forEach(function (rowNode) {
            rowNode.addEventListener("click", function () {
                const rowKey = rowNode.getAttribute("data-row-key");
                const row = state.filteredRows.find(function (learner) {
                    return String(learner._row_key) === String(rowKey);
                });
                if (row) {
                    openLearnerDrawer(row);
                }
            });
        });
    }

    function emptyState(message) {
        return `<div class="empty-state">${escapeHtml(message)}</div>`;
    }

    function openLearnerDrawer(row) {
        els.drawerTitle.textContent = row.name;
        els.drawerKicker.textContent = `${row.risk_level} Risk | ${row.status_label}`;
        renderDrawer(row, null);
        els.drawerScrim.hidden = false;
        els.learnerDrawer.classList.add("is-open");
        els.learnerDrawer.setAttribute("aria-hidden", "false");

        if (row.user_id && !state.demoMode) {
            fetchJson(`/user-id/${encodeURIComponent(row.user_id)}`, "Learner profile", false)
                .then(function (profile) {
                    renderDrawer(row, profile);
                })
                .catch(function () {
                    renderDrawer(row, null, "Detailed profile API is unavailable; showing loaded course-level learner data.");
                });
        }
    }

    function closeDrawer() {
        els.learnerDrawer.classList.remove("is-open");
        els.learnerDrawer.setAttribute("aria-hidden", "true");
        els.drawerScrim.hidden = true;
    }

    function renderDrawer(row, profile, warning) {
        const profileCourses = profile && Array.isArray(profile.courses) ? profile.courses : [];
        const profileBlock = profileCourses.length
            ? `<div class="drawer-card">
                    <h3>Other course signals</h3>
                    <div class="timeline-grid">
                        ${profileCourses.slice(0, 4).map(function (course) {
                            return `<div class="timeline-step"><span>${escapeHtml(course.course_name || course.course_id)}</span><strong>${formatPercent(course.percent_grade || course.grade)}</strong></div>`;
                        }).join("")}
                    </div>
                </div>`
            : "";
        els.drawerBody.innerHTML = `
            <div class="drawer-grid">
                ${warning ? `<div class="notice warning">${escapeHtml(warning)}</div>` : ""}
                <div class="drawer-card">
                    <h3>Profile summary</h3>
                    <div class="profile-grid">
                        ${drawerField("Email", row.email)}
                        ${drawerField("Username", row.username)}
                        ${drawerField("Dealer ID", row.dealer_id)}
                        ${drawerField("Cluster", row.cluster)}
                        ${drawerField("ASM", row.asm)}
                        ${drawerField("RSM", row.rsm)}
                    </div>
                </div>
                <div class="drawer-card">
                    <h3>Progress timeline</h3>
                    <div class="timeline-grid">
                        ${drawerField("Course", row.course_name)}
                        ${drawerField("Enrollment", formatDate(row.enrollment_date))}
                        ${drawerField("Last activity", formatDate(row.last_activity))}
                        ${drawerField("Progress", formatPercent(row.percent_grade))}
                        ${drawerField("Completed units", `${formatNumber(row.completed_units)} / ${formatNumber(row.total_units)}`)}
                        ${drawerField("Estimated time", formatHours(row.time_spent_hours))}
                    </div>
                </div>
                <div class="drawer-card">
                    <h3>Risk reason</h3>
                    <p class="muted-text">${escapeHtml(row.risk_reason)}</p>
                </div>
                <div class="drawer-card action-box">
                    <h3>Recommended intervention</h3>
                    <p>${escapeHtml(row.recommended_action)}</p>
                </div>
                ${profileBlock}
            </div>
        `;
    }

    function drawerField(label, value) {
        return `
            <div class="profile-field">
                <span>${escapeHtml(label)}</span>
                <strong>${escapeHtml(value || "N/A")}</strong>
            </div>
        `;
    }

    function exportRows(rows, filename) {
        const headers = [
            "learner_name", "email", "username", "course", "enrollment_date", "last_activity",
            "progress_percent", "completed_units", "total_units", "time_spent_hours", "status",
            "risk_level", "risk_reason", "recommended_action", "cluster", "asm", "rsm", "dealer_id",
        ];
        const csvRows = [headers.join(",")].concat(rows.map(function (row) {
            return headers.map(function (header) {
                const value = {
                    learner_name: row.name,
                    email: row.email,
                    username: row.username,
                    course: row.course_name,
                    enrollment_date: row.enrollment_date,
                    last_activity: row.last_activity,
                    progress_percent: row.percent_grade,
                    completed_units: row.completed_units,
                    total_units: row.total_units,
                    time_spent_hours: row.time_spent_hours,
                    status: row.status_label,
                    risk_level: row.risk_level,
                    risk_reason: row.risk_reason,
                    recommended_action: row.recommended_action,
                    cluster: row.cluster,
                    asm: row.asm,
                    rsm: row.rsm,
                    dealer_id: row.dealer_id,
                }[header];
                return csvEscape(value);
            }).join(",");
        }));
        const blob = new Blob([csvRows.join("\n")], { type: "text/csv;charset=utf-8" });
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        URL.revokeObjectURL(link.href);
        link.remove();
    }

    function csvEscape(value) {
        const text = String(value == null ? "" : value);
        if (/[",\n]/.test(text)) {
            return `"${text.replace(/"/g, '""')}"`;
        }
        return text;
    }

    function bindEvents() {
        els.dateRange.addEventListener("change", function () {
            updateCustomDates();
            loadDashboardData();
        });
        els.startDate.addEventListener("change", loadDashboardData);
        els.endDate.addEventListener("change", loadDashboardData);
        els.courseSelect.addEventListener("change", loadDashboardData);
        els.refreshBtn.addEventListener("click", loadDashboardData);
        els.exportBtn.addEventListener("click", function () {
            exportRows(visibleRows(), "learning-intelligence-visible-learners.csv");
        });
        els.riskExportBtn.addEventListener("click", function () {
            exportRows(state.learners.filter(function (row) {
                return row.risk_level === "High" || row.risk_level === "Medium";
            }), "learning-intelligence-risk-radar.csv");
        });
        els.themeToggle.addEventListener("click", function () {
            const current = document.documentElement.getAttribute("data-theme") || "dark";
            setTheme(current === "dark" ? "light" : "dark");
        });
        [els.tableSearch, els.statusFilter, els.riskFilter].forEach(function (input) {
            input.addEventListener("input", function () {
                state.page = 1;
                applyTableFilters();
            });
        });
        document.querySelectorAll("th button[data-sort]").forEach(function (button) {
            button.addEventListener("click", function () {
                const key = button.getAttribute("data-sort");
                if (state.sort.key === key) {
                    state.sort.dir = state.sort.dir === "asc" ? "desc" : "asc";
                } else {
                    state.sort = { key, dir: "asc" };
                }
                applyTableFilters();
            });
        });
        els.prevPageBtn.addEventListener("click", function () {
            state.page = Math.max(1, state.page - 1);
            renderTable();
        });
        els.nextPageBtn.addEventListener("click", function () {
            state.page = Math.min(totalPages(), state.page + 1);
            renderTable();
        });
        els.drawerClose.addEventListener("click", closeDrawer);
        els.drawerScrim.addEventListener("click", closeDrawer);
        window.addEventListener("resize", debounce(renderEngagementTrend, 140));
        window.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                closeDrawer();
            }
        });
    }

    function debounce(fn, wait) {
        let timer = null;
        return function () {
            clearTimeout(timer);
            timer = setTimeout(fn, wait);
        };
    }

    function init() {
        bindElements();
        bindEvents();
        setTheme(getSavedTheme());
        updateCustomDates();
        loadDashboardData();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
}());
