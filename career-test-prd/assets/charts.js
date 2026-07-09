(function() {
  var style = getComputedStyle(document.documentElement);
  var accent = style.getPropertyValue('--accent').trim();
  var accent2 = style.getPropertyValue('--accent2').trim();
  var ink = style.getPropertyValue('--ink').trim();
  var muted = style.getPropertyValue('--muted').trim();
  var rule = style.getPropertyValue('--rule').trim();
  var bg2 = style.getPropertyValue('--bg2').trim();
  var success = '#10B981';

  // --- Chart: assessment-radar ---
  var radarEl = document.getElementById('chart-assessment-radar');
  if (radarEl) {
    var radarChart = echarts.init(radarEl, null, { renderer: 'svg' });
    radarChart.setOption({
      animation: false,
      tooltip: { appendToBody: true },
      radar: {
        indicator: [
          { name: '兴趣匹配', max: 100 },
          { name: '性格适配', max: 100 },
          { name: '价值观契合', max: 100 },
          { name: '能力趋势', max: 100 },
          { name: '发展潜力', max: 100 }
        ],
        shape: 'polygon',
        splitNumber: 4,
        axisName: { color: ink, fontSize: 13 },
        splitLine: { lineStyle: { color: rule } },
        splitArea: { show: true, areaStyle: { color: [bg2, 'transparent'] } },
        axisLine: { lineStyle: { color: rule } }
      },
      series: [{
        type: 'radar',
        data: [
          {
            value: [90, 85, 80, 70, 75],
            name: '基础报告（免费）',
            lineStyle: { color: accent, width: 2 },
            areaStyle: { color: accent + '22' },
            itemStyle: { color: accent }
          },
          {
            value: [95, 92, 90, 88, 90],
            name: '深度报告（付费）',
            lineStyle: { color: accent2, width: 2 },
            areaStyle: { color: accent2 + '22' },
            itemStyle: { color: accent2 }
          }
        ]
      }],
      legend: {
        bottom: 0,
        textStyle: { color: muted, fontSize: 12 }
      }
    });
    window.addEventListener('resize', function() { radarChart.resize(); });
  }

  // --- Chart: pricing-comparison ---
  var priceEl = document.getElementById('chart-pricing-comparison');
  if (priceEl) {
    var priceChart = echarts.init(priceEl, null, { renderer: 'svg' });
    priceChart.setOption({
      animation: false,
      tooltip: {
        appendToBody: true,
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          var p = params[0];
          return p.name + '<br/>' + p.seriesName + ': ' + p.value + ' 元';
        }
      },
      grid: { left: 60, right: 30, top: 30, bottom: 50 },
      xAxis: {
        type: 'category',
        data: ['职探\n深度解读', '职探\n职业匹配', '职探\n全面发展', '行业均价\n基础报告', '北森\n单次测评'],
        axisLabel: { color: muted, fontSize: 11, interval: 0 },
        axisLine: { lineStyle: { color: rule } },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        name: '价格（元）',
        nameTextStyle: { color: muted, fontSize: 12 },
        axisLabel: { color: muted, fontSize: 12 },
        splitLine: { lineStyle: { color: rule, type: 'dashed' } },
        axisLine: { show: false }
      },
      series: [{
        name: '价格',
        type: 'bar',
        barWidth: '50%',
        data: [
          { value: 4.88, itemStyle: { color: accent } },
          { value: 9.90, itemStyle: { color: accent } },
          { value: 16.90, itemStyle: { color: accent } },
          { value: 49.00, itemStyle: { color: muted } },
          { value: 99.00, itemStyle: { color: muted } }
        ],
        label: {
          show: true,
          position: 'top',
          formatter: '¥{c}',
          color: ink,
          fontSize: 13,
          fontWeight: 600
        }
      }]
    });
    window.addEventListener('resize', function() { priceChart.resize(); });
  }

  // --- Chart: market-segment ---
  var segEl = document.getElementById('chart-market-segment');
  if (segEl) {
    var segChart = echarts.init(segEl, null, { renderer: 'svg' });
    segChart.setOption({
      animation: false,
      tooltip: { appendToBody: true },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { color: ink, fontSize: 12, formatter: '{b}\n{d}%' },
        labelLine: { lineStyle: { color: rule } },
        data: [
          { value: 5800, name: 'MBTI 测试用户', itemStyle: { color: accent } },
          { value: 3000, name: '霍兰德测试用户', itemStyle: { color: accent2 } },
          { value: 1200, name: '职业价值观测试', itemStyle: { color: success } },
          { value: 800, name: '其他测评工具', itemStyle: { color: muted } }
        ]
      }],
      legend: {
        bottom: 0,
        textStyle: { color: muted, fontSize: 12 }
      }
    });
    window.addEventListener('resize', function() { segChart.resize(); });
  }
})();
