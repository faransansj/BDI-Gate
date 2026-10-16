이 저장소는 BDI-Gate 연구 코드다. 지금은 W1 단계다.

먼저 다음 세 파일을 읽어라: `AGENTS.md`, `docs/goals/CURRENT.md`가 가리키는 주차 목표 파일, `docs/research_context.md`. 그다음 `schemas/` 아래 세 스키마와 `configs/w1_smoke.yaml`도 읽어라.

읽은 뒤 코드는 아직 쓰지 말고 plan mode로 다음을 보여줘.
1. W1 완료 조건(G1~G6)을 네가 이해한 대로 한 줄씩 다시 써라. 모호하거나 서로 충돌하는 부분이 있으면 질문으로 표시해라.
2. AgentDojo에서 확인해야 할 것 목록 (pipeline element 끼우는 위치, tool 결과가 메시지에 들어가는 방식, injection 주입 위치, utility/security 판정 함수, benchmark 버전 이름). 각 항목마다 explore 서브에이전트로 설치된 패키지 소스를 찾아 파일 경로와 함께 답해라. 추측은 "추측"이라고 표시해라.
3. 구현 순서: G1 → G2 → G3 → G4 → G5(smoke) 까지를 커밋 단위 5~8개로 나눈 계획. 각 커밋의 테스트와 완료 확인 방법을 적어라.
4. 누출 위험 지점 목록: 이 구현에서 메타 정보가 이벤트·belief 파일로 새어 들어갈 수 있는 경로를 전부 적고, 각각 어떻게 막을지 적어라.

내가 승인하면 첫 커밋부터 시작한다. baseline run(G5 후반)은 smoke 결과를 보고 내가 따로 지시한다.
