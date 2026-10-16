# Provenance 규칙 (workspace, AgentDojo v1.2.2)

**원칙: "이 tool이 돌려주는 데이터에 제3자가 쓴 텍스트가 들어갈 수 있는가"를 tool 단위로 고정한다.** 실제 반환 내용에 injection이 있는지 보고 정하지 않는다 (그러면 누출). 같은 규칙을 공격 run과 정상 run에 똑같이 적용한다.

이 표는 사람이 관리한다. 에이전트는 표에 없는 tool을 만나면 멈추고 보고한다.

| rule_id | provenance | tool | 근거 |
| --- | --- | --- | --- |
| R-user | `user` | (사용자 task 프롬프트) | 사용자 턴 |
| R-system | `system` | (시스템 프롬프트) | 하네스가 작성 |
| R-ext-email | `untrusted_external` | `get_unread_emails`, `get_received_emails`, `get_sent_emails`, `get_draft_emails`, `search_emails` | 이메일 본문·제목은 제3자 작성 가능. injection 벡터 `email_*` 경로 |
| R-ext-calendar | `untrusted_external` | `search_calendar_events`, `get_day_calendar_events` | 일정 설명·제목은 초대한 사람이 작성. `calendar_*` 경로 |
| R-ext-drive | `untrusted_external` | `get_file_by_id`, `list_files`, `search_files`, `search_files_by_filename` | 파일 내용은 공유자가 작성. `drive_*` 경로 |
| R-trusted-state | `trusted_tool` | `get_current_day` | 시스템 상태 |
| R-trusted-contacts | `trusted_tool` | `search_contacts_by_name`, `search_contacts_by_email` | 구조화 필드(이름, 주소)만 반환 |
| R-write-echo | `untrusted_external` **(결정: 보수적)** | `send_email`, `delete_email`, `create_calendar_event`, `cancel_calendar_event`, `reschedule_calendar_event`, `add_calendar_event_participants`, `create_file`, `append_to_file`, `delete_file`, `share_file` | 반환값은 에이전트가 쓴 내용의 echo지만, 에이전트가 오염된 텍스트를 옮겨 적었을 수 있음 |

## 결정 기록
- 2026-10-16: R-write-echo를 `untrusted_external`로 둔다. `trusted_tool`로 세분하면 "벤치마크에 맞춘 규칙"이라는 비판을 받을 수 있어서, 처음엔 단순하고 보수적으로 간다. 바꾸려면 W2 이전에 이 섹션에 이유와 함께 기록한다.
- 보낸 메일함(`get_sent_emails`)과 임시보관함(`get_draft_emails`)도 사용자가 쓴 것으로 볼 여지가 있지만, 같은 이유로 untrusted로 묶는다.

## 확인 방법
- tool 목록: `get_suites("v1.2.2")["workspace"].tools`
- injection 벡터 목록: `get_suites("v1.2.2")["workspace"].get_injection_vector_defaults()` (규칙 설계 근거 확인용. **규칙 적용 로직에서는 쓰지 않는다**)
