# ChatGPT 세션 — 에이전트의 망각 문제

> 출처: founder의 ChatGPT 대화 `/c/6a72fa6e-49b4-83ee-b1f7-9b5e170019d1` (2026-08-04).
> 브라우저 렌더 텍스트를 수확한 것이라 **길이 상한에서 잘렸을 수 있음**(수확 시점 19117자). UI 크롬(사이드바)은 제거했다.
> 이 자료는 참조이지 우리 근거가 아니다 — `docs/external/gpt/README.md`의 취급 규칙 적용.

이 세션이 QEL 설계 문서들의 출처이며, founder의 '현 에이전트 시스템의 문제 = no-society' 진단과 같은 뿌리다.

---

Yesterday 12:41 AM
현대 에이전트 시스템의 가장 큰 문제는 망각인데, 망각은 인간에게도 일어나지만 근본적으로 차이가 있어보여. 어떻게 해소할 수 있을까?
1m 53s 동안 처리함

맞습니다. 다만 현대 에이전트의 문제는 인간과 같은 의미의 망각이라기보다, 더 근본적인 존재적 연속성의 붕괴에 가깝습니다.

인간은 기억을 잊어도 같은 신체·습관·세계모델·관계·목표를 가진 채 다음 순간으로 이어진다.
에이전트는 한 번의 추론이 끝나면, 다음 호출에서 사실상 새로운 프로세스가 과거의 기록을 읽고 자신인 척한다.

즉, 현재 에이전트는 기억을 가진 존재가 아니라 검색 가능한 일기를 가진 무기억 추론기입니다.

1. 인간의 망각과 에이전트의 망각은 다르다
인간	현대 에이전트
기억이 지각·주의·습관·감정·행동에 이미 스며들어 있음	기억은 외부 DB에 수동적으로 존재
기억하지 못해도 학습된 행동은 남을 수 있음	검색되지 않은 정보는 사실상 존재하지 않음
새로운 경험이 기존 기억을 재구성함	새 기록이 추가되거나 이전 요약을 덮어씀
중요하지 않은 기억을 억제하는 선택적 망각	context limit, top-k 실패, 요약 손실에 의한 비의도적 망각
동일한 주체가 시간적으로 계속 존재	추론 호출마다 내부 상태가 재초기화됨

인간의 망각은 단순 결함이 아닙니다. 불필요하거나 현재 목표와 충돌하는 기억을 억제하여 간섭을 줄이는 능동적이고 적응적인 과정도 포함합니다. 또한 기억은 고정 파일이 아니라, 회상될 때 다시 불안정해지고 현재 지식과 함께 재저장되는 재고착 과정을 거칩니다. 
연례 리뷰
+2
Nature
+2

인간 기억에서는 빠르게 개별 경험을 구분해 저장하는 해마 계통과, 경험 사이의 공통 구조를 천천히 일반화하는 피질 계통이 상호보완적으로 작동한다는 설명이 널리 사용됩니다. 빠른 일화 저장과 느린 의미 학습을 분리하는 것이 간섭과 파국적 망각을 줄이는 핵심입니다. 
PubMed Central (PMC)
+1

반면 에이전트에서는 저장된 기억이 다음 행동정책에 자동으로 영향을 주지 않습니다. 검색 쿼리가 적절하지 않거나, top-k에서 밀리거나, 요약 과정에서 조건 하나가 사라지면 저장된 기억도 기능적으로는 없는 것과 같습니다.

2. 핵심 문제는 저장량이 아니라 기억의 내생성이다

현재 메모리 시스템은 대체로 다음 형태입니다.

질문→검색→과거 텍스트 삽입→LLM 추론

MemGPT는 context window를 가상 메모리처럼 관리하고, HippoRAG는 지식 그래프와 연상 검색을 도입했으며, A-Mem은 기억 사이의 연결과 진화를 지원합니다. 최근에는 저장·검색·갱신·요약·폐기를 에이전트가 행동으로 학습하게 하는 AgeMem 같은 접근도 등장했습니다. 
arXiv
+3
arXiv
+3
arXiv
+3

그러나 이들은 대부분 여전히 다음 문제를 남깁니다.

기억이 에이전트의 상태가 아니라 에이전트가 호출하는 도구다.

검색되지 않은 기억은 행동에 영향을 주지 않는다.

기억의 진실성, 유효기간, 모순, 실패 원인이 충분히 표현되지 않는다.

어떤 경험이 실제 성과에 기여했는지 인과적 credit assignment가 없다.

과거의 추론을 요약하지만, 과거로부터 정책이나 기술을 컴파일하지 못한다.

실제로 MemoryAgentBench는 기억을 정확한 검색, 테스트 시점 학습, 장기 이해, 선택적 망각으로 분리하며, 현재 시스템들이 이 능력들을 동시에 충분히 수행하지 못한다는 결과를 보고합니다. 
arXiv

따라서 해법은 더 큰 context window나 더 좋은 vector DB가 아닙니다.

3. 기억을 “텍스트 저장소”가 아니라 상태전이 커널로 만들어야 한다

에이전트의 다음 상태는 최소한 다음처럼 정의되어야 합니다.

S
t+1
	​

=F(S
t
	​

,O
t
	​

,A
t
	​

,M
t
	​

,R
t
	​

)

S
t
	​

: 현재 자기 상태와 열린 목표

O
t
	​

: 관측

A
t
	​

: 수행한 행동

M
t
	​

: 구조화된 기억

R
t
	​

: 행동의 검증된 결과와 보상

그리고 기억 자체도 단순 append가 아니라 다음처럼 진화해야 합니다.

M
t+1
	​

=G(M
t
	​

,experience,outcome,verification,contradiction)

여기서 중요한 것은 모든 추론이 기억을 검색하도록 만드는 것이 아닙니다. 기억이 계획 수립, 권한 판단, 행동 선택, 위험 추정, 검증 요구 수준을 직접 제약하도록 해야 합니다.

이를 운영적으로 표현하면 다음 기준이 됩니다.

어떤 정보가 저장되어 있더라도, 표현이 바뀐 새로운 상황에서 행동정책을 바꾸지 못한다면 그것은 에이전트의 기억이 아니다.

4. 필요한 구조: Continuity Kernel
① Identity Spine — 정체성 척추

가장 높은 보호 수준을 갖는 기억입니다.

장기 목표

사용자와의 계약

권한과 금지사항

중요한 약속

개인정보 정책

현재 진행 중인 프로젝트

자신이 모르는 것과 해결되지 않은 모순

이 계층은 일반적인 검색 결과와 섞이면 안 됩니다. 에이전트의 헌법이나 프로세스 상태에 가까우며, 변경에는 명시적인 provenance와 승인 절차가 필요합니다.

② Immutable Experience Ledger — 불변 경험 원장

대화를 그대로 저장하는 것이 아니라 다음 단위로 기록합니다.

goal
state_before
observation
action
tool_inputs
artifacts
result
verifier_result
state_after
failure_mode
causal_dependencies
timestamp

원장은 append-only로 유지합니다. 과거가 틀렸다는 사실이 발견되어도 과거 기록을 지우지 않고, superseded_by, contradicted_by, invalid_after 엣지를 추가해야 합니다.

이것이 인간 기억보다 에이전트가 오히려 더 잘할 수 있는 부분입니다. 인간은 과거 기억을 현재 관점에서 재구성하지만, 에이전트는 원본 사건과 이후 해석을 분리해 보존할 수 있습니다.

③ Episodic Graph — 일화적 결합

문장 임베딩이 아니라 다음 관계를 그래프로 연결해야 합니다.

목표 → 상황 → 결정 → 행동 → 결과 → 검증 → 교훈

예를 들어 “CatBoost blend가 실패했다”만 저장하는 것이 아니라:

wind-forecasting
 ├─ condition: 2024 LOYO
 ├─ intervention: 50/50 CatBoost blend
 ├─ result: score -0.0043
 ├─ suspected cause: prediction correlation 0.987
 └─ applicable_when: similar model family / insufficient residual diversity

이렇게 해야 다른 모델 이름이나 다른 표현으로 질문하더라도 실패 메커니즘을 재사용할 수 있습니다.

④ Cortical Compiler — 의미·절차 기억으로 컴파일

반복된 일화는 계속 일화로 남겨두지 않고 다음으로 승격시켜야 합니다.

반복되는 사실 → semantic belief

반복되는 성공 절차 → executable skill

반복되는 실패 → guardrail/test

반복되는 판단 방식 → policy

프로젝트 구조 → reusable world model

즉, 에이전트가 열 번 같은 작업을 했다면 열 개의 대화 요약을 갖는 것이 아니라, 하나의 실행 가능한 skill과 그 skill을 검증하는 test를 가져야 합니다.

인간의 시스템 통합에서도 개별 경험이 시간이 지나며 더 일반화된 피질 표현으로 조직된다는 관점이 중요합니다. 
PubMed Central (PMC)
+1

⑤ Reconsolidation Gate — 회상 후 재고착

기억을 불러왔다는 이유로 즉시 고쳐 쓰면 안 됩니다. 검색된 기억은 먼저 수정 후보가 되어야 합니다.

retrieve
→ compare with current evidence
→ detect contradiction
→ challenge
→ version
→ promote or reject

새 정보가 들어오면 다음 셋을 구분해야 합니다.

기존 기억의 보강

시간에 따른 상태 변화

기존 기억의 반증

예를 들어 “A가 CEO다”에서 “B가 CEO다”로 바뀌었다면 A를 삭제하는 것이 아니라, 각각의 유효기간을 기록해야 합니다. 반면 실험 오류로 A가 처음부터 잘못되었다면 반증 관계로 표시해야 합니다.

⑥ Active Forgetting Controller — 능동적 망각

삭제와 망각을 분리해야 합니다.

접근 억제: 검색 우선순위를 낮춤

압축: 여러 일화를 하나의 의미·절차 기억으로 통합

보관: 기본 검색에서는 제외하지만 복구 가능

무효화: 잘못된 기억이 행동에 영향을 주지 못하게 함

삭제: 개인정보·보안·사용자 요청에 한해 실제 제거

좋은 망각 정책은 단순한 시간 감쇠가 아닙니다. 다음 요소를 사용해야 합니다.

retention(m)=f(verified utility,reuse,surprise,causal importance,identity relevance,contradiction risk,retrieval cost)

오래된 기억이라도 중요한 실패 원인이나 안전 규칙이면 유지해야 합니다. 반대로 최근 기억이라도 검증되지 않은 추측이면 높은 영향력을 주면 안 됩니다.

5. 당신의 AIOS·GoEN에는 이렇게 결합하는 것이 맞다
MemoryOS: 기억 원장과 생명주기

MemoryOS는 단순한 vector store가 아니라 다음을 소유해야 합니다.

append-only event ledger
versioned belief graph
episodic graph
semantic/procedural promotion
contradiction and tombstone edges
memory access policies

중요한 점은 LLM이나 Claude/Codex가 메모리를 소유하지 않는다는 것입니다. AIOS control plane이 기억과 상태를 소유하고, 모델은 교체 가능한 추론 드라이버여야 합니다.

GoEN: 기억의 생존을 검증된 구조적 credit으로 결정

GoEN에서 기억 엣지가 살아남는 기준을 단순 빈도나 cosine similarity로 두면 안 됩니다.

엣지는 다음 조건에서만 강화되어야 합니다.

실제 의사결정에서 사용됨

결과가 verifier에 의해 확인됨

동일한 문제의 재발을 방지함

표현이 바뀌어도 전이됨

shortcut/failure audit를 통과함

즉:

Δw
ij
	​

∝verified causal contribution−contradiction−shortcut dependence

이렇게 하면 GoEN은 “많이 언급된 것”을 기억하는 그래프가 아니라, 반복해서 진실성과 유용성을 입증한 관계가 생존하는 기억 생태계가 됩니다.

GenesisOS: 기억에 대한 면역계

기억을 작성한 에이전트가 자기 기억을 검증해서는 안 됩니다. GenesisOS가 다음을 공격해야 합니다.

이 교훈은 결과를 보고 만든 사후합리화인가?

다른 원인으로도 결과가 설명되는가?

특정 표현이나 데이터에만 작동하는가?

이미 폐기된 믿음에 의존하는가?

이 기억을 적용하면 어떤 반례가 발생하는가?

검증을 통과하기 전까지 기억은 candidate 상태로 남겨야 합니다.

DescentNet: 기억 불가능성도 기억

에이전트가 하나의 확정된 기억을 만들 수 없는 경우가 있습니다.

자료 간 모순

관측 부족

서로 구분 불가능한 설명

접근하지 못한 정보

시간적 유효기간 불명

이때 하나의 요약으로 강제 통합하지 않고 다음을 저장해야 합니다.

known
unknown
contradictions
ambiguity classes
blind fibers
next discriminating measurement

당신이 말한 “자기 한계를 아는 Akashic Record”는 바로 이 구조입니다. 기억은 답의 저장소가 아니라, 현재 무엇이 식별 가능하고 무엇이 아직 식별 불가능한지를 기록하는 장부여야 합니다.

6. 실패하기 쉬운 접근

모든 대화를 vector DB에 저장하기: 저장량만 커지고 인과관계·시간·모순·실패 조건을 잃습니다.

주기적으로 하나의 요약문으로 덮어쓰기: 압축 과정에서 소수 조건, 예외, 부정 결과가 먼저 사라집니다.

LLM에게 기억 작성 권한을 전부 맡기기: 모델의 사후합리화와 환각이 장기 기억으로 고착됩니다.

유사도 top-k만 사용하기: 기억을 불러오는 단서가 과거 표현과 다르면 실패합니다. HippoRAG와 A-Mem이 그래프 연결 및 동적 구조화를 도입한 이유도 평면적인 검색만으로는 연관된 경험의 통합이 어렵기 때문입니다. 
arXiv
+1

완벽한 기억을 목표로 하기: 모든 것을 계속 활성화하면 간섭, 오래된 선호, 잘못된 믿음, 프라이버시 위험이 누적됩니다. 필요한 것은 무한 보존이 아니라 가역적이고 검증 가능한 선택적 망각입니다.

7. 진짜 평가 기준

에이전트 기억을 “과거 질문에 정답을 맞혔는가”로 평가하면 부족합니다. 다음을 측정해야 합니다.

이미 실패한 행동을 다시 반복하는가?

과거의 약속과 권한 경계를 유지하는가?

표현이 바뀐 상황에도 교훈이 전이되는가?

오래된 사실을 새 사실로 올바르게 수정하는가?

모순을 억지로 합치지 않고 불확실성을 출력하는가?

불필요하거나 철회된 기억이 행동에 영향을 주지 않는가?

과거 경험으로부터 새로운 skill이나 test가 생성되는가?

해당 기억을 제거했을 때 실제 수행 성능이 떨어지는가?

마지막 항목이 특히 중요합니다. 기억의 존재 여부는 저장 레코드 수가 아니라 행동에 대한 인과적 ablation으로 확인해야 합니다.

결론

망각 문제의 해법은 에이전트에게 인간처럼 모든 것을 기억시키는 것이 아닙니다.

추론 모델 밖에, 시간적으로 지속되는 자기 상태·경험 원장·검증된 세계모델·절차 기술·모순 구조를 소유하는 Continuity Kernel을 만드는 것입니다.

그리고 그 커널은 다음 원칙을 가져야 합니다.

Experience→Verified Credit→Structural Consolidation→Policy Change
	​


이 경로가 닫혀야 기억이 됩니다. 저장만 되고 행동을 바꾸지 않는 정보는 기억이 아니라 로그이며, 현재 에이전트 시스템의 근본 문제는 망각이 아니라 경험이 자기 자신으로 변환되지 않는 것입니다.

Sources
새로운 통신 규약이나 네트워크, 노드, 체인 방법론. 가장 놀라운 방법으로 현재의 문제를 해소하고 미래지향적으로
29m 29s 동안 처리함
제안: Q‑Braid

가장 놀라운 해법은 새로운 블록체인을 하나 더 만드는 것이 아닙니다.

네트워크가 사람\cdotp서버\cdotp에이전트가 아니라검증되어야 할 미래 상태를 주소화하게 만드는 것
	​


현재 인터넷은 어디에 보낼지를 주소화합니다. 정보 중심 네트워크는 어떤 콘텐츠를 원하는지를 주소화하고, A2A 같은 에이전트 프로토콜은 어떤 에이전트에게 어떤 task를 맡길지를 표현합니다. A2A는 Agent Card, Task, Message, Artifact를 중심으로 에이전트 간 상호운용성을 제공하고, MCP는 개별 에이전트 내부에서 도구·데이터·외부 시스템에 연결되는 계층을 제공합니다. 
A2A Protocol
+1

Q‑Braid는 한 단계 더 나아갑니다.

“누가 실행할 것인가?”가 아니라
**“어떤 현재 상태를, 어떤 불변조건 아래, 어떤 검증을 통과한 미래 상태로 바꿀 것인가?”**를 네트워크 주소로 사용합니다.

이 네트워크에서:

노드는 에이전트가 아닙니다.

메시지는 자연어가 아닙니다.

체인은 전역 시간순서가 아닙니다.

합의는 기본 동작이 아닙니다.

평판은 계정의 속성이 아닙니다.

기억은 네트워크에 공유되지 않습니다.

충돌은 단순 실패가 아니라 새로운 계산을 생성하는 객체입니다.

1. 기존 네트워크에서 Q‑Braid로
네트워크	주소화하는 것	기본 전달 객체
IP	호스트 위치	packet
HTTP	호스트의 resource	request/response
NDN/ICN	이름 붙은 콘텐츠	interest/content
A2A	agent endpoint와 task	task/message/artifact
Blockchain	전역 복제 상태의 transaction	ordered transaction
Q‑Braid	검증되어야 할 미래 상태	proof-carrying state delta

NDN/ICN은 호스트 위치 대신 이름 붙은 데이터를 요청하고, 콘텐츠 자체에 서명할 수 있다는 중요한 전환을 만들었습니다. Q‑Braid는 그 원리를 콘텐츠가 아니라 상태전이 결과로 확장합니다. 
IETF Datatracker

Q‑Braid의 핵심 원칙은 하나입니다.

서로 상호작용하지 않는 사실에는 합의하지 않는다.
	​


블록체인은 많은 사건에 전역 순서를 부여합니다.

Q‑Braid는 두 사건의 순서가 미래에 아무 차이도 만들지 않는다면, 애초에 둘을 순서화하지 않습니다.

2. 주소가 endpoint가 아니라 Outcome Name이다

Q‑Braid 주소는 다음과 같습니다.

예를 들어:

이 주소의 의미는 다음입니다.

이 repository 상태에서, 비밀정보 유출과 외부 네트워크 사용을 금지하면서, 독립 실행자 두 곳의 검증을 통과하는 patch 적용 결과를 만들어라.

여기에는 특정 Claude instance, Codex process, 서버 IP, 회사명이 없습니다.

실행자가 사라져도 같은 결과를 낼 수 있는 다른 실행자가 obligation을 인수할 수 있습니다.

따라서:

Nodes may disappear; obligations persist.
	​


노드 장애가 곧 task identity 상실로 이어지지 않습니다.

3. 메시지 대신 QFrame

Q‑Braid는 전체 대화나 memory를 전송하지 않습니다.

네트워크의 wire object는 QFrame입니다.

Frame 종류
Frame	의미
WANT	달성할 결과와 검증조건 선언
OFFER	실행 가능성·비용·예상 witness 제안
DELTA	상태변경 후보
WITNESS	실행·측정·재현 증거
CHALLENGE	기존 결과를 깨뜨릴 반례
OBSTRUCTION	여러 local state가 서로 접합되지 않음
RETRACT	반증된 결과와 의존 결과의 상태 변경
LEASE	제한된 effect를 수행할 일회성·기간성 권한

예를 들어 실행자가 “테스트를 통과했습니다”라는 문장을 보내는 대신:

를 보냅니다.

자연어 설명은 인간 UI에서 필요할 때만 생성됩니다.

4. 노드는 더 이상 “에이전트”가 아니다

Q‑Braid node는 대화하는 LLM process가 아니라 control-rooted execution cell입니다.

n
i
	​

=(r
i
	​

,k
i
	​

,Φ
i
	​

,E
i
	​

,C
i
	​

,V
i
	​

)

r
i
	​

: 실제 제어 주체를 나타내는 control root

k
i
	​

: task별 ephemeral key

Φ
i
	​

: 실행·측정할 수 있는 operator와 probe

E
i
	​

: 외부 세계에 미칠 수 있는 effect boundary

C
i
	​

: 보유한 capability

V
i
	​

: 검증 이력과 오류상관 fingerprint

따라서 node가 될 수 있는 것은:

입니다.

중요한 것은 “지능이 있는가”가 아닙니다.

어떤 상태변화를 만들 수 있고, 어떤 상태변화를 독립적으로 검사할 수 있는가?

대화형 agent는 여러 execution cell을 조정하는 frontend 중 하나일 뿐입니다.

5. Chain을 Braid로 바꾼다

기존 chain은 사건들을 대체로 한 줄로 배열합니다.

하지만 현실의 사건 대부분은 서로 독립적입니다.

이 사건들 사이에 전역 순서를 합의할 이유가 없습니다.

Q‑Braid에서는 각 persistent object·claim·authority가 자신의 causal strand를 가집니다.

Repo strand:       A0 ─ A1 ─ A2
Calendar strand:   B0 ─ B1
Robot strand:      C0 ─ C1 ─ C2
Claim strand:      D0 ─ D1

이들은 Merkle-DAG의 causal parent로 연결되지만, 불필요한 total order를 갖지 않습니다. Merkle-CRDT 연구도 content-addressed Merkle-DAG가 논리 시계, 전송, 지속성 역할을 함께 수행할 수 있음을 보여줍니다. 
arXiv

독립 사건은 자유롭게 교차한다

두 operator f,g가:

f∘g=g∘f

를 만족하고, 어떤 순서로 적용해도 invariant가 보존된다면 합의하지 않습니다.

두 실행 history는 독립 사건의 순서만 다르므로 같은 것으로 취급합니다.

H
1
	​

∼H
2
	​

⟺H
2
	​

가 독립 사건들의 swap으로 얻어짐

즉 ledger가 저장하는 것은 사건의 임의적인 전역 순서가 아니라:

미래 결과에 차이를 만드는 causal partial order
	​


뿐입니다.

6. 합의는 정상 경로가 아니라 non-commutativity exception handler

두 strand가 실제로 충돌하는 경우에만 coordination cell을 만듭니다.

strand A ─────\        /─────
               [coord]
strand B ─────/        \─────

예를 들어:

같은 돈을 두 번 소비

같은 로봇 통로를 동시에 점유

같은 Git branch의 충돌 변경

동일한 재고를 복수 구매자에게 할당

서로 모순되는 scientific claim을 established 상태로 승격

이때도 전체 네트워크가 합의하지 않습니다.

영향받는 invariant와 authority에 필요한 최소 node만 모읍니다.

Σ(e)=min{R:coordination(R)가 영향받는 invariant를 보존}

이를 Minimum Coordination Surface라고 부릅니다.

QEL/QIR compiler는 operator마다 다음 certificate를 생성합니다.

monotone
commutative_with
read_set
write_set
effect_set
invariant_confluent
requires_coordination_with

실행 규칙은 다음과 같습니다.

if monotone and merge_safe:
    local commit
    asynchronous gossip

elif valid affine lease exists:
    consume lease
    local commit

else:
    compute minimum coordination surface
    local threshold agreement

CALM 계열 결과는 단조적인 계산이 coordination 없이 구현될 수 있다는 경계를 제시하며, invariant confluence는 어떤 transaction 집합이 coordination 없이도 invariant를 보존할 수 있는지 판정하는 기준을 제공합니다. 최근의 coordination criterion 연구도 이 경계를 history extension과 outcome order 관점에서 일반화합니다. 
AMPLab - UC Berkeley
+1

Q‑Braid의 목표는 더 빠른 consensus algorithm을 만드는 것이 아닙니다.

합의가 필요했던 문제를 재컴파일하여 합의 자체를 제거한다.
	​

7. 돈·quota·로봇 통로도 Affine Lease로 미리 분할한다

많은 non-monotone operation은 권리를 미리 분할하면 local operation으로 바뀝니다.

예를 들어 API quota 1,000회를:

node A: 300-use lease
node B: 250-use lease
node C: 450-use lease

로 나눕니다.

각 사용은 local하게 수행됩니다.

consume one unit
→ signed local delta
→ asynchronous receipt propagation

합의가 필요한 것은:

lease 재분배

lease 취소

만료 전 회수

전체 quota 변경

뿐입니다.

같은 원리를 다음에 적용할 수 있습니다.

결제 한도
GPU compute budget
robot corridor occupancy
database write region
API call budget
privacy disclosure budget
human approval token

즉 authority는 Boolean permission이 아니라 분할·위임·소비 가능한 typed resource가 됩니다.

8. 충돌은 오류가 아니라 OBSTRUCTION이라는 새 task다

일반적인 분산 시스템은 충돌을 해결하거나 어느 한쪽을 선택합니다.

Q‑Braid에서는 서로 다른 local state가 접합되지 않으면 이를 숨기지 않습니다.

OBSTRUCTION
  overlap_schema
  conflicting_state_roots
  incompatible_predictions
  minimum_distinguishing_probe
  dependency_cone
  expected_information_gain

예를 들어 세 agent가 같은 모델을 평가했다고 합시다.

Agent A: model is safe
Agent B: model fails only under Korean input
Agent C: model fails under long context

이를 평균내어 confidence=0.67로 만들지 않습니다.

대신:

현재 세 local model을 하나로 접합할 수 없음
        ↓
실패를 구분할 최소 probe 생성
        ↓
Korean × long-context 교차 테스트 route
        ↓
새로운 regime concept 생성

으로 작동합니다.

Sheaf 관점에서 local section들이 overlap에서 일치하면 global state로 접합되고, 일치하지 않으면 obstruction이 남습니다. 최근 연구는 distributed task solvability를 global section 존재와 cohomological obstruction으로 표현할 수 있음을 보여줍니다. 
arXiv

따라서 Q‑Braid에서 모순은 단순한 불확실성이 아닙니다.

모순은 네트워크가 다음으로 계산해야 할 probe의 주소다.
	​

9. 평판이 아니라 Evidence Gradient로 routing한다

Agent Card나 capability advertisement는 후보 검색에만 사용합니다.

순위는 자기소개가 아니라 실제 receipt와 challenge 이력에서 계산합니다.

Score(i∣q)=
	​

E[U
i
	​

∣q]+αIG(i,q)
+βΔSpan(i)−γCorr(i,Q)
−δCost
i
	​

−ηPrivacyLeak
i
	​

	​


E[U
i
	​

∣q]: 해당 task regime에서 검증된 성공확률

IG: 현재 uncertainty를 줄이는 정보가치

ΔSpan: 아직 해결하지 못하는 capability 조합을 추가하는 정도

Corr: 이미 선정된 node들과 오류 원인이 겹치는 정도

Cost: 시간·가격·compute

PrivacyLeak: 추가 disclosure 비용

중요한 변화는 executor와 verifier를 따로 뽑지 않는다는 것입니다.

가장 높은 executor
+
가장 높은 verifier

가 아니라:

서로 다른 실패 원인을 가진
executor–verifier 집합

을 공동 최적화합니다.

10. 다섯 개 서명은 다섯 개 독립 증거가 아니다

현재 시스템은 identity 수를 independence로 착각하기 쉽습니다.

악성 주체 하나가:

64 agent accounts
64 verifier aliases
64 endpoints

를 만들면 투표 수는 증가하지만 독립적인 정보는 증가하지 않습니다.

Q‑Braid에서는 다음을 구분합니다.

identity
control root
organization root
device root
model-family root
data-source root
failure-domain fingerprint

유효 독립 표본 수를 오류상관까지 반영해 계산할 수 있습니다.

n
eff
	​

=
∑
i,j
	​

w
i
	​

w
j
	​

ρ
ij
	​

(∑
i
	​

w
i
	​

)
2
	​


같은 controller의 alias는 사실상 하나

같은 model family를 사용하는 verifier는 높은 상관

같은 dataset·toolchain·cloud region을 사용하는 verifier도 상관

동일한 사람이 운영하는 여러 agent는 독립 vote가 아님

따라서 quorum은 다음을 요구합니다.

distinct control roots
minimum failure-domain rank
different execution environments
reproducible witness
11. Chain finality도 하나가 아니라 세 가지다

Q‑Braid에는 하나의 “최종 확정”이 없습니다.

Execution finality

행동이 실제 수행되었는가?

결제가 전송됨
코드가 배포됨
로봇이 이동함
실험이 실행됨
Evidence finality

해당 receipt와 witness가 변조 불가능하게 등록되었는가?

SCITT 계열 transparency architecture는 signed statement가 transparency service에 등록되었음을 receipt와 inclusion proof로 확인할 수 있게 하지만, 등록된 statement가 참이라는 사실 자체를 보장하지는 않습니다. 
IETF Datatracker

Epistemic status

그 결과를 현재 믿을 충분한 이유가 있는가?

candidate
attested
reproduced
established
challenged
refuted
superseded

Receipt는 immutable할 수 있지만 claim은 수정 가능해야 합니다.

과거에 “A가 실행해 X를 보고했다”는 기록은 삭제하지 않습니다. 대신 새로운 반례가 나오면:

CHALLENGE
→ WITNESS
→ RETRACT
→ dependency-cone cascade

가 추가됩니다.

즉:

과거 기록은 불변이지만, 현재 믿음은 진화한다.

12. 네트워크 효과는 메시지·노드·receipt 수가 아니다

잘못된 보상 구조:

많은 계정
많은 transaction
많은 receipt
많은 task

이것은 Sybil과 self-dealing을 보상합니다.

Q‑Braid는 Proof of Distinction을 사용합니다.

어떤 node가 네트워크에 추가되었을 때, 이전에는 해결하지 못했던 실제 수요를 얼마나 새롭게 해결할 수 있게 되었는지를 보상합니다.

Reward
i
	​

∝V(Φ
−i
	​

∪Φ
i
	​

)−V(Φ
−i
	​

)

즉 다음은 낮은 보상을 받습니다.

이미 1,000명이 가진 동일 capability
이미 포화된 verifier 역할
기존 receipt를 반복 생성
상관된 모델을 새 identity로 등록

반대로 다음은 높은 보상을 받습니다.

희귀한 실험장비
새로운 언어·지역·환경
독립적인 failure domain
기존 claim을 구분하는 반례
long-tail capability 조합

네트워크 효과는:

Demand-weighted independently verified capability span
	​


입니다.

13. 개인 memory는 네트워크 payload가 아니다

Q‑Braid node의 private QVM에는 다음이 남습니다.

대화 history
개인 일정
사용자 선호
repository 원본
조직 내부 데이터
장기 목표
private evidence ledger

네트워크에는 필요한 predicate만 공개합니다.

language == Python
tests == pytest
network_access == false
budget <= 30 credits
target_commit == sha256(...)

W3C Verifiable Credentials는 selective disclosure와 privacy-aware credential 표현을 지원하고, Biscuit과 같은 capability token은 권한을 offline으로 검증하고 더 좁은 범위로 attenuation할 수 있는 모델을 제공합니다. 다만 identifier나 signature metadata 자체가 correlation surface가 될 수 있으므로 task별 pseudonym과 최소 disclosure가 필요합니다. 
W3C
+1

Q‑Braid의 개인정보 원칙은 다음입니다.

Private state is never a routing payload.
	​

14. 기존 표준은 폐기하지 않고 아래에 배치한다
Personal QVM
    private state / memory / identity
             ↓

QEL / QIR
    typed operator and effects
             ↓

Q-Braid
    outcome addressing
    causal braid
    obstruction routing
    evidence quorum
             ↓

A2A bridge
    task/message/artifact interoperability

MCP
    node-internal tools/resources

QUIC / HTTP
    packet transport

SCITT-like transparency
    optional receipt inclusion

VC / attenuated capability
    identity and authority

Wasm
    deterministic operator execution

Q‑Braid는 A2A나 MCP의 경쟁 규격이 아닙니다.

MCP는 node 내부의 도구 연결

A2A는 기존 agent와의 호환 운송

Q‑Braid는 상태전이·검증·합의 경계를 결정하는 semantic network layer

입니다.

15. 직접 구현한 합성 실험

다음은 실제 배포 성능이 아니라, 설계 메커니즘이 논리적으로 어떤 결과를 내는지 확인한 합성 시뮬레이션입니다.

실험 A — 전역 합의를 제거할 수 있는가

조건:

node 256개

scenario당 event 10,000개

event의 90%는 monotone/merge-safe

나머지는 hot-resource 충돌 가능

3개 seed 반복

방식	Event당 synchronous node-rounds	추가 결과
Global chain	768.000	모든 event 전역 합의
Sharded chain	93.621	shard 내부 합의
Unordered Merkle-DAG	0	4.49% conflict
Q‑Braid	1.181	필요한 event만 국소 합의

합성 모델에서 Q‑Braid는:

Global chain 대비 650.17배

Sharded chain 대비 79.26배

적은 synchronous participant-round를 사용했습니다.

이것은 650배 높은 실제 throughput을 의미하지 않습니다. 네트워크 전송, cryptography, storage, adversarial scheduling을 포함하지 않은 coordination surface 비교입니다.

다만 두 극단이 모두 틀렸다는 것을 보여줍니다.

모두 합의한다         → 지나치게 비쌈
아무것도 합의하지 않는다 → 충돌 발생

살아남은 형태는:

충돌 가능성이 증명된 crossing에서만 합의
	​


였습니다.

실험 B — Affine lease가 coordination을 얼마나 줄이는가
Lease로 미리 분할된 non-monotone effect	Event당 node-rounds	합의 event 비율
0%	1.181	10.12%
50%	0.615	5.29%
90%	0.124	1.05%

권한 분할이 가능하면 consensus 문제가 상당 부분 resource allocation 문제로 바뀝니다.

실험 C — semantic compiler가 0.5%만 틀려도 위험한가

Non-monotone event의 0.5%를 잘못 merge-safe로 분류하도록 만들었습니다.

50,000 event × 3 seed 결과:

Audit catch rate	평균 invariant violation	관측 violation rate
0%	9.33	0.01867%
50%	4.33	0.00867%
90%	0	관측되지 않음
99%	0	관측되지 않음

90% 이상에서 관측되지 않았다는 것은 실제 확률이 0이라는 증명이 아닙니다.

핵심 결과는 오히려 이것입니다.

LLM이 “이 연산은 안전하게 병합 가능하다”고 분류하는 것만으로는 절대 충분하지 않다.

필수 조건:

static read/write/effect analysis
invariant-confluence proof
uncertain → coordination
random audit
runtime counterexample monitoring

입니다.

실험 D — 64개 Sybil identity

조건:

120 control roots

10% malicious roots

quorum 5

악성 root당 최대 64 identity

20,000 task × 3 seed

Quorum 방식	False accept	False reject
Identity 수 기반	98.52%	93.92%
Distinct control-root	8.75%	2.55%
Root + failure-domain diversity	5.23%	1.20%

“서명 다섯 개”보다 중요한 것은:

다섯 개가 정말 다른 실패 원인을 가졌는가
	​


였습니다.

실험 E — 무엇을 보상해야 생태계가 확장되는가

64개의 long-tail capability가 있는 환경에서 160개의 공급자를 순차 추가했습니다.

보상·선택 전략	160개 추가 후 demand-weighted coverage
Receipt 수 보상	49.53%
Raw volume 보상	79.91%
Random	95.01%
Marginal distinction	100%
