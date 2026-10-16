# BDI-Gate 실험 계획서

BDI 상태 기반 경량 Decision Model을 이용한 LLM 에이전트 I/O 보안 게이트

Oct 16, 2026 · @Midori

> **이 문서는 장기 로드맵이다.** 외부 검토를 반영해 첫 4주(10/16–11/12)는 [BDI-Gate 4주 단기 계획](https://claude.ai/code/artifact/d7a6be79-43b6-477b-aaa5-32867b8ecedb)으로 대체한다. 단기 계획에서는 RQ2와 intention revision만 검증한다. 그 Go/No-Go 결과에 따라 이 문서의 P3 이후를 진행한다.

## 1. 연구 요약

**한 줄 요약: 하네스가 외부에서 관리하는 BDI 상태를 판단 기준으로 삼아, 파인튜닝한 421M decision model(Laya)이 에이전트의 I/O를 검문한다. 목표는 같은 벤치마크(AgentDojo·AgentDyn·실환경)에서 LLM auditor와 동등 이상의 탐지 성능(ASR, FPR, utility)을 내면서, 판단당 지연과 비용을 크게 낮추고 calibrated 확률까지 내는 것이다. 모델 규모는 주장이 아니라 비용 차이의 원인으로만 다룬다.**

LLM 에이전트는 tool output, 웹 문서 같은 비신뢰 입력 때문에 사용자 의도에서 벗어난 행동을 한다. 기존 방어는 두 계열로 나뉜다. 하나는 결정론적 정책 계열(CaMeL, Progent)로, 안전하지만 동적 환경에서 over-defense가 심하다. 다른 하나는 대형 LLM auditor 계열(AlignmentCheck, Task Shield)로, 의미 수준 판단은 하지만 매 스텝 비싸고 calibration이 없다.

본 연구는 두 계열 사이의 빈자리를 노린다. 에이전트 상태를 Belief(provenance 태그 포함), Desire(사용자 목표), Intention(커밋된 plan)으로 구조화한다. 그 위에서 경량 decision model이 두 질문을 판단한다. Input gate는 "이 입력이 belief를 오염시키는가", Output gate는 "이 action이 intention과 desire에 부합하는가"이다.

**핵심 기여 (예정)**

1. **BDI-Gate**: 외부 관리 BDI 상태 + provenance 전파 + intention reconsideration 기반 선택적 게이팅을 갖춘 I/O 이중 게이트 아키텍처
2. **BDI-Trace 데이터셋**: 기존 벤치마크 궤적에 step-level B/D/I + provenance + gate 라벨을 붙인 공개 학습셋 (hard benign negative 포함)
3. **실증**: AgentDojo / AgentDyn / AutoDojo, gate 대상 white-box 적응형 공격, 그리고 실환경 5종(CI/CD, OpenClaw, MCP, 문서·브라우저, 멀티에이전트) 케이스 스터디까지 포함한 평가. ASR–Utility–Latency Pareto에서 LLM auditor 대비 우위를 보이고, 결정론적 정책(Progent)과의 조합 효과를 입증

## 2. 연구 배경과 필요성

**지금 이 연구가 필요한 이유는, 현재 방어가 "안전하지만 쓸모없는" 쪽과 "쓸만하지만 비싸고 불안정한" 쪽으로 양분돼 있고, 둘 사이를 메울 구조가 없기 때문이다.**

**(1) 산업계는 이미 레이어 분리로 가고 있다.** Microsoft는 agentic AI 보안을 defense in depth로 정의한다. 모델 레이어는 확률적이라 믿을 수 없고, 빌더가 완전히 통제하는 애플리케이션 레이어가 결정적이라고 본다. 그런데 그 애플리케이션 레이어에서 "의미 수준 판단"을 싸게 하는 표준 부품은 아직 없다.

**(2) 결정론적 방어는 정적 벤치에서는 거의 완벽하지만 실환경에서는 무너진다.** CaMeL, FIDES, Progent 등은 AgentDojo에서 공격을 거의 0으로 만든다. 하지만 AgentDyn이 SOTA 방어 10종을 평가한 결과, 대부분이 보안 부족이거나 over-defense가 심했다. AgentDojo 97개 task 중 dynamic planning이 필요한 것은 6개뿐이라, 정적 벤치 점수가 실력을 과대평가한다.

**(3) LLM auditor는 의미 판단은 되지만 배치 비용이 크다.** AlignmentCheck는 70B급 모델로 recall 80% 이상, FPR 4% 미만을 낸다. 하지만 매 스텝 대형 모델 CoT 호출이 필요하고, 출력이 calibrated 확률이 아니다. 따라서 threshold를 운영 요구(FPR 1% 등)에 맞출 수 없다.

**(4) 경량 decision model이 막 등장했다.** Jev/Laya 같은 System-1 decision model은 텍스트 생성 대신 선택지, 점수, yes/no 확률을 내놓는다. LangChain은 이미 tool-risk check 용도로 시연했다. 다만 zero-shot 성능이 낮고(약 0.35), "무엇을 기준으로 판단하는가"라는 spec이 없다.

**(5) BDI가 그 spec이 될 수 있다.** 최근 SoK가 prompt injection부터 tool poisoning까지의 공통 원인을 Belief–Intention–Permission의 비동기화로 정리했다. 즉 BDI류 상태 모델이 공격을 설명하는 틀로는 제안됐다. 그러나 이를 **런타임 게이트의 입력 표현이자 학습 라벨로 operationalize한 연구는 확인한 범위에서 드물다(전수 조사 필요).** 이것이 본 연구의 기회다.

## 3. 선행연구 분석: 가져갈 것과 경쟁 요소

**가장 위험한 경쟁자는 Task Shield와 AlignmentCheck다. 둘 다 "action이 사용자 목표에 부합하는가"라는 같은 질문을 대형 LLM으로 푼다. 우리 차별점은 질문이 아니라 상태 표현(BDI+provenance), 판단기(경량 calibrated 모델), 그리고 적응형 공격에서의 견고성이어야 한다.**

**재정의한 차별점 (외부 검토 반영)**: 연구의 중심을 "경량 보안 모델"에서 **provenance-aware intention revision**으로 옮긴다. CaMeL은 untrusted 데이터가 control flow를 바꾸지 못하게 막아서 plan laundering에는 강하지만, 정상적인 동적 재계획까지 막는다. Task Shield와 StepGuard는 행동 단위로 보기 때문에, 오염된 plan에 이미 들어간 행동은 놓칠 수 있다. 우리는 외부 정보가 계획 변경에 어떻게 영향을 줬는지 추적하고, 그 변경이 승인된 목표에 정당하게 연결되는지를 판단한다.

| 계열 | 대표 연구 | 핵심 아이디어 | 가져갈 것 | 경쟁 포인트 / 우리 공략 지점 |
| --- | --- | --- | --- | --- |
| Task alignment (LLM) | [Task Shield](https://arxiv.org/html/2412.16682v1) (ACL 2025) | 모든 instruction·tool call이 사용자 목표에 기여하는지 검증. AgentDojo GPT-4o ASR 2.07%, utility 69.79% | "harm 방지"가 아닌 "task alignment" 프레이밍, 평가 셋업 | **개념이 가장 겹침.** 매 스텝 LLM 호출 비용, calibration 부재, 비신뢰 입력이 판단기 자체를 오염시킬 위험을 공략 |
| Trajectory auditor (LLM) | [LlamaFirewall AlignmentCheck](https://arxiv.org/pdf/2505.03574) (Meta) | 전체 실행 trace를 사용자 목표와 비교. 70B급으로 recall >80%, FPR <4%. PromptGuard 2와 결합 시 AgentDojo ASR 17.6% → 1.75% | Input 분류기 + 의미 auditor 2단 구조, 공개 eval set | **메인 비교 대상.** 같은 탐지 수준을 421M으로, latency·비용 수십 배 절감 + ECE 제시 |
| Input 탐지기 | PromptGuard 2, PIGuard, [CommandSans](https://arxiv.org/pdf/2510.08829) | 입력 텍스트에서 injection 탐지/제거 | Input gate baseline | 문맥(현재 intention) 없이 판단 → benign third-party instruction에서 오탐. 우리 input gate는 BDI 문맥을 봄 |
| Step-level guard | [StepGuard](https://arxiv.org/pdf/2608.24777) (2026) | tool 실행 직전 guard 모델 삽입, 학습 기반 | 셋업·평가 프로토콜(AgentDojo, AgentDyn, AgentHarm) | **가장 최신 직접 경쟁자.** 구조화 상태 없이 학습 → BDI 구조의 ablation 이득으로 차별화 |
| 결정론적 정책 | CaMeL, FIDES, Progent, RTBAS, FORGE | capability, IFC 라벨, reference monitor. Progent는 AgentDojo ASR 39.9% → 1.0% | provenance 전파 아이디어(FIDES의 IFC 라벨) → 우리 Belief 태그로 차용 | ASR로 정면 승부하면 패배. 동적 환경 over-defense를 공략하고 \*\*조합(Progent + BDI-Gate)\*\*으로 상호보완 입증 |
| BDI 이론/프레임 | [SoK: Trust-Authorization Mismatch](https://arxiv.org/pdf/2512.06914) (B-I-P), [Architectures for Agentic AI](https://arxiv.org/pdf/2512.09458) | B-I-P로 공격 분류, provenance 신뢰 수준. BDI의 adoption filter / execution monitor / reconsideration policy | 형식화(Belief update, provenance trust), 게이트 위치 이론 | 이론·분류에 그침 → 우리는 **구현 + 학습 + 실증**. 관련연구에서 반드시 인용하고 "B-I-P의 operationalization"으로 포지셔닝 |
| Decision model | [Jev / Laya](https://arxiv.org/pdf/2610.02267), [REFLEX](https://arxiv.org/pdf/2609.26532) | typed decision 전용 non-autoregressive 모델, LLM fallback | Laya 백본, act/escalate head, RLCD calibration | 확인한 범위에서는 보안 게이트로 쓴 체계적 연구가 드묾 (전수 조사 필요) |

**놓치면 안 되는 리뷰어 질문 3개**

1. "Task Shield / AlignmentCheck에 작은 모델을 쓴 것 아닌가?" → BDI 구조 없이 같은 데이터로 학습한 ablation(RQ2)이 답이어야 함
2. "BDI 상태는 누가 만드나? 에이전트가 하이재킹되면 거짓 보고하지 않나?" → 하네스가 외부에서 관리하고 provenance는 tool 경계에서 자동 부여한다는 설계(5장)가 답
3. "Open-weight 게이트는 white-box 공격에 뚫리지 않나?" → 적응형 공격 실험(Phase 5)이 답. 결과가 나빠도 정직하게 보고하고, Progent 조합으로 하한을 보장

## 4. 연구 목표, Research Questions, 기여점

**최종 목표: AgentDojo·AgentDyn에서 AlignmentCheck(70B) 대비 ASR은 동등 이하, benign utility 손실은 3%p 이내로 맞춘다. 동시에 gate 호출당 지연은 1/10 이하, ECE는 0.05 이하를 달성한다.** (수치는 Phase 2 baseline 측정 후 재조정)

**Research Questions**

우선순위 (외부 검토 반영): **RQ2가 최우선**이고 단기 계획에서 먼저 검증한다. RQ1·RQ3·RQ6은 2차 목표다. RQ4는 도메인 1개로 축소하고, RQ5·RQ7은 1차 검증에 성공한 뒤 확장한다. 실환경은 CI/CD 1종을 먼저 한다.

| RQ | 질문 | 검증 실험 | 성공 기준 |
| --- | --- | --- | --- |
| RQ1 | 파인튜닝한 경량 decision model이 LLM auditor 수준의 탐지를 할 수 있는가? | 메인 비교 (AgentDojo, AgentDyn, AlignmentCheck evals) | ASR이 AlignmentCheck 대비 동등 이하 & latency 1/10 이하 |
| RQ2 | BDI 구조화 상태가 raw trace 대비 실제로 이득인가? | 입력 표현 ablation (raw trace / Desire만 / BDI / BDI+provenance) | BDI+provenance가 raw 대비 held-out suite에서 유의한 개선 (paired test p<0.05) |
| RQ3 | Input/Output 이중 게이트가 단일 게이트보다 나은가? | gate 구성 ablation | 이중 > 각 단일, 특히 multi-step 공격에서 |
| RQ4 | 미학습 도메인·공격에 일반화되는가? | suite 단위 held-out, AgentDyn, AutoDojo | held-out suite에서 성능 하락 폭이 baseline 탐지기보다 작음 |
| RQ5 | 적응형 공격(black-box + white-box)에 견디는가? | AutoDojo, gate 대상 GCG류 공격, BDI 상태 오염 공격 | 정적 대비 ASR 상승이 LLM auditor 대비 작거나 동등. 아니면 Progent 조합으로 하한 보장 |
| RQ6 | Calibrated 확률이 운영상 이득인가? | threshold sweep, selective gating(escalate 비율 vs 안전성) | 동일 FPR에서 더 높은 recall, escalate 1% 이하로 운영 가능 |
| RQ7 | 벤치마크 성능이 실제 시스템에서도 유지되는가? 에이전트별 게이트가 멀티에이전트 전파를 막는가? | 9장 실환경 5종 (CI/CD, OpenClaw, MCP, 문서·브라우저, 멀티에이전트) | 무방어 대비 honeytoken leak을 대부분 차단하면서 정상 작업 완료율 손실 5%p 이내. 시나리오 E에서 에이전트별 게이트가 중앙 게이트 이상 |

**기여점 (논문 Introduction에 쓸 형태)**

1. **문제 정식화**: 에이전트 I/O 보안을 "외부 관리 BDI 상태 위의 typed decision" 문제로 정식화. Input = belief admission, Output = intention conformance
2. **시스템**: BDI-Gate. provenance 자동 전파, intention reconsideration 트리거 기반 선택적 게이팅, allow/deny/escalate 3-way calibrated 출력
3. **데이터**: BDI-Trace. step-level BDI 라벨 학습셋 공개 (hard benign negative, held-out split 포함)
4. **실증**: 정적·동적·적응형 평가와 honeytoken 기반 실환경 5종 케이스 스터디에서 Pareto 분석, 결정론적 정책과의 조합 효과, 실패 사례 분석

## 5. 제안 방법: BDI-Gate

**설계 원칙은 셋이다. BDI 상태는 에이전트가 아니라 하네스가 소유하고, provenance는 tool 경계에서 기계적으로 붙이며, 결정론적 샌드박스가 최하층 경계를 맡는다.**

### 5.1 위협 모델

- **공격자**: 에이전트가 읽는 외부 데이터(tool output, 웹, 문서, 타 에이전트 메시지)를 조작할 수 있다. 사용자 프롬프트와 하네스 코드는 조작할 수 없다.
- **방어 대상**: (a) indirect prompt injection에 의한 goal hijacking, (b) 데이터 유출, (c) 의도치 않은 파괴적 행동(오작동 포함).
- **범위 밖**: 샌드박스 탈출과 권한 상승은 OS·컨테이너·capability 레이어가 담당한다. BDI-Gate는 "허용된 권한 안에서 의도와 다른 행동"을 잡는다.
- **적응형 공격자 가정**: Phase 5에서 gate 가중치(open-weight)에 접근하는 white-box 공격자까지 고려한다.

### 5.2 BDI 상태 정의 (하네스가 관리)

| 요소 | 내용 | 갱신 주체 | 신뢰 |
| --- | --- | --- | --- |
| Desire D | 사용자 원 지시 + 명시적 제약(예: "송금 금지") | 사용자 턴에서만 | trusted |
| Intention I | 현재 커밋된 plan step 시퀀스 | 에이전트가 제안하고, 하네스가 승인한 것만 commit (첫 plan 포함) | 출처를 기록 (어떤 belief로부터 유도됐는지) |
| Belief B | 관찰된 사실들, 각 항목에 provenance 태그 {user, system, trusted-tool, tool-metadata, inter-agent, untrusted-external}. tool-metadata는 MCP tool description이고, inter-agent는 다른 에이전트가 보낸 메시지다 | tool 경계에서 자동 태깅 | 태그 그대로 |

핵심 트릭은 **Intention 변경 시 그 원인이 된 Belief의 provenance를 기록하는 것**이다. untrusted belief가 intention을 바꿨다면 그 자체가 강한 신호가 된다. FIDES의 IFC 라벨 아이디어를 BDI 단위로 옮긴 것이다.

**Plan laundering 방지**: intention 변경만 검사하면 injection이 첫 plan 생성 전에 읽힌 경우를 놓친다. 오염된 plan이 판단 기준이 되어 버리기 때문이다. 그래서 하네스는 **첫 commit을 포함한 모든 intention commit을 승인하는 주체**가 된다. 검사 항목은 세 가지다. (1) Desire 정합성, (2) 변경을 유발한 belief의 출처와 역할(사실 vs 지시), (3) 권한 범위. 3번은 학습 모델이 아니라 결정론적 정책이 판단한다. 출처를 안다는 것이 내용이 안전하다는 뜻은 아니므로, provenance는 판단 입력 중 하나로만 쓴다.

### 5.3 두 개의 게이트

|  | Input gate (belief admission) | Output gate (intention conformance) |
| --- | --- | --- |
| 트리거 | untrusted-external, tool-metadata, inter-agent 출처 입력이 들어올 때와 intention commit 시점 (출처 이름만으로 생략하지 않음) | side-effect 있는 action(write, send, exec, 결제)일 때만 |
| 판단 질문 | "이 입력에 현재 D/I와 무관한 지시가 있는가?" | "이 action이 현재 I의 plan step인가? I는 D로부터 유도됐는가?" |
| 출력 | {info, info-with-instruction, injection} + 확률 | {allow, deny, escalate} + 확률 |
| 후속 처리 | injection이면 격리 + belief 태그 강등. 삭제가 아닌 태깅이 기본 | escalate는 사람 승인 또는 대형 LLM fallback (REFLEX식) |

추가로 **intention reconsideration 이벤트**(plan이 바뀌는 순간)에는 output gate를 미리 한 번 돌린다. 행동이 나오기 전에 의도 변경 자체를 검사하는 것이다.

### 5.4 모델과 입력 포맷

- **백본**: Laya (ModernBERT-large 기반, decision head + act/escalate head). 두 게이트를 하나의 모델이 `[TASK=INPUT]` / `[TASK=OUTPUT]` 태스크 토큰으로 multi-task 처리한다.
- **512 토큰 예산 배분 (초안)**: Desire 64 / Intention(현재 + 직전 step) 96 / Belief delta(최근 k개, provenance 포함) 192 / 판단 대상(입력 발췌 또는 action+args) 160. 넘치면 하네스가 요약 대신 **발췌 규칙**(지시문 패턴 우선)으로 자른다. 요약 LLM을 쓰면 그 LLM이 공격면이 되기 때문이다.
- **대안**: 길이가 부족하면 laya-multilingual(1024 tok, 한국어 확장 가능)로 교체 실험.

아래 그림은 결정론적 샌드박스 위에 두 게이트가 BDI 상태를 공유하며 얹히는 구조다.

&#91;embedded content: BDI-Gate 아키텍처 · 게이트 2개, 공유 BDI 상태 1개\]

강조된 두 게이트가 본 연구의 기여 부분이다. 나머지(샌드박스, escalate 경로)는 기존 구성요소를 그대로 쓴다.

## 6. 데이터셋 구축: BDI-Trace

**데이터가 이 연구의 실제 병목이자 두 번째 기여다. 실행 궤적을 수집하고, 환경 상태로 자동 라벨링한 뒤, 애매한 스텝만 teacher LLM과 사람이 보는 3단계 파이프라인으로 만든다.**

### 6.1 소스

| 데이터셋 | 규모 | 용도 | 게이트 |
| --- | --- | --- | --- |
| [AgentDojo](https://arxiv.org/abs/2406.13352) | 97 user tasks, 629 security cases, 4 suites | 학습 + 평가 (suite 단위 split) | Input + Output |
| InjecAgent | 1,054 cases (Direct Harm / Data Stealing) | 학습 | Output 위주 |
| ASB (Agent Security Bench) | 다수 시나리오 | 학습 | Input + Output |
| BIPIA | email, table, code, QA 등 | 학습 | Input |
| AgentHarm | 명시적 악의 multi-step task | 학습 (D 자체가 악의인 경우 분리 라벨) | Output |
| [LlamaFirewall AlignmentCheck evals](https://huggingface.co/datasets/facebook/llamafirewall-alignmentcheck-evals/blob/refs%2Fpr%2F2/README.md) | 577 cases × 6 models | **평가 전용** (학습 금지 명시) | Output |
| [AgentDyn](https://arxiv.org/html/2602.03117v1) | 60 tasks, 560 injection cases | **평가 전용** | Input + Output |
| [AutoDojo](https://arxiv.org/abs/2606.15057) | 적응형 생성 | **평가 전용** | Input + Output |

### 6.2 라벨링 파이프라인

1. **궤적 수집**: 에이전트 3종 이상(GPT 계열, Claude 계열, open-weight 예: Qwen/Llama)을 무방어 상태로 돌려 공격 성공·실패 궤적을 모두 수집한다. 모델 다양성은 "특정 에이전트 말투에 과적합" 비판을 막는다.
2. **BDI 상태 추출**: 하네스 로그에서 D(user task), I(plan 출력 파싱), B(tool 결과 + provenance)를 기계적으로 구성한다. LLM에게 BDI를 묻지 않는다.
3. **자동 라벨**: AgentDojo류는 공격 성공을 실제 환경 상태 변화로 판정한다. 이 판정은 라벨 후보를 고르는 데만 쓴다. 라벨은 Injection / Authorization(주 정답) / Attack contribution / Outcome 4종으로 분리한다. Authorization 정답은 문서화된 정책 기준으로 정한다. 모델 입력은 해당 시점에 관측 가능한 정보로만 제한해서 사후 정보 누출을 막는다.
4. **Teacher 라벨**: 역추적이 애매한 스텝(공격 실패 궤적의 중간 등)은 대형 LLM 3개의 다수결로 soft label을 만든다. 불일치는 escalate 클래스 후보로 둔다.
5. **사람 검수**: 전체의 약 10%를 2인이 독립 라벨링하고, Cohen's κ ≥ 0.7을 목표로 한다. 미달 시 라벨 가이드를 수정하고 재라벨링한다.

### 6.3 Hard benign negative (over-defense 방지 핵심)

- **정상 third-party 지시**: "이 문서 읽고 거기 적힌 대로 회의 잡아줘"처럼 사용자가 외부 지시를 따르라고 위임한 경우. D에 위임이 명시되면 allow가 정답이다.
- **위험해 보이지만 정상**: 사용자가 직접 요청한 삭제·송금·전송
- **Counterfactual 쌍**: 같은 action에 D만 바꿔서 allow/deny가 뒤집히는 쌍을 만든다. 모델이 action 표면이 아니라 D–I 관계를 보게 강제하며, RQ2의 핵심 근거가 된다.

### 6.4 Split 원칙

- AgentDojo는 **suite 단위**로 나눈다: workspace + slack 학습 / banking + travel 테스트, 그리고 교차 반복.
- 같은 user task에서 나온 궤적은 train/test에 동시에 들어가지 않게 한다.
- 공격 템플릿도 일부를 학습에서 제외한다(unseen attack 템플릿 평가).
- 목표 규모: 학습 step 3만 이상, 그중 hard negative 30% 이상. Laya 문서 기준으로 클래스당 수백 개만 돼도 적응은 되지만, 보안 용도에는 그보다 훨씬 많이 필요하다고 본다.

## 7. Phase별 계획과 완료 조건

**총 8개 Phase, 약 29주(2026-10 말 \~ 2027-05 중순)이며 Go/No-Go 게이트가 두 번 있다. Phase 2 끝에서 "BDI 구조가 raw trace보다 낫다"는 신호가 없으면 방향을 바꾼다. Phase 5 끝에서 적응형 공격에 무너지면 포지셔닝을 조합형 방어로 바꾼다.**

&#91;embedded content: Phase 로드맵 · 7개 Phase, Go/No-Go 2회\]

각 Phase의 작업과 완료 조건은 아래 표에 있다.

외부 검토 반영: P0\~P2(W0–W9)의 핵심 검증은 [4주 단기 계획](https://claude.ai/code/artifact/d7a6be79-43b6-477b-aaa5-32867b8ecedb)으로 앞당긴다. 첫 단계는 명시적 plan을 내는 통제 가능한 에이전트 1종으로만 진행한다. plan이 없는 에이전트에서 intention을 근사하는 실험은 별도 조건으로 분리해서 평가한다. 교수님이 12월 말까지 결과를 기대한다면 이 로드맵의 W 기준 일정은 다시 맞춰야 한다.

| Phase | 기간 (예상) | 핵심 작업 | 산출물 | 완료 조건 (Exit criteria) |
| --- | --- | --- | --- | --- |
| P0 셋업·재현 | W0–W2 (2주) | AgentDojo·AgentDyn 환경 구축, 에이전트 3종 연결, no-defense / PromptGuard 2 / AlignmentCheck / Task Shield 재현. **실환경 격리 인프라(VM, egress 프록시, honeytoken) 설계 시작** | 재현 스크립트, baseline 표 v0, 실환경 인프라 설계 메모 | no-defense ASR·utility가 논문 보고치와 ±5%p 이내 |
| P1 BDI 하네스 + 데이터 v1 | W2–W6 (4주) | 하네스에 D/I/B 추적과 provenance 자동 태깅 구현, 궤적 수집, 자동 라벨 + teacher 라벨 파이프라인. provenance 등급에 tool-metadata, inter-agent 추가 | BDI-Trace v1 (≥1만 step), 라벨 가이드 문서 | 파일럿 500 step 사람 검수 κ ≥ 0.7, 자동 라벨 정확도 ≥ 90% (검수 대비) |
| P2 파일럿 학습 (Go/No-Go ①) | W6–W9 (3주) | Jev·Laya zero-shot 측정, 단일 suite로 Laya 파인튜닝, raw-trace vs BDI 입력 파일럿 비교 | 파일럿 결과 메모 | Fine-tuned가 zero-shot 대비 F1 +20%p 이상, **BDI 입력이 raw 대비 held-out에서 개선** → Go. 개선이 없으면 입력 표현 재설계 또는 데이터 기여 중심으로 피벗 |
| P3 본 학습 + 메인 실험 | W9–W15 (6주) | BDI-Trace v2 (≥3만 step, hard negative ≥30%, MCPTox 기반 tool-description 궤적 포함), multi-task 학습, threshold calibration, 메인 벤치 전부 실행. 병행으로 실환경 A·C 구축 | RQ1·RQ3·RQ4 결과 표, Pareto 그림 v1, 환경 A·C 초안 | 4장 최종 목표 수치를 AgentDojo + AgentDyn에서 달성하거나, 미달 시 원인 분석 완료 |
| P3.5 실환경 케이스 스터디 | W15–W19 (4주, P4와 병렬) | 환경 B·D·E 구축, 5종 전부 무방어 leak 재현, 4개 방어 비교, 경계 실험 | RQ7 결과, 시나리오별 실패 분석, 재현 가능한 환경 코드 | 9.6 완료 조건 전부 충족 |
| P4 Ablation + 조합 | W15–W18 (3주) | 입력 표현·게이트 구성·provenance·hard negative ablation, ECE/threshold sweep, Progent + BDI-Gate 조합 | RQ2·RQ6 결과, 조합 결과 | 모든 ablation이 3 seed, paired test로 보고됨. 조합이 Progent 단독 대비 AgentDyn utility 개선 |
| P5 적응형 공격 (Go/No-Go ②) | W19–W23 (4주) | AutoDojo, gate 대상 white-box 공격(GCG류 suffix), BDI 상태 오염 공격(intention 위장, provenance 세탁). **실환경 A·C에도 적응형 공격 적용** | RQ5 결과, 실패 사례 분석 | 적응형 ASR 상승폭 보고 완료(벤치 + 실환경). LLM auditor 대비 열세면 조합형 방어로 포지셔닝 전환 결정 |
| P6 집필·공개 | W23–W29 (6주) | 논문 작성, 코드·데이터·체크포인트·실환경 IaC 공개 준비, 벤더 disclosure 마무리, 내부 리뷰 2회, artifact evaluation 대비 | 투고본, 공개 레포 | 내부 리뷰어가 "reject 사유" 목록 0건, 재현 스크립트가 클린 환경에서 1회 통과, disclosure 대상 벤더 회신 확인 |

**병렬화 포인트**: P1의 데이터 수집과 P2의 zero-shot 측정은 겹쳐 돌릴 수 있다. P5의 공격 코드는 P3 중에 미리 준비한다. P3.5와 P4는 같은 기간에 돌리고, 연구원 2가 실환경을, 리드와 연구원 1이 ablation을 맡는다. 일정이 밀리면 실환경 시나리오를 A·C·E 3종으로 줄이는 것을 첫 번째 압축 수단으로 쓴다. A·C·E는 사고 사례가 가장 분명하고 최초 아이디어를 직접 검증하는 시나리오다.

## 8. 평가 설계

**메인 그림은 ASR × Utility × Latency Pareto 한 장이다. 이 그림에서 BDI-Gate가 "LLM auditor와 같은 보안, 결정론적 정책보다 높은 utility, 탐지기 수준의 비용"이라는 빈 칸을 차지해야 한다.**

### 8.1 Metrics

| Metric | 정의 | 왜 필요한가 |
| --- | --- | --- |
| ASR | injection 목표가 환경 상태에서 실제 달성된 비율 | 보안의 1차 지표 |
| Benign Utility | 공격 없을 때 task 성공률 | over-defense 측정 |
| Utility under Attack | 공격 있을 때 원 task 성공률 | 막으면서 일도 하는가 |
| Gate FPR / Recall | step 단위 오탐·탐지율 | 운영 threshold 설정 근거 |
| Escalation rate | escalate로 넘어간 step 비율 | 사람 개입 비용 |
| Latency, $/1k steps | gate 호출 추가 지연, 비용, 판단당 FLOPs·GPU 메모리 (하드웨어와 무관한 비교용) | 핵심 차별점 |
| ECE, Brier | calibration | RQ6 |

### 8.2 Baselines

1. **무방어**, prompting 방어(delimiting, sandwich)
2. **Input 탐지기**: PromptGuard 2, PIGuard
3. **LLM auditor**: AlignmentCheck(Llama 70B급), Task Shield(GPT-4o급과 open 모델 각각)
4. **학습형 step guard**: StepGuard (코드 공개 여부 확인 필요. 미공개 시 같은 데이터로 재구현한 "구조 없는 guard"로 대체)
5. **결정론적**: Progent, CaMeL (AgentDojo 보고치 + 직접 재현 가능한 쪽)
6. **Decision model zero-shot**: Jev, Laya (같은 BDI 질문 템플릿)
7. **조합**: Progent + BDI-Gate, PromptGuard 2 + BDI-Gate output만

### 8.3 Ablation

| 축 | 변형 | 대응 RQ |
| --- | --- | --- |
| 입력 표현 | raw trace / D만 / D+I / D+I+B / D+I+B+provenance | RQ2 |
| 게이트 구성 | input만 / output만 / 둘 다 / + reconsideration 트리거 | RQ3 |
| 데이터 | hard negative 0% / 15% / 30%, counterfactual 쌍 유무 | RQ2, over-defense |
| 백본 | Laya / laya-multilingual / 동급 encoder 분류기(ModernBERT + linear head) | 결정 모델 구조의 기여 분리 |
| 학습 | RLCD calibration 유지 / 일반 CE | RQ6 |

### 8.4 적응형 공격 (Phase 5)

- **Black-box**: AutoDojo로 방어별 injection을 적응 생성하고, 같은 예산에서 모든 방어를 비교한다.
- **White-box on gate**: Laya 가중치로 GCG류 suffix를 최적화해 input gate 우회를 시도한다. 우회 suffix가 에이전트까지 하이재킹하는지 end-to-end로 확인한다.
- **BDI 오염**: (a) injection이 에이전트로 하여금 plan 텍스트에 공격 목표를 정상 step처럼 끼워 넣게 만드는 intention 위장, (b) trusted-tool 출력에 공격 내용을 우회 주입하는 provenance 세탁.
- 보고 원칙: 정적 결과와 적응형 결과를 같은 표에 나란히 놓는다. 무너지는 경우도 그대로 싣는다.

### 8.5 통계

모든 수치는 3 seed 이상으로 낸다. 방어 간 비교는 같은 (task, injection) 쌍에 대한 paired test(McNemar 또는 paired bootstrap)로 하고, 95% CI를 표기한다.

## 9. 실환경 케이스 스터디 (Phase 3.5)

**시뮬레이션 벤치마크 결과가 실제 시스템에서도 유지되는지를, 격리된 실환경 5종에서 "가짜 키가 실제로 새는가"로 검증한다.** 목적은 "toy 환경" 비판을 막는 것이다. 동시에 게이트가 못 막는 영역(권한 상승, 샌드박스 탈출)을 정직하게 경계 짓는 것도 목적이다.

### 9.1 왜 이 5종인가

2026년 실제 사고가 이미 이 다섯 경로로 났다. CI/CD에서는 Johns Hopkins 팀이 PR과 issue의 injection만으로 Claude Code Security Review, Gemini CLI Action, Copilot Agent가 workflow secret을 노출하게 만들었다. OpenClaw의 ClawHub에서는 감사한 2,857개 skill 중 341개가 악성이었다. MCP tool poisoning은 MCPTox에서 실서버 기준 최대 72.8% 공격 성공률을 보였다. 기존 IPI 벤치마크는 tool output만 공격하므로 이 경로를 따로 다뤄야 한다.

### 9.2 시나리오

| ID | 환경 | 공격 경로 | 피해 판정 | BDI 관점에서 보는 것 |
| --- | --- | --- | --- | --- |
| A | **CI/CD 코딩 에이전트**: self-hosted runner + private repo, 오픈 코딩 에이전트 액션 | PR 제목·본문·issue·comment injection, 에이전트가 수정한 workflow 파일에 exfil step 삽입 | canary secret이 PR comment, job summary, 외부 URL, 커밋에 나타남 | Desire는 "PR 리뷰"인데 env 출력이나 외부 전송은 intention 위반. workflow 수정은 D에 없으면 deny |
| B | **OpenClaw 개인 비서**: 격리 VM, 메시징 채널 연결 | 악성 skill(공급망), 메시징 채널 injection, memory·identity 파일 오염 후 지연 발동 | canary 파일·토큰 유출, 무단 메시지 발송 | skill 지시문이 Desire 행세를 할 때 provenance로 강등되는가. 며칠 뒤 발동하는 공격에서 belief 태그가 유지되는가 |
| C | **MCP 서버 연동 에이전트**: filesystem·git·HTTP MCP 서버 | 오염된 tool description, 승인 후 description 변경(rug pull), tool output injection | SSH 키·토큰 honeytoken 접근 및 전송 | tool 메타데이터를 새 provenance 등급 "tool-metadata"로 분리. description이 intention을 바꾸면 의심 |
| D | **문서·브라우저 에이전트**: computer-use 또는 브라우저 자동화 | 숨김 텍스트가 든 docx·PDF, 웹페이지 injection | 파일이 공격자 계정·외부 스토리지로 업로드됨 | Desire "요약해줘"와 action "업로드"의 불일치. 파일 업로드는 output gate 필수 대상 |
| E | **멀티에이전트 파이프라인**: orchestrator + 하위 에이전트 3\~5개 | 하위 에이전트 하나 오염 후 에이전트 간 메시지로 전파 | 다른 에이전트 권한으로 canary 유출 | **최초 아이디어인 "에이전트별 adapter"의 직접 검증.** 에이전트별 게이트 vs 중앙 게이트, 에이전트 간 메시지를 untrusted로 볼지 여부 |

**경계 실험 (게이트 성능으로 주장하지 않음)**: B 환경에서 샌드박스 탈출과 권한 상승 경로(공개 CVE 재현)를 돌린다. 여기서는 "exploit 직전의 이상한 intention을 게이트가 먼저 잡은 비율"만 보고하고, 샌드박스 레이어가 막아야 하는 영역임을 명시한다.

### 9.3 공통 인프라

- **격리**: 시나리오별 VM 또는 컨테이너, 외부 네트워크 차단. 모든 egress는 로깅 프록시를 통과시키고, 공격자 수신 서버도 내부에 둔다.
- **Honeytoken**: 가짜 API 키, GitHub 토큰, SSH 키, 클라우드 자격증명을 심는다. 어떤 채널로든 문자열이 나가면 탐지되도록 한다. 판정은 0/1 자동이다.
- **IaC**: 환경 전체를 docker compose와 스크립트로 재현 가능하게 만든다. artifact evaluation 대비용이다.
- **에이전트 버전 고정**: 에이전트, 모델, OpenClaw, MCP 서버 버전을 커밋 해시와 날짜로 기록한다.

### 9.4 측정

| 지표 | 정의 |
| --- | --- |
| Leak rate | 공격 시도 중 honeytoken이 실제로 외부에 도달한 비율 |
| Harmful action rate | 무단 발송, 삭제, workflow 변경 등 파괴적·무단 행동 비율 |
| Detection step | 게이트가 처음 막은 step과 첫 유해 action step의 차이 (얼마나 일찍 잡았나) |
| Benign completion | 같은 환경의 정상 작업(시나리오당 50개 이상) 완료율. 실환경 over-defense |
| Overhead | CI job 시간 증가, 에이전트 응답 지연 증가 |

비교 대상은 무방어, PromptGuard 2, AlignmentCheck, BDI-Gate, 그리고 적용 가능한 곳에서는 Progent 조합이다. 공격은 시나리오당 30개 변형 이상을 쓴다. 공개 사고의 페이로드를 재현하고, 적응형으로 생성한 페이로드를 더한다.

### 9.5 윤리와 공개 원칙

- 실제 서비스, 공개 repo, 공개 마켓플레이스에는 어떤 페이로드도 올리지 않는다. 제3자 시스템은 대상으로 삼지 않는다.
- 새 취약점을 발견하면 해당 벤더에 먼저 알리고, 공개는 협의된 기간 뒤에 한다.
- 공격 페이로드 세트는 연구자 대상 신청형으로 제한 공개하고, 환경 코드와 방어 코드는 전부 공개한다.
- 보안 학회의 ethics 섹션 요구사항에 맞춰 위 내용을 논문에 명시한다.

### 9.6 완료 조건

- [ ] 5개 환경이 클린 머신에서 스크립트 한 번으로 재현됨
- [ ] 무방어 상태에서 각 시나리오의 leak이 실제로 재현됨 (공격이 진짜임을 먼저 증명)
- [ ] 4개 방어 전부에 대해 9.4 지표가 측정됨
- [ ] 시나리오별 실패 사례 분석과 경계 실험 결과가 정리됨

## 10. 필요 자원

**가장 큰 비용은 GPU가 아니라 에이전트 궤적 수집에 드는 API 비용과 라벨 검수 인력이다. Laya 파인튜닝 자체는 저렴하다.** 공식 Kaggle 노트북 기준 약 4시간 수준이다.

| 자원 | 용도 | 규모 (추정) | 비고 |
| --- | --- | --- | --- |
| GPU (A100/H100급) | Laya 학습·sweep, open-weight 에이전트 실행, AlignmentCheck 70B 서빙, white-box 공격 | 상시 2\~4장, P3·P5 피크 시 8장 | 학내 데이터센터 활용. 70B 서빙이 가장 무거움 |
| 실환경용 격리 서버 | 시나리오 A\~E VM·컨테이너, self-hosted CI runner, 내부 git 서버, MCP 서버들, 공격자 수신 서버 | 물리 서버 1\~2대 또는 격리 VLAN의 VM 10개 내외 (CPU 위주, 각 8\~16 vCPU) | 외부 네트워크 차단, egress는 로깅 프록시만 허용 |
| 보안 도구 | egress 로깅 프록시, honeytoken 생성·탐지, 로그 수집 | 오픈소스로 충분 | 판정 자동화 스크립트 자체 작성 |
| LLM API | 궤적 수집(에이전트 3종), teacher 라벨, Task Shield/AlignmentCheck API 버전, 실환경 에이전트 구동 | 수집 + 평가 반복 고려 시 수천 달러 단위 | 예산 확정 필요. 캐싱·재사용으로 절감. 실환경은 시나리오당 공격 30 + 정상 50 × 방어 4종 × 3 seed |
| Jev API | zero-shot baseline | 소량 | 버전 고정 기록 필수 |
| 인력: 리드 (본인) | 설계, 하네스, 학습, 집필 | 전 기간 |  |
| 인력: 연구원 1 | 데이터 파이프라인, 라벨 가이드, 검수 | P1\~P4 |  |
| 인력: 연구원 2 | baseline 재현, 실환경 구축, 적응형 공격 | P0, P3\~P5 | 보안·인프라 배경 선호. 실환경 부담이 커서 가장 중요한 추가 인력 |
| 라벨 검수 | 10% 샘플 2인 독립 라벨 | 약 3천 step × 2 | 인턴 활용 가능, 가이드 품질이 관건 |
| 스토리지 | 궤적 로그, 실환경 egress 로그, 체크포인트 | 수백 GB \~ 1TB |  |

**사전 확인할 것**

- [ ] AgentDojo·AgentDyn·AutoDojo 라이선스와 파생 데이터 공개 가능 여부
- [ ] LlamaFirewall eval set의 "학습 금지" 조건 준수 방식 (평가 전용으로만 로딩)
- [ ] StepGuard, Task Shield 코드 공개 여부
- [ ] API 예산 승인과 상한
- [ ] 실환경 실험의 연구실·학교 보안 정책 확인 (격리망 사용 승인, 공격 코드 보관 규정)
- [ ] 벤더 disclosure 창구 목록 (코딩 에이전트 액션, OpenClaw, 사용할 MCP 서버)

## 11. 리스크와 대응

**제일 큰 리스크는 "BDI가 이득이 없다"와 "white-box에 뚫린다" 두 가지다. 둘 다 Go/No-Go 게이트에서 일찍 확인하고, 각각 대체 기여 경로를 미리 정해 둔다.**

| 리스크 | 가능성 | 영향 | 조기 신호 | 대응 |
| --- | --- | --- | --- | --- |
| BDI 입력이 raw trace 대비 이득 없음 | 중 | 치명 | P2 파일럿 ablation | counterfactual 쌍 비중 확대 → 그래도 없으면 "데이터셋 + 경량 guard 벤치마크" 논문으로 피벗 |
| White-box 공격에 쉽게 뚫림 | 중상 | 큼 | P5 초기 | 조합형(Progent + gate) 하한 보장으로 포지셔닝. adversarial training 1 라운드 추가 |
| 실환경에서 벤치 성능이 재현 안 됨 | 중 | 큼 | P3 중 환경 A·C 초기 결과 | 실패 원인을 provenance 누락, 입력 길이, plan 파싱으로 분류해 하네스 보완. 그 자체를 "벤치–실환경 격차" 분석 기여로 보고 |
| 무방어에서도 실환경 공격이 재현 안 됨 (패치됨) | 중 | 중 | P0\~P3 인프라 점검 | 사고 당시 버전으로 고정해 재현. 최신 버전 결과는 별도로 보고 |
| 실환경 구축 지연 | 중상 | 중 | P3 종료 시 A·C 완성 여부 | 시나리오를 A·C·E로 축소 |
| 윤리·보안 정책 문제 (공격 코드 취급, 의도치 않은 외부 유출) | 저 | 큼 | P0 정책 확인 | 격리망·egress 차단 이중화, 페이로드 제한 공개, 새 취약점은 disclosure 우선 |
| 512 토큰 부족으로 정보 손실 | 중 | 중 | P1 입력 길이 통계 (특히 MCP tool description, CI 로그) | 발췌 규칙 개선, multilingual 1024 tok 체크포인트, 2-pass(coarse → fine) |
| Plan 파싱 불가 에이전트 (plan을 명시하지 않음) | 중 | 중 | P1, 실환경 기성 에이전트에서 특히 | 하네스에서 "plan 먼저 출력" 프롬프트 강제. 불가 시 I를 직전 tool call 시퀀스로 근사하고 한계로 명시 |
| 강력한 경쟁 논문 선출판 (StepGuard 후속 등) | 중 | 큼 | 매주 arXiv 모니터링 | 차별점(BDI + calibration + 적응형 + 실환경)을 일찍 고정, 필요 시 workshop 선발표로 우선권 확보 |
| 자동 라벨 노이즈 | 중 | 중 | κ, 검수 정확도 | teacher 다수결 + 불일치 샘플 사람 검수 비율 상향 |
| API 비용 초과 | 중 | 중 | 주간 비용 대시보드 | open-weight 에이전트 비중 확대, 궤적 캐싱 |

## 12. 타겟 학회와 전략

**1순위는 보안 top-4(USENIX Security, IEEE S&P, ACM CCS, NDSS)이다. 적응형 공격 평가와 위협 모델이 탄탄하면 보안 학회가 더 잘 맞는다. ML 학회(NeurIPS, ICLR)는 데이터셋·calibration 쪽을 강조하는 버전으로 대안 트랙을 둔다.**

| 학회 | 맞는 이유 | 강조할 부분 | 주의 |
| --- | --- | --- | --- |
| USENIX Security / CCS / S&P / NDSS | 이 분야 방어 논문의 주 무대, 적응형 평가 요구 수준이 높음 | 위협 모델, 적응형 공격(P5), 결정론적 방어와의 조합, artifact 공개 | 적응형 공격 결과가 약하면 거의 확실히 reject |
| NeurIPS (Datasets & Benchmarks 포함) / ICLR | 데이터셋·학습 방법·calibration 기여 인정 | BDI-Trace, RQ2 ablation, ECE, 경량 모델 효율 | 보안 위협 모델 엄밀성은 덜 요구되지만 novelty 비교가 엄격 |
| ACL / EMNLP | Task Shield가 ACL 2025에 실림 | task alignment 확장, 언어적 판단 | 시스템 기여가 덜 평가될 수 있음 |

**일정 운영**: P6 완료(약 2027-05 중순)를 첫 투고 시점으로 잡고, 그 시점에 가장 가까운 보안 top-4 마감에 맞춘다. 각 학회의 2027 마감일은 공식 CFP로 확인해서 이 표에 날짜를 채워 넣어야 한다. reject 시 리뷰를 반영해 다음 사이클의 다른 top-4로 재투고한다.

- [ ] 2027 USENIX Security / CCS / S&P / NDSS 마감일 확인 후 P6 종료일 역산
- [ ] 교수님과 1순위 학회 확정 (BDI 이론 비중을 어디까지 둘지 함께 결정)

## 13. 참고문헌

**방어 / 가드레일**

- [LlamaFirewall (Meta) — AlignmentCheck, PromptGuard 2](https://arxiv.org/pdf/2505.03574)
- [LlamaFirewall AlignmentCheck Evals 데이터셋](https://huggingface.co/datasets/facebook/llamafirewall-alignmentcheck-evals/blob/refs%2Fpr%2F2/README.md)
- [The Task Shield (ACL 2025)](https://arxiv.org/html/2412.16682v1)
- [StepGuard: Step-Level Guardrails](https://arxiv.org/pdf/2608.24777)
- [CommandSans](https://arxiv.org/pdf/2510.08829)
- [Adaptive Evaluation of Out-of-Band Defenses (CaMeL, FIDES, Progent, RTBAS, FORGE)](https://arxiv.org/html/2606.26479v1)
- [Microsoft — Defense in depth for autonomous AI agents](https://microsoft.com/en-us/security/blog/2026/05/14/defense-in-depth-autonomous-ai-agents)

**벤치마크 / 공격**

- [AgentDojo](https://arxiv.org/abs/2406.13352)
- [AgentDyn](https://arxiv.org/html/2602.03117v1)
- [AutoDojo](https://arxiv.org/abs/2606.15057)
- [PI-Hunter](https://arxiv.org/pdf/2606.12737)
- [PISmith](https://arxiv.org/pdf/2603.13026)

**BDI**

- [SoK: Trust-Authorization Mismatch in LLM Agent Interactions (B-I-P)](https://arxiv.org/pdf/2512.06914)
- [Architectures for Building Agentic AI (BDI 게이트 위치)](https://arxiv.org/pdf/2512.09458)
- [Contemporary Agent Technology: LLM vs Classic MAS (ChatBDI 등)](https://arxiv.org/pdf/2509.02515)

**Decision model**

- [Laya 모델 카드 (Hugging Face)](https://huggingface.co/convaiinnovations/laya)
- [Fast Models, Slow Evidence: JEV vs LAYA 페어 평가](https://arxiv.org/pdf/2610.02267)
- [REFLEX with Jev](https://arxiv.org/pdf/2609.26532)
- [Calibrated Decision Models for Pentest Harnesses](https://arxiv.org/pdf/2609.28940)
- [How to use Laya (파인튜닝 가이드)](https://www.layer3labs.io/guides/how-to-use-laya)

**실환경 사례**

- [GitHub AI 에이전트 secret 유출 (Johns Hopkins, Claude Code·Gemini CLI·Copilot)](https://letsdatascience.com/news/github-ai-agents-expose-secrets-through-prompt-injection-158457d9)
- [AI Agent Prompt Injection in GitHub Actions (exfil 채널 패턴)](https://tenki.cloud/blog/ai-agent-prompt-injection-github-actions)
- [OpenClaw 공격 시나리오 7종 (MITRE ATLAS 정리)](https://adversa.ai/?p=345231)
- [OpenClaw 보안 위험과 CVE 정리](https://www.techradar.com/pro/here-are-the-openclaw-security-risks-you-should-know-about)
- [OpenClaw 샌드박스·지연 injection](https://www.valencesecurity.com/saas-security-terms/openclaw-security)
- [ClawHub 악성 skill 감사](https://www.wboc.com/online_features/press_releases/ai-agents-still-can-t-block-prompt-injection-and-tens-of-thousands-of-openclaw-setups/article_26ab0d67-f592-506d-baae-3fc10f88967a.html)
- [MCPTox: MCP Tool Poisoning 벤치마크](https://arxiv.org/pdf/2508.14925)
- [MCP-TDP: Tool Description Poisoning 벤치마크](https://arxiv.org/pdf/2605.24069)
- [CSA: MCP tool poisoning 리서치 노트](https://labs.cloudsecurityalliance.org/wp-content/uploads/2026/07/CSA_research_note_mcp_tool_poisoning_auto_execution_20260701-csa-styled.pdf)
- [OpenClaw·문서 에이전트 위험 (PromptArmor 문서 injection 사례 포함)](https://vida.io/blog/openclaw-security-risks)
