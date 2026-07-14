(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();

  // --- Chart 1: API P95 Performance ---
  var chartPerf = echarts.init(document.getElementById('chart-perf'), null, { renderer: 'svg' });
  chartPerf.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      appendToBody: true,
      formatter: function(params) {
        return params[0].name + '<br/>P95: ' + params[0].value + ' ms';
      }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['GET /questions/', 'POST /assessments/', 'GET /assessments/', 'GET /dashboard/'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11, rotate: 15 }
    },
    yAxis: {
      type: 'value',
      name: 'P95 (ms)',
      nameTextStyle: { color: muted, fontSize: 11 },
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [{
      type: 'bar',
      data: [15.7, 89.2, 12.3, 45.6],
      itemStyle: {
        color: function(params) {
          var colors = [accent2, accent, accent2, accent];
          return colors[params.dataIndex];
        },
        borderRadius: [4, 4, 0, 0]
      },
      barWidth: '45%',
      label: {
        show: true,
        position: 'top',
        color: ink,
        fontSize: 12,
        fontWeight: 700,
        formatter: '{c} ms'
      }
    }]
  });
  window.addEventListener('resize', function() { chartPerf.resize(); });

  // --- Chart 2: Test Summary by Phase ---
  var chartSummary = echarts.init(document.getElementById('chart-summary'), null, { renderer: 'svg' });
  chartSummary.setOption({
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      appendToBody: true
    },
    legend: {
      data: ['通过', '失败'],
      top: 0,
      right: 10,
      textStyle: { color: muted, fontSize: 12 }
    },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: ['1.用例矩阵', '2.功能测试', '3.算法数据', '4.性能测试', '5.安全测试', '6.UAT'],
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '用例数',
      nameTextStyle: { color: muted, fontSize: 11 },
      axisLine: { lineStyle: { color: rule } },
      axisLabel: { color: muted, fontSize: 11 },
      splitLine: { lineStyle: { color: rule, type: 'dashed' } }
    },
    series: [
      {
        name: '通过',
        type: 'bar',
        data: [170, 89, 20, 7, 18, 4],
        itemStyle: { color: accent2, borderRadius: [4, 4, 0, 0] },
        barWidth: '30%',
        label: {
          show: true,
          position: 'top',
          color: ink,
          fontSize: 11,
          fontWeight: 700
        }
      },
      {
        name: '失败',
        type: 'bar',
        data: [0, 0, 0, 0, 0, 0],
        itemStyle: { color: '#dc2626', borderRadius: [4, 4, 0, 0] },
        barWidth: '30%'
      }
    ]
  });
  window.addEventListener('resize', function() { chartSummary.resize(); });
})();
