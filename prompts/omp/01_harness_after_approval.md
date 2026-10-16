계획 승인. 커밋 1부터 진행해.

진행 규칙:
- 커밋마다 끝나면 멈추지 말고 다음 커밋으로 가되, 각 커밋 끝에 (a) 무엇을 했는지 2줄, (b) 통과한 테스트, (c) `docs/goals/W1.md`에서 체크한 항목과 근거 파일을 짧게 남겨.
- 다음 경우에는 멈추고 나에게 물어봐.
  - AgentDojo 내부를 고쳐야만 해결되는 상황
  - 스키마를 바꿔야 하는 상황
  - provenance 분류가 tool 단위 정적 규칙으로 정해지지 않는 tool이 나온 경우
  - API 비용이 드는 실행 (smoke run 포함, 처음 한 번은 실행 전에 예상 호출 수를 알려줘)
- provenance는 `docs/notes/provenance_rules.md`의 표를 그대로 따르고, 각 belief에 `provenance_rule` id를 남겨. 표를 수정하지 마. 표에 없는 tool을 만나면 멈추고 물어봐.
- ASR 계산에서 AgentDojo의 `security` 값을 쓸 때는 W1.md G1의 두 사실(True = 공격 성공, 에러도 True로 기록됨)을 반영해. 에러는 meta의 `error`에 반드시 남겨.

smoke run이 끝나면 `scripts/validate.py`와 `scripts/w1_metrics.py`를 돌린 결과를 보여주고 멈춰.
