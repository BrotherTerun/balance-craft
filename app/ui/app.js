let backend = null;
let currentProject = null;
let projectsCache = [];
let bindingDropdownHandlersBound = false;
let whatIfControlsCache = null;
let whatIfSliderHandlersBound = false;
let lastAnalysisData = null;
let lastWhatIfScenario = null;
const SCENARIO_DATASET_PREFIX = "__what_if__";

const APP_THEME_STORAGE_KEY = "balancecraft.ui.theme";

// Единая палитра графиков. Без явного цвета Chart.js/QWebEngine
// иногда рисует добавленные сценарные линии почти чёрными на тёмном фоне.
// Поэтому задаём цвета вручную и для истории, и для what-if продолжений.
const CHART_SERIES_COLORS = [
    "#38bdf8",
    "#fb7185",
    "#fb923c",
    "#facc15",
    "#2dd4bf",
    "#a78bfa",
    "#34d399",
    "#f472b6"
];

const CHART_SCENARIO_COLORS = [
    "#7dd3fc",
    "#fda4af",
    "#fdba74",
    "#fde047",
    "#5eead4",
    "#c4b5fd",
    "#86efac",
    "#f9a8d4"
];

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

    setTimeout(() => stabilizeUILayout("dashboard-open"), 150);
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
    stabilizeUILayout("annotations");
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
                Для текущего набора данных не найдено устойчивых практических выводов.
                Проверьте выбранный шаблон, семантические привязки и рассчитанные метрики.
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

    await loadProjects();
    await loadPlayers();
});

const ctx = document.getElementById('chartCanvas').getContext('2d');

const annotationPlugin =
    window.ChartAnnotation ||
    window['chartjs-plugin-annotation'];

if (annotationPlugin) {

    Chart.register(annotationPlugin);

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
                content: 'НЕСТАБИЛЬНОСТЬ',
                position: 'start'
            }
        };
    });

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

let layoutStabilizeTimer = null;
let resizeRaf = null;

function stabilizeUILayout(reason = "") {
    if (!document.body) {
        return;
    }

    document.body.classList.add("ui-render-stabilizing");

    // Принудительно завершаем текущий layout pass QWebEngine перед resize Chart.js.
    // Это помогает после разворачивания окна, открытия панелей и смены темы,
    // не отключая hover-эффекты в обычной работе интерфейса.
    void document.body.offsetHeight;

    if (chart && typeof chart.resize === "function") {
        requestAnimationFrame(() => {
            chart.resize();
        });
    }

    clearTimeout(layoutStabilizeTimer);
    layoutStabilizeTimer = setTimeout(() => {
        document.body.classList.remove("ui-render-stabilizing");
    }, 140);
}

function handleViewportResize() {
    if (resizeRaf) {
        cancelAnimationFrame(resizeRaf);
    }

    resizeRaf = requestAnimationFrame(() => {
        stabilizeUILayout("resize");
        resizeRaf = null;
    });
}

window.addEventListener("resize", handleViewportResize);
window.addEventListener("orientationchange", handleViewportResize);

async function analyzePlayer() {
    if (!backend) {
        alert("Система ещё загружается. Повторите попытку через несколько секунд.");
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

    if (data.scope === "all_players_average") {
        addLog("[ANALYSIS] Построена средняя траектория по всем игрокам");
    }

    if (data.success === false) {
        alert(data.message || "Не удалось построить графики");
        addLog(`[ANALYSIS] ${data.details || data.message || "Ошибка анализа"}`);
        return;
    }

    lastAnalysisData = data;
    lastWhatIfScenario = null;
    hideWhatIfScenarioInsights();

    updateChart(data);
    updateInstabilityAnalysis(data);
    renderPracticalInsights(data);
}

function getMetricColorIndex(dataset, fallbackIndex = 0) {

    const metricKey = dataset.metric_key || dataset.metricKey || "";

    if (metricKey && Array.isArray(lastAnalysisData?.datasets)) {

        const sourceIndex = lastAnalysisData.datasets.findIndex(item => {
            return item.metric_key === metricKey || item.metricKey === metricKey;
        });

        if (sourceIndex >= 0) {
            return sourceIndex;
        }
    }

    return fallbackIndex;
}

function getDatasetColor(dataset, index) {

    const isScenario = Boolean(dataset.scenario);
    const colorIndex = getMetricColorIndex(dataset, index);
    const palette = isScenario
        ? CHART_SCENARIO_COLORS
        : CHART_SERIES_COLORS;

    return palette[colorIndex % palette.length];
}

function normalizeChartDataset(dataset, index) {

    const isScenario = Boolean(dataset.scenario);
    const color = getDatasetColor(dataset, index);

    return {
        label: dataset.label || dataset.metric_key || `Метрика ${index + 1}`,
        data: Array.isArray(dataset.data) ? dataset.data : [],
        yAxisID: "y",
        borderColor: dataset.borderColor || color,
        backgroundColor: dataset.backgroundColor || color,
        pointBackgroundColor: dataset.pointBackgroundColor || color,
        pointBorderColor: dataset.pointBorderColor || color,
        borderWidth: dataset.borderWidth || (isScenario ? 2.5 : 2),
        tension: 0.25,
        pointRadius: dataset.pointRadius ?? (isScenario ? 2 : 3),
        pointHoverRadius: isScenario ? 4 : 5,
        borderDash: dataset.borderDash || (isScenario ? [8, 6] : []),
        spanGaps: false,
        scenario: isScenario,
        scenarioId: dataset.scenario_id || ""
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
    stabilizeUILayout("chart-update");
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
    stabilizeUILayout("chart-labels");
}

document.getElementById("runBtn").addEventListener("click", analyzePlayer);



const metricsBtn = document.getElementById("metricsBtn");

let metricLabels = {
    ev: "Скорость прогрессии",
    pgr: "Темп роста силы",
    dr: "Деградация прогрессии"
};

const saveMetricsBtn =
    document.getElementById("saveMetricsBtn");

if (saveMetricsBtn) {
    saveMetricsBtn.addEventListener("click", () => {

        try {
            metricLabels.ev =
                document.getElementById("evInput")?.value || metricLabels.ev;

            metricLabels.pgr =
                document.getElementById("pgrInput")?.value || metricLabels.pgr;

            metricLabels.dr =
                document.getElementById("drInput")?.value || metricLabels.dr;

            updateChartLabels();
        }
        catch (TypeError) {
            addLog("Не удалось обновить подписи метрик для текущего графика.");
        }
        finally {
            const metricsModal = document.getElementById("metricsModal");
            if (metricsModal) {
                metricsModal.classList.add("is-hidden");
            }
            setModalOpenState(false);
            stabilizeUILayout("metrics-labels-close");
        }
    });
}

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
    // Служебное значение ALL_PLAYERS_ID сообщает приложению, что нужно посчитать
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

    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "d") {

        event.preventDefault();

        const devConsole = document.getElementById("devConsole");

        if (devConsole) {
            devConsole.classList.toggle("visible");
        }
    }
});



const newProjectBtn =
    document.getElementById("newProjectBtn");

const openProjectBtn =
    document.getElementById("openProjectBtn");

newProjectBtn.addEventListener("click", async () => {

    if (!backend) {
        alert("Система ещё загружается. Повторите попытку через несколько секунд.");
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

function updateThemeToggleButton(theme) {
    const themeToggleBtn = document.getElementById("themeToggleBtn");

    if (!themeToggleBtn) {
        return;
    }

    themeToggleBtn.textContent = theme === "light"
        ? "Тёмная тема"
        : "Светлая тема";
}

function applyAppTheme(theme, shouldPersist = true) {
    const normalizedTheme = theme === "light" ? "light" : "dark";

    document.body.classList.toggle("theme-light", normalizedTheme === "light");
    document.body.dataset.theme = normalizedTheme;
    updateThemeToggleButton(normalizedTheme);

    if (shouldPersist) {
        try {
            localStorage.setItem(APP_THEME_STORAGE_KEY, normalizedTheme);
        }
        catch (error) {
            console.warn("Не удалось сохранить тему интерфейса", error);
        }
    }

    requestAnimationFrame(() => stabilizeUILayout("theme-change"));
}

function initThemeToggle() {
    let savedTheme = "dark";

    try {
        savedTheme = localStorage.getItem(APP_THEME_STORAGE_KEY) || "dark";
    }
    catch (error) {
        savedTheme = "dark";
    }

    applyAppTheme(savedTheme, false);

    const themeToggleBtn = document.getElementById("themeToggleBtn");

    if (!themeToggleBtn) {
        return;
    }

    themeToggleBtn.addEventListener("click", () => {
        const nextTheme = document.body.classList.contains("theme-light")
            ? "dark"
            : "light";

        applyAppTheme(nextTheme, true);

        if (analysisMenu) {
            analysisMenu.classList.add("is-hidden");
        }
    });
}

initThemeToggle();

/* ---------- MODALS ---------- */

function openModal(id) {

    if (analysisMenu) {
        analysisMenu.classList.add("is-hidden");
    }

    const modal =
        document.getElementById(id);

    if (!modal) {
        console.error(`Модальное окно ${id} не найдено`);
        alert(`Не удалось открыть окно ${id}. Перезапустите приложение.`);
        return;
    }

    modal.classList.remove("is-hidden");

    setModalOpenState(true);
    stabilizeUILayout("modal-open");
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
    stabilizeUILayout("modal-close");
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
        alert("Не удалось открыть окно источника событий. Перезапустите приложение.");
        return;
    }

    if (!sourceFolderPath) {
        console.error("sourceFolderPath не найден в index.html");
        alert("Не удалось открыть поле источника событий. Перезапустите приложение.");
        return;
    }

    if (!resultBox) {
        console.error("sourceImportResult не найден в index.html");
        alert("Не удалось открыть блок результата импорта. Перезапустите приложение.");
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
    stabilizeUILayout("source-modal-open");
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
    stabilizeUILayout("source-import-result");
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
        },
        {
            value: "computed.previous_power",
            label: "computed.previous_power · сила до начала сессии",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.current_power",
            label: "computed.current_power · сила на конец сессии",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.delta_power",
            label: "computed.delta_power · изменение силы за сессию",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.net_progress",
            label: "computed.net_progress · входящий поток минус потери",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.previous_resource",
            label: "computed.previous_resource · ресурс до начала сессии",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.current_resource",
            label: "computed.current_resource · ресурс на конец сессии",
            isNumeric: true,
            sourceKind: "computed"
        },
        {
            value: "computed.resource_delta",
            label: "computed.resource_delta · изменение ресурса за сессию",
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


function getDefaultEventDataSource() {
    const fields = bindingDraft.candidates?.attribute_fields || [];
    const numericFields = fields.filter(item => item && item.is_numeric && item.path);

    const preferredNames = ["value", "amount", "quantity", "reward", "cost", "delta", "score"];

    for (const preferred of preferredNames) {
        const match = numericFields.find(item => String(item.key || "").toLowerCase() === preferred);
        if (match) {
            return match.path;
        }
    }

    return numericFields.length
        ? numericFields[0].path
        : "events.event_data.value";
}

function getDefaultBindingForVariable(variableKey) {

    const key = String(variableKey || "").toLowerCase();

    if (key.includes("duration") || key.includes("time")) {
        return "computed.duration_minutes";
    }

    if (key === "previous_power" || key.includes("previous_power")) {
        return "computed.previous_power";
    }

    if (key === "current_power" || key.includes("current_power")) {
        return "computed.current_power";
    }

    if (key === "delta_power" || key.includes("delta_power")) {
        return "computed.delta_power";
    }

    if (key === "net_progress" || key.includes("net_progress")) {
        return "computed.net_progress";
    }

    if (key === "previous_resource" || key.includes("previous_resource")) {
        return "computed.previous_resource";
    }

    if (key === "current_resource" || key.includes("current_resource")) {
        return "computed.current_resource";
    }

    if (key === "resource_delta" || key.includes("resource_delta")) {
        return "computed.resource_delta";
    }

    if (
        key.includes("action") ||
        key.includes("engagement") ||
        key.includes("count")
    ) {
        return "computed.action_count";
    }

    return getDefaultEventDataSource();
}



function isEventDataSource(source) {
    return String(source || "").startsWith("events.event_data.");
}

function getBindingSource(binding) {
    if (!binding) {
        return "";
    }

    if (typeof binding === "string") {
        return binding;
    }

    return binding.source || "";
}

function normalizeVariableBinding(binding, fallbackSource = "") {
    if (!binding) {
        return {
            source: fallbackSource || "",
            event_types: [],
            aggregation: "sum"
        };
    }

    if (typeof binding === "string") {
        return {
            source: binding || fallbackSource || "",
            event_types: [],
            aggregation: "sum"
        };
    }

    return {
        source: binding.source || fallbackSource || "",
        event_types: Array.isArray(binding.event_types)
            ? [...binding.event_types]
            : [],
        aggregation: binding.aggregation || "sum"
    };
}

function getBindingEventTypes(variableKey) {
    const binding = normalizeVariableBinding(
        bindingDraft.variableBindings[variableKey]
    );

    return binding.event_types || [];
}

function setVariableBindingSource(variableKey, source) {
    const previous = normalizeVariableBinding(
        bindingDraft.variableBindings[variableKey]
    );

    bindingDraft.variableBindings[variableKey] = {
        source: source || "",
        event_types: isEventDataSource(source)
            ? previous.event_types || []
            : [],
        aggregation: previous.aggregation || "sum"
    };
}

function setVariableBindingEventType(variableKey, eventType, checked) {
    const binding = normalizeVariableBinding(
        bindingDraft.variableBindings[variableKey]
    );

    const eventTypes = new Set(binding.event_types || []);

    if (checked) {
        eventTypes.add(eventType);
    } else {
        eventTypes.delete(eventType);
    }

    binding.event_types = Array.from(eventTypes);
    bindingDraft.variableBindings[variableKey] = binding;
}

function getBindingEventTypeOptions() {
    const data = bindingDraft.candidates || {};

    return (data.event_types || [])
        .map(item => typeof item === "string" ? item : item.value)
        .filter(Boolean);
}

function formatBindingForDisplay(binding) {
    const normalized = normalizeVariableBinding(binding);

    if (!normalized.source) {
        return "не выбрано";
    }

    if (!isEventDataSource(normalized.source)) {
        return normalized.source;
    }

    const eventTypes = normalized.event_types || [];

    if (!eventTypes.length) {
        return `${normalized.source} · типы событий не выбраны`;
    }

    return `${normalized.source} · ${eventTypes.join(", ")}`;
}

function initializeBindingDraftFromProject() {
    if (!currentProject) {
        return;
    }

    const bindingConfig = currentProject.binding_config || {};

    bindingDraft.formulas = Object.assign(
        {},
        currentProject.formula_config || {},
        bindingConfig.formula_config || bindingConfig.formulas || {}
    );

    bindingDraft.metricLabels = Object.assign(
        {},
        currentProject.metric_labels || {},
        bindingConfig.metric_labels || bindingConfig.metricLabels || {}
    );

    const projectBindings = Object.assign(
        {},
        currentProject.semantic_bindings || {},
        bindingConfig.semantic_bindings || bindingConfig.variable_bindings || {}
    );

    bindingDraft.variableBindings = {};

    Object.keys(projectBindings).forEach(key => {
        bindingDraft.variableBindings[key] = normalizeVariableBinding(
            projectBindings[key]
        );
    });
}

function eventTypeSetsAreEqual(left, right) {
    const a = new Set(left || []);
    const b = new Set(right || []);

    if (a.size !== b.size) {
        return false;
    }

    for (const item of a) {
        if (!b.has(item)) {
            return false;
        }
    }

    return true;
}

function validateOppositeEventFlows() {
    const pairs = [
        ["flow_in", "flow_out", "входящего потока и потерь прогрессии"],
        ["resource_income", "resource_spend", "дохода и расхода ресурса"],
        ["power_gain", "resource_cost", "прироста силы и затрат"]
    ];

    for (const [leftKey, rightKey, label] of pairs) {
        const left = normalizeVariableBinding(bindingDraft.variableBindings[leftKey]);
        const right = normalizeVariableBinding(bindingDraft.variableBindings[rightKey]);

        if (!left.source || !right.source) {
            continue;
        }

        if (!isEventDataSource(left.source) || !isEventDataSource(right.source)) {
            continue;
        }

        if (left.source !== right.source) {
            continue;
        }

        if (eventTypeSetsAreEqual(left.event_types, right.event_types)) {
            alert(
                `Для ${label} выбран один и тот же источник ${left.source} ` +
                `и одинаковый набор event_type. Разделите типы событий, иначе метрики могут стать нулевыми или неинформативными.`
            );

            setBindingStep(4);
            return false;
        }
    }

    return true;
}

function validateEventScopedBindings() {
    const template = getSelectedTemplate();

    if (!template) {
        return true;
    }

    for (const variable of buildFormulaVariableList()) {
        const key = variable.key;
        const binding = normalizeVariableBinding(
            bindingDraft.variableBindings[key]
        );

        if (
            isEventDataSource(binding.source) &&
            (!binding.event_types || !binding.event_types.length)
        ) {
            alert(
                `Для переменной "${variable.name || key}" выбран источник ${binding.source}, ` +
                `но не выбраны типы событий. На 4 шаге отметьте event_type, из которых нужно брать это поле.`
            );

            setBindingStep(4);
            return false;
        }
    }

    return validateOppositeEventFlows();
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



const FORMULA_FUNCTION_NAMES = new Set([
    "sum", "count", "max", "min", "abs", "round", "sqrt", "log", "pow"
]);

function extractFormulaVariables(expression) {
    const text = String(expression || "");
    const names = new Set();
    const matches = text.match(/[A-Za-z_][A-Za-z0-9_]*/g) || [];

    matches.forEach(name => {
        if (!FORMULA_FUNCTION_NAMES.has(name)) {
            names.add(name);
        }
    });

    return Array.from(names);
}

function getFormulaVariableKeys() {
    const template = getSelectedTemplate();

    if (!template) {
        return [];
    }

    ensureFormulaAndMetricDrafts(template);

    const metricKeys = new Set((template.metrics || []).map(metric => metric.key));
    const variableSet = new Set();

    (template.metrics || []).forEach(metric => {
        const expression = bindingDraft.formulas[metric.key] || metric.formula || "";
        extractFormulaVariables(expression).forEach(name => {
            if (!metricKeys.has(name)) {
                variableSet.add(name);
            }
        });
    });

    if (!variableSet.size) {
        (template.variables || []).forEach(variable => variableSet.add(variable.key));
    }

    return Array.from(variableSet);
}

function ensureFormulaAndMetricDrafts(template) {
    (template.metrics || []).forEach(metric => {
        if (!bindingDraft.formulas[metric.key]) {
            bindingDraft.formulas[metric.key] = metric.formula || "";
        }

        if (!bindingDraft.metricLabels[metric.key]) {
            bindingDraft.metricLabels[metric.key] = metric.name || metric.key;
        }
    });
}

function buildFormulaVariableList() {
    const template = getSelectedTemplate();

    if (!template) {
        return [];
    }

    ensureFormulaAndMetricDrafts(template);

    const stockVariables = new Map(
        (template.variables || []).map(variable => [variable.key, variable])
    );

    return getFormulaVariableKeys().map(key => {
        const stock = stockVariables.get(key);

        if (stock) {
            return stock;
        }

        return {
            key: key,
            name: key,
            description: "Пользовательская переменная, найденная в формулах шага 3.",
            required: true,
            formulaDerived: true
        };
    });
}

function ensureDraftForSelectedTemplate() {

    const template = getSelectedTemplate();

    if (!template) {
        return;
    }

    ensureFormulaAndMetricDrafts(template);

    buildFormulaVariableList().forEach(variable => {

        const defaultSource = getDefaultBindingForVariable(
            variable.key
        );

        bindingDraft.variableBindings[variable.key] = normalizeVariableBinding(
            bindingDraft.variableBindings[variable.key],
            defaultSource
        );
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
            Формулы используются при пересчёте метрик после сохранения мастера.
            При изменении формулы сохраняйте исходный смысл метрики выбранного шаблона.
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
    const eventTypeOptions = getBindingEventTypeOptions();

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

    const activeVariables = buildFormulaVariableList();

    const variablesHtml = activeVariables
        .map(variable => {

            const binding = normalizeVariableBinding(
                bindingDraft.variableBindings[variable.key],
                getDefaultBindingForVariable(variable.key)
            );

            const selectedValue = binding.source || "";
            const selectedLabel = getSelectedSourceLabel(selectedValue);
            const selectedEventTypes = new Set(binding.event_types || []);
            const needsEventTypes = isEventDataSource(selectedValue);

            const eventTypeHtml = needsEventTypes
                ? `
                    <div class="binding-event-scope">
                        <div class="binding-event-scope-header">
                            <strong>Типы событий</strong>
                            <span>Отметьте, из каких event_type брать поле ${escapeHtml(selectedValue)}</span>
                        </div>
                        <div class="binding-event-type-list">
                            ${eventTypeOptions.length ? eventTypeOptions.map(eventType => `
                                <label class="binding-event-type-option" title="${escapeHtml(eventType)}">
                                    <input type="checkbox"
                                        data-variable-key="${escapeHtml(variable.key)}"
                                        data-event-type="${escapeHtml(eventType)}"
                                        ${selectedEventTypes.has(eventType) ? "checked" : ""}>
                                    <span>${escapeHtml(eventType)}</span>
                                </label>
                            `).join("") : `<div class="binding-empty">Типы событий не найдены</div>`}
                        </div>
                        ${selectedEventTypes.size ? "" : `
                            <div class="binding-warning-note">
                                Для event_data-поля нужно выбрать хотя бы один тип события, иначе переменная не будет сохранена.
                            </div>
                        `}
                    </div>
                `
                : "";

            return `
                <div class="binding-config-row binding-mapping-row">
                    <label>
                        <strong>${escapeHtml(variable.key)}</strong>
                        <span>${escapeHtml(variable.name)} · ${variable.formulaDerived ? "из формулы" : (variable.required ? "обязательная" : "дополнительная")}</span>
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

                    ${eventTypeHtml}
                </div>
            `;
        })
        .join("");

    root.innerHTML = `
        <div class="binding-info-note">
            На этом шаге переменные выбранного шаблона связываются с найденными
            атрибутами событий и полями таблиц. Для источников вида
            <strong>events.event_data.*</strong> дополнительно выбираются типы событий,
            чтобы одно и то же поле value могло означать доход, расход, награду или потерю
            в зависимости от event_type.
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
                    const currentSource = getBindingSource(
                        bindingDraft.variableBindings[variableKey]
                    );

                    optionButton.classList.toggle(
                        "active",
                        optionValue === currentSource
                    );

                    optionButton.addEventListener("click", event => {

                        event.stopPropagation();

                        const value = optionButton.dataset.value || "";
                        const labelNode = optionButton.querySelector("span");
                        const label = labelNode
                            ? labelNode.textContent
                            : "Не выбрано";

                        setVariableBindingSource(variableKey, value);

                        closeBindingCustomSelects();
                        renderBindingVariableMappingDraft();
                    });
                });
        });

    root
        .querySelectorAll(".binding-event-type-option input")
        .forEach(input => {
            input.addEventListener("change", () => {
                setVariableBindingEventType(
                    input.dataset.variableKey,
                    input.dataset.eventType,
                    input.checked
                );
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
                    <span>${escapeHtml(bindingDraft.formulas[metric.key] || metric.formula || "")}</span>
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

    const variableHtml = buildFormulaVariableList()
        .map(variable => `
            <div class="binding-overview-row">
                <strong>${escapeHtml(variable.key)}</strong>
                <span>${escapeHtml(formatBindingForDisplay(bindingDraft.variableBindings[variable.key]))}</span>
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
        showBindingStatus("error", "Система ещё загружается. Повторите попытку через несколько секунд.");
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
        initializeBindingDraftFromProject();

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

    buildFormulaVariableList().forEach(variable => {

        const key = variable.key;

        if (!key) {
            return;
        }

        const binding = normalizeVariableBinding(
            bindingDraft.variableBindings[key],
            getDefaultBindingForVariable(key)
        );

        semanticBindings[key] = {
            source: binding.source || "",
            event_types: isEventDataSource(binding.source)
                ? binding.event_types || []
                : [],
            aggregation: binding.aggregation || "sum"
        };
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

    if (!validateEventScopedBindings()) {
        return;
    }

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
    openWhatIfPanel();
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

    if (bindingDraft.currentStep === 4 && !validateEventScopedBindings()) {
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

            alert("Система ещё загружается. Повторите попытку через несколько секунд.");
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

            alert("Система ещё загружается. Повторите попытку через несколько секунд.");
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

function setWhatIfStatus(type, message) {

    const status =
        document.getElementById("whatIfStatus");

    if (!status) {
        return;
    }

    status.classList.remove(
        "success",
        "error",
        "loading"
    );

    if (type) {
        status.classList.add(type);
    }

    status.innerHTML = message;
}

function openWhatIfPanel() {

    if (!whatIfPanel) {
        console.error("whatIfPanel не найден в index.html");
        return;
    }

    if (analysisMenu) {
        analysisMenu.classList.add("is-hidden");
    }

    whatIfPanel.classList.remove("is-hidden");
    whatIfPanel.classList.add("visible");

    loadWhatIfParameters();

    setTimeout(() => stabilizeUILayout("what-if-open"), 120);
}

function closeWhatIfPanel() {

    if (!whatIfPanel) {
        return;
    }

    whatIfPanel.classList.remove("visible");
    whatIfPanel.classList.add("is-hidden");

    setTimeout(() => stabilizeUILayout("what-if-close"), 120);
}

if (whatIfBtn) {
    whatIfBtn.addEventListener("click", () => {

        if (
            whatIfPanel &&
            !whatIfPanel.classList.contains("is-hidden")
        ) {
            closeWhatIfPanel();
        } else {
            openWhatIfPanel();
        }
    });
}

if (closeWhatIf) {
    closeWhatIf.addEventListener("click", () => {
        closeWhatIfPanel();
    });
}

async function loadWhatIfParameters() {

    const container =
        document.getElementById("whatIfControlsContainer");

    if (!container) {
        return;
    }

    if (!backend) {
        setWhatIfStatus(
            "error",
            "Система ещё загружается. Повторите попытку после открытия проекта."
        );
        return;
    }

    if (!currentProject || !currentProject.id) {
        setWhatIfStatus(
            "error",
            "Сначала создайте или откройте проект анализа."
        );
        return;
    }

    setWhatIfStatus(
        "loading",
        "Подготовка источников What-if анализа по настройкам мастера семантики..."
    );

    container.innerHTML = "";

    try {

        const response =
            await backend.getWhatIfControls(currentProject.id);

        const data = JSON.parse(response);

        whatIfControlsCache = data;

        renderWhatIfControls(data);

    } catch (error) {

        console.error(error);

        setWhatIfStatus(
            "error",
            `Не удалось подготовить параметры What-if анализа:<br>${escapeHtml(error)}`
        );
    }
}

function formatWhatIfNumber(value) {

    const numeric = Number(value);

    if (!Number.isFinite(numeric)) {
        return "0";
    }

    if (Math.abs(numeric) >= 1000) {
        return numeric.toFixed(0);
    }

    if (Math.abs(numeric) >= 10) {
        return numeric.toFixed(1);
    }

    return numeric.toFixed(2);
}

function getWhatIfSourceLabel(sourceKind) {

    const labels = {
        table_field: "справочник / таблица",
        event_signal: "событийный сигнал",
        computed_signal: "расчётное поле",
        formula_unused: "не используется формулой",
        missing: "источник не задан",
        unknown: "неизвестный источник"
    };

    return labels[sourceKind] || sourceKind || "источник";
}

function renderWhatIfControls(data) {

    const container =
        document.getElementById("whatIfControlsContainer");

    if (!container) {
        return;
    }

    if (!data || data.success === false) {

        container.innerHTML = "";

        setWhatIfStatus(
            "error",
            escapeHtml(data?.message || "Не удалось получить параметры What-if анализа.")
        );

        return;
    }

    const controls = Array.isArray(data.controls)
        ? data.controls
        : [];

    const summary = data.summary || {};

    setWhatIfStatus(
        "success",
        `Подготовлено источников: <strong>${summary.editable_sources_count || 0}</strong>; `
        + `параметров справочников: <strong>${summary.entity_controls_count || 0}</strong>; `
        + `шаблон: <strong>${escapeHtml(data.template_id || "не выбран")}</strong>.`
    );

    if (!controls.length) {

        container.innerHTML = `
            <div class="whatif-control-group">
                <h3>Нет доступных параметров</h3>
                <p class="whatif-control-message">
                    В проекте пока нет сохранённых semantic_bindings.
                    Пройдите мастер семантики и назначьте источники переменным шаблона.
                </p>
            </div>
        `;

        return;
    }

    container.innerHTML = controls
        .map(renderWhatIfControlGroup)
        .join("");

    const applyBtn = document.getElementById("applySimulationBtn");
    if (applyBtn) {
        applyBtn.disabled = !Number(summary.editable_sources_count || 0);
    }

    setupWhatIfSliderHandlers();
}

function renderWhatIfControlGroup(control) {

    const type = control.type || "unsupported";

    if (type === "entity_table") {
        return renderWhatIfEntityGroup(control);
    }

    if (type === "signal_multiplier") {
        return renderWhatIfSignalGroup(control);
    }

    return renderWhatIfUnsupportedGroup(control);
}

function renderWhatIfEntityGroup(control) {

    const rows = Array.isArray(control.controls)
        ? control.controls
        : [];

    const renderedRows = rows
        .map(row => {

            const controlId = escapeHtml(row.control_id);
            const original = Number(row.original_value || 0);
            const valueText = formatWhatIfNumber(original);

            return `
                <div class="whatif-param" data-whatif-row="${controlId}">
                    <div class="whatif-param-label">
                        <span title="${escapeHtml(row.entity_id)}">
                            ${escapeHtml(row.entity_name || row.entity_id)}
                        </span>
                        <span class="whatif-param-value" data-whatif-value="${controlId}">
                            ${valueText}
                        </span>
                    </div>

                    <input
                        type="range"
                        min="${Number(row.min)}"
                        max="${Number(row.max)}"
                        step="${Number(row.step)}"
                        value="${original}"
                        class="whatif-slider"
                        data-whatif-control-id="${controlId}"
                        data-original-value="${original}"
                    >
                </div>
            `;
        })
        .join("");

    const moreNote = "";

    return `
        <section class="whatif-control-group" data-variable-key="${escapeHtml(control.variable_key)}">
            <h3>${escapeHtml(control.variable_label)}</h3>

            <div class="whatif-control-meta">
                ${escapeHtml(control.table_label || control.table)} ·
                ${escapeHtml(control.field_label || control.field)}<br>
                Источник: <code>${escapeHtml(control.source_path)}</code>
            </div>

            <div class="whatif-control-description">
                ${escapeHtml(control.description || "")}
            </div>

            <div class="whatif-entity-list">
                ${renderedRows || `<div class="whatif-control-message">В таблице не найдено числовых значений для этого поля.</div>`}
            </div>

            ${moreNote}
        </section>
    `;
}

function renderWhatIfSignalGroup(control) {

    const controlId = escapeHtml(`signal:${control.variable_key}`);
    const percent = Number(control.current_percent || 100);
    const baseValue = formatWhatIfNumber(control.base_value || 0);
    const sourceLabel = getWhatIfSourceLabel(control.source_kind);
    const eventTypes = control.details && Array.isArray(control.details.event_types)
        ? control.details.event_types
        : [];
    const eventScopeHtml = eventTypes.length
        ? `<br>Типы событий: <code>${escapeHtml(eventTypes.join(", "))}</code>`
        : "";

    return `
        <section class="whatif-control-group" data-variable-key="${escapeHtml(control.variable_key)}">
            <h3>${escapeHtml(control.variable_label)}</h3>

            <div class="whatif-control-meta">
                ${escapeHtml(sourceLabel)}<br>
                Источник: <code>${escapeHtml(control.source_path)}</code>${eventScopeHtml}<br>
                База: ${escapeHtml(control.base_label || "историческая оценка мат. ожидания")} = <strong>${baseValue}</strong>
            </div>

            <div class="whatif-control-description">
                ${escapeHtml(control.description || "")}
            </div>

            <div class="whatif-param">
                <div class="whatif-param-label">
                    <span>Множитель будущего сигнала</span>
                    <span class="whatif-param-value" data-whatif-value="${controlId}">
                        ${percent}%
                    </span>
                </div>

                <input
                    type="range"
                    min="${Number(control.min_percent || 0)}"
                    max="${Number(control.max_percent || 200)}"
                    step="${Number(control.step_percent || 5)}"
                    value="${percent}"
                    class="whatif-slider"
                    data-whatif-control-id="${controlId}"
                    data-original-value="${percent}"
                    data-value-suffix="%"
                >
            </div>
        </section>
    `;
}

function renderWhatIfUnsupportedGroup(control) {

    const sourcePath = control.source_path
        ? `<br>Источник: <code>${escapeHtml(control.source_path)}</code>`
        : "";

    return `
        <section class="whatif-control-group" data-variable-key="${escapeHtml(control.variable_key)}">
            <h3>${escapeHtml(control.variable_label || control.variable_key || "Переменная")}</h3>
            <div class="whatif-control-meta">
                ${escapeHtml(getWhatIfSourceLabel(control.source_kind))}
                ${sourcePath}
            </div>
            <p class="whatif-control-message">
                ${escapeHtml(control.message || "Этот источник пока не поддерживается в What-if анализе.")}
            </p>
        </section>
    `;
}

function setupWhatIfSliderHandlers() {

    if (whatIfSliderHandlersBound) {
        return;
    }

    whatIfSliderHandlersBound = true;

    const container =
        document.getElementById("whatIfControlsContainer");

    if (!container) {
        return;
    }

    container.addEventListener("input", event => {

        const slider = event.target.closest(".whatif-slider");

        if (!slider) {
            return;
        }

        const controlId = slider.dataset.whatifControlId;
        const suffix = slider.dataset.valueSuffix || "";
        const output = Array
            .from(document.querySelectorAll("[data-whatif-value]"))
            .find(element => element.dataset.whatifValue === controlId);

        if (output) {
            const numeric = Number(slider.value);
            output.textContent = suffix
                ? `${formatWhatIfNumber(numeric)}${suffix}`
                : formatWhatIfNumber(numeric);
        }
    });
}

function resetWhatIfControls() {

    document
        .querySelectorAll(".whatif-slider")
        .forEach(slider => {

            const original = slider.dataset.originalValue;

            if (original === undefined) {
                return;
            }

            slider.value = original;

            slider.dispatchEvent(
                new Event("input", { bubbles: true })
            );
        });

    clearWhatIfScenario();
    hideWhatIfScenarioInsights();

    addLog("[What-if] Настройки сценария сброшены");
}

const resetWhatIfBtn =
    document.getElementById("resetWhatIfBtn");

if (resetWhatIfBtn) {
    resetWhatIfBtn.addEventListener("click", () => {
        resetWhatIfControls();
    });
}

const applySimulationBtn =
    document.getElementById("applySimulationBtn");

function getWhatIfHorizon() {

    const horizonInput =
        document.getElementById("whatIfHorizon");

    const value = Number(horizonInput ? horizonInput.value : 5);

    if (!Number.isFinite(value)) {
        return 5;
    }

    return Math.max(1, Math.min(10, Math.round(value)));
}

function escapeCssSelectorValue(value) {

    if (window.CSS && typeof window.CSS.escape === "function") {
        return window.CSS.escape(String(value));
    }

    return String(value).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

function collectWhatIfScenarioConfig() {

    const controls = [];

    if (!whatIfControlsCache || !Array.isArray(whatIfControlsCache.controls)) {
        return {
            horizon: getWhatIfHorizon(),
            controls: []
        };
    }

    whatIfControlsCache.controls.forEach(control => {

        if (control.type === "signal_multiplier") {

            const controlId = `signal:${control.variable_key}`;
            const slider = document.querySelector(
                `.whatif-slider[data-whatif-control-id="${escapeCssSelectorValue(controlId)}"]`
            );

            controls.push({
                type: "signal_multiplier",
                control_id: controlId,
                variable_key: control.variable_key,
                variable_label: control.variable_label,
                source_path: control.source_path,
                base_value: Number(control.base_value || 0),
                percent: Number(slider ? slider.value : control.current_percent || 100)
            });
        }

        if (control.type === "entity_table") {

            const values = (control.controls || []).map(row => {

                const slider = document.querySelector(
                    `.whatif-slider[data-whatif-control-id="${escapeCssSelectorValue(row.control_id)}"]`
                );

                return {
                    control_id: row.control_id,
                    entity_id: row.entity_id,
                    value: Number(slider ? slider.value : row.original_value || 0)
                };
            });

            controls.push({
                type: "entity_table",
                variable_key: control.variable_key,
                variable_label: control.variable_label,
                source_path: control.source_path,
                table: control.table,
                field: control.field,
                values: values
            });
        }
    });

    return {
        horizon: getWhatIfHorizon(),
        controls: controls
    };
}

function clearWhatIfScenario() {

    if (!chart) {
        return;
    }

    chart.data.datasets = chart.data.datasets.filter(dataset => {
        return !dataset.scenario && !String(dataset.scenarioId || "").startsWith(SCENARIO_DATASET_PREFIX);
    });

    if (lastAnalysisData && Array.isArray(lastAnalysisData.labels)) {
        chart.data.labels = lastAnalysisData.labels;

        chart.data.datasets.forEach(dataset => {
            if (Array.isArray(dataset.data)) {
                dataset.data = dataset.data.slice(0, lastAnalysisData.labels.length);
            }
        });
    }

    chart.update();
    stabilizeUILayout("scenario-clear");
    lastWhatIfScenario = null;
}

function extendHistoricalDatasetsForScenario(labelsLength) {

    chart.data.datasets.forEach(dataset => {

        if (dataset.scenario) {
            return;
        }

        if (!Array.isArray(dataset.data)) {
            dataset.data = [];
        }

        while (dataset.data.length < labelsLength) {
            dataset.data.push(null);
        }
    });
}

function applyScenarioToChart(data) {

    if (!chart || !data) {
        return;
    }

    clearWhatIfScenario();

    const labels = Array.isArray(data.labels)
        ? data.labels
        : chart.data.labels;

    chart.data.labels = labels;
    extendHistoricalDatasetsForScenario(labels.length);

    const scenarioDatasets = Array.isArray(data.scenario_datasets)
        ? data.scenario_datasets
        : [];

    scenarioDatasets.forEach((dataset, index) => {
        chart.data.datasets.push(
            normalizeChartDataset(
                {
                    ...dataset,
                    scenario: true,
                    scenario_id: dataset.scenario_id || `${SCENARIO_DATASET_PREFIX}${index}`
                },
                chart.data.datasets.length + index
            )
        );
    });

    chart.update();
    stabilizeUILayout("scenario-apply");
}

function hideWhatIfScenarioInsights() {

    const panel = document.getElementById("whatIfScenarioInsights");
    const list = document.getElementById("whatIfScenarioInsightsList");

    if (panel) {
        panel.classList.add("is-hidden");
    }

    if (list) {
        list.innerHTML = "";
    }
}

function renderWhatIfScenarioInsights(data) {

    const panel = document.getElementById("whatIfScenarioInsights");
    const list = document.getElementById("whatIfScenarioInsightsList");

    if (!panel || !list) {
        return;
    }

    const insights = Array.isArray(data?.scenario_insights)
        ? data.scenario_insights
        : [];

    if (!insights.length) {
        panel.classList.remove("is-hidden");
        list.innerHTML = `
            <div class="insight-empty">
                Сценарий построен, но backend не вернул отдельных выводов.
            </div>
        `;
        return;
    }

    panel.classList.remove("is-hidden");
    list.innerHTML = insights
        .slice(0, 6)
        .map(insight => {

            const level = String(insight.level || "info").toLowerCase();
            const safeLevel = ["success", "info", "warning", "danger"].includes(level)
                ? level
                : "info";

            const title = escapeHtml(insight.title || "Вывод сценария");
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
                    ${recommendation ? `<p><strong>Рекомендация:</strong> ${recommendation}</p>` : ""}
                    ${evidence ? `<div class="insight-evidence">${evidence}</div>` : ""}
                </div>
            `;
        })
        .join("");
}

function setWhatIfBusy(isBusy) {

    const btn = document.getElementById("applySimulationBtn");

    if (!btn) {
        return;
    }

    btn.disabled = isBusy;
    btn.textContent = isBusy
        ? "Прогноз выполняется..."
        : "Спрогнозировать сценарий";
}

async function forecastWhatIfScenario() {

    if (!backend || !currentProject || !currentProject.id) {
        alert("Сначала откройте проект анализа");
        return;
    }

    const playerId = document.getElementById("playerSelect").value;

    if (!playerId) {
        alert("Выберите игрока или режим среднего значения");
        return;
    }

    const config = collectWhatIfScenarioConfig();

    if (!config.controls.length) {
        alert("Нет доступных what-if параметров для прогноза");
        return;
    }

    setWhatIfBusy(true);
    setWhatIfStatus("loading", "Построение сценарного продолжения графиков...");

    try {

        const response = await backend.applyWhatIfScenario(
            currentProject.id,
            playerId,
            JSON.stringify(config)
        );

        const data = JSON.parse(response);

        if (data.success === false) {
            setWhatIfStatus(
                "error",
                `${escapeHtml(data.message || "Не удалось построить сценарий")}<br>${escapeHtml(data.details || "")}`
            );
            return;
        }

        lastWhatIfScenario = data;
        applyScenarioToChart(data);
        renderWhatIfScenarioInsights(data);

        setWhatIfStatus(
            "success",
            `Сценарий построен: <strong>${data.horizon || config.horizon}</strong> будущих сессий. `
            + `Исторические данные и БД не изменены.`
        );

        addLog("[What-if] Сценарное продолжение графиков построено");

    } catch (error) {

        console.error(error);
        setWhatIfStatus(
            "error",
            `Ошибка построения What-if сценария:<br>${escapeHtml(error)}`
        );

    } finally {
        setWhatIfBusy(false);
    }
}

if (applySimulationBtn) {
    applySimulationBtn.addEventListener("click", forecastWhatIfScenario);
}

window.addEventListener("resize", () => {

    if (chart) {
        chart.resize();
    }
});