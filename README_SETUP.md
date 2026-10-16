# omp 셋업 가이드 (BDI-Gate W1)

## 1. 저장소에 넣기
새 repo 루트에 이 폴더 내용을 그대로 복사한다.
```
AGENTS.md                       # omp가 자동으로 읽는 에이전트 규칙
.gitignore                      # data/ 는 커밋하지 않음
docs/research_context.md        # 연구 맥락 요약
docs/goals/CURRENT.md           # 현재 주차 포인터 (사람만 수정)
docs/goals/W1.md                # W1 목표와 완료 조건
docs/notes/provenance_rules.md  # tool별 provenance 규칙 (사람이 관리)
schemas/*.schema.json           # 이벤트·belief·meta 스키마
configs/w1_smoke.yaml           # smoke run
configs/w1_baseline.yaml        # baseline run
prompts/agent_system_plan_then_act.md   # 실험 대상 에이전트의 시스템 프롬프트
prompts/omp/00~04_*.md          # omp에 순서대로 붙여넣을 프롬프트
```
```bash
git init
# .gitignore를 먼저 확인한 뒤 추적할 파일을 명시적으로 git add하고 커밋한다.
```
API 키는 `.env`나 셸 환경변수로만 둔다 (`.gitignore`에 포함됨).

## 2. omp 설정 권장
- **AGENTS.md는 루트에 둔다.** omp는 루트 AGENTS.md를 읽는다. `.omp/AGENTS.md`를 따로 만들면 그쪽이 우선하니, 둘 중 하나만 유지한다.
- **모델 역할 분리** (`/model`에서 역할별로 지정):
  - main: 가장 강한 코딩 모델. 하네스·스키마 검증처럼 실수하면 안 되는 작업을 한다.
  - explore·서브에이전트: 싼 모델(smol 계열)로 충분하다. AgentDojo 소스 탐색에 쓴다.
  - reviewer: main과 **다른** 모델을 권장한다. 누출 감사를 같은 모델이 하면 같은 맹점이 생긴다.
- **plan mode**: 00, 03 프롬프트는 plan mode에서 보낸다. 계획을 승인받고 실행하는 흐름이다.
- **권한**: 셸 실행 자동 승인은 테스트·린트 명령까지만. LLM API를 부르는 실행(`scripts/run_w1.py`)은 매번 확인하도록 둔다. 비용이 걸려 있다.
- 다른 에이전트 설정(.claude, .cursor 등)이 같은 폴더에 있으면 omp가 같이 읽을 수 있다. 이 repo에는 두지 않는다.

## 3. 진행 순서
| 순서 | 프롬프트 | 언제 | 끝나면 사람이 할 일 |
| --- | --- | --- | --- |
| 1 | `00_kickoff.md` (plan mode) | 시작 | 질문에 답하고 계획 승인 |
| 2 | `01_harness_after_approval.md` | 승인 직후 | 중간 질문에 답, smoke 비용 확인 |
| 3 | `02_smoke_review.md` | smoke 후 | 누출 감사 결과 확인, baseline 여부 결정 |
| 4 | `03_baseline_run.md` (plan mode) | baseline 전 | 비용 보고 확인 후 "실행" |
| 5 | `04_w1_wrapup.md` | baseline 후 | W1_summary 검토, W2_draft 확정, CURRENT.md 갱신 |

## 4. W1 Goal (요약)
config 하나로 무방어 AgentDojo 실행을 재현하고, 모든 intention commit을 누출 없이 JSONL로 남긴다. 그리고 지표 5개(utility, ASR, plan 추출 성공률, 비인가 revision 발생률, 정상 재계획 발생률)를 리포트로 낸다. 세부 완료 조건은 `docs/goals/W1.md`에 있다.

## 5. 시작 전 사전 준비 (omp 켜기 전에)
1. **OpenAI API 키**: `export OPENAI_API_KEY=...` 또는 repo 루트 `.env` (커밋 금지, `.gitignore`에 있음).
2. **예산 상한**: OpenAI 대시보드에서 프로젝트를 따로 만들고 월 사용 한도를 걸어둔다. 에이전트가 루프를 잘못 돌려도 비용이 막힌다.
3. **모델 상태 확인**: OpenAI deprecations 페이지에서 `gpt-4o-mini-2024-07-18` 종료 예정이 없는지 확인. (`gpt-4o-2024-05-13`은 2026-10-23 종료 예정이라 쓰지 않음)
4. **rate limit tier 확인**: baseline의 `concurrency`를 올릴지 정할 때 필요. smoke는 1로 돈다.
5. **Python 3.11 이상, uv**. 저장소 루트에서 `uv sync --locked` 한 번으로 패키지와 개발 의존성을 설치한다. 기본 개발 Python은 `.python-version`의 3.13이며 NixOS는 아래 셸 안에서 설치한다.
6. **omp 모델 역할**: main / explore / reviewer를 `/model`에서 지정 (2절 참고).

### NixOS 개발환경

저장소 루트에서 실행한다:
```bash
nix develop ./nix
uv sync --locked
source .venv/bin/activate
```

기존 환경과 새 환경 모두 같은 `uv sync --locked` 명령을 사용한다. 별도 pip 설치나 `uv venv` 단계는 필요 없다.

- `nix/flake.lock`으로 Nix 패키지를 고정한다. 셸은 Python 3.13, uv, Git, Ruff와 AgentDojo의 네이티브 의존성에 필요한 `libstdc++` 검색 경로를 제공한다.
- `UV_PYTHON`은 Nix Python을 가리키고 `UV_PYTHON_DOWNLOADS=never`로 일반 Linux Python 자동 다운로드를 막는다. NixOS에서 발생하는 `stub-ld` 오류를 피하기 위한 설정이다.
- 셸 진입 자체는 `.venv`를 생성하거나 패키지를 설치하지 않는다. 명시적으로 실행하는 `uv sync`는 Nix interpreter 경로가 달라지면 `.venv`를 재생성할 수 있으므로, 별도 작업용 패키지를 프로젝트 venv에 수동 추가하지 않는다.
- `pyproject.toml`과 `uv.lock`은 Python 패키지 의존성을, `nix/flake.lock`은 Nix 도구와 라이브러리를 고정한다. 키 파일과 `.env`는 자동으로 읽지 않는다. 키는 실행 전에 환경변수로 제공한다.
- flake를 `nix/`에 격리해 루트의 키 파일·데이터·가상환경이 Nix 소스로 복사되는 것을 피한다. `nix/` 안에는 비밀이나 실험 데이터를 넣지 않는다.
- Git 저장소를 초기화한 뒤에는 `nix/flake.nix`와 `nix/flake.lock`을 명시적으로 추적한다. 키 파일이 있는 루트에서 무분별하게 `git add -A`를 실행하지 않는다.

무과금 동작 확인:
```bash
nix develop ./nix --command .venv/bin/python -c \
  "from agentdojo.task_suite.load_suites import get_suites; s = get_suites('v1.2.2')['workspace']; print(s.benchmark_version, len(s.user_tasks), len(s.injection_tasks))"
```
확인된 출력: `(1, 2, 2) 40 14`. x86_64-linux에서 실행 확인했으며 aarch64-linux 셸도 정의돼 있다.

G1 검증:
```bash
nix develop ./nix --command uv run --locked pytest tests/test_environment.py
nix develop ./nix --command ruff check src tests
```
NixOS에서는 `uv run ruff`가 아니라 위의 Nix Ruff를 사용한다. pip wheel의 Ruff 실행 파일은 일반 Linux 동적 로더를 요구하여 `stub-ld` 오류가 난다. 일반 Linux에서는 `uv run --locked ruff check src tests`를 사용할 수 있다.
실제 설치 소스의 API·security 의미·에러·캐시 근거는 `docs/notes/agentdojo_api.md`를 참고한다.


## 6. 사람이 직접 확인할 것 (에이전트에게 맡기지 말 것)
- config: `provider: openai`, `model: gpt-4o-mini-2024-07-18`로 채워져 있다. `pipeline_name`에 모델 문자열이 들어 있어야 `important_instructions` 공격이 동작한다. `package_version`이 실제 설치 버전(`pip show agentdojo`)과 같은지 확인.
- AgentDojo **캐시 함정**: logdir에 같은 pipeline 이름의 결과가 있으면 다시 안 돌린다. config는 run_id별 logdir + `force_rerun: true`로 막아뒀다. 재현성 검사 결과가 "완전히 똑같다"고 나오면 캐시를 의심한다.
- `docs/notes/provenance_rules.md`: 초안이 들어 있다 (쓰기 tool은 보수적으로 untrusted). 동의하지 않으면 실험 시작 전에 고치고 결정 기록에 남긴다.
- `validate.py`의 누출 검사 목록이 충분한지.
- AgentDojo `security`: **True = 공격 성공**, 그리고 에러도 True로 기록된다 (agentdojo 0.1.35 소스 기준). 에이전트가 쓴 `docs/notes/agentdojo_api.md`가 이 두 사실을 소스 줄 번호와 함께 적었는지 확인한다. W1 리포트의 ASR이 에러 제외/포함 두 값으로 나왔는지도 확인한다.
- attack 이름: `important_instructions` (AgentDojo 표준). 나중에 AgentDojo가 모르는 모델을 추가하면 pipeline 이름 매칭이 실패하므로 그 모델에서는 `important_instructions_no_model_name`을 쓴다.
