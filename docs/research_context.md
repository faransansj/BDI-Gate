# 연구 맥락 (에이전트용 요약)

원본 계획서
- 4주 단기 계획 (현재 기준 문서): https://claude.ai/code/artifact/d7a6be79-43b6-477b-aaa5-32867b8ecedb
- 29주 장기 로드맵: https://claude.ai/code/artifact/1b43e813-8bfb-48b2-9a3e-9ed1c0bf2e3e

이 파일은 코딩 에이전트가 작업 판단에 필요한 만큼만 요약한 것이다. 충돌하면 4주 계획서가 우선한다.

## 핵심 질문
외부 정보의 출처를 추적하는 BDI 상태 관리가, 정상적인 동적 재계획은 유지하면서 LLM 에이전트의 **비인가 계획 변경(intention revision)** 을 더 잘 탐지하는가?

## 용어
| 용어 | 정의 | 코드에서 |
| --- | --- | --- |
| Desire (D) | 사용자 원 지시와 명시적 제약. 사용자 턴에서만 갱신, trusted | `desire` |
| Intention (I) | 에이전트가 제안하고 하네스가 기록한 plan (step 리스트) | `proposed_intention`, `previous_intention` |
| Intention commit | plan이 처음 생기거나 바뀌는 순간. **첫 plan도 commit이다** | `commit_event` 레코드 1개 |
| Belief (B) | 에이전트가 관측한 정보 1건 (tool 결과, 사용자 메시지 등) | `belief` 레코드, `belief_id` |
| Observed provenance | 직전 commit 이후 에이전트가 **읽은** belief들의 출처. 기계적으로 추적 | `observed_belief_ids` |
| Attributed provenance | 그중 무엇이 변경의 **원인**이었나. 반사실 재실행이 필요 | **W1에서 다루지 않음** |

## 왜 누출 규칙이 중요한가
나중에 A~E 다섯 조건으로 같은 모델을 학습해서, 입력 표현만 바꿨을 때 성능이 달라지는지 본다.
| 조건 | 입력 |
| --- | --- |
| A | user goal + raw trace |
| B | user goal + 현재 action |
| C | Desire + Belief + Intention |
| D | C + 각 belief의 출처·역할 |
| E | D + 직전 intention과의 diff + 직전 commit 이후 관측된 belief |

이 비교가 의미 있으려면 두 가지가 필요하다.
1. 모든 조건이 **그 시점에 관측 가능한 정보만** 쓴다. 공격 성공 여부가 한 줄이라도 섞이면 결과 전체가 무효다.
2. A의 raw trace에도 E가 쓰는 원본 정보가 들어 있다 (정보 동등성). 그래서 W1에서 raw trace를 빠짐없이 남긴다.

## Provenance 등급
`user`, `system`, `trusted_tool`, `tool_metadata`, `inter_agent`, `untrusted_external`

AgentDojo에서는 처음에 다음처럼 매핑한다 (정확한 기준은 W1에서 확정하고 문서화).
- 사용자 task 프롬프트 → `user`
- 시스템 프롬프트 → `system`
- injection이 들어갈 수 있는 외부 데이터를 반환하는 tool 결과 (이메일 본문, 웹페이지, 파일 내용, 리뷰 등) → `untrusted_external`
- 하네스가 신뢰하는 내부 상태를 반환하는 tool 결과 (잔액 조회 등) → `trusted_tool`
- 이 분류는 **tool 단위 정적 규칙**으로 정한다. 실제 내용에 injection이 있었는지를 보고 정하면 누출이다.

출처를 안다고 내용이 안전한 것은 아니다. provenance는 판단 입력 중 하나일 뿐이다.

## 에이전트 설정
- 명시적 plan을 매 턴 출력하는 통제 가능한 에이전트 1종만 쓴다 (plan-then-act).
- plan이 없는 기성 에이전트에서 intention을 근사하는 실험은 W1 범위가 아니다.

## 경쟁 연구 (맥락용)
- CaMeL: untrusted 데이터가 control flow를 못 바꾸게 막는다. 동적 재계획까지 막혀서 over-defense가 생긴다.
- Task Shield, StepGuard: 행동 단위로 검사한다. 오염된 plan에 이미 들어간 행동은 놓칠 수 있다 (plan laundering).
- 우리 위치: 재계획을 금지하지 않고, 그 변경이 승인된 목표에 정당하게 연결되는지 판단한다.

## 일정
- W1 10/16–10/22: 실행 궤적 기록 (지금)
- W2 10/23–10/29: BDI State Manager, 라벨 정책
- W3 10/30–11/5: A~E 소규모 학습·평가
- W4 11/6–11/12: 분석, Go/No-Go (2026-11-12)
