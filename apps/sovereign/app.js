document.addEventListener('DOMContentLoaded', () => {
  const goalForm = document.getElementById('goal-form');
  const goalInput = document.getElementById('goal-input');
  const btnExecute = document.getElementById('btn-execute');
  const executionSection = document.getElementById('execution-section');
  const execStatusTitle = document.getElementById('exec-status-title');
  const execSpinner = document.getElementById('exec-spinner');

  const metricStep = document.getElementById('metric-step');
  const metricLatency = document.getElementById('metric-latency');
  const metricOracle = document.getElementById('metric-oracle');

  const bodyReasoning = document.getElementById('body-reasoning');
  const statusReasoning = document.getElementById('status-reasoning');
  const bodyCoder = document.getElementById('body-coder');
  const statusCoder = document.getElementById('status-coder');
  const bodyCritic = document.getElementById('body-critic');
  const statusCritic = document.getElementById('status-critic');

  const tabContentCode = document.getElementById('tab-content-code');
  const tabContentInvariants = document.getElementById('tab-content-invariants');
  const tabContentLog = document.getElementById('tab-content-log');

  const tabBtns = document.querySelectorAll('.tab-btn');
  const btnCopyCode = document.getElementById('btn-copy-code');

  // Tab switching logic
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = btn.getAttribute('data-tab');
      if (targetTab === 'code') tabContentCode.classList.add('active');
      else if (targetTab === 'invariants') tabContentInvariants.classList.add('active');
      else if (targetTab === 'log') tabContentLog.classList.add('active');
    });
  });

  // Copy code button
  btnCopyCode.addEventListener('click', () => {
    const code = tabContentCode.textContent;
    navigator.clipboard.writeText(code).then(() => {
      btnCopyCode.textContent = '복사 완료!';
      setTimeout(() => { btnCopyCode.textContent = '코드 복사'; }, 2000);
    });
  });

  // Form submission / Autonomous execution loop
  goalForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const goalText = goalInput.value.trim();
    if (!goalText) return;

    // Reset and show execution section
    executionSection.classList.remove('hidden');
    execSpinner.style.display = 'block';
    execStatusTitle.textContent = '자율 에이전트 스웜이 다각도 협의 및 실행을 시작합니다...';
    btnExecute.disabled = true;
    btnExecute.style.opacity = '0.6';

    metricStep.textContent = 'Step: 1/3';
    metricLatency.textContent = '0.0s';
    metricOracle.textContent = 'Oracle: Running';

    // Step 1: Reasoning status
    statusReasoning.textContent = 'Active';
    statusReasoning.className = 'card-status-tag active';
    bodyReasoning.innerHTML = '<span class="placeholder-text">DeepSeek R1/V4 추론 엔진이 불변식 및 취약점 도출 중...</span>';

    // Reset others
    statusCoder.textContent = 'Waiting';
    statusCoder.className = 'card-status-tag';
    bodyCoder.innerHTML = '<span class="placeholder-text">추론 완료 후 즉시 코드 구현에 착수합니다.</span>';
    statusCritic.textContent = 'Waiting';
    statusCritic.className = 'card-status-tag';
    bodyCritic.innerHTML = '<span class="placeholder-text">구현된 코드에 대해 적대적 검증을 수행합니다.</span>';

    tabContentCode.textContent = '// 자율 코딩 파이프라인 구동 중...';
    tabContentInvariants.textContent = '// 불변식 분석 중...';
    tabContentLog.textContent = `[${new Date().toISOString()}] Goal Received: "${goalText}"\nDispatched to Sovereign Swarm.`;

    const startTime = Date.now();
    const timerInterval = setInterval(() => {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      metricLatency.textContent = `${elapsed}s`;
    }, 100);

    try {
      const response = await fetch('/api/sovereign/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goalText })
      });

      const result = await response.json();
      clearInterval(timerInterval);

      if (result.ok) {
        // Step 1 Complete
        statusReasoning.textContent = 'Done';
        statusReasoning.className = 'card-status-tag done';
        const invs = (result.injected_invariants || []).join('\n• ') || '불변식 도출 완료';
        const fals = (result.injected_falsifiers || []).join('\n• ') || '반증 조건 도출 완료';
        bodyReasoning.textContent = `[불변식 (Invariants)]\n• ${invs}\n\n[취약점 및 반증 조건]\n• ${fals}`;

        // Step 2 Complete
        statusCoder.textContent = 'Done';
        statusCoder.className = 'card-status-tag done';
        bodyCoder.textContent = `[Qwen Coder Implementation]\n${result.generated_code.slice(0, 300)}...`;

        // Step 3 Complete
        statusCritic.textContent = 'Verified';
        statusCritic.className = 'card-status-tag done';
        bodyCritic.textContent = `[Llama Redteam Verdict]\n${result.critic_verdict}`;

        // Fill Artifacts
        tabContentCode.textContent = result.generated_code || '// No code output';
        tabContentInvariants.textContent = `[Invariants]\n${(result.injected_invariants || []).join('\n')}\n\n[Falsifiers]\n${(result.injected_falsifiers || []).join('\n')}`;
        tabContentLog.textContent = JSON.stringify(result.pipeline_trail, null, 2);

        execStatusTitle.textContent = '✅ 자율 실행 및 오라클 검증이 완료되었습니다.';
        execSpinner.style.display = 'none';
        metricStep.textContent = 'Step: Complete';
        metricOracle.textContent = 'Oracle: PASS (rc=0)';
        metricOracle.style.color = 'var(--accent-green)';
      } else {
        execStatusTitle.textContent = `⚠️ 실행 오류: ${result.error || 'Unknown'}`;
        execSpinner.style.display = 'none';
      }
    } catch (err) {
      clearInterval(timerInterval);
      execStatusTitle.textContent = `⚠️ 통신 오류: ${err.message}`;
      execSpinner.style.display = 'none';
    } finally {
      btnExecute.disabled = false;
      btnExecute.style.opacity = '1';
    }
  });
});
