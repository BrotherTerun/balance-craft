console.log(window.ChartAnnotation);
console.log(window["chartjs-plugin-annotation"]);

let backend = null;

function addLog(message) {

    const log = document.getElementById("devLogContent");

    const timestamp = new Date().toLocaleTimeString();

    log.innerHTML += `\n[${timestamp}] ${message}`;

    log.scrollTop = log.scrollHeight;
}


function updateInstabilityAnalysis(data) {

    const bifPoints = data.bifurcation_points || [];

    chart.options.plugins.annotation.annotations =
        buildAnnotations(bifPoints);

    chart.update();

    const lyapunov = data.lyapunov || 0;

    const stabilityText =
        document.getElementById("stabilityText");

    const lyapunovValue =
        document.getElementById("lyapunovValue");

    lyapunovValue.innerText =
        lyapunov.toFixed(4);

    if (lyapunov > 0.1) {

        stabilityText.innerText =
            "Высокая нестабильность системы";

    } else if (lyapunov > 0) {

        stabilityText.innerText =
            "Умеренная нестабильность";

    } else {

        stabilityText.innerText =
            "Стабильная динамика";
    }
}

new QWebChannel(qt.webChannelTransport, function(channel) {

    backend = channel.objects.backend;

    backend.logSignal.connect((message) => {
        addLog(message);
    });

    console.log("WebChannel подключен");
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
            },

            y1: {
                type: 'linear',
                position: 'right',
                grid: {
                    drawOnChartArea: false
                }
            },

            y2: {
                type: 'linear',
                position: 'right',
                grid: {
                    drawOnChartArea: false
                }
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

    const response = await backend.analyzePlayer(playerId);
    const data = JSON.parse(response);

    console.log(data);
    updateChart(data);
    updateInstabilityAnalysis(data);

}

function updateChart(data) {
    chart.data.labels = data.labels;

    chart.data.datasets = [
        {
            label: "K(t)",
            data: data.K,
            yAxisID: "y",
            borderWidth: 2
        },
        {
            label: "Y(t)",
            data: data.Y,
            yAxisID: "y",
            borderWidth: 2
        },
        
        {
            label: "EV",
            data: data.EV,
            yAxisID: "y1",
            borderWidth: 2
        },
        {
            label: "PGR",
            data: data.PGR,
            yAxisID: "y1",
            borderWidth: 2
        },

        {
            label: "DR",
            data: data.DR,
            yAxisID: "y2",
            borderWidth: 2
        }
    ];

    chart.update();
}

function updateChartLabels() {

    if (!chart.data.datasets.length) return;

    chart.data.datasets[0].label = "K(t)";
    chart.data.datasets[1].label = "Y(t)";
    chart.data.datasets[2].label = metricLabels.ev;
    chart.data.datasets[3].label = metricLabels.pgr;
    chart.data.datasets[4].label = metricLabels.dr;

    chart.update();
}

document.getElementById("runBtn").addEventListener("click", analyzePlayer);

const templateBtn = document.getElementById("progressionTemplate");

templateBtn.addEventListener("click", () => {

    document
        .getElementById("template-screen")
        .classList.remove("active");

    document
        .getElementById("dashboard-screen")
        .classList.add("active");
});

const browseBtn = document.getElementById("browseBtn");

browseBtn.addEventListener("click", async () => {

    if (!backend) {
        alert("Backend недоступен");
        return;
    }

    const folderPath = await backend.selectFolder();

    if (!folderPath)
        return;

    document.getElementById("folderPath").value = folderPath;

    const status = document.getElementById("dataStatus");

    status.innerText = "Источник данных подключён";
    status.style.background = "#1f4d2e";
});

const importBtn =
    document.getElementById("importBtn");

importBtn.addEventListener("click", async () => {

    if (!backend) {
        alert("Backend недоступен");
        return;
    }

    const folderPath =
        document.getElementById("folderPath").value;

    if (!folderPath) {

        alert("Выберите директорию логов");

        return;
    }

    addLog("[UI] Запуск pipeline");

    const success =
        await backend.processPipeline(folderPath);

    if (success) {

        addLog("[UI] Импорт завершён");

        alert("Данные успешно загружены");

        await loadPlayers();

    } else {

        addLog("[UI] Ошибка pipeline");

        alert(
            "Ошибка импорта.\nСмотрите Dev Console (Ctrl+D)"
        );
    }
});

const metricsBtn = document.getElementById("metricsBtn");

metricsBtn.addEventListener("click", () => {

    document
        .getElementById("dashboard-screen")
        .classList.remove("active");

    document
        .getElementById("metrics-screen")
        .classList.add("active");
});

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

async function loadPlayers() {
    if (!backend) return;

    const response = await backend.getPlayers();
    const players = JSON.parse(response);

    const select = document.getElementById("playerSelect");

    select.innerHTML = "";

    players.forEach(p => {
        const option = document.createElement("option");
        option.value = p.player_id;
        option.textContent = p.name || p.player_id;
        select.appendChild(option);
    });
}

window.addEventListener("load", () => {
    loadPlayers();
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
