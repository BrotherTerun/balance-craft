console.log(window.ChartAnnotation);
console.log(window["chartjs-plugin-annotation"]);

let backend = null;
let currentProject = null;
let projectsCache = [];
let bindingDropdownHandlersBound = false;

// Служебный идентификатор для режима общей картины:
// backend строит среднюю траекторию метрик по всем игрокам.
const ALL_PLAYERS_ID = "__ALL_PLAYERS__";
const ALL_PLAYERS_LABEL = "Все игроки — среднее значение";
let bindingDraft = {
    candidates: null,
    templates: [],
    selectedTemplateId: null,
    currentStep: 1,
    maxStep: 6,
    formulas: {},
    variableBindings: {},
    metricLabels: {}
};

function addLog(message) {

    const log = document.getElementById("devLogContent");

    const timestamp = new Date().toLocaleTimeString();

    log.innerHTML += `\n[${timestamp}] ${message}`;

    log.scrollTop = log.scrollHeight;
}

function formatProjectDate(value) {

    if (!value) {
        return "Дата неизвестна";
    }

    try {
        return new Date(value).toLocaleString();
    }
    catch {
        return value;
    }
}

function openDashboard(project) {

    currentProject = project;

    closeAllModals();

    const projectScreen =
        document.getElementById("project-screen");

    const dashboardScreen =
        document.getElementById("dashboard-screen");

    if (projectScreen) {
        projectScreen.classList.remove("active");
    }

    if (dashboardScreen) {
        dashboardScreen.classList.add("active");
    }

    addLog(
        `[PROJECT] Открыт проект: ${project.name}`
    );

    loadPlayers();

    maybeOpenSourceModal();

    setTimeout(() => {
        if (chart) {
            chart.resize();
        }
    }, 150);
}




function renderProjectCard(project) {

    const card =
        document.createElement("div");

    card.className = "project-card";
    card.dataset.projectId = project.id;

    const source =
        project.data_source_path
            ? project.data_source_path
            : "Источник данных не выбран";

    card.innerHTML = `
        <div class="project-card-title">
            ${project.name}
        </div>

        <div class="project-card-db">
            DB: ${project.database || "monitor_rpg_model"}
        </div>

        <div class="project-card-meta">
            Последнее открытие: ${formatProjectDate(project.last_opened)}
        </div>

        <div class="project-card-source">
            ${source}
        </div>
    `;

    card.addEventListener("click", async () => {

        const response =
            await backend.openProject(project.id);

        const openedProject =
            JSON.parse(response);

        if (!openedProject.id) {
            alert("Не удалось открыть проект");
            return;
        }

        openDashboard(openedProject);
    });

    return card;
}


async function loadProjects() {

    if (!backend) return;

    const response =
        await backend.getProjects();

    projectsCache =
        JSON.parse(response);

    renderRecentProjects();
}


function renderRecentProjects() {

    const container =
        document.getElementById("recentProjectsList");

    container.innerHTML = "";

    if (!projectsCache.length) {

        container.innerHTML = `
            <div class="empty-projects">
                Проекты пока не созданы
            </div>
        `;

        return;
    }

    projectsCache
        .slice(0, 5)
        .forEach(project => {

            container.appendChild(
                renderProjectCard(project)
            );
        });
}


function renderOpenProjectsModal() {

    const container =
        document.getElementById("openProjectsList");

    container.innerHTML = "";

    if (!projectsCache.length) {

        container.innerHTML = `
            <div class="empty-projects">
                Проекты пока не созданы
            </div>
        `;

        return;
    }

    projectsCache.forEach(project => {

        container.appendChild(
            renderProjectCard(project)
        );
    });
}


function updateInstabilityAnalysis(data) {

    const bifPoints = data.bifurcation_points || [];

    chart.options.plugins.annotation.annotations =
        buildAnnotations(bifPoints);

    chart.update();
}

function getInsightLevelLabel(level) {

    const labels = {
        success: "OK",
        info: "INFO",
        warning: "WARN",
        danger: "RISK"
    };

    return labels[level] || "INFO";
}

function getAnalysisScopeText(data) {

    const scope = data.scope || data.analysis_scope || "single_player";
    const templateId = data.template_id || "шаблон не выбран";
    const sessionsCount = data.stability_details?.sessions_count;

    const scopeText = scope === "all_players_average"
        ? "Средняя траектория по всем игрокам"
        : "Индивидуальная траектория выбранного игрока";

    const sessionsText = Number.isFinite(Number(sessionsCount))
        ? ` · точек анализа: ${sessionsCount}`
        : "";

    return `${scopeText} · шаблон: ${templateId}${sessionsText}`;
}

function buildStabilityInsight(data) {

    if (!data) {
        return null;
    }

    const lyapunov = data.lyapunov;
    const hasLyapunov = !(
        lyapunov === null ||
        lyapunov === undefined ||
        Number.isNaN(Number(lyapunov))
    );

    const status = String(data.stability_status || "").toLowerCase();
    let level = "info";

    if (status.includes("stable") || status.includes("convergent")) {
        level = "success";
    }

    if (status.includes("moderate") || status.includes("neutral")) {
        level = "warning";
    }

    if (status.includes("high") || status.includes("unstable")) {
        level = "danger";
    }

    if (!hasLyapunov || status.includes("insufficient")) {
        level = "info";
    }

    const lyapunovText = hasLyapunov
        ? `Оценка показателя Ляпунова: ${Number(lyapunov).toFixed(4)}.`
        : "Оценка показателя Ляпунова недоступна для текущего набора данных.";

    return {
        level: level,
        category: "general",
        title: data.stability_text || "Оценка устойчивости динамики",
        text: lyapunovText,
        recommendation: hasLyapunov
            ? "Используйте этот показатель как общий индикатор чувствительности системы к малым изменениям траектории метрик."
            : "Добавьте больше сессий или проверьте наличие рассчитанных метрик выбранного шаблона.",
        evidence: getAnalysisScopeText(data)
    };
}

function mergeStabilityInsight(data, insights) {

    const prepared = Array.isArray(insights)
        ? [...insights]
        : [];

    const alreadyHasStability = prepared.some(insight => {
        const title = String(insight.title || "").toLowerCase();
        const metricKeys = Array.isArray(insight.metric_keys)
            ? insight.metric_keys.join(" ").toLowerCase()
            : "";

        return (
            title.includes("устойчив") ||
            title.includes("стабил") ||
            title.includes("ляпун") ||
            metricKeys.includes("lyapunov")
        );
    });

    if (!alreadyHasStability) {
        const stabilityInsight = buildStabilityInsight(data);

        if (stabilityInsight) {
            prepared.unshift(stabilityInsight);
        }
    }

    return prepared;
}

function renderPracticalInsights(data) {

    const container =
        document.getElementById("practicalInsightsList");

    if (!container) {
        return;
    }

    const backendInsights = Array.isArray(data?.practical_insights)
        ? data.practical_insights
        : [];

    const insights = mergeStabilityInsight(
        data || {},
        backendInsights
    );

    if (!insights.length) {

        container.innerHTML = `
            <div class="insight-empty">
                Backend не вернул практических выводов для текущего анализа.
                Проверьте, что выбран шаблон, рассчитаны session_metrics и построены графики.
            </div>
        `;

        return;
    }

    container.innerHTML = insights
        .slice(0, 7)
        .map(insight => {

            const level = String(insight.level || "info").toLowerCase();
            const safeLevel = ["success", "info", "warning", "danger"].includes(level)
                ? level
                : "info";

            const title = escapeHtml(insight.title || "Вывод анализа");
            const text = escapeHtml(insight.text || "");
            const recommendation = escapeHtml(insight.recommendation || "");
            const evidence = escapeHtml(insight.evidence || "");
            const badge = getInsightLevelLabel(safeLevel);

            return `
                <div class="insight-card ${safeLevel}">
                    <div class="insight-topline">
                        <div class="insight-title">${title}</div>
                        <div class="insight-badge">${badge}</div>
                    </div>

                    ${text ? `<p>${text}</p>` : ""}
                    ${recommendation ? `<p class="insight-recommendation"><strong>Рекомендация:</strong> ${recommendation}</p>` : ""}
                    ${evidence ? `<p class="insight-evidence">${evidence}</p>` : ""}
                </div>
            `;
        })
        .join("");
}

new QWebChannel(qt.webChannelTransport, async function(channel) {

    backend = channel.objects.backend;

    backend.logSignal.connect((message) => {
        addLog(message);
    });

    console.log("WebChannel подключен");

    await loadProjects();
    await loadPlayers();
});

const ctx = document.getElementById('chartCanvas').getContext('2d');

const annotationPlugin =
    window.ChartAnnotation ||
    window['chartjs-plugin-annotation'];

console.log(annotationPlugin);

if (annotationPlugin) {

    Chart.register(annotationPlugin);

    console.log("Annotation plugin loaded");

} else {

    console.error("Annotation plugin NOT loaded");
}

function buildAnnotations(points) {

    const annotations = {};

    points.forEach((point, index) => {

        annotations[`bif_${index}`] = {

            type: 'line',

            xMin: chart.data.labels[point],
            xMax: chart.data.labels[point],

            borderColor: 'red',
            borderWidth: 2,

            label: {
                display: true,
                content: 'INSTABILITY',
                position: 'start'
            }
        };
    });

    console.log("BIF POINTS:", points);

    return annotations;
}

let chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: []
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,

        plugins: {
            annotation: {
                annotations: {}
            }
        },

        scales: {

            x: {
                grid: { color: "#333" }
            },

            y: {
                type: 'linear',
                position: 'left',
                beginAtZero: false,
                grace: '8%'
            }
        }
    }
}); 

async function analyzePlayer() {
    if (!backend) {
        alert("Backend не готов");
        return;
    }

    const playerId = document.getElementById("playerSelect").value;
    if (!playerId) {
        alert("Выберите игрока");
        return;
    }

    let response;

    if (currentProject && backend.analyzeProjectPlayer) {

        response = await backend.analyzeProjectPlayer(
            currentProject.id,
            playerId
        );

    } else {

        // Fallback для старой версии backend.
        response = await backend.analyzePlayer(playerId);
    }

    const data = JSON.parse(response);

    console.log(data);

    if (data.scope === "all_players_average") {
        addLog("[ANALYSIS] Построена средняя траектория по всем игрокам");
    }

    if (data.success === false) {
        alert(data.message || "Не удалось построить графики");
        addLog(`[ANALYSIS] ${data.details || data.message || "Ошибка анализа"}`);
        return;
    }

    updateChart(data);
    updateInstabilityAnalysis(data);
    renderPracticalInsights(data);
}

function normalizeChartDataset(dataset, index) {

    return {
        label: dataset.label || dataset.metric_key || `Метрика ${index + 1}`,
        data: Array.isArray(dataset.data) ? dataset.data : [],
        yAxisID: "y",
        borderWidth: dataset.borderWidth || 2,
        tension: 0.25,
        pointRadius: 3
    };
}

function updateChart(data) {

    chart.data.labels = data.labels || [];

    if (Array.isArray(data.datasets) && data.datasets.length) {

        chart.data.datasets = data.datasets.map(
            (dataset, index) => normalizeChartDataset(dataset, index)
        );

    } else {

        // Legacy fallback: старый формат K/Y/EV/PGR/DR.
        chart.data.datasets = [
            { label: "K(t)", data: data.K || [], yAxisID: "y", borderWidth: 2 },
            { label: "Y(t)", data: data.Y || [], yAxisID: "y", borderWidth: 2 },
            { label: "EV", data: data.EV || [], yAxisID: "y", borderWidth: 2 },
            { label: "PGR", data: data.PGR || [], yAxisID: "y", borderWidth: 2 },
            { label: "DR", data: data.DR || [], yAxisID: "y", borderWidth: 2 }
        ];
    }

    chart.update();
}

function updateChartLabels() {

    if (!chart.data.datasets.length) return;

    // Старый редактор названий метрик оставлен как fallback.
    // Основные подписи теперь приходят из backend через data.datasets.
    if (chart.data.datasets.length >= 5) {
        chart.data.datasets[0].label = chart.data.datasets[0].label || "K(t)";
        chart.data.datasets[1].label = chart.data.datasets[1].label || "Y(t)";
        chart.data.datasets[2].label = metricLabels.ev;
        chart.data.datasets[3].label = metricLabels.pgr;
        chart.data.datasets[4].label = metricLabels.dr;
    }

    chart.update();
}

document.getElementById("runBtn").addEventListener("click", analyzePlayer);



const metricsBtn = document.getElementById("metricsBtn");

let metricLabels = {
    ev: "Скорость получения опыта",
    pgr: "Темп роста уровня",
    dr: "Деградация прогрессии"
};

const saveMetricsBtn =
    document.getElementById("saveMetricsBtn");

saveMetricsBtn.addEventListener("click", () => {

    try {
        metricLabels.ev =
            document.getElementById("evInput").value;

        metricLabels.pgr =
            document.getElementById("pgrInput").value;

        metricLabels.dr =
            document.getElementById("drInput").value;

        updateChartLabels();
    }
    catch (TypeError) {
        addLog("Произошла ошибка: Невозможно задать свойства для undefined (объект 'label')")
    }
    finally {
        document
            .getElementById("metrics-screen")
            .classList.remove("active");

        document
            .getElementById("dashboard-screen")
            .classList.add("active");
    }
});

function formatPlayerId(playerId) {

    if (!playerId) {
        return "Неизвестный игрок";
    }

    if (playerId.length <= 18) {
        return playerId;
    }

    return `${playerId.slice(0, 8)}…${playerId.slice(-6)}`;
}


function closePlayerDropdown() {

    const menu =
        document.getElementById("playerDropdownMenu");

    if (menu) {
        menu.classList.add("is-hidden");
    }
}


function setSelectedPlayer(playerId, label) {

    const hiddenInput =
        document.getElementById("playerSelect");

    const button =
        document.getElementById("playerDropdownBtn");

    hiddenInput.value = playerId;
    button.textContent = label || formatPlayerId(playerId);

    document
        .querySelectorAll(".custom-select-option")
        .forEach(option => {

            option.classList.toggle(
                "active",
                option.dataset.playerId === playerId
            );
        });
}


function createPlayerOption(playerId, label, title = null) {

    const option =
        document.createElement("div");

    option.className = "custom-select-option";
    option.dataset.playerId = playerId;
    option.title = title || playerId;
    option.textContent = label;

    option.addEventListener("click", () => {

        setSelectedPlayer(playerId, label);

        closePlayerDropdown();
    });

    return option;
}


async function loadPlayers() {

    if (!backend) return;

    const response =
        await backend.getPlayers();

    const players =
        JSON.parse(response);

    const menu =
        document.getElementById("playerDropdownMenu");

    const button =
        document.getElementById("playerDropdownBtn");

    const hiddenInput =
        document.getElementById("playerSelect");

    menu.innerHTML = "";
    hiddenInput.value = "";

    if (!players.length) {

        button.textContent = "Игроки не найдены";

        return;
    }

    // Первый пункт — агрегированная картина по проекту.
    // Backend интерпретирует ALL_PLAYERS_ID как команду посчитать
    // среднее значение каждой метрики по порядковому номеру сессии игрока.
    const allPlayersOption =
        createPlayerOption(
            ALL_PLAYERS_ID,
            ALL_PLAYERS_LABEL,
            "Среднее значение метрик по всем игрокам на их 1-й, 2-й, 3-й и последующих сессиях"
        );

    menu.appendChild(allPlayersOption);
    setSelectedPlayer(ALL_PLAYERS_ID, ALL_PLAYERS_LABEL);

    players.forEach(p => {

        const playerId =
            p.player_id;

        const label =
            p.name || formatPlayerId(playerId);

        menu.appendChild(
            createPlayerOption(
                playerId,
                label,
                playerId
            )
        );
    });
}

window.addEventListener("load", () => {

    const dropdownBtn =
        document.getElementById("playerDropdownBtn");

    const dropdownMenu =
        document.getElementById("playerDropdownMenu");

    dropdownBtn.addEventListener("click", (event) => {

        event.stopPropagation();

        dropdownMenu.classList.toggle("is-hidden");
    });

    document.addEventListener("click", () => {

        closePlayerDropdown();
    });

    document.addEventListener("keydown", (event) => {

        if (event.key === "Escape") {
            closePlayerDropdown();
        }
    });
});
window.addEventListener("keydown", (event) => {

    if (event.ctrlKey && event.key === "d") {

        event.preventDefault();
        
        const devConsole = document.getElementById("devConsole");

        devConsole.classList.toggle("visible");

        console.log("TAB PRESSED");
    }
});

const originalConsoleLog = console.log;

console.log = function(message) {

    addLog("[JS] " + message);

    originalConsoleLog(message);
};


const newProjectBtn =
    document.getElementById("newProjectBtn");

const openProjectBtn =
    document.getElementById("openProjectBtn");

newProjectBtn.addEventListener("click", async () => {

    if (!backend) {
        alert("Backend не готов");
        return;
    }

    const projectName =
        prompt("Введите название проекта:", "Новый проект анализа");

    if (!projectName) {
        return;
    }

    const response =
        await backend.createProject(projectName);

    const project =
        JSON.parse(response);

    await loadProjects();

    openDashboard(project);
});


openProjectBtn.addEventListener("click", async () => {

    await loadProjects();

    renderOpenProjectsModal();

    document
        .getElementById("openProjectModal")
        .classList.remove("is-hidden");
});

/* ---------- ANALYSIS MENU ---------- */

const analysisBtn =
    document.getElementById("analysisBtn");

const analysisMenu =
    document.getElementById("analysisMenu");

analysisBtn.addEventListener("click", () => {

    analysisMenu.classList.toggle("is-hidden");
});

/* ---------- MODALS ---------- */

function openModal(id) {

    if (analysisMenu) {
        analysisMenu.classList.add("is-hidden");
    }

    const modal =
        document.getElementById(id);

    if (!modal) {
        console.error(`Модальное окно ${id} не найдено в index.html`);
        alert(`Ошибка UI: не найдено окно ${id}`);
        return;
    }

    modal.classList.remove("is-hidden");

    setModalOpenState(true);
}

function setModalOpenState(isOpen) {

    if (!document.body) {
        return;
    }

    document.body.classList.toggle(
        "modal-open",
        Boolean(isOpen)
    );
}


function closeAllModals() {

    if (typeof closeBindingCustomSelects === "function") {
        closeBindingCustomSelects();
    }

    if (typeof hideBindingTemplateTooltip === "function") {
        hideBindingTemplateTooltip();
    }

    document
        .querySelectorAll(".modal-overlay")
        .forEach(m => {

            m.classList.add("is-hidden");
        });

    setModalOpenState(false);
}

function getCurrentProjectId() {

    if (!currentProject || !currentProject.id) {
        return "";
    }

    return currentProject.id;
}


function openSourceModal() {

    closeAllModals();

    if (analysisMenu) {
        analysisMenu.classList.add("is-hidden");
    }

    const sourceModal =
        document.getElementById("sourceModal");

    const sourceFolderPath =
        document.getElementById("sourceFolderPath");

    const resultBox =
        document.getElementById("sourceImportResult");

    if (!sourceModal) {
        console.error("sourceModal не найден в index.html");
        alert("Ошибка UI: не найдено окно источника событий");
        return;
    }

    if (!sourceFolderPath) {
        console.error("sourceFolderPath не найден в index.html");
        alert("Ошибка UI: не найдено поле пути источника событий");
        return;
    }

    if (!resultBox) {
        console.error("sourceImportResult не найден в index.html");
        alert("Ошибка UI: не найден блок результата импорта");
        return;
    }

    sourceFolderPath.value =
        currentProject?.data_source_path || "";

    resultBox.classList.add("is-hidden");
    resultBox.classList.remove(
        "success",
        "error",
        "loading"
    );

    resultBox.innerHTML = "";

    sourceModal.classList.remove("is-hidden");

    setModalOpenState(true);
}


function showSourceImportResult(type, html) {

    const resultBox =
        document.getElementById("sourceImportResult");

    resultBox.classList.remove(
        "is-hidden",
        "success",
        "error",
        "loading"
    );

    resultBox.classList.add(type);

    resultBox.innerHTML = html;
}


function setSourceImportBusy(isBusy) {

    const importBtn =
        document.getElementById("sourceImportBtn");

    importBtn.disabled = isBusy;

    importBtn.innerText = isBusy
        ? "Импорт выполняется..."
        : "Импортировать события";
}


function maybeOpenSourceModal() {

    if (!currentProject) {
        return;
    }

    const needSource =
        !currentProject.data_source_path ||
        currentProject.import_status === "not_imported";

    if (needSource) {

        setTimeout(() => {
            openSourceModal();
        }, 250);
    }
}



/* ---------- BINDING WIZARD ---------- */

function escapeHtml(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


function showBindingStatus(type, message) {

    const status =
        document.getElementById("bindingStatus");

    if (!status) {
        return;
    }

    status.classList.remove(
        "loading",
        "success",
        "error"
    );

    status.classList.add(type);
    status.innerHTML = message;
}


function formatBindingSamples(samples) {

    if (!samples || !samples.length) {
        return "примеров нет";
    }

    return samples
        .slice(0, 4)
        .map(escapeHtml)
        .join(", ");
}


function getSelectedTemplate() {

    return bindingDraft.templates.find(
        template => template.id === bindingDraft.selectedTemplateId
    );
}


function shouldShowBindingTableField(item) {

    if (!item) {
        return false;
    }

    const dataType = String(item.data_type || "").toLowerCase();
    const fieldName = String(item.field || item.path || "").toLowerCase();

    if (
        dataType === "datetime" ||
        dataType === "timestamp" ||
        dataType === "date" ||
        dataType === "time" ||
        dataType === "json" ||
        dataType === "jsonl" ||
        dataType.includes("json")
    ) {
        return false;
    }

    if (fieldName.includes("id")) {
        return false;
    }

    return true;
}


function getVisibleBindingTableFields(dataOverride = null) {

    const data = dataOverride || bindingDraft.candidates || {};

    return (data.table_fields || [])
        .filter(shouldShowBindingTableField);
}


function getBindingSourceOptions() {

    const data = bindingDraft.candidates || {};
    const options = [
        {
            value: "computed.duration_minutes",
            label: "computed.duration_minutes · длительность окна, мин",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.action_count",
            label: "computed.action_count · количество событий",
            isNumeric: true,
            sourceKind: "computed"
        }
    ];

    (data.attribute_fields || []).forEach(item => {

        options.push({
            value: item.path,
            label: `${item.path} · ${item.data_type}`,
            isNumeric: item.is_numeric,
            sourceKind: "attribute"
        });
    });

    getVisibleBindingTableFields(data).forEach(item => {

        options.push({
            value: item.path,
            label: `${item.path} · ${item.label || item.data_type}`,
            isNumeric: item.is_numeric,
            sourceKind: "table"
        });
    });

    return options;
}


function getDefaultBindingForVariable(variableKey) {

    const key = String(variableKey || "").toLowerCase();

    if (key.includes("duration")) {
        return "computed.duration_minutes";
    }

    if (
        key.includes("action") ||
        key.includes("engagement") ||
        key.includes("count")
    ) {
        return "computed.action_count";
    }

    return "events.event_data.value";
}


function ensureBindingTemplateTooltip() {

    let tooltip = document.getElementById("bindingTemplateHoverTooltip");

    if (tooltip) {
        return tooltip;
    }

    tooltip = document.createElement("div");
    tooltip.id = "bindingTemplateHoverTooltip";
    tooltip.className = "binding-template-hover-tooltip";

    tooltip.innerHTML = `
        <strong></strong>
        <p></p>
    `;

    document.body.appendChild(tooltip);

    return tooltip;
}


function positionBindingTemplateTooltip(event) {

    const tooltip = document.getElementById("bindingTemplateHoverTooltip");

    if (!tooltip || !tooltip.classList.contains("visible")) {
        return;
    }

    const margin = 18;
    const offset = 16;

    let left = event.clientX + offset;
    let top = event.clientY + offset;

    const rect = tooltip.getBoundingClientRect();
    const maxLeft = window.innerWidth - rect.width - margin;
    const maxTop = window.innerHeight - rect.height - margin;

    if (left > maxLeft) {
        left = event.clientX - rect.width - offset;
    }

    if (top > maxTop) {
        top = event.clientY - rect.height - offset;
    }

    tooltip.style.left = `${Math.max(margin, left)}px`;
    tooltip.style.top = `${Math.max(margin, top)}px`;
}


function showBindingTemplateTooltip(event, card) {

    const tooltip = ensureBindingTemplateTooltip();

    const title = card.dataset.tooltipTitle || "Шаблон анализа";
    const body = card.dataset.tooltipBody || "Описание шаблона недоступно.";

    tooltip.querySelector("strong").textContent = title;
    tooltip.querySelector("p").textContent = body;

    tooltip.classList.add("visible");

    positionBindingTemplateTooltip(event);
}


function hideBindingTemplateTooltip() {

    const tooltip = document.getElementById("bindingTemplateHoverTooltip");

    if (!tooltip) {
        return;
    }

    tooltip.classList.remove("visible");
}


function closeBindingCustomSelects(exceptSelect = null) {

    document
        .querySelectorAll(".binding-custom-select")
        .forEach(select => {

            if (exceptSelect && select === exceptSelect) {
                return;
            }

            select.classList.remove("open");

            const menu = select.querySelector(".binding-custom-select-menu");

            if (menu) {
                menu.classList.add("is-hidden");
            }
        });
}


function setupBindingDropdownGlobalHandlers() {

    if (bindingDropdownHandlersBound) {
        return;
    }

    bindingDropdownHandlersBound = true;

    document.addEventListener("click", event => {

        if (!event.target.closest(".binding-custom-select")) {
            closeBindingCustomSelects();
        }
    });

    document.addEventListener("keydown", event => {

        if (event.key === "Escape") {
            closeBindingCustomSelects();
        }
    });
}


function renderBindingCandidates(data) {

    const root =
        document.getElementById("bindingCandidates");

    if (!root) {
        return;
    }

    const summary = data.summary || {};
    const eventTypes = data.event_types || [];
    const attributeFields = data.attribute_fields || [];
    const tableFields = getVisibleBindingTableFields(data);

    const eventTypeHtml = eventTypes.length
        ? eventTypes.map(item => `
            <div class="binding-pill">
                <strong>${escapeHtml(item.value)}</strong>
                <span>${item.count} событий</span>
            </div>
        `).join("")
        : `<div class="binding-empty">Типы событий не найдены</div>`;

    const attributeHtml = attributeFields.length
        ? attributeFields.map(item => `
            <div class="binding-field-row">
                <div>
                    <strong>${escapeHtml(item.path)}</strong>
                    <span>
                        тип: ${escapeHtml(item.data_type)};
                        найдено: ${item.count};
                        примеры: ${formatBindingSamples(item.samples)}
                    </span>
                </div>
                <em>${item.is_numeric ? "числовое" : "категория"}</em>
            </div>
        `).join("")
        : `<div class="binding-empty">Атрибуты событий не найдены</div>`;

    const tableHtml = tableFields.length
        ? tableFields.map(item => `
            <div class="binding-field-row compact">
                <div>
                    <strong>${escapeHtml(item.path)}</strong>
                    <span>${escapeHtml(item.label)} · ${escapeHtml(item.data_type)}</span>
                </div>
                <em>${item.is_numeric ? "числовое" : "поле"}</em>
            </div>
        `).join("")
        : `<div class="binding-empty">Поля таблиц не найдены</div>`;

    root.innerHTML = `
        <div class="binding-summary-line">
            <span>Событий: <strong>${summary.events_count || 0}</strong></span>
            <span>Сессий: <strong>${summary.sessions_count || 0}</strong></span>
            <span>Игроков: <strong>${summary.players_count || 0}</strong></span>
        </div>

        <h4>Типы событий</h4>
        <div class="binding-pill-list">
            ${eventTypeHtml}
        </div>

        <h4>Атрибуты event_data</h4>
        <div class="binding-field-list">
            ${attributeHtml}
        </div>

        <h4>Поля таблиц</h4>
        <div class="binding-field-list table-fields">
            ${tableHtml}
        </div>
    `;
}


function renderTemplateSummary(template) {

    const root =
        document.getElementById("bindingTemplateSummary");

    if (!root || !template) {
        return;
    }

    const variablesHtml = (template.variables || [])
        .map(variable => `
            <div class="binding-variable-row">
                <strong>${escapeHtml(variable.key)}</strong>
                <span>${escapeHtml(variable.name)}</span>
                <em>${variable.required ? "обязательная" : "дополнительная"}</em>
            </div>
        `)
        .join("");

    const metricsHtml = (template.metrics || [])
        .map(metric => `
            <div class="binding-metric-row">
                <strong>${escapeHtml(metric.key)}</strong>
                <span>${escapeHtml(metric.name)}</span>
                <code>${escapeHtml(metric.formula)}</code>
            </div>
        `)
        .join("");

    root.innerHTML = `
        <h4>${escapeHtml(template.name)}</h4>
        <p>${escapeHtml(template.description)}</p>

        <h5>Переменные шаблона</h5>
        <div class="binding-variable-list">
            ${variablesHtml || "<div class='binding-empty'>Переменные не заданы</div>"}
        </div>

        <h5>Метрики и формулы</h5>
        <div class="binding-metric-list">
            ${metricsHtml || "<div class='binding-empty'>Метрики не заданы</div>"}
        </div>
    `;

    root.classList.remove("is-hidden");
}


function renderBindingTemplates(templates, selectedTemplateId) {

    const root =
        document.getElementById("bindingTemplates");

    if (!root) {
        return;
    }

    bindingDraft.templates = templates || [];
    bindingDraft.selectedTemplateId = selectedTemplateId ||
        currentProject?.selected_template ||
        bindingDraft.templates[0]?.id ||
        "progression_decay";

    root.innerHTML = bindingDraft.templates
        .map(template => {

            const isActive =
                template.id === bindingDraft.selectedTemplateId;

            return `
                <div class="binding-template-card ${isActive ? "active" : ""}"
                    data-template-id="${escapeHtml(template.id)}"
                    data-tooltip-title="${escapeHtml(template.name)}"
                    data-tooltip-body="${escapeHtml(template.description)}">

                    <h4>${escapeHtml(template.name)}</h4>
                    <p>${escapeHtml(template.description)}</p>
                    <span>${(template.metrics || []).length} метрик · ${(template.variables || []).length} переменных</span>

                </div>
            `;
        })
        .join("");

    root
        .querySelectorAll(".binding-template-card")
        .forEach(card => {

            card.addEventListener("mouseenter", event => {
                showBindingTemplateTooltip(event, card);
            });

            card.addEventListener("mousemove", event => {
                positionBindingTemplateTooltip(event);
            });

            card.addEventListener("mouseleave", () => {
                hideBindingTemplateTooltip();
            });

            card.addEventListener("click", () => {

                bindingDraft.selectedTemplateId =
                    card.dataset.templateId;

                root
                    .querySelectorAll(".binding-template-card")
                    .forEach(item => item.classList.remove("active"));

                card.classList.add("active");

                hideBindingTemplateTooltip();

                renderTemplateSummary(
                    getSelectedTemplate()
                );

                renderBindingStepContent();
            });
        });

    renderTemplateSummary(
        getSelectedTemplate()
    );
}


function ensureDraftForSelectedTemplate() {

    const template = getSelectedTemplate();

    if (!template) {
        return;
    }

    (template.metrics || []).forEach(metric => {

        if (!bindingDraft.formulas[metric.key]) {
            bindingDraft.formulas[metric.key] = metric.formula || "";
        }

        if (!bindingDraft.metricLabels[metric.key]) {
            bindingDraft.metricLabels[metric.key] = metric.name || metric.key;
        }
    });

    (template.variables || []).forEach(variable => {

        if (!bindingDraft.variableBindings[variable.key]) {
            bindingDraft.variableBindings[variable.key] = getDefaultBindingForVariable(
                variable.key
            );
        }
    });
}


function renderBindingFormulaDraft() {

    const root =
        document.getElementById("bindingFormulaDraft");

    const template = getSelectedTemplate();

    if (!root) {
        return;
    }

    if (!template) {
        root.innerHTML = `<div class="binding-empty">Сначала выберите шаблон анализа.</div>`;
        return;
    }

    ensureDraftForSelectedTemplate();

    const metricsHtml = (template.metrics || [])
        .map(metric => `
            <div class="binding-config-row">
                <label>
                    <strong>${escapeHtml(metric.key)}</strong>
                    <span>${escapeHtml(metric.name)}</span>
                </label>
                <input
                    type="text"
                    class="binding-formula-input"
                    data-metric-key="${escapeHtml(metric.key)}"
                    value="${escapeHtml(bindingDraft.formulas[metric.key] || metric.formula || "")}">
            </div>
        `)
        .join("");

    root.innerHTML = `
        <div class="binding-info-note">
            Сейчас значения остаются черновиком UI. На следующих подпунктах добавим сохранение
            formula_config и перерасчёт метрик по пользовательским формулам.
        </div>
        <div class="binding-config-list">
            ${metricsHtml || "<div class='binding-empty'>У выбранного шаблона нет метрик.</div>"}
        </div>
    `;

    root
        .querySelectorAll(".binding-formula-input")
        .forEach(input => {

            input.addEventListener("input", () => {
                bindingDraft.formulas[input.dataset.metricKey] = input.value;
            });
        });
}


function renderBindingVariableMappingDraft() {

    const root =
        document.getElementById("bindingVariableMappingDraft");

    const template = getSelectedTemplate();

    if (!root) {
        return;
    }

    if (!template) {
        root.innerHTML = `<div class="binding-empty">Сначала выберите шаблон анализа.</div>`;
        return;
    }

    ensureDraftForSelectedTemplate();
    setupBindingDropdownGlobalHandlers();

    const sourceOptions = getBindingSourceOptions();

    function getSelectedSourceLabel(value) {

        if (!value) {
            return "Не выбрано";
        }

        const option = sourceOptions.find(item => item.value === value);

        return option ? option.label : value;
    }

    const sourceOptionsHtml = sourceOptions
        .map(option => `
            <button type="button"
                class="binding-custom-select-option"
                data-value="${escapeHtml(option.value)}"
                title="${escapeHtml(option.label)}">
                <span>${escapeHtml(option.label)}</span>
                <em>${option.isNumeric ? "числовое" : "строковое"}</em>
            </button>
        `)
        .join("");

    const variablesHtml = (template.variables || [])
        .map(variable => {

            const selectedValue =
                bindingDraft.variableBindings[variable.key] || "";

            const selectedLabel =
                getSelectedSourceLabel(selectedValue);

            return `
                <div class="binding-config-row binding-mapping-row">
                    <label>
                        <strong>${escapeHtml(variable.key)}</strong>
                        <span>${escapeHtml(variable.name)} · ${variable.required ? "обязательная" : "дополнительная"}</span>
                    </label>

                    <div class="binding-custom-select"
                        data-variable-key="${escapeHtml(variable.key)}"
                        data-selected-value="${escapeHtml(selectedValue)}">

                        <button type="button"
                            class="binding-custom-select-btn"
                            title="${escapeHtml(selectedLabel)}">
                            <span>${escapeHtml(selectedLabel)}</span>
                        </button>

                        <div class="binding-custom-select-menu is-hidden">
                            <button type="button"
                                class="binding-custom-select-option"
                                data-value="">
                                <span>Не выбрано</span>
                                <em>пустое значение</em>
                            </button>
                            ${sourceOptionsHtml || "<div class='binding-empty'>Источники данных не найдены</div>"}
                        </div>
                    </div>
                </div>
            `;
        })
        .join("");

    root.innerHTML = `
        <div class="binding-info-note">
            На этом шаге переменные выбранного шаблона связываются с найденными
            атрибутами событий и полями таблиц. Выпадающие списки здесь сделаны
            кастомными, чтобы избежать системного бело-синего select-окна в QWebEngine.
        </div>
        <div class="binding-config-list">
            ${variablesHtml || "<div class='binding-empty'>У выбранного шаблона нет переменных.</div>"}
        </div>
    `;

    root
        .querySelectorAll(".binding-custom-select")
        .forEach(select => {

            const button =
                select.querySelector(".binding-custom-select-btn");

            const menu =
                select.querySelector(".binding-custom-select-menu");

            const variableKey =
                select.dataset.variableKey;

            if (!button || !menu || !variableKey) {
                return;
            }

            button.addEventListener("click", event => {

                event.stopPropagation();

                const isOpen = select.classList.contains("open");

                closeBindingCustomSelects(select);

                select.classList.toggle("open", !isOpen);
                menu.classList.toggle("is-hidden", isOpen);
            });

            menu
                .querySelectorAll(".binding-custom-select-option")
                .forEach(optionButton => {

                    const optionValue = optionButton.dataset.value || "";

                    optionButton.classList.toggle(
                        "active",
                        optionValue === (bindingDraft.variableBindings[variableKey] || "")
                    );

                    optionButton.addEventListener("click", event => {

                        event.stopPropagation();

                        const value = optionButton.dataset.value || "";
                        const labelNode = optionButton.querySelector("span");
                        const label = labelNode
                            ? labelNode.textContent
                            : "Не выбрано";

                        bindingDraft.variableBindings[variableKey] = value;
                        select.dataset.selectedValue = value;

                        button.querySelector("span").textContent = label;
                        button.title = label;

                        menu
                            .querySelectorAll(".binding-custom-select-option")
                            .forEach(item => {
                                item.classList.toggle(
                                    "active",
                                    (item.dataset.value || "") === value
                                );
                            });

                        closeBindingCustomSelects();
                    });
                });
        });
}


function renderBindingMetricLabelsDraft() {

    const root =
        document.getElementById("bindingMetricLabelsDraft");

    const template = getSelectedTemplate();

    if (!root) {
        return;
    }

    if (!template) {
        root.innerHTML = `<div class="binding-empty">Сначала выберите шаблон анализа.</div>`;
        return;
    }

    ensureDraftForSelectedTemplate();

    const labelsHtml = (template.metrics || [])
        .map(metric => `
            <div class="binding-config-row">
                <label>
                    <strong>${escapeHtml(metric.key)}</strong>
                    <span>${escapeHtml(metric.formula || "")}</span>
                </label>
                <input
                    type="text"
                    class="binding-label-input"
                    data-metric-key="${escapeHtml(metric.key)}"
                    value="${escapeHtml(bindingDraft.metricLabels[metric.key] || metric.name || metric.key)}">
            </div>
        `)
        .join("");

    root.innerHTML = `
        <div class="binding-config-list">
            ${labelsHtml || "<div class='binding-empty'>У выбранного шаблона нет метрик.</div>"}
        </div>
    `;

    root
        .querySelectorAll(".binding-label-input")
        .forEach(input => {

            input.addEventListener("input", () => {
                bindingDraft.metricLabels[input.dataset.metricKey] = input.value;
            });
        });
}


function renderBindingOverviewDraft() {

    const root =
        document.getElementById("bindingOverviewDraft");

    const template = getSelectedTemplate();

    if (!root) {
        return;
    }

    if (!template) {
        root.innerHTML = `<div class="binding-empty">Сначала выберите шаблон анализа.</div>`;
        return;
    }

    ensureDraftForSelectedTemplate();

    const variableHtml = (template.variables || [])
        .map(variable => `
            <div class="binding-overview-row">
                <strong>${escapeHtml(variable.key)}</strong>
                <span>${escapeHtml(bindingDraft.variableBindings[variable.key] || "не выбрано")}</span>
            </div>
        `)
        .join("");

    const metricHtml = (template.metrics || [])
        .map(metric => `
            <div class="binding-overview-row metric">
                <strong>${escapeHtml(metric.key)}</strong>
                <span>${escapeHtml(bindingDraft.metricLabels[metric.key] || metric.name || metric.key)}</span>
                <code>${escapeHtml(bindingDraft.formulas[metric.key] || metric.formula || "")}</code>
            </div>
        `)
        .join("");

    root.innerHTML = `
        <div class="binding-summary-card">
            <h4>Выбранный шаблон</h4>
            <p><strong>${escapeHtml(template.name)}</strong></p>
            <p>${escapeHtml(template.description)}</p>
        </div>

        <div class="binding-summary-card">
            <h4>Связь переменных и данных</h4>
            ${variableHtml || "<div class='binding-empty'>Переменные не заданы</div>"}
        </div>

        <div class="binding-summary-card">
            <h4>Метрики и формулы</h4>
            ${metricHtml || "<div class='binding-empty'>Метрики не заданы</div>"}
        </div>
    `;
}


function renderBindingStepContent() {

    if (bindingDraft.currentStep === 3) {
        renderBindingFormulaDraft();
    }

    if (bindingDraft.currentStep === 4) {
        renderBindingVariableMappingDraft();
    }

    if (bindingDraft.currentStep === 5) {
        renderBindingMetricLabelsDraft();
    }

    if (bindingDraft.currentStep === 6) {
        renderBindingOverviewDraft();
    }
}


function setBindingStep(step) {

    closeBindingCustomSelects();
    hideBindingTemplateTooltip();

    const maxStep = bindingDraft.maxStep || 6;

    bindingDraft.currentStep = Math.min(
        Math.max(step, 1),
        maxStep
    );

    document
        .querySelectorAll(".binding-step-panel")
        .forEach(panel => {

            const panelStep = Number(panel.dataset.bindingStep);

            panel.classList.toggle(
                "active",
                panelStep === bindingDraft.currentStep
            );
        });

    document
        .querySelectorAll(".binding-progress-step")
        .forEach(item => {

            const itemStep = Number(item.dataset.bindingProgress);

            item.classList.toggle(
                "active",
                itemStep === bindingDraft.currentStep
            );

            item.classList.toggle(
                "complete",
                itemStep < bindingDraft.currentStep
            );
        });

    const badge =
        document.getElementById("bindingStepBadge");

    if (badge) {
        badge.textContent = `Шаг ${bindingDraft.currentStep} из ${maxStep}`;
    }

    const backBtn =
        document.getElementById("bindingBackBtn");

    const nextBtn =
        document.getElementById("bindingNextBtn");

    if (backBtn) {
        backBtn.disabled = bindingDraft.currentStep === 1;
    }

    if (nextBtn) {
        nextBtn.textContent = bindingDraft.currentStep === maxStep
            ? "Сохранить"
            : "Далее";
    }

    renderBindingStepContent();
}


async function loadBindingWizardData() {

    if (!backend) {
        showBindingStatus("error", "Backend недоступен.");
        return;
    }

    if (!currentProject) {
        showBindingStatus("error", "Сначала создайте или откройте проект.");
        return;
    }

    showBindingStatus(
        "loading",
        "Загружаем найденные события, атрибуты, поля таблиц и шаблоны анализа..."
    );

    try {

        const response =
            await backend.getBindingCandidates(
                currentProject.id
            );

        const data = JSON.parse(response);

        if (!data.success) {
            showBindingStatus(
                "error",
                `<strong>${escapeHtml(data.message || "Ошибка загрузки данных")}</strong><br>${escapeHtml(data.details || "")}`
            );
            return;
        }

        bindingDraft.candidates = data;

        renderBindingCandidates(data);
        renderBindingTemplates(
            data.templates || [],
            currentProject.selected_template
        );

        setBindingStep(1);

        showBindingStatus(
            "success",
            "Данные загружены. Проверьте найденные события и переходите к выбору шаблона анализа."
        );

    } catch (error) {

        console.error(error);

        showBindingStatus(
            "error",
            `<strong>Ошибка загрузки Binding Wizard</strong><br>${escapeHtml(error)}`
        );
    }
}


async function openBindingWizard() {

    closeAllModals();
    openModal("bindingModal");

    setBindingStep(1);

    await loadBindingWizardData();
}


function buildSelectedTemplateBindingPayload() {

    const template = getSelectedTemplate();

    if (!template) {
        return {
            selected_template: bindingDraft.selectedTemplateId,
            semantic_bindings: {},
            formula_config: {},
            metric_labels: {}
        };
    }

    const semanticBindings = {};

    (template.variables || []).forEach(variable => {

        const key = variable.key;

        if (!key) {
            return;
        }

        semanticBindings[key] =
            bindingDraft.variableBindings[key] ||
            getDefaultBindingForVariable(key) ||
            "";
    });

    const formulaConfig = {};
    const metricLabels = {};

    (template.metrics || []).forEach(metric => {

        const key = metric.key;

        if (!key) {
            return;
        }

        formulaConfig[key] =
            bindingDraft.formulas[key] ||
            metric.formula ||
            "0";

        metricLabels[key] =
            bindingDraft.metricLabels[key] ||
            metric.name ||
            key;
    });

    return {
        selected_template: bindingDraft.selectedTemplateId,
        semantic_bindings: semanticBindings,
        formula_config: formulaConfig,
        metric_labels: metricLabels
    };
}


async function saveBindingWizardDraft() {

    if (!backend || !currentProject) {
        alert("Сначала создайте или откройте проект");
        return;
    }

    if (!bindingDraft.selectedTemplateId) {
        alert("Выберите шаблон анализа");
        setBindingStep(2);
        return;
    }

    ensureDraftForSelectedTemplate();

    const payload = buildSelectedTemplateBindingPayload();

    showBindingStatus(
        "loading",
        "Сохраняем семантическое связывание и пересчитываем метрики..."
    );

    try {

        let result;

        if (backend.saveProjectBindingConfig) {

            const response = await backend.saveProjectBindingConfig(
                currentProject.id,
                JSON.stringify(payload)
            );

            result = JSON.parse(response);

        } else {

            const ok = await backend.updateProjectTemplate(
                currentProject.id,
                bindingDraft.selectedTemplateId
            );

            result = {
                success: Boolean(ok),
                message: ok
                    ? "Шаблон сохранён без перерасчёта"
                    : "Не удалось сохранить выбранный шаблон"
            };
        }

        if (!result.success) {

            showBindingStatus(
                "error",
                `<strong>${escapeHtml(result.message || "Не удалось сохранить семантическое связывание")}</strong><br>${escapeHtml(result.details || "")}`
            );

            return;
        }

        if (result.project) {
            currentProject = result.project;
        } else {
            currentProject.selected_template = bindingDraft.selectedTemplateId;
            currentProject.semantic_bindings = payload.semantic_bindings;
            currentProject.formula_config = payload.formula_config;
            currentProject.metric_labels = payload.metric_labels;
            currentProject.needs_binding = false;
        }

        const recalc = result.recalculation_result || {};

        addLog(
            `[BINDING] Сохранено: ${bindingDraft.selectedTemplateId}; `
            + `сессий: ${recalc.processed_sessions || 0}; `
            + `метрик: ${recalc.written_metrics || 0}`
        );

        showBindingStatus(
            "success",
            "Семантическое связывание сохранено. Метрики пересчитаны."
        );

        closeAllModals();

    } catch (error) {

        console.error(error);

        showBindingStatus(
            "error",
            `<strong>Ошибка сохранения Binding Wizard</strong><br>${escapeHtml(error)}`
        );
    }
}


/* ---------- OPEN MODALS ---------- */

function bindClick(elementId, handler) {

    const element =
        document.getElementById(elementId);

    if (!element) {
        console.error(`Элемент ${elementId} не найден в index.html`);
        return;
    }

    element.addEventListener("click", handler);
}

bindClick("openWhatIfModal", () => {
    openModal("whatIfModal");
});

bindClick("openSourceModal", () => {
    openSourceModal();
});

bindClick("openBindingModal", () => {
    openBindingWizard();
});

bindClick("bindingCancelBtn", () => {
    closeAllModals();
});

bindClick("bindingBackBtn", () => {
    setBindingStep(bindingDraft.currentStep - 1);
});

bindClick("bindingNextBtn", async () => {

    if (bindingDraft.currentStep === 2 && !bindingDraft.selectedTemplateId) {
        alert("Выберите шаблон анализа");
        return;
    }

    if (bindingDraft.currentStep >= bindingDraft.maxStep) {
        await saveBindingWizardDraft();
        return;
    }

    setBindingStep(bindingDraft.currentStep + 1);
});

bindClick("sourceBrowseBtn", async () => {

        if (!backend) {

            alert("Backend недоступен");
            return;
        }

        const folderPath =
            await backend.selectFolder();

        if (!folderPath) {
            return;
        }

        document
            .getElementById("sourceFolderPath")
            .value = folderPath;

        if (
            currentProject &&
            backend.updateProjectSource
        ) {

            await backend.updateProjectSource(
                currentProject.id,
                folderPath
            );

            currentProject.data_source_path = folderPath;
            currentProject.import_status = "not_imported";
            currentProject.needs_binding = true;
        }

        showSourceImportResult(
            "loading",
            "Источник выбран. Нажмите «Импортировать события», чтобы загрузить данные."
        );
    });


bindClick("sourceImportBtn", async () => {

        if (!backend) {

            alert("Backend недоступен");
            return;
        }

        if (!currentProject) {

            alert("Сначала создайте или откройте проект");
            return;
        }

        const folderPath =
            document
                .getElementById("sourceFolderPath")
                .value;

        if (!folderPath) {

            alert("Выберите директорию событий");
            return;
        }

        setSourceImportBusy(true);

        showSourceImportResult(
            "loading",
            "Импорт событий выполняется..."
        );

        addLog("[UI] Запуск pipeline");

        try {

            const response =
                await backend.processPipeline(
                    currentProject.id,
                    folderPath
                );

            const result = JSON.parse(response);

            console.log(result);

            if (result.success) {

                addLog("[UI] Импорт завершён");

                if (result.updated_project) {
                    currentProject = result.updated_project;
                } else {
                    currentProject.data_source_path = folderPath;
                    currentProject.import_status = "success";
                    currentProject.needs_binding = true;
                    currentProject.last_import =
                        new Date().toISOString();
                }

                showSourceImportResult(
                    "success",
                    `
                    <strong>Импорт завершён</strong><br>
                    Файлов найдено: ${result.source_files_count || 0}<br>
                    Событий проверено: ${result.validated_events || 0}<br>
                    Событий импортировано: ${result.imported_events || 0}<br>
                    Сессий обработано: ${result.processed_sessions || 0}<br>
                    <br>
                    Следующий шаг: семантическое связывание данных.
                    `
                );

                await loadPlayers();

                setTimeout(() => {

                    closeAllModals();
                    openBindingWizard();

                }, 900);

            } else {

                addLog("[UI] Ошибка pipeline");

                showSourceImportResult(
                    "error",
                    `
                    <strong>${result.message || "Ошибка импорта"}</strong><br>
                    ${result.details || ""}
                    `
                );
            }

        } catch (error) {

            console.error(error);

            showSourceImportResult(
                "error",
                `
                <strong>Ошибка обработки ответа backend</strong><br>
                ${error}
                `
            );

        } finally {

            setSourceImportBusy(false);
        }
    });

/* ---------- CLOSE BUTTONS ---------- */

document
    .querySelectorAll(".closeModalBtn")
    .forEach(btn => {

        btn.addEventListener("click", () => {

            closeAllModals();
        });
});

const whatIfBtn =
    document.getElementById("whatIfBtn");

const whatIfPanel =
    document.getElementById("whatIfPanel");

const closeWhatIf =
    document.getElementById("closeWhatIf");

whatIfBtn.addEventListener("click", () => {

    whatIfPanel.classList.add("visible");

    loadWhatIfParameters();
});

closeWhatIf.addEventListener("click", () => {

    whatIfPanel.classList.remove("visible");
});

function loadWhatIfParameters() {

    const items = [
        { name: "Iron Sword Cost", value: 25 },
        { name: "Legendary Drop Rate", value: 5 }
    ];

    const skills = [
        { name: "Fireball Damage", value: 60 },
        { name: "Healing Efficiency", value: 40 }
    ];

    renderParameters(
        "itemsContainer",
        items
    );

    renderParameters(
        "skillsContainer",
        skills
    );
}

function renderParameters(containerId, data) {

    const container =
        document.getElementById(containerId);

    container.innerHTML = "";

    data.forEach(param => {

        const div =
            document.createElement("div");

        div.className = "whatif-param";

        div.innerHTML = `
            <div class="whatif-param-label">
                <span>${param.name}</span>
                <span>${param.value}</span>
            </div>

            <input
                type="range"
                min="0"
                max="100"
                value="${param.value}"
                class="whatif-slider"
            >
        `;

        container.appendChild(div);
    });
}

const applySimulationBtn =
    document.getElementById("applySimulationBtn");

applySimulationBtn.addEventListener("click", () => {

    addLog(
        "[What-if] Simulation parameters applied"
    );

    alert(
        "Simulation configuration applied"
    );
});

window.addEventListener("resize", () => {

    if (chart) {
        chart.resize();
    }
});