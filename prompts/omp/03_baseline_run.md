baseline run을 준비해. 아직 실행하지 마.

1. `configs/w1_baseline.yaml` 기준으로 실제 episode 수(정상, 공격), 예상 LLM 호출 수, 예상 토큰과 비용 범위를 계산해서 보여줘. 근거는 smoke run의 평균 턴 수와 토큰 수.
2. `max_attack_pairs` 샘플링이 적용되면 어떤 쌍이 뽑혔는지 목록을 파일로 남기고, 샘플링 seed를 manifest에 기록하는지 확인해.
3. 중간에 끊겨도 이어서 돌릴 수 있게 episode 단위 재시작이 되는지 확인해. 이미 끝난 episode는 다시 돌리지 않아야 한다.

내가 "실행"이라고 하면 돌리고, 끝나면 validate → metrics 순서로 돌린 뒤 `docs/reports/W1_<run_id>.md`를 커밋해.
