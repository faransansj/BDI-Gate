# BDI-Gate 4주 단기 계획

Oct 16, 2026 · @Midori

4주 동안 RQ2(BDI 상태 표현의 효과)와 intention revision 검증만 수행하고, Nov 12, 2026에 Go/No-Go를 판단한다. 29주 계획서는 장기 로드맵으로 둔다.

## 1. 핵심 질문과 이번 4주 목표

**질문: 외부 정보의 출처를 추적하는 BDI 상태 관리가, 정상적인 동적 재계획은 유지하면서 LLM 에이전트의 비인가 계획 변경(intention revision)을 더 잘 탐지하는가?**

> Can provenance-aware BDI state tracking improve the detection of unauthorized intention revisions in LLM agents while preserving legitimate dynamic replanning?

이번 4주는 시스템 완성이 아니라 이 질문 하나에 답하는 것이 목표다. 같은 에이전트, 같은 데이터, 같은 백본을 쓰고 입력 상태 표현만 바꿔 비교한다.

**검증할 가설**

| 가설 | 내용 | 핵심 비교 |
| --- | --- | --- |
| H1 | Provenance가 붙은 belief가 공격성 지시와 정상적인 외부 지시(위임된 지시)를 더 정확히 구별한다 | D vs C |
| H2 | Intention 변경 이력을 보면 최종 tool call만 볼 때 놓치는 목표 변조를 더 일찍 잡는다 | E vs D |
| H3 | 구조화된 Desire–Intention 표현이 raw trace보다 정상 재계획은 허용하고 비인가 변경은 막는다 | C vs A |
| 종합 | 전체 접근의 효과 | E vs A |

B(goal + action)는 Task Shield식 행동 단위 기준선으로 따로 비교한다. 각 요소의 효과는 바로 앞 단계와의 비교(C vs A, D vs C, E vs D)로만 주장한다.

**4주 후 산출물**: 실행 가능한 하네스와 BDI State Manager, 라벨된 revision 이벤트 소규모 데이터셋, A\~E ablation 결과표와 실패 사례, Go/No-Go 판단 메모

## 2. 포지셔닝

**CaMeL은 재계획을 구조적으로 막아서 안전하지만 동적 환경에서 과하게 막는다. Task Shield와 StepGuard는 행동 단위만 봐서 오염된 plan을 놓칠 수 있다. 우리는 그 사이에서 "이 재계획이 정당한가"를 판단한다.**

| 방식 | 판단 단위 | 재계획 처리 | 예상 약점 | 우리와의 차이 |
| --- | --- | --- | --- | --- |
| [CaMeL](https://arxiv.org/html/2606.26479v1) | 신뢰 질의에서 만든 control flow | untrusted 데이터는 control flow를 못 바꿈 | 정상적인 동적 재계획까지 막음. AgentDyn류 환경에서 over-defense | 재계획을 금지하지 않고 정당성을 판단 |
| [Task Shield](https://arxiv.org/html/2412.16682v1) | instruction·tool call이 사용자 목표에 기여하는가 | 행동 단위 정합성만 검사 | 오염된 plan에 이미 포함된 행동이면 통과 가능(plan laundering) | 행동이 아니라 intention commit을 검사, 변경 원인의 provenance 사용 |
| [StepGuard](https://arxiv.org/pdf/2608.24777) | 학습 기반 step-level tool action 검사 | 구조화된 상태 없음 | 같은 질문 | 같은 학습형이지만 BDI 상태 표현이 추가로 이득을 주는지가 핵심 검증 대상 |
| [B-I-P SoK](https://arxiv.org/pdf/2512.06914) | 이론·분류 | Belief→Intention 갱신을 형식화 | 구현·실증 없음 | 형식화를 런타임 검사로 구현하고 실험으로 검증 |

주의: "최초"라는 표현은 쓰지 않는다. 관련 연구 전수 조사 전까지는 위 네 연구와의 차이만 주장한다.

## 3. 설계: 하네스가 intention commit을 승인한다

**하네스는 plan을 저장만 하는 게 아니라 모든 intention commit을 승인하는 주체다. 첫 plan도 예외가 아니다.** 이 원칙이 plan laundering을 막는다. injection이 첫 plan을 만들기 전에 읽혀서 "변경"이 없는 경우도 같이 막힌다.

**승인 단계에서 검사하는 세 가지**

1. **Desire 정합성**: 제안된 intention의 각 step이 사용자 목표·제약으로 정당화되는가
2. **변경 원인의 출처**: 직전 commit 이후 에이전트가 관찰한 belief들(observed provenance)의 출처와 정보 역할(사실 vs 지시)이 이번 commit을 정당화하는가. 어떤 belief가 실제 원인이었는지(attributed provenance)는 아래처럼 따로 다룬다
3. **권한 범위**: 새 step이 요구하는 capability가 현재 허용 범위 안인가. 이것은 학습 모델이 아니라 **결정론적 정책**이 판단한다

결과는 commit / reject / escalate 셋 중 하나다. 학습 모델(이번 4주는 1번, 2번 판단만)은 확률을 내고, 3번 정책 검사는 그와 별개로 항상 적용한다. 학습 모델의 확률적 판단만으로 보안을 보장한다고 주장하지 않는다.

**Observed vs attributed provenance**

| 구분 | 의미 | 얻는 방법 | 4주 파일럿에서의 사용 |
| --- | --- | --- | --- |
| Observed | 직전 commit 이후 무엇을 읽었는가 | 하네스가 tool 입출력을 기계적으로 기록 | D·E 조건의 모델 입력 |
| Attributed | 그중 무엇이 계획 변경의 원인이었는가 | 반사실 재실행: commit 시점에서 후보 belief를 하나씩 가리고 다시 plan을 생성해, plan이 바뀌는지 확인 | 샘플 이벤트에서만 분석용으로 측정. 모델 입력에 쓰지 않음 |

Attributed provenance는 추정치로만 기록하고, 확정된 사실처럼 쓰지 않는다. 재실행 결과가 일관되지 않으면(같은 조건에서 plan이 흔들리면) "귀속 불명"으로 남긴다.

&#91;embedded content: intention commit 승인 흐름 · 검사 3개, 결과 3개\]

학습 모델은 1·2번만 판단하고, 권한 범위는 모델 판단과 관계없이 결정론적 정책이 항상 검사한다.

**Provenance ≠ 안전**: 출처가 알려져 있다는 것과 내용이 믿을 만하다는 것은 다르다. 그래서 출처 태그는 판단 입력 중 하나로만 쓰고, 정보의 역할(사실 제공 vs 행동 지시)과 함께 본다.

**이번 4주 범위**

- 명시적 plan을 매 단계 출력하도록 만든 통제 가능한 에이전트 1종만 쓴다. plan이 없는 기성 에이전트에서 intention을 근사하는 실험은 이후로 미룬다. 두 경우를 섞으면 BDI 방식의 문제인지 plan 추출의 문제인지 구분할 수 없다.
- Input gate·output gate 이중 구조는 만들지 않는다. intention revision 검증 하나만 한다.

## 4. 실험: 입력 상태 표현만 바꾼 A\~E 비교

**판단 대상은 intention commit 이벤트이고, 다섯 조건은 같은 백본·같은 학습 데이터·같은 토큰 예산을 쓴다. 바뀌는 것은 입력 표현뿐이다.**

| 조건 | 모델 입력 | 검증 가설 |
| --- | --- | --- |
| A. Raw | User goal + raw execution trace (최근 구간을 예산에 맞춰 자름) | 기준선 |
| B. Goal-aware | User goal + 현재 제안된 action | Task Shield식 기준선 |
| C. BDI | Desire + Belief + 제안된 Intention | H3 |
| D. BDI + Provenance | C + 각 belief의 출처와 역할(사실/지시) | H1, H3 |
| E. BDI + Revision | D + 직전 intention과의 diff + 직전 commit 이후 관측된 belief (observed만, 사후 반사실로 추정한 attributed provenance는 절대 넣지 않음) | H2, H3 |

**통제 조건**

- **백본**: Laya. zero-shot이 약하므로 조건마다 같은 레시피로 소규모 파인튜닝을 한다. 백본 효과와 분리하려고 ModernBERT + linear head 대조군 1개를 둔다(시간이 되면).
- **토큰 예산**: 모든 조건 512 토큰. 조건 간 정보량 차이가 "길이" 때문이 아니라 "구조" 때문임을 보이기 위해서다.
- **정보 동등성**: 토큰 수를 맞추는 것만으로는 부족하다. A의 raw trace에도 E가 쓰는 같은 belief와 plan 이력 원본이 들어 있는지 이벤트마다 확인한다. 잘라야 할 때는 같은 선택 규칙을 모든 조건에 적용하고, 원본 정보 포함률을 조건별로 보고한다.
- **Seed**: 3개, 같은 (task, injection) 쌍에 paired 비교(paired bootstrap, 95% CI).

**지표**

| 평가 집합 | 정의 |
| --- | --- |
| S\_unauth | 비인가 intention commit (injection으로 바뀌었거나 오염된 첫 plan) |
| S\_legit-commit | 재계획이 아닌 정상 commit (첫 plan, 단순 진행) |
| S\_legit-replan | 정상적인 동적 재계획 commit (tool 오류 대응, 위임된 외부 지시 반영 등) |

| 지표 | 정의 |
| --- | --- |
| 운영점 | validation에서 S\_legit-commit ∪ S\_legit-replan 전체 기준 FPR 5%가 되는 threshold |
| Unauthorized revision recall | 그 운영점에서 S\_unauth를 reject·escalate로 잡은 비율 |
| Legitimate replan block rate | **같은 운영점에서 S\_legit-replan만 따로** 계산한 차단율. 전체 FPR이 5%여도 재계획만 보면 훨씬 높을 수 있고, 그 차이 자체가 핵심 결과 |
| AUROC (집합별) | S\_unauth vs S\_legit-commit, S\_unauth vs S\_legit-replan을 따로 보고해서 운영점 선택에 덜 의존하는 비교 제공 |
| 탐지 시점 분석 | 오프라인 궤적에서 비인가 commit을 잡은 step과 첫 유해 action step의 차이. 실제 조기 차단 효과는 아님, 온라인 게이트 실험(Go 이후)에서 검증 |
| End-to-end ASR / utility | 게이트를 하네스에 실제로 붙였을 때 AgentDojo 공격 성공률과 정상 완료율 (W4, 여유 있을 때) |

## 5. 데이터와 라벨

**가장 막히기 쉬운 곳은 "정상 재계획" 데이터다. AgentDojo는 97개 task 중 dynamic planning이 필요한 것이 6개뿐이다. 그래서 AgentDyn을 3주 차부터 쓰고, 정상 재계획 시나리오를 따로 합성한다.**

### 5.1 소스와 목표 규모 (초안)

| 소스 | 얻는 것 | 목표 commit 이벤트 수 |
| --- | --- | --- |
| [AgentDojo](https://arxiv.org/abs/2406.13352) 공격 궤적 | 비인가 revision (injection으로 바뀐 plan) | 약 800 |
| AgentDojo 무공격 궤적 | 첫 commit, 단순 재계획 | 약 600 |
| [AgentDyn](https://arxiv.org/html/2602.03117v1) 일부 suite | 동적 계획, 도움이 되는 제3자 지시 | 약 400 |
| 합성 정상 재계획 | tool 오류·데이터 누락으로 강제된 재계획, 사용자가 위임한 외부 지시("문서에 적힌 대로 해줘") | 약 400 |
| Counterfactual 쌍 | 같은 revision에 Desire만 바꿔 정답이 뒤집히는 쌍 | 약 200쌍 |

합계 약 2\~3천 이벤트가 목표지만 잠정치다. 공격 시도 수가 비인가 revision 수는 아니다. 에이전트가 공격을 무시하거나 계획을 안 바꾸는 경우가 많다. 그래서 W1에 무방어 에이전트를 돌려 공격 시도당 비인가 revision 발생률을 먼저 재고, 그 값으로 위 목표 규모를 확정한다. 발생률이 낮으면 공격 시도 수를 늘리거나 합성 비중을 조정한다.

### 5.2 라벨 4종 분리

| 라벨 | 질문 | 용도 |
| --- | --- | --- |
| Injection | 외부 입력에 지시를 바꾸려는 공격이 있는가? | 분석·보조 |
| **Authorization (주 라벨)** | 이 intention commit이 사용자 승인 범위 안에서 정당화되는가? | **학습 정답** |
| Attack contribution | 이 commit이 공격 목표 달성에 기여했는가? | 분석 |
| Outcome | 최종적으로 공격이 성공했는가? | 분석, end-to-end 평가 |

### 5.3 사후 정보 누출 방지

- **모델 입력은 그 commit 시점에 관측 가능한 정보로만 제한한다.** 미래 step, 최종 결과, 환경 판정은 입력에 절대 넣지 않는다.
- Outcome과 contribution은 라벨 후보를 고르는 데만 쓴다. Authorization 정답은 별도로 문서화한 정책 기준으로 정한다.
- 예: injection이 든 문서를 읽고도 지시를 따르지 않고 정보만 뽑았다면 Authorization = 정당. 공격 성공 여부와 무관하다.
- 애매한 이벤트는 2인이 독립 검수하고 κ를 보고한다. 라벨 정책 문서는 1\~2주 차 산출물이다.

### 5.4 Split

AgentDojo는 suite 단위로 학습과 테스트를 나눈다. 같은 user task에서 나온 이벤트는 train과 test에 함께 들어가지 않게 한다. 합성 정상 재계획도 템플릿 단위로 나눈다.

## 6. 주차별 계획

**매주 교수님께 보여줄 수 있는 산출물이 하나씩 나오도록 짰다. 3주 차에 첫 ablation 결과표가 나오는 것이 핵심 마일스톤이다.**

| 주차 | 기간 | 작업 | 산출물 | 완료 기준 |
| --- | --- | --- | --- | --- |
| W1 | 10/16–10/22 | AgentDojo 환경 구축, plan을 매 단계 출력하는 에이전트 1종 연결, 궤적에서 goal·tool 호출·응답·plan 변경이 추출되는지 확인, 공격 시도당 비인가 revision 발생률 측정 → 데이터 목표 규모 확정 | 실행 가능한 하네스, 샘플 trace, 무방어 baseline | 무방어 ASR·utility가 보고치와 ±5%p 이내, plan 추출 성공률 ≥ 95%, 발생률 기반 목표 규모 메모 |
| W2 | 10/23–10/29 | 최소 BDI State Manager 구현(commit 전후 상태, 변경 유발 belief와 provenance 기록), 라벨 정책 문서, 합성 정상 재계획 시나리오 작성 시작 | 상태 추적 코드, commit 로그, 라벨 정책 v1, 검수된 라벨 300+ | 파일럿 κ ≥ 0.7 |
| W3 | 10/30–11/5 | 데이터 2\~3천 이벤트로 확대(AgentDyn 일부 포함), A\~E 소규모 파인튜닝, 3 seed 평가 | **첫 ablation 결과표**, recall@FPR5%·정상 재계획 차단율, 실패 사례 | 다섯 조건 모두 같은 예산·레시피로 학습·평가 완료 |
| W4 | 11/6–11/12 | E 조건(revision 이력) 효과 정밀 분석, AgentDyn 동적 시나리오에서 정상 재계획 유지 확인, 여유 있으면 end-to-end ASR | RQ2 파일럿 결과, Go/No-Go 메모, 후속 계획 | 7장 기준으로 판단 완료 |

**역할 (초안)**: 리드는 하네스와 학습 담당. 연구원 1은 라벨 정책과 검수, 연구원 2는 AgentDyn 연동과 합성 시나리오 담당.

**시간 압축 규칙**: 병목은 학습보다 데이터 수집, 라벨 검수, 하네스 디버깅일 가능성이 크다. W3에 시간이 부족하면 단계 비교(C vs A, D vs C, E vs D)에 필요한 조건만 3 seed로 돌리고, B는 1 seed로 줄인다.

## 7. Go/No-Go 기준과 이후 확장

**Go 조건: held-out suite에서 E가 A보다 비인가 revision을 유의하게 더 잘 잡고(종합), 단계 비교(C vs A, D vs C, E vs D)로 어느 요소가 이득을 냈는지 식별될 것. 같은 운영점에서 정상 재계획 차단율은 B보다 나쁘지 않을 것.** 수치 기준은 초안이며 W3 결과를 보고 교수님과 확정한다.

| 판단 | 조건 (초안) | 다음 단계 |
| --- | --- | --- |
| **Go** | E의 recall이 A 대비 +10%p 이상이고 단계 비교 중 하나 이상이 유의함 (paired bootstrap 95% CI가 0을 넘음), 같은 운영점에서 S\_legit-replan 차단율 ≤ B | 11월 중순부터 장기 계획의 Laya 본 학습, input/output 이중 게이트, 실환경 1종(CI/CD) 순으로 확장. 12월 말 프로토타입과 실환경 사례 1건 목표 |
| **부분 Go** | C·D·E가 A보다는 좋지만 B와 차이가 없음 | "BDI 전체"가 아니라 이득이 확인된 요소(provenance 또는 revision 이력)만 남기고 질문을 좁혀 재실험 2주 |
| **No-Go** | C·D·E가 A·B와 유의한 차이 없음 | BDI 구조 주장을 접는다. 후보: (1) plan laundering 공격 자체를 정식화한 공격·벤치마크 연구, (2) 데이터셋 + 경량 guard 비교 연구 |

**확장 순서 (Go일 때)**: Intention revision 검증 → output gate → input gate → 실환경 CI/CD 1종 → 적응형 공격 → 나머지 실환경. 장기 순서와 세부는 [29주 실험 계획서](https://claude.ai/code/artifact/1b43e813-8bfb-48b2-9a3e-9ed1c0bf2e3e)를 따른다.

**12월 말 일정**: 교수님이 12월 말까지 실제 결과를 기대한다면, 위 Go 경로 기준으로 "intention revision 게이트 프로토타입 + AgentDojo/AgentDyn 결과 + CI/CD 사례 1건"이 현실적인 12월 말 산출물이다. 교수님과 이 범위를 먼저 맞춘다.

## 8. 리스크

| 리스크 | 조기 신호 | 대응 |
| --- | --- | --- |
| 정상 재계획 데이터 부족 | W2 말 합성 시나리오 수 < 200 | AgentDyn 비중 확대, tool 오류 주입 자동화로 재계획을 대량 생성 |
| 에이전트가 plan을 안정적으로 안 냄 | W1 plan 추출 성공률 < 95% | plan-then-act 프롬프트 강화, 출력 스키마 강제(JSON), 다른 모델로 교체 |
| 512 토큰에 E 조건(diff + 원인 belief)이 안 들어감 | W3 입력 길이 통계 | diff를 step 단위로 압축, 원인 belief 발췌 규칙 고정, 필요 시 1024 토큰 체크포인트로 전 조건 동시 변경 |
| 파인튜닝 후 calibration 붕괴 | W3 ECE 측정 | 이번 4주는 부가 지표로만 보고, 주장하지 않음 |
| 라벨 정책이 애매해 κ 미달 | W2 파일럿 | 정책 문서에 경계 사례 예시 추가 후 재라벨 |
| A\~E 차이가 데이터 규모 부족으로 안 보임 | W3 CI가 넓음 | No-Go 대신 데이터 2배 확대 후 1주 재실험 |

## Sources

- [CaMeL·Progent 등 out-of-band 방어 평가](https://arxiv.org/html/2606.26479v1)
- [The Task Shield (ACL 2025)](https://arxiv.org/html/2412.16682v1)
- [StepGuard](https://arxiv.org/pdf/2608.24777)
- [SoK: Trust-Authorization Mismatch (B-I-P)](https://arxiv.org/pdf/2512.06914)
- [AgentDojo](https://arxiv.org/abs/2406.13352)
- [AgentDyn](https://arxiv.org/html/2602.03117v1)
- [Laya 모델 카드](https://huggingface.co/convaiinnovations/laya)
- [BDI-Gate 29주 실험 계획서 (장기)](https://claude.ai/code/artifact/1b43e813-8bfb-48b2-9a3e-9ed1c0bf2e3e)
