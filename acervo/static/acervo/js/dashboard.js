(function () {
    if (typeof Chart === 'undefined') {
        return;
    }

    function lerDados(id) {
        const el = document.getElementById(id);
        if (!el) {
            return [];
        }
        try {
            return JSON.parse(el.textContent) || [];
        } catch {
            return [];
        }
    }

    const corPrimaria = '#0b291a';
    const corLimaSuave = 'rgba(204, 248, 142, 0.45)';
    const corFloresta = '#1b3d2b';
    const corBotao = '#274a33';
    const corDestaque = '#2f8f5b';

    // 1. Série Temporal: Gráfico de Linha
    const dadosMes = lerDados('dados-mes');
    const canvasMes = document.getElementById('grafico-mes');
    if (canvasMes && dadosMes.length > 0) {
        new Chart(canvasMes, {
            type: 'line',
            data: {
                labels: dadosMes.map((item) => item.mes),
                datasets: [{
                    label: 'Empréstimos',
                    data: dadosMes.map((item) => item.total),
                    borderColor: corPrimaria,
                    backgroundColor: corLimaSuave,
                    pointBackgroundColor: '#ccf88e',
                    pointBorderColor: corPrimaria,
                    pointBorderWidth: 2,
                    fill: true,
                    tension: 0.28,
                    pointRadius: 5,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                },
            },
        });
    }

    // 2. Ranking: Barras Horizontais
    const dadosRanking = lerDados('dados-ranking');
    const canvasRanking = document.getElementById('grafico-ranking');
    if (canvasRanking && dadosRanking.length > 0) {
        new Chart(canvasRanking, {
            type: 'bar',
            data: {
                labels: dadosRanking.map((item) => item.titulo),
                datasets: [{
                    label: 'Empréstimos',
                    data: dadosRanking.map((item) => item.total),
                    backgroundColor: corFloresta,
                    borderRadius: 6,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0 } },
                },
            },
        });
    }

    // 3. Distribuição por Categoria Dewey: Barras Verticais (sem gráfico de pizza)
    const dadosCategoria = lerDados('dados-categoria');
    const canvasCategoria = document.getElementById('grafico-categoria');
    if (canvasCategoria && dadosCategoria.length > 0) {
        new Chart(canvasCategoria, {
            type: 'bar',
            data: {
                labels: dadosCategoria.map((item) => item.categoria),
                datasets: [{
                    label: 'Empréstimos',
                    data: dadosCategoria.map((item) => item.total),
                    backgroundColor: corBotao,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 } },
                },
            },
        });
    }

    // 4. Distribuição de Exemplares por Estado: Barras Horizontais (sem gráfico de pizza)
    const dadosEstados = lerDados('dados-estados');
    const canvasEstados = document.getElementById('grafico-estados');
    if (canvasEstados && dadosEstados.length > 0) {
        new Chart(canvasEstados, {
            type: 'bar',
            data: {
                labels: dadosEstados.map((item) => item.estado),
                datasets: [{
                    label: 'Exemplares',
                    data: dadosEstados.map((item) => item.total),
                    backgroundColor: corDestaque,
                    borderRadius: 6,
                }],
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, ticks: { precision: 0 } },
                },
            },
        });
    }
})();
