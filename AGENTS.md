# BDI-Gate — Agent Instructions

## 프로젝트 한 줄 요약
LLM 에이전트의 **intention commit**(첫 plan 포함, plan이 확정되는 모든 순간)을 하네스가 외부에서 기록·검증하는 연구 코드다.
지금은 **W1 단계**다. 목표는 AgentDojo 실행 궤적을 재현 가능하게 기록하는 것이고, 모델 학습은 아직 하지 않는다.

작업 전에 항상 아래 순서로 읽는다.
1. `docs/goals/CURRENT.md` — 지금 주차의 목표와 완료 조건 (가장 중요)
2. `docs/research_context.md` — 왜 이걸 하는지, 무엇을 측정하는지
3. `schemas/` — 이벤트 스키마 (스키마를 바꾸려면 먼저 제안하고 승인받는다)

## 절대 규칙 (위반하면 실험 전체가 무효)
1. **사후 정보 누출 금지.** commit 이벤트에는 그 시점까지 관측 가능한 정보만 기록한다.
   - 공격 성공 여부, `injection_task_id`, 공격 이름, utility 결과, 정답 같은 메타데이터는 `data/meta/`에만 쓴다.
   - 이 메타데이터를 `data/events/`, `data/beliefs/`에 절대 섞지 않는다. 같은 파일, 같은 레코드에 넣지 않는다.
   - 미래 step의 내용이나 최종 결과를 이벤트 필드로 넣지 않는다.
2. **Attributed provenance를 계산하거나 기록하지 않는다.** "어떤 belief가 변경의 원인이었나"는 W1 범위가 아니다. 이벤트에는 `observed_belief_ids`(직전 commit 이후 관측한 belief 목록)만 기록한다.
3. **`commit_decision`은 항상 `null`이다.** 라벨링은 이후 별도 파이프라인에서 한다.
4. **raw 데이터는 불변이다.** `data/raw/` 아래 파일은 쓴 뒤 수정하지 않는다. 파생 데이터는 스크립트로 다시 만든다.
5. **plan 추출 실패도 기록한다.** 실패한 step을 버리지 말고 `plan_parse_ok: false`로 남긴다.
6. **방어를 켜지 않는다.** W1 baseline은 무방어다. AgentDojo의 defense 옵션은 모두 끈다.

## 재현성 규칙
- 실행 조건은 `configs/*.yaml` 하나로 정의한다. CLI 인자로 실험 조건을 바꾸지 않는다 (config 경로만 받는다).
- run마다 `run_id`를 만들고 `data/raw/<run_id>/run_manifest.json`에 다음을 저장한다.
  - git commit hash, dirty 여부, config 전문, agentdojo 버전, benchmark(suite) 버전, 모델 이름·버전, temperature, seed, 시작·종료 시각
- temperature는 0으로 둔다. 모델은 날짜가 박힌 버전 문자열로 고정한다 (alias 금지).
- API 키는 환경변수로만 읽는다. 코드, config, 로그, manifest에 키를 남기지 않는다.

## 코드 구조
```
src/bdigate/
  harness/        # AgentDojo pipeline에 끼우는 로깅 레이어, plan 파서
  schema.py       # 이벤트·belief·meta 데이터클래스 + JSON schema 검증
  io.py           # JSONL append-only writer
scripts/
  run_w1.py       # config를 받아 AgentDojo 실행 + 기록
  w1_metrics.py   # 기록된 데이터로 W1 지표 계산 → docs/reports/
  validate.py     # 스키마 검증 + 누출 검사
configs/
schemas/
tests/
data/             # .gitignore 대상
docs/reports/     # 지표 결과 (md + json), 커밋한다
```
- Python 3.11 이상, 타입힌트 필수, `ruff`와 `pytest`를 쓴다.
- AgentDojo 내부 코드를 수정(vendor patch)하지 않는다. pipeline element를 추가하는 방식으로 해결한다. 불가능하면 멈추고 이유를 보고한다.

## 작업 방식
- 큰 작업은 plan mode로 계획을 먼저 보여주고, 승인을 받은 뒤 구현한다.
- AgentDojo API는 추측하지 않는다. 설치된 패키지 소스를 직접 읽어서 확인한다 (explore 서브에이전트를 쓴다).
- 기능 하나가 끝날 때마다 순서를 지킨다: 테스트 → 작은 실제 실행(2~3 task) → 커밋.
- API 비용이 드는 실행은 task 수와 예상 호출 수를 먼저 말한다. **20 task 이상이면 실행 전에 확인을 받는다.**
- 막히면 우회하지 않는다. 무엇이 막혔는지와 선택지 2~3개를 보고한다.
- 지표를 보고할 때 숫자는 반드시 `docs/reports/`의 파일에서 인용한다. 기억으로 쓰지 않는다.
- 주차 목표의 체크박스는 근거 파일 경로와 함께 체크한다.

## 하지 말 것 (W1 범위 밖)
- Laya나 다른 분류기 학습, 라벨링, gate 구현
- 반사실 재실행 (attributed provenance)
- AgentDyn, 실환경(CI/CD 등) 연동
- 에이전트 2종 이상 지원
- 스키마 무단 변경
