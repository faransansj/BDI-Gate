smoke run 결과를 리뷰하자. 코드 수정 전에 아래를 먼저 보고해.

1. `docs/reports/`의 smoke 리포트에서 지표 5개를 그대로 인용해 (숫자는 파일에서만).
2. 샘플 trace 3개(정상, 공격 성공, 공격 실패)에서 commit 이벤트를 순서대로 보여줘. 각 commit마다 `previous_intention` → `proposed_intention` diff와 `observed_belief_ids`의 provenance만.
3. reviewer 서브에이전트로 누출 감사를 따로 돌려. 지시: "events.jsonl, beliefs.jsonl, raw_trace.jsonl에 공격 성공 여부, injection task, 공격 이름, 정답을 추론할 수 있는 정보가 직접 또는 간접으로 들어있는지 찾아라. episode_id 형식, 파일 이름, 정렬 순서, 필드 존재 여부 같은 간접 신호도 포함." 결과를 그대로 전달해.
4. plan 추출 실패한 턴이 있으면 원인을 분류해 (형식 위반 / plan 생략 / 파서 버그).
5. 같은 config로 두 번 돌렸을 때 차이가 있으면 어디서 갈렸는지.

이 다섯 개를 보고 내가 baseline 실행 여부를 정한다.
