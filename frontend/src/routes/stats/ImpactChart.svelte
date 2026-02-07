<script>
    import { onMount } from 'svelte';
    import Chart from 'chart.js/auto';
    
    export let events;
    
    let chartCanvas;
    let chartInstance;
    
    onMount(() => {
      if (events && events.length > 0) {
        renderChart();
      }
    });
    
    $: if (chartCanvas && events) {
      renderChart();
    }
    
    function renderChart() {
      if (chartInstance) {
        chartInstance.destroy();
      }
      
      const labels = events.map(e => e.event.event_name.substring(0, 20) + '...');
      const data = events.map(e => e.impact.movement_pips);
      const colors = events.map(e => {
        if (e.impact.movement_pips > 30) return '#ef4444';
        if (e.impact.movement_pips > 15) return '#f59e0b';
        return '#10b981';
      });
      
      chartInstance = new Chart(chartCanvas, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Mouvement (pips)',
            data,
            backgroundColor: colors,
            borderRadius: 8,
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (context) => {
                  const event = events[context.dataIndex];
                  return [
                    `Mouvement: ${event.impact.movement_pips} pips`,
                    `Direction: ${event.impact.direction}`,
                    `Date: ${event.event.date} ${event.event.time}`
                  ];
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Mouvement (pips)'
              }
            }
          }
        }
      });
    }
  </script>
  
  <div class="chart-container">
    <canvas bind:this={chartCanvas}></canvas>
  </div>
  
  <style>
    .chart-container {
      height: 400px;
      position: relative;
    }
  </style>