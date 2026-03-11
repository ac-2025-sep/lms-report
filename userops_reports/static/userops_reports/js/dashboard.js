const API_BASE_URL = new URL('../api', `${window.location.origin}${window.location.pathname.replace(/\/?$/, '/')}`).pathname;
        let mainChart, statusChart;
        let currentView = 'courses';
        let currentViewMode = 'card';
        let selectedAsm = null;
        let selectedCourse = null;
        let asmsList = [];
        let coursesList = [];
        let allCourses = [];
        
        // Pagination variables
        let currentPage = 1;
        let rowsPerPage = 10;
        let totalPages = 1;
        let tableSortBy = 'name';
        let tableSortOrder = 'asc';
        
        // Store current data for table view
        window.currentViewData = [];
        window.currentViewType = 'course';

        // Switch to Clusters View
        function switchToClustersView() {
    currentView = 'clusters';
    document.getElementById('viewSelect').value = 'clusters';
    document.getElementById('asmSelectContainer').style.display = 'none';
    document.getElementById('courseSelectContainer').style.display = 'none';
    document.getElementById('backBtn').style.display = 'none';
    selectedAsm = null;
    selectedCourse = null;
    
    // Update active card styling
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    // Clusters card is the second card (index 1)
    document.querySelectorAll('.summary-card')[1].classList.add('active');
    
    loadClusterPerformance();
}


function switchToAsmsView() {
    currentView = 'asms';
    document.getElementById('viewSelect').value = 'asms';
    document.getElementById('asmSelectContainer').style.display = 'inline-block';
    document.getElementById('courseSelectContainer').style.display = 'none';
    document.getElementById('backBtn').style.display = 'none';
    selectedAsm = null;
    selectedCourse = null;
    
    // Update active card styling
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    // ASMs card is the third card (index 2)
    document.querySelectorAll('.summary-card')[2].classList.add('active');
    
    loadAsmsOverview();
}



        function switchToCoursesView() {
    currentView = 'courses';
    document.getElementById('viewSelect').value = 'courses';
    document.getElementById('courseSelectContainer').style.display = 'inline-block';
    document.getElementById('asmSelectContainer').style.display = 'none';
    document.getElementById('backBtn').style.display = 'none';
    selectedCourse = null;
    selectedAsm = null;
    
    // Update active card styling
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    // Active Courses card is the first card (index 0)
    document.querySelectorAll('.summary-card')[0].classList.add('active');
    
    loadCoursesOverview();
}



        function showLoading(show) {
            document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
        }

        function showError(message) {
            const errorDiv = document.getElementById('errorMessage');
            document.getElementById('errorText').textContent = message;
            errorDiv.style.display = 'block';
            setTimeout(() => {
                errorDiv.style.display = 'none';
            }, 5000);
        }

        function formatNumber(num) {
            if (num === null || num === undefined) return '0';
            return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        }

        function closeModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }

        function backToMainView() {
            selectedAsm = null;
            selectedCourse = null;
            document.getElementById('backBtn').style.display = 'none';
            document.getElementById('asmSelectContainer').style.display = 'none';
            document.getElementById('courseSelectContainer').style.display = 'none';
            document.getElementById('asmSelect').value = '';
            document.getElementById('courseSelect').value = '';
            currentView = document.getElementById('viewSelect').value;
            loadViewData();
        }

        function setViewMode(mode) {
            currentViewMode = mode;
            
            document.getElementById('cardViewBtn').classList.toggle('active', mode === 'card');
            document.getElementById('tableViewBtn').classList.toggle('active', mode === 'table');
            
            const clustersGrid = document.getElementById('clustersGrid');
            const tableViewContainer = document.getElementById('tableViewContainer');
            const paginationContainer = document.getElementById('paginationContainer');
            
            if (mode === 'card') {
                clustersGrid.style.display = 'grid';
                tableViewContainer.style.display = 'none';
                paginationContainer.style.display = 'none';
            } else {
                clustersGrid.style.display = 'none';
                tableViewContainer.style.display = 'block';
                paginationContainer.style.display = 'flex';
            }
            
            if (window.currentViewData.length > 0) {
                if (mode === 'card') {
                    if (currentView === 'courses') {
                        renderCourseCardView(window.currentViewData);
                    } else {
                        renderCardView(window.currentViewData, window.currentViewType);
                    }
                } else {
                    renderTableView(window.currentViewData, window.currentViewType);
                }
            }
        }

        async function loadAllData() {
            showLoading(true);
            try {
                await loadSummaryMetrics();
                await loadCourses();
                await loadAsmsList();
                await loadCoursesList();
                
                if (currentView === 'clusters') {
                    await loadClusterPerformance();
                } else if (currentView === 'asms') {
                    if (selectedAsm) {
                        await loadAsmDetails(selectedAsm);
                    } else {
                        await loadAsmsOverview();
                    }
                } else if (currentView === 'courses') {
                    if (selectedCourse) {
                        await loadCourseDetails(selectedCourse);
                    } else {
                        await loadCoursesOverview();
                    }
                }
                
                document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error loading data:', error);
                showError('Failed to load dashboard data');
            } finally {
                showLoading(false);
            }
        }

        async function loadCourses() {
            try {
                const response = await fetch(`${API_BASE_URL}/courses/overview`);
                if (!response.ok) throw new Error('Failed to fetch courses');
                
                const data = await response.json();
                allCourses = data.courses || [];
                document.getElementById('activeCourses').textContent = allCourses.length;
                
            } catch (error) {
                console.error('Error loading courses:', error);
                document.getElementById('activeCourses').textContent = '0';
            }
        }

        async function loadCoursesList() {
            try {
                const response = await fetch(`${API_BASE_URL}/courses`);
                if (!response.ok) throw new Error('Failed to fetch courses');
                
                const data = await response.json();
                coursesList = data.courses || [];
                
                const select = document.getElementById('courseSelect');
                select.innerHTML = '<option value="">Select Course...</option>';
                coursesList.forEach(course => {
                    const option = document.createElement('option');
                    option.value = course.id;
                    option.textContent = course.display_name || course.name || 'Unknown';
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading courses list:', error);
            }
        }

        async function showCoursesModal() {
            showLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/courses/overview`);
                if (!response.ok) throw new Error('Failed to fetch courses');
                
                const data = await response.json();
                allCourses = data.courses || [];
                
                renderCoursesTable(allCourses);
                document.getElementById('coursesModal').style.display = 'flex';
                
            } catch (error) {
                console.error('Error loading courses:', error);
                showError('Failed to load courses');
            } finally {
                showLoading(false);
            }
        }

        function renderCoursesTable(courses) {
            const tbody = document.getElementById('coursesTableBody');
            
            if (!courses || courses.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No courses found</td></tr>';
                return;
            }

            let html = '';
            courses.forEach(course => {
                const completionRate = course.total_enrollments > 0 
                    ? ((course.certificates_issued / course.total_enrollments) * 100).toFixed(1) 
                    : 0;
                
                html += `
                    <tr onclick="showCourseDetailsFromModal('${course.course_id}')" style="cursor: pointer;">
                        <td><strong>${course.course_name || 'Unknown'}</strong></td>
                        <td><span class="course-badge">${course.course_id || 'N/A'}</span></td>
                        <td>${formatNumber(course.total_enrollments || 0)}</td>
                        <td>${formatNumber(course.certificates_issued || 0)}</td>
                        <td>${completionRate}%</td>
                        <td>${course.last_activity ? new Date(course.last_activity).toLocaleDateString() : 'N/A'}</td>
                    </tr>
                `;
            });
            
            tbody.innerHTML = html;
        }

        function filterCourses() {
            const searchTerm = document.getElementById('courseSearch').value.toLowerCase();
            const filtered = allCourses.filter(course => 
                (course.course_name || '').toLowerCase().includes(searchTerm) ||
                (course.course_id || '').toLowerCase().includes(searchTerm)
            );
            renderCoursesTable(filtered);
        }

        async function loadAsmsList() {
            try {
                const response = await fetch(`${API_BASE_URL}/asms`);
                if (!response.ok) throw new Error('Failed to fetch ASMs');
                
                const data = await response.json();
                asmsList = data.asms || [];
                
                const select = document.getElementById('asmSelect');
                select.innerHTML = '<option value="">Select ASM...</option>';
                asmsList.forEach(asm => {
                    const option = document.createElement('option');
                    option.value = asm;
                    option.textContent = asm;
                    select.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading ASMs:', error);
            }
        }

        async function loadSummaryMetrics() {
            try {
                const response = await fetch(`${API_BASE_URL}/dashboard-metrics`);
                if (!response.ok) throw new Error('Failed to fetch metrics');
                
                const data = await response.json();

                document.getElementById('totalClusters').textContent = data.total_clusters || 0;
                document.getElementById('totalAsms').textContent = data.total_asms || 0;
                document.getElementById('totalDealers').textContent = formatNumber(data.total_dealers || 0);
                document.getElementById('totalCourses').textContent = formatNumber(data.total_assigned_courses || 0);
                document.getElementById('avgProgress').textContent = (data.overall_progress || 0) + '%';

                // document.getElementById('assignedCount').textContent = formatNumber(data.total_assigned_courses || 0);
                // document.getElementById('completedCount').textContent = formatNumber(data.total_completed || 0);
                // document.getElementById('progressCount').textContent = formatNumber(data.total_in_progress || 0);
                // document.getElementById('notStartedCount').textContent = formatNumber(data.total_not_started || 0);

                updateStatusChart(data);
                
            } catch (error) {
                console.error('Error loading summary metrics:', error);
                throw error;
            }
        }

        async function loadViewData() {
            if (currentView === 'clusters') {
                await loadClusterPerformance();
            } else if (currentView === 'asms') {
                if (selectedAsm) {
                    await loadAsmDetails(selectedAsm);
                } else {
                    await loadAsmsOverview();
                }
            } else if (currentView === 'courses') {
                if (selectedCourse) {
                    await loadCourseDetails(selectedCourse);
                } else {
                    await loadCoursesOverview();
                }
            }
        }

        async function loadClusterPerformance() {
            try {
                const response = await fetch(`${API_BASE_URL}/cluster-performance`);
                if (!response.ok) throw new Error('Failed to fetch cluster data');
                
                const data = await response.json();

                document.getElementById('gridTitleText').textContent = 'Clusters';
                document.getElementById('gridIcon').className = 'fas fa-layer-group';
                document.getElementById('chartTitle').textContent = 'Cluster Performance';
                
                window.currentViewData = data.clusters || [];
                window.currentViewType = 'cluster';
                
                currentPage = 1;
                
                if (currentViewMode === 'card') {
                    renderCardView(window.currentViewData, 'cluster');
                } else {
                    renderTableView(window.currentViewData, 'cluster');
                }
                updateMainChart(window.currentViewData, 'cluster');
                
            } catch (error) {
                console.error('Error loading cluster performance:', error);
                throw error;
            }
        }

        async function loadAsmsOverview() {
            showLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/asm-overview`);
                if (!response.ok) throw new Error('Failed to fetch ASM overview');
                
                const data = await response.json();

                document.getElementById('gridTitleText').textContent = 'ASMs';
                document.getElementById('gridIcon').className = 'fas fa-user-tie';
                document.getElementById('chartTitle').textContent = 'ASM Performance';
                
                window.currentViewData = data;
                window.currentViewType = 'asm';
                
                currentPage = 1;
                
                if (currentViewMode === 'card') {
                    renderCardView(data, 'asm');
                } else {
                    renderTableView(data, 'asm');
                }
                updateMainChart(data, 'asm');
                
            } catch (error) {
                console.error('Error loading ASM overview:', error);
                showError('Failed to load ASM overview');
                document.getElementById('clustersGrid').innerHTML = 
                    '<div style="grid-column:1/-1; text-align:center; padding:40px;">No ASM data found</div>';
            } finally {
                showLoading(false);
            }
        }

        async function loadCoursesOverview() {
            showLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/courses/overview`);
                if (!response.ok) throw new Error('Failed to fetch courses');
                
                const data = await response.json();

                document.getElementById('gridTitleText').textContent = 'Courses';
                document.getElementById('gridIcon').className = 'fas fa-book-open';
                document.getElementById('chartTitle').textContent = 'Course Performance';
                
                window.currentViewData = data.courses || [];
                window.currentViewType = 'course';
                
                currentPage = 1;
                
                if (currentViewMode === 'card') {
                    renderCourseCardView(data.courses || []);
                } else {
                    renderTableView(data.courses || [], 'course');
                }
                updateCourseChart(data.courses || []);
                
            } catch (error) {
                console.error('Error loading courses overview:', error);
                showError('Failed to load courses');
                document.getElementById('clustersGrid').innerHTML = 
                    '<div style="grid-column:1/-1; text-align:center; padding:40px;">No courses found</div>';
            } finally {
                showLoading(false);
            }
        }

        async function loadAsmDetails(asmName) {
            showLoading(true);
            try {
                const response = await fetch(`${API_BASE_URL}/asm-dealers/${encodeURIComponent(asmName)}`);
                if (!response.ok) throw new Error('Failed to fetch ASM details');
                
                const data = await response.json();
                
                document.getElementById('gridTitleText').textContent = `Clusters under ${asmName}`;
                document.getElementById('gridIcon').className = 'fas fa-layer-group';
                document.getElementById('chartTitle').textContent = `ASM ${asmName} - Clusters`;
                
                window.currentViewData = data.clusters || [];
                window.currentViewType = 'cluster';
                
                currentPage = 1;
                
                if (currentViewMode === 'card') {
                    renderCardView(data.clusters || [], 'cluster');
                } else {
                    renderTableView(data.clusters || [], 'cluster');
                }
                updateMainChart(data.clusters || [], 'cluster');
                
            } catch (error) {
                console.error('Error loading ASM details:', error);
                showError('Failed to load ASM details');
            } finally {
                showLoading(false);
            }
        }

        async function loadCourseDetails(courseId) {
            showLoading(true);
            try {
                await showCourseDetails(courseId);
                document.getElementById('gridTitleText').textContent = `Course: ${courseId}`;
            } catch (error) {
                console.error('Error loading course details:', error);
                showError('Failed to load course details');
            } finally {
                showLoading(false);
            }
        }


function renderCourseCardView(courses) {
    const grid = document.getElementById('clustersGrid');
    grid.style.display = 'grid';
    
    if (!courses || courses.length === 0) {
        grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px;">No courses found</div>';
        return;
    }

    let html = '';
    courses.forEach(course => {
        const name = course.course_name || 'Unknown';
        const learners = course.total_enrollments || 0;
        const completed = course.active_learners || 0;
        // Use avg_completion (average grade) instead of completion rate
        const avgGrade = course.avg_completion || 0;  // This comes from /courses/overview endpoint
        
        html += `
            <div class="cluster-card" onclick="showCourseDetails('${course.course_id}')">
                <div class="cluster-header">
                    <span class="cluster-name">${name.length > 30 ? name.substring(0,30)+'...' : name}</span>
                    <span class="cluster-badge">${learners} learners</span>
                </div>
                <div class="cluster-stats">
                    <div class="stat-item">
                        <div class="stat-value">${formatNumber(learners)}</div>
                        <div class="stat-label">Enrollments</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">${formatNumber(completed)}</div>
                        <div class="stat-label">Passed</div>
                    </div>
                </div>
                <div class="progress-container">
                    <div class="progress-label">
                        <span>Avg Grade</span>
                        <span>${avgGrade}%</span>
                    </div>
                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: ${avgGrade}%;"></div>
                    </div>
                </div>
                <div style="font-size:0.7rem; color:#6c757d; margin-top:8px;">
                    Last activity: ${course.last_activity ? new Date(course.last_activity).toLocaleDateString() : 'N/A'}
                </div>
            </div>
        `;
    });
    
    grid.innerHTML = html;
}




        function renderCardView(items, type) {
            const grid = document.getElementById('clustersGrid');
            grid.style.display = 'grid';
            
            if (!items || items.length === 0) {
                grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px;">No items found</div>';
                return;
            }

            let html = '';
            items.forEach(item => {
                const name = item.cluster || item.name;
                const dealers = item.dealers || item.total_users || 0;
                const assigned = item.assigned_courses || item.assigned || 0;
                const completed = item.completed_courses || item.completed || 0;
                const inProgress = item.in_progress || 0;
                const notStarted = item.not_started || 0;
                const progress = parseFloat(item.avg_progress || 0).toFixed(1);
                
                html += `
                    <div class="cluster-card" onclick="${type === 'cluster' ? `showClusterDetails('${name.replace(/'/g, "\\'")}')` : `showAsmDetails('${name.replace(/'/g, "\\'")}')`}">
                        <div class="cluster-header">
                            <span class="cluster-name">${name}</span>
                            <span class="cluster-badge">${dealers} dealers</span>
                        </div>
                        <div class="cluster-stats">
                            <div class="stat-item">
                                <div class="stat-value">${formatNumber(assigned)}</div>
                                <div class="stat-label">Assigned</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${formatNumber(completed)}</div>
                                <div class="stat-label">Completed</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${formatNumber(inProgress)}</div>
                                <div class="stat-label">In Progress</div>
                            </div>
                            <div class="stat-item">
                                <div class="stat-value">${formatNumber(notStarted)}</div>
                                <div class="stat-label">Not Started</div>
                            </div>
                        </div>
                        <div class="progress-container">
                            <div class="progress-label">
                                <span>Avg Progress</span>
                                <span>${progress}%</span>
                            </div>
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill" style="width: ${progress}%;"></div>
                            </div>
                        </div>
                    </div>
                `;
            });
            
            grid.innerHTML = html;
        }

        
        
// Render table view with pagination - FIXED for ASM and Cluster
function renderTableView(items, type) {
    const sortedItems = sortItems(items, tableSortBy, tableSortOrder);
    
    const start = (currentPage - 1) * rowsPerPage;
    const end = start + rowsPerPage;
    const paginatedItems = sortedItems.slice(start, end);
    
    renderTableHeader(type);
    
    let tbodyHtml = '';
    paginatedItems.forEach(item => {
        if (type === 'course') {
            // Course table view
            const name = item.course_name || 'Unknown';
            const learners = item.total_enrollments || 0;
            const completed = item.certificates_issued || 0;
            const inProgress = item.active_learners || 0;
            const notStarted = learners - completed - inProgress;
            const progress = parseFloat(item.avg_completion || 0).toFixed(1);
            
            tbodyHtml += `
                <tr onclick="showCourseDetails('${item.course_id}')">
                    <td><strong>${name}</strong></td>
                    <td>${learners}</td>
                    <td>${completed}</td>
                    <td>${inProgress}</td>
                    <td>${Math.max(0, notStarted)}</td>
                    <td>
                        <div class="table-progress">
                            <span>${progress}%</span>
                            <div class="table-progress-bar">
                                <div class="table-progress-fill" style="width: ${progress}%;"></div>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        } else if (type === 'cluster') {
            // Cluster table view - FIXED
            const name = item.cluster || 'Unknown';
            const dealers = item.total_users || 0;
            const assigned = item.assigned_courses || 0;
            const completed = item.completed_courses || 0;
            const inProgress = item.in_progress || 0;
            const notStarted = item.not_started || 0;
            const progress = parseFloat(item.avg_progress || 0).toFixed(1);
            
            tbodyHtml += `
                <tr onclick="showClusterDetails('${name.replace(/'/g, "\\'")}')">
                    <td><strong>${name}</strong></td>
                    <td>${dealers}</td>
                    <td>${assigned}</td>
                    <td>${completed}</td>
                    <td>${inProgress}</td>
                    <td>${notStarted}</td>
                    <td>
                        <div class="table-progress">
                            <span>${progress}%</span>
                            <div class="table-progress-bar">
                                <div class="table-progress-fill" style="width: ${progress}%;"></div>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        } else if (type === 'asm') {
            // ASM table view - FIXED
            const name = item.name || 'Unknown';
            const dealers = item.dealers || 0;
            const assigned = item.assigned_courses || 0;
            const completed = item.completed_courses || 0;
            const inProgress = item.in_progress || 0;
            const notStarted = item.not_started || 0;
            const progress = parseFloat(item.avg_progress || 0).toFixed(1);
            
            tbodyHtml += `
                <tr onclick="showAsmDetails('${name.replace(/'/g, "\\'")}')">
                    <td><strong>${name}</strong></td>
                    <td>${dealers}</td>
                    <td>${assigned}</td>
                    <td>${completed}</td>
                    <td>${inProgress}</td>
                    <td>${notStarted}</td>
                    <td>
                        <div class="table-progress">
                            <span>${progress}%</span>
                            <div class="table-progress-bar">
                                <div class="table-progress-fill" style="width: ${progress}%;"></div>
                            </div>
                        </div>
                    </td>
                </tr>
            `;
        }
    });
    
    // If no rows, show empty message
    if (tbodyHtml === '') {
        const colSpan = type === 'course' ? 6 : 7;
        tbodyHtml = `<tr><td colspan="${colSpan}" style="text-align:center; padding:40px;">No data found</td></tr>`;
    }
    
    document.getElementById('tableBody').innerHTML = tbodyHtml;
    updatePagination(items.length);
}



// Render table header - UPDATED
function renderTableHeader(type) {
    let headers;
    if (type === 'course') {
        headers = [
            { key: 'name', label: 'Course Name' },
            { key: 'learners', label: 'Learners' },
            { key: 'completed', label: 'Completed' },
            { key: 'inProgress', label: 'In Progress' },
            { key: 'notStarted', label: 'Not Started' },
            { key: 'progress', label: 'Completion %' }
        ];
    } else if (type === 'cluster') {
        headers = [
            { key: 'name', label: 'Cluster' },
            { key: 'dealers', label: 'Dealers' },
            { key: 'assigned', label: 'Assigned' },
            { key: 'completed', label: 'Completed' },
            { key: 'inProgress', label: 'In Progress' },
            { key: 'notStarted', label: 'Not Started' },
            { key: 'progress', label: 'Avg Progress' }
        ];
    } else if (type === 'asm') {
        headers = [
            { key: 'name', label: 'ASM' },
            { key: 'dealers', label: 'Dealers' },
            { key: 'assigned', label: 'Assigned' },
            { key: 'completed', label: 'Completed' },
            { key: 'inProgress', label: 'In Progress' },
            { key: 'notStarted', label: 'Not Started' },
            { key: 'progress', label: 'Avg Progress' }
        ];
    }
    
    let headerHtml = '<tr>';
    headers.forEach(header => {
        const isSorted = tableSortBy === header.key;
        const sortIcon = isSorted ? 
            (tableSortOrder === 'asc' ? 'fa-sort-up' : 'fa-sort-down') : 
            'fa-sort';
        
        headerHtml += `
            <th onclick="sortTable('${header.key}')">
                ${header.label} <i class="fas ${sortIcon}"></i>
            </th>
        `;
    });
    headerHtml += '</tr>';
    
    document.getElementById('tableHeader').innerHTML = headerHtml;
}






// Sort items helper - UPDATED for ASM and Cluster
function sortItems(items, sortBy, sortOrder) {
    return [...items].sort((a, b) => {
        let valA, valB;
        
        if (sortBy === 'name') {
            valA = (a.course_name || a.cluster || a.name || '').toLowerCase();
            valB = (b.course_name || b.cluster || b.name || '').toLowerCase();
        } else if (sortBy === 'learners' || sortBy === 'dealers') {
            valA = a.total_enrollments || a.dealers || a.total_users || 0;
            valB = b.total_enrollments || b.dealers || b.total_users || 0;
        } else if (sortBy === 'assigned') {
            valA = a.assigned_courses || a.assigned || 0;
            valB = b.assigned_courses || b.assigned || 0;
        } else if (sortBy === 'completed') {
            valA = a.completed_courses || a.completed || 0;
            valB = b.completed_courses || b.completed || 0;
        } else if (sortBy === 'inProgress') {
            valA = a.in_progress || 0;
            valB = b.in_progress || 0;
        } else if (sortBy === 'notStarted') {
            valA = a.not_started || 0;
            valB = b.not_started || 0;
        } else if (sortBy === 'progress') {
            valA = parseFloat(a.avg_progress || a.avg_completion || 0);
            valB = parseFloat(b.avg_progress || b.avg_completion || 0);
        }
        
        if (sortOrder === 'asc') {
            return valA > valB ? 1 : -1;
        } else {
            return valA < valB ? 1 : -1;
        }
    });
}



        function sortTable(column) {
            if (tableSortBy === column) {
                tableSortOrder = tableSortOrder === 'asc' ? 'desc' : 'asc';
            } else {
                tableSortBy = column;
                tableSortOrder = 'asc';
            }
            
            currentPage = 1;
            renderTableView(window.currentViewData, window.currentViewType);
        }

        function updatePagination(totalItems) {
            totalPages = Math.ceil(totalItems / rowsPerPage);
            
            const start = ((currentPage - 1) * rowsPerPage) + 1;
            const end = Math.min(currentPage * rowsPerPage, totalItems);
            
            document.getElementById('paginationStart').textContent = totalItems > 0 ? start : 0;
            document.getElementById('paginationEnd').textContent = end;
            document.getElementById('paginationTotal').textContent = totalItems;
            
            document.getElementById('firstPage').disabled = currentPage === 1 || totalItems === 0;
            document.getElementById('prevPage').disabled = currentPage === 1 || totalItems === 0;
            document.getElementById('nextPage').disabled = currentPage === totalPages || totalItems === 0;
            document.getElementById('lastPage').disabled = currentPage === totalPages || totalItems === 0;
            
            let pageNumbers = '';
            const maxVisiblePages = 5;
            let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
            let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);
            
            if (endPage - startPage + 1 < maxVisiblePages) {
                startPage = Math.max(1, endPage - maxVisiblePages + 1);
            }
            
            for (let i = startPage; i <= endPage; i++) {
                pageNumbers += `
                    <button class="pagination-btn ${i === currentPage ? 'active' : ''}" 
                            onclick="goToPage(${i})">${i}</button>
                `;
            }
            
            document.getElementById('pageNumbers').innerHTML = pageNumbers;
        }

        function changeRowsPerPage() {
            rowsPerPage = parseInt(document.getElementById('rowsPerPage').value);
            currentPage = 1;
            renderTableView(window.currentViewData, window.currentViewType);
        }

        function goToPage(page) {
            if (page < 1 || page > totalPages) return;
            currentPage = page;
            renderTableView(window.currentViewData, window.currentViewType);
        }

        function updateMainChart(items, type) {
            const ctx = document.getElementById('mainChart').getContext('2d');
            
            if (mainChart) mainChart.destroy();
            
            const labels = items.map(i => i.cluster || i.name);
            const completedData = items.map(i => i.completed_courses || i.completed || 0);
            const inProgressData = items.map(i => i.in_progress || 0);
            const notStartedData = items.map(i => i.not_started || 0);
            
            mainChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Completed',
                            data: completedData,
                            backgroundColor: '#107c41',
                            stack: 'total'
                        },
                        {
                            label: 'In Progress',
                            data: inProgressData,
                            backgroundColor: '#f9b84a',
                            stack: 'total'
                        },
                        {
                            label: 'Not Started',
                            data: notStartedData,
                            backgroundColor: '#dc3545',
                            stack: 'total'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    },
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true, beginAtZero: true }
                    },
                    onClick: (event, items) => {
                        if (items && items.length > 0) {
                            const index = items[0].dataIndex;
                            const name = labels[index];
                            if (type === 'cluster') {
                                showClusterDetails(name);
                            } else if (type === 'asm') {
                                showAsmDetails(name);
                            }
                        }
                    }
                }
            });
        }

        function updateCourseChart(courses) {
            const ctx = document.getElementById('mainChart').getContext('2d');
            
            if (mainChart) mainChart.destroy();
            
            const labels = courses.map(c => (c.course_name || '').substring(0, 20) + '...');
            const learners = courses.map(c => c.total_enrollments || 0);
            const completed = courses.map(c => c.certificates_issued || 0);
            
            mainChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Enrollments',
                            data: learners,
                            backgroundColor: '#1e6bc7'
                        },
                        {
                            label: 'Completed',
                            data: completed,
                            backgroundColor: '#107c41'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    },
                    scales: {
                        y: { beginAtZero: true }
                    },
                    onClick: (event, items) => {
                        if (items && items.length > 0) {
                            const index = items[0].dataIndex;
                            showCourseDetails(courses[index].course_id);
                        }
                    }
                }
            });
        }

        function updateStatusChart(data) {
            const ctx = document.getElementById('statusChart').getContext('2d');
            
            if (statusChart) statusChart.destroy();
            
            statusChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Completed', 'In Progress', 'Not Started'],
                    datasets: [{
                        data: [
                            data.total_completed || 0,
                            data.total_in_progress || 0,
                            data.total_not_started || 0
                        ],
                        backgroundColor: ['#107c41', '#f9b84a', '#dc3545'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }

        async function showClusterDetails(clusterName) {
            showLoading(true);
            try {
                document.getElementById('modalClusterName').textContent = clusterName;
                
                const response = await fetch(`${API_BASE_URL}/asm-performance/${encodeURIComponent(clusterName)}`);
                if (!response.ok) throw new Error('Failed to fetch cluster details');
                
                const data = await response.json();

                document.getElementById('modalSummary').innerHTML = `
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${data.totals?.dealers || 0}</div>
                        <div class="modal-summary-label">Total Dealers</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${formatNumber(data.totals?.assigned_courses || 0)}</div>
                        <div class="modal-summary-label">Assigned Courses</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${data.totals?.completed || 0}</div>
                        <div class="modal-summary-label">Completed</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${data.totals?.avg_progress || 0}%</div>
                        <div class="modal-summary-label">Avg Progress</div>
                    </div>
                `;

                // In showClusterDetails function, update the RSM grouping:

// Group by RSM (rsm field)
const rsmMap = new Map();
data.dealers?.forEach(dealer => {
    const rsm = dealer.rsm || 'Unassigned';  // Changed from asm_2 to rsm
    
    if (rsm !== 'Unassigned' && rsm !== 'N/A') {
        if (!rsmMap.has(rsm)) {
            rsmMap.set(rsm, {
                dealers: [],
                assigned: 0,
                completed: 0,
                inProgress: 0,
                notStarted: 0,
                totalProgress: 0,
                asmDetails: new Map()
            });
        }
        const rsmData = rsmMap.get(rsm);
        rsmData.dealers.push(dealer);
        rsmData.assigned += dealer.courses_assigned || 0;
        rsmData.completed += dealer.completed_courses || 0;
        rsmData.inProgress += dealer.in_progress || 0;
        rsmData.notStarted += dealer.not_started || 0;
        rsmData.totalProgress += dealer.avg_progress || 0;
        
        const asm = dealer.asm || 'Unassigned';  // Changed from asm_1 to asm
        if (!rsmData.asmDetails.has(asm)) {
            rsmData.asmDetails.set(asm, {
                dealers: [],
                assigned: 0,
                completed: 0,
                inProgress: 0,
                notStarted: 0,
                totalProgress: 0
            });
        }
        const asmData = rsmData.asmDetails.get(asm);
        asmData.dealers.push(dealer);
        asmData.assigned += dealer.courses_assigned || 0;
        asmData.completed += dealer.completed_courses || 0;
        asmData.inProgress += dealer.in_progress || 0;
        asmData.notStarted += dealer.not_started || 0;
        asmData.totalProgress += dealer.avg_progress || 0;
    }
});

                let rsmArray = [];
                for (const [rsm, rsmData] of rsmMap) {
                    const avgProgress = rsmData.dealers.length > 0 ? 
                        (rsmData.totalProgress / rsmData.dealers.length).toFixed(1) : 0;
                    
                    let asmArray = [];
                    for (const [asm, asmData] of rsmData.asmDetails) {
                        const asmAvgProgress = asmData.dealers.length > 0 ? 
                            (asmData.totalProgress / asmData.dealers.length).toFixed(1) : 0;
                        
                        asmArray.push({
                            name: asm,
                            dealers: asmData.dealers.length,
                            assigned: asmData.assigned,
                            completed: asmData.completed,
                            inProgress: asmData.inProgress,
                            notStarted: asmData.notStarted,
                            avgProgress: asmAvgProgress,
                            dealerList: asmData.dealers
                        });
                    }
                    
                    asmArray.sort((a, b) => a.name.localeCompare(b.name));
                    
                    rsmArray.push({
                        name: rsm,
                        dealers: rsmData.dealers.length,
                        assigned: rsmData.assigned,
                        completed: rsmData.completed,
                        inProgress: rsmData.inProgress,
                        notStarted: rsmData.notStarted,
                        avgProgress: avgProgress,
                        asmDetails: asmArray,
                        expanded: false
                    });
                }

                rsmArray.sort((a, b) => a.name.localeCompare(b.name));
                
                window.currentRsmData = rsmArray;

                renderRsmTable(rsmArray);

                document.getElementById('clusterModal').style.display = 'flex';
                
            } catch (error) {
                console.error('Error loading cluster details:', error);
                showError('Failed to load cluster details');
            } finally {
                showLoading(false);
            }
        }

        function renderRsmTable(rsmArray) {
            let rsmHtml = '';
            
            rsmArray.forEach(rsm => {
                rsmHtml += `
                    <tr onclick="toggleRsmExpand('${rsm.name.replace(/'/g, "\\'")}')" 
                        style="cursor: pointer; background-color: ${rsm.expanded ? '#f0f7ff' : 'white'};">
                        <td><span class="rsm-badge">${rsm.name}</span></td>
                        <td>${rsm.dealers}</td>
                        <td>${formatNumber(rsm.assigned)}</td>
                        <td>${rsm.completed}</td>
                        <td>${rsm.inProgress}</td>
                        <td>${rsm.notStarted}</td>
                        <td>${rsm.avgProgress}%</td>
                    </tr>
                `;
                
                if (rsm.expanded && rsm.asmDetails && rsm.asmDetails.length > 0) {
                    rsm.asmDetails.forEach(asm => {
                        rsmHtml += `
                            <tr onclick="showAsmDealers('${rsm.name.replace(/'/g, "\\'")}', '${asm.name.replace(/'/g, "\\'")}')" 
                                style="cursor: pointer; background-color: #f8fafd;">
                                <td style="padding-left: 40px;">
                                    <span class="asm-badge">↳ ${asm.name}</span>
                                </td>
                                <td>${asm.dealers}</td>
                                <td>${formatNumber(asm.assigned)}</td>
                                <td>${asm.completed}</td>
                                <td>${asm.inProgress}</td>
                                <td>${asm.notStarted}</td>
                                <td>${asm.avgProgress}%</td>
                            </tr>
                        `;
                    });
                }
            });

            const header = `
                <tr>
                    <th>RSM</th>
                    <th>Dealers</th>
                    <th>Assigned</th>
                    <th>Completed</th>
                    <th>In Progress</th>
                    <th>Not Started</th>
                    <th>Avg Progress</th>
                </tr>
            `;

            document.getElementById('modalRsmHeader').innerHTML = header;
            document.getElementById('modalRsmTable').innerHTML = rsmHtml;
        }

        function toggleRsmExpand(rsmName) {
            const rsm = window.currentRsmData.find(r => r.name === rsmName);
            if (rsm) {
                rsm.expanded = !rsm.expanded;
                renderRsmTable(window.currentRsmData);
            }
            event.stopPropagation();
        }

        function showAsmDealers(rsmName, asmName) {
            event.stopPropagation();
            
            const rsm = window.currentRsmData.find(r => r.name === rsmName);
            if (!rsm) return;
            
            const asm = rsm.asmDetails.find(a => a.name === asmName);
            if (!asm || !asm.dealerList) return;

            document.getElementById('dealersModalTitle').textContent = `Dealers under ${asmName}`;
            
            document.getElementById('dealersModalSummary').innerHTML = `
                <div class="modal-summary-card">
                    <div class="modal-summary-value">${asm.dealers}</div>
                    <div class="modal-summary-label">Dealers</div>
                </div>
                <div class="modal-summary-card">
                    <div class="modal-summary-value">${formatNumber(asm.assigned)}</div>
                    <div class="modal-summary-label">Assigned</div>
                </div>
                <div class="modal-summary-card">
                    <div class="modal-summary-value">${asm.completed}</div>
                    <div class="modal-summary-label">Completed</div>
                </div>
                <div class="modal-summary-card">
                    <div class="modal-summary-value">${asm.avgProgress}%</div>
                    <div class="modal-summary-label">Avg Progress</div>
                </div>
            `;

            let dealerHtml = '';
            asm.dealerList.forEach(dealer => {
                const progressClass = dealer.avg_progress >= 70 ? 'badge-completed' : 
                                     dealer.avg_progress > 0 ? 'badge-progress' : 'badge-notstarted';
                
                dealerHtml += `
                    <tr>
                        <td><strong>${dealer.dealer_name || 'N/A'}</strong></td>
                        <td>${dealer.dealer_id || 'N/A'}</td>
                        <td>${dealer.champion_name || dealer.username || 'N/A'}</td>
                        <td>${dealer.champion_mobile || 'N/A'}</td>
                        <td>${dealer.courses_assigned || 0}</td>
                        <td>${dealer.completed || 0}</td>
                        <td>${dealer.in_progress || 0}</td>
                        <td>${dealer.not_started || 0}</td>
                        <td>
                            <span class="status-badge ${progressClass}">${dealer.avg_progress || 0}%</span>
                            <div class="mini-progress">
                                <div style="height:100%; width:${dealer.avg_progress || 0}%; background: #1e6bc7;"></div>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            document.getElementById('dealersModalTable').innerHTML = dealerHtml || 
                '<tr><td colspan="9" style="text-align:center;">No dealers found</td></tr>';

            document.getElementById('dealersModal').style.display = 'flex';
        }

        async function showAsmDetails(asmName) {
            showLoading(true);
            try {
                document.getElementById('modalAsmName').textContent = asmName;
                
                const response = await fetch(`${API_BASE_URL}/asm-dealers/${encodeURIComponent(asmName)}`);
                if (!response.ok) throw new Error('Failed to fetch ASM details');
                
                const data = await response.json();

                const totals = {
                    dealers: data.dealers?.length || 0,
                    assigned: data.totals?.assigned_courses || 0,
                    completed: data.totals?.completed_courses || 0,
                    inProgress: data.totals?.in_progress || 0,
                    notStarted: data.totals?.not_started || 0,
                    avgProgress: data.totals?.avg_progress || 0
                };

                document.getElementById('asmModalSummary').innerHTML = `
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${totals.dealers}</div>
                        <div class="modal-summary-label">Dealers</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${formatNumber(totals.assigned)}</div>
                        <div class="modal-summary-label">Assigned</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${totals.completed}</div>
                        <div class="modal-summary-label">Completed</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${totals.avgProgress}%</div>
                        <div class="modal-summary-label">Avg Progress</div>
                    </div>
                `;

                let clusterHtml = '';
                data.clusters?.forEach(cluster => {
                    clusterHtml += `
                        <tr>
                            <td><strong>${cluster.name}</strong></td>
                            <td>${cluster.dealers}</td>
                            <td>${formatNumber(cluster.assigned_courses)}</td>
                            <td>${cluster.completed_courses}</td>
                            <td>${cluster.in_progress}</td>
                            <td>${cluster.not_started}</td>
                            <td>${cluster.avg_progress}%</td>
                        </tr>
                    `;
                });
                
                document.getElementById('asmModalClustersTable').innerHTML = clusterHtml || 
                    '<tr><td colspan="7" style="text-align:center;">No clusters found</td></tr>';

                let dealerHtml = '';
                data.dealers?.forEach(dealer => {
                    const progressClass = dealer.avg_progress >= 70 ? 'badge-completed' : 
                                         dealer.avg_progress > 0 ? 'badge-progress' : 'badge-notstarted';
                    
                    dealerHtml += `
                        <tr>
                            <td><strong>${dealer.dealer_name || 'N/A'}</strong></td>
                            <td>${dealer.dealer_id || 'N/A'}</td>
                            <td>${dealer.cluster || 'N/A'}</td>
                            <td>${dealer.champion_name || dealer.username || 'N/A'}</td>
                            <td>${dealer.champion_mobile || 'N/A'}</td>
                            <td>${dealer.courses_assigned || 0}</td>
                            <td>
                                <span class="status-badge ${progressClass}">${dealer.avg_progress || 0}%</span>
                                <div class="mini-progress">
                                    <div style="height:100%; width:${dealer.avg_progress || 0}%; background: #1e6bc7;"></div>
                                </div>
                            </td>
                        </tr>
                    `;
                });
                
                document.getElementById('asmModalDealersTable').innerHTML = dealerHtml || 
                    '<tr><td colspan="7" style="text-align:center;">No dealers found</td></tr>';

                document.getElementById('asmModal').style.display = 'flex';
                
            } catch (error) {
                console.error('Error loading ASM details:', error);
                showError('Failed to load ASM details');
            } finally {
                showLoading(false);
            }
        }

        // FIXED: showCourseDetails function - working version
        async function showCourseDetails(courseId) {
            showLoading(true);
            try {

                
                // Close courses modal if open
                const coursesModal = document.getElementById('coursesModal');
                if (coursesModal && coursesModal.style.display === 'flex') {
                    coursesModal.style.display = 'none';
                }
                
                document.getElementById('modalCourseName').textContent = `Course: ${courseId}`;
                
                // Fetch course and learners data
                const [courseRes, learnersRes] = await Promise.all([
                    fetch(`${API_BASE_URL}/courses/${courseId}`),
                    fetch(`${API_BASE_URL}/courses/${courseId}/learners`)
                ]);

                // Process course data
                let courseData = {};
                if (courseRes.ok) {
                    courseData = await courseRes.json();
                }

                const avgGrade = courseData.avg_grade || 0;  // Use the value from backend

                // Process learners data
                let learnersData = { learners: [] };
                if (learnersRes.ok) {
                    learnersData = await learnersRes.json();
                }

                // Get all learners
                const allLearners = learnersData.learners || [];
                
                // Calculate counts
                const totalLearners = allLearners.length;
                const completedCount = allLearners.filter(l => l.completion_status === 'Passed').length;
                const inProgressCount = allLearners.filter(l => l.completion_status === 'Not Passed' && l.percent_grade > 0).length;
                
                // Calculate average progress
                const avgProgress = allLearners.length > 0 
                    ? Math.round(allLearners.reduce((sum, l) => sum + (l.percent_grade || 0), 0) / allLearners.length) 
                    : 0;

                // Update summary
                // Update the summary's 4th card
                document.getElementById('courseModalSummary').innerHTML = `
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${totalLearners}</div>
                        <div class="modal-summary-label">Total Enrollments</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${completedCount}</div>
                        <div class="modal-summary-label">Passed</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${inProgressCount}</div>
                        <div class="modal-summary-label">In Progress</div>
                    </div>
                    <div class="modal-summary-card">
                        <div class="modal-summary-value">${avgGrade}%</div>
                        <div class="modal-summary-label">Avg Grade</div>
                    </div>
                `;

                // Update the Learners section heading
                const learnersHeading = document.querySelector('#courseModal .modal-section h3');
                if (learnersHeading) {
                    learnersHeading.innerHTML = `<i class="fas fa-users"></i> Learners Progress (${totalLearners} total, ${inProgressCount} active)`;
                }

                // Get the learners table body
                const learnersTableBody = document.getElementById('courseModalDealersTable');
                if (!learnersTableBody) return;

                // Render learners table
                let learnerHtml = '';
                
                if (allLearners.length > 0) {
                    const sortedLearners = [...allLearners].sort((a, b) => (b.percent_grade || 0) - (a.percent_grade || 0));
                    
                    sortedLearners.forEach(l => {
                        const gradeValue = l.percent_grade || 0;
                        const statusClass = l.completion_status === 'Passed' ? 'badge-passed' : 'badge-not-passed';
                        const statusText = l.completion_status || 'Not Passed';
                        const letterGrade = l.letter_grade || 'N/A';
                        const passedDate = l.passed_timestamp ? new Date(l.passed_timestamp).toLocaleDateString() : 'N/A';
                        
                        learnerHtml += `
                            <tr>
                                <td><strong>${l.dealer_name || l.username || 'N/A'}</strong></td>
                                <td>${l.username || 'N/A'}</td>
                                <td>${l.dealer_id || 'N/A'}</td>
                                <td>${l.cluster || 'N/A'}</td>
                                <td>${l.asm || 'N/A'}</td>
                                <td>${l.rsm || 'N/A'}</td>
                                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                                <td>${gradeValue.toFixed(1)}%</td>
                                <td>${letterGrade}</td>
                                <td>${passedDate}</td>
                            </tr>
                        `;
                    });
                } else {
                    learnerHtml = '<tr><td colspan="10" style="text-align:center; padding:30px;">No learners found for this course</td></tr>';
                }
                
                learnersTableBody.innerHTML = learnerHtml;

                document.getElementById('courseModal').style.display = 'flex';
                
            } catch (error) {
                console.error('Error in showCourseDetails:', error);
                showError('Failed to load course details: ' + error.message);
            } finally {
                showLoading(false);
            }
        }

        async function showCourseDetailsFromModal(courseId) {
            closeModal('coursesModal');
            await showCourseDetails(courseId);
        }

        async function refreshData() {
            await loadAllData();
        }

        async function exportToExcel() {
            // Excel export function remains the same as before
            showLoading(true);
            try {
                // ... existing export code ...
                // (keeping it as is)
            } catch (error) {
                console.error('Error exporting:', error);
                showError('Failed to export data');
            } finally {
                showLoading(false);
            }
        }

        document.getElementById('viewSelect').addEventListener('change', function(e) {
            currentView = e.target.value;
            selectedAsm = null;
            selectedCourse = null;
            
            document.getElementById('asmSelectContainer').style.display = 'none';
            document.getElementById('courseSelectContainer').style.display = 'none';
            document.getElementById('backBtn').style.display = 'none';
            
            if (currentView === 'asms') {
                document.getElementById('asmSelectContainer').style.display = 'inline-block';
                loadAsmsOverview();
            } else if (currentView === 'courses') {
                document.getElementById('courseSelectContainer').style.display = 'inline-block';
                loadCoursesOverview();
            } else {
                loadClusterPerformance();
            }
        });

        document.getElementById('asmSelect').addEventListener('change', function(e) {
            selectedAsm = e.target.value;
            if (selectedAsm) {
                document.getElementById('backBtn').style.display = 'inline-flex';
                loadAsmDetails(selectedAsm);
            } else {
                document.getElementById('backBtn').style.display = 'none';
                loadAsmsOverview();
            }
        });

        document.getElementById('courseSelect').addEventListener('change', function(e) {
            selectedCourse = e.target.value;
            if (selectedCourse) {
                document.getElementById('backBtn').style.display = 'inline-flex';
                loadCourseDetails(selectedCourse);
            } else {
                document.getElementById('backBtn').style.display = 'none';
                loadCoursesOverview();
            }
        });

        window.onclick = function(event) {
            if (event.target.classList.contains('modal-overlay')) {
                event.target.style.display = 'none';
            }
        };

        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                document.querySelectorAll('.modal-overlay').forEach(modal => {
                    modal.style.display = 'none';
                });
            }
        });

        // Set active card based on view
function setActiveCard(viewName) {
    // Remove active class from all cards
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    
    // Find and activate cards with matching data-view
    // Note: There might be multiple cards with same view (Active Courses and Courses)
    document.querySelectorAll(`.summary-card[data-view="${viewName}"]`).forEach(card => {
        card.classList.add('active');
    });
}









// Search functionality
let searchTimeout;
const searchInput = document.getElementById('userSearch');
const searchResults = document.getElementById('searchResults');

searchInput.addEventListener('input', function(e) {
    clearTimeout(searchTimeout);
    const query = e.target.value.trim();
    
    if (query.length < 2) {
        searchResults.classList.remove('show');
        return;
    }
    
    searchTimeout = setTimeout(() => performSearch(query), 300);
});

// Close search results when clicking outside
document.addEventListener('click', function(e) {
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
        searchResults.classList.remove('show');
    }
});

async function performSearch(query) {
    searchResults.innerHTML = '<div class="search-loading"><i class="fas fa-spinner fa-spin"></i> Searching...</div>';
    searchResults.classList.add('show');
    
    try {
        const response = await fetch(`${API_BASE_URL}/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        displaySearchResults(data.users || []);
    } catch (error) {
        console.error('Search error:', error);
        searchResults.innerHTML = '<div class="search-no-results">Error searching. Please try again.</div>';
    }
}

function displaySearchResults(users) {
    if (!users || users.length === 0) {
        searchResults.innerHTML = '<div class="search-no-results">No users found</div>';
        return;
    }
    
    let html = '';
    users.forEach(user => {
        const progressClass = user.avg_progress >= 70 ? 'badge-completed' :
                            user.avg_progress > 0 ? 'badge-progress' : 'badge-notstarted';
        
        html += `
            <div class="search-result-item" onclick="showUserDetails(${user.user_id})">
                <div class="search-result-name">
                    <i class="fas fa-user"></i> ${user.dealer_name || user.username}
                </div>
                <div class="search-result-details">
                    <span><i class="fas fa-at"></i> ${user.username}</span>
                    <span><i class="fas fa-id-card"></i> ${user.dealer_id}</span>
                    <span><i class="fas fa-layer-group"></i> ${user.cluster}</span>
                    <span><i class="fas fa-chart-line"></i> <span class="${progressClass}">${user.avg_progress}%</span></span>
                </div>
            </div>
        `;
    });
    
    searchResults.innerHTML = html;
}

async function showUserDetails(userId) {
    showLoading(true);
    searchResults.classList.remove('show');
    searchInput.value = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/user-id/${userId}`);
        if (!response.ok) throw new Error('Failed to fetch user details');
        
        const user = await response.json();
        
        document.getElementById('modalUserName').textContent = user.dealer_name || user.username;
        
        // User Info Summary
        document.getElementById('userInfoSummary').innerHTML = `
            <div class="user-info-item">
                <i class="fas fa-user"></i>
                <div>
                    <div class="user-info-label">Username</div>
                    <div class="user-info-value">${user.username}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-envelope"></i>
                <div>
                    <div class="user-info-label">Email</div>
                    <div class="user-info-value">${user.email || 'N/A'}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-id-card"></i>
                <div>
                    <div class="user-info-label">Dealer ID</div>
                    <div class="user-info-value">${user.dealer_id}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-layer-group"></i>
                <div>
                    <div class="user-info-label">Cluster</div>
                    <div class="user-info-value">${user.cluster}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-user-tie"></i>
                <div>
                    <div class="user-info-label">ASM</div>
                    <div class="user-info-value">${user.asm}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-user-tie"></i>
                <div>
                    <div class="user-info-label">RSM</div>
                    <div class="user-info-value">${user.rsm}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-star"></i>
                <div>
                    <div class="user-info-label">Champion</div>
                    <div class="user-info-value">${user.champion_name}</div>
                </div>
            </div>
            <div class="user-info-item">
                <i class="fas fa-phone"></i>
                <div>
                    <div class="user-info-label">Mobile</div>
                    <div class="user-info-value">${user.champion_mobile}</div>
                </div>
            </div>
        `;
        
        // Stats Cards
        document.getElementById('userStatsSummary').innerHTML = `
            <div class="modal-summary-card">
                <div class="modal-summary-value">${user.total_courses_assigned}</div>
                <div class="modal-summary-label">Assigned</div>
            </div>
            <div class="modal-summary-card">
                <div class="modal-summary-value">${user.courses_completed}</div>
                <div class="modal-summary-label">Completed</div>
            </div>
            <div class="modal-summary-card">
                <div class="modal-summary-value">${user.courses_in_progress}</div>
                <div class="modal-summary-label">In Progress</div>
            </div>
            <div class="modal-summary-card">
                <div class="modal-summary-value">${user.overall_progress}%</div>
                <div class="modal-summary-label">Avg Progress</div>
            </div>
        `;
        
        // Courses Table
        let coursesHtml = '';
        if (user.courses && user.courses.length > 0) {
            user.courses.forEach(course => {
                const statusClass = course.status === 'completed' ? 'badge-completed' :
                                   course.status === 'in_progress' ? 'badge-progress' : 'badge-notstarted';
                const statusText = course.status === 'completed' ? 'Completed' :
                                  course.status === 'in_progress' ? 'In Progress' : 'Not Started';
                
                coursesHtml += `
                    <tr>
                        <td><strong>${course.course_name}</strong></td>
                        <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                        <td>${course.grade}%</td>
                        <td>${course.letter_grade}</td>
                        <td>${course.enrollment_date ? new Date(course.enrollment_date).toLocaleDateString() : 'N/A'}</td>
                        <td>${course.certificate_issued ? '✅ Yes' : '❌ No'}</td>
                    </tr>
                `;
            });
        } else {
            coursesHtml = '<tr><td colspan="6" style="text-align:center;">No courses enrolled</td></tr>';
        }
        document.getElementById('userCoursesTable').innerHTML = coursesHtml;
        
        document.getElementById('userModal').style.display = 'flex';
        
    } catch (error) {
        console.error('Error loading user details:', error);
        showError('Failed to load user details');
    } finally {
        showLoading(false);
    }
}





        // Initial load
document.addEventListener('DOMContentLoaded', function() {
    currentView = 'courses';
    document.getElementById('viewSelect').value = 'courses';
    document.getElementById('courseSelectContainer').style.display = 'inline-block';
    document.getElementById('asmSelectContainer').style.display = 'none';
    
    // Set Active Courses card as active initially
    document.querySelectorAll('.summary-card').forEach(card => {
        card.classList.remove('active');
    });
    document.querySelectorAll('.summary-card')[0].classList.add('active');
    
    loadAllData();
});
