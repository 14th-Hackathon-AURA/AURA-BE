# MCM 케어 서비스 백엔드 시작점

와이어프레임의 회원·AI 챗·방문 준비·디지털 클로젯·제품 등록/상세·케어 가이드/진단/이력/결과·AS/매장·커뮤니티 흐름을 기준으로 만든 Django REST API 골격이다.

## 공평한 역할 분담

| 담당 | 도메인과 화면 | 핵심 API / 책임 |
|---|---|---|
| Backend 1 — 사용자 경험·소통 | 회원가입/로그인, 온보딩, 홈 피드, 알림, AI 챗봇/상담, 방문 카드·방문 준비, 커뮤니티, 설정 | JWT·Profile·Notification·VisitRequest·Post/Comment·ChatSession. 챗봇은 대화 저장, 권한, RAG 문서 검색을 맡는다. |
| Backend 2 — 제품 자산·케어 AI | 디지털 클로젯, 제품 등록/상세, 디지털 패스포트, 케어 가이드, 사진 진단, 진단 이력/결과, AI 케어 추천, 전문가/AS·매장 | Product·Passport·Diagnosis·CarePlan·Store/ServiceRequest. 이미지 업로드/저장, 비동기 진단 작업, 추천 결과의 버전/근거 저장을 맡는다. |
| 공동 (첫 1일) | ERD/API 계약, 공통 예외 형식, 배포/환경변수, CI | API 명세(OpenAPI), `User.id`/JWT, 파일 업로드 규칙, 코드 리뷰. 운영 계정·DB·배포 권한은 함께 관리한다. |

이렇게 배정하면 Backend 1은 인증·커뮤니티·챗봇(RAG)을, Backend 2는 제품 CRUD·미디어·컴퓨터비전·추천을 가져가므로 단순 화면 수가 아닌 구현 난이도까지 균형이 맞는다. `Product`와 `Diagnosis`는 Backend 2 소유이며, Backend 1은 공개된 API만 호출한다.

## 현재 포함된 API

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/auth/register/` | 회원 생성 |
| POST | `/api/auth/token/` | JWT access/refresh 발급 |
| GET/PATCH | `/api/me/` | 온보딩/프로필 |
| CRUD | `/api/products/` | 내 디지털 클로젯·제품 등록 |
| CRUD | `/api/diagnoses/` | 제품 사진 진단 요청/이력 |
| CRUD | `/api/posts/` | 커뮤니티 게시글 |
| POST | `/api/ai/chat/` | 케어 챗봇 |
| POST | `/api/ai/care-recommendations/` | 완료 진단을 근거로 한 추천 |

`POST /api/diagnoses/`는 `multipart/form-data`로 `product`, `image`를 보내면 된다. 실제 서비스에서는 생성 직후 Celery 큐에 진단 작업을 넣고, 작업 완료 시 `status=DONE`, `result={damage_type, severity, confidence, evidence}`로 갱신한다.

## 로컬 실행

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations accounts catalog care community
python manage.py migrate
python manage.py runserver
```

## AI 구현 순서 — '학습'부터 시작하지 않기

1. **MVP:** 이미지 진단은 사람 검수 또는 규칙 기반 체크리스트로 결과 JSON을 만들고, LLM은 그 결과와 공식 케어 가이드만 받아 설명한다. 이 저장소의 `apps/ai/views.py`가 이 단계다. API 키가 없으면 데모 응답을 내므로 프론트 연결도 가능하다.
2. **RAG 챗봇:** 소재별 공식 관리 문서, AS 정책, FAQ를 작은 문서 조각으로 쪼개 임베딩 DB(pgvector 등)에 저장한다. 질문마다 상위 3~5개 문서만 검색해 프롬프트에 붙이고, 답변에는 문서 ID를 함께 저장한다. 이는 모델 재학습보다 빠르고 정책 변경도 안전하다.
3. **사진 진단 데이터:** 사용자 동의를 받은 이미지에 `정상/스크래치/오염/변색/마모`, 부위(bag, handle, corner 등), 심각도(1~3), 검수자, 라벨 버전을 남긴다. 최소 수백 장/클래스의 검수 라벨과 별도 검증·테스트 세트를 준비한다. 클래스 불균형, 조명/배경 편향을 먼저 점검한다.
4. **비전 모델:** 초기에는 사전학습 객체 탐지/분류 모델을 전이학습한다. F1, recall(손상을 놓치지 않는 정도), 오탐률을 사람 검수 기준과 비교한다. confidence가 낮으면 자동 결론 대신 “전문가 확인 필요”로 라우팅한다.
5. **운영:** 원본 사진 접근권한·보존기간·삭제 요청, 모델/프롬프트 버전, 입력/출력 감사 로그, 편향/성능 재평가를 필수로 둔다. 사용자 사진으로 외부 모델을 학습시키려면 별도 명시 동의를 받아야 한다.

## 배포 체크리스트

- PostgreSQL로 전환하고 `DB_ENGINE`, `DB_NAME` 등 DB 환경변수를 실제 값으로 설정한다. 미디어는 로컬 디스크 대신 S3 호환 스토리지에 둔다.
- `DEBUG=false`, 긴 무작위 `DJANGO_SECRET_KEY`, 정확한 `ALLOWED_HOSTS`와 `CORS_ALLOWED_ORIGINS`를 설정한다.
- HTTPS, 정적 파일 수집(`collectstatic`), DB migration, 관리자 계정, 에러 모니터링을 릴리스 절차에 포함한다.
- Docker는 `docker compose up --build`로 시작할 수 있다. 프로덕션에서는 서비스 시작 시 매번 migration하는 대신 CI/CD 배포 단계에서 한 번만 실행한다.


## 구현 된 부분 


| 영역 | 구현된 기능 | 상태 |
|---|---|---|
| `accounts` | 회원가입, JWT 로그인/토큰 재발급, 프로필 조회·수정 | 구현됨 |
| `accounts` | 온보딩 완료 여부, 선호 카테고리, 마케팅 동의, 프로필 이미지 필드 | 구현됨 |
| `accounts` | 알림 모델·알림 목록·읽음 처리 API | 구현됨 |
| `catalog` | 제품 등록·목록·상세·수정·삭제 | 구현됨 |
| `catalog` | 디지털 클로젯용 제품 정보, 브랜드, 카테고리, 구매일, 패스포트 코드 | 구현됨 |
| `catalog` | 제품 이미지·영수증 업로드 구조 | 구현됨 |
| `catalog` | 케어 가이드 북마크 | 구현됨 |
| `care` | 진단 사진 업로드·진단 이력 저장 | 구현됨 |
| `care` | 케어 가이드 조회 | 구현됨 |
| `care` | 매장 조회 | 구현됨 |
| `care` | 방문 예약·예약 번호 생성·예약 목록 | 구현됨 |
| `care` | AS 접수·상태 저장·접수 목록 | 구현됨 |
| `community` | 게시글 등록·목록·상세·수정·삭제 | 구현됨 |
| `community` | 댓글 작성·목록·삭제 | 구현됨 |
| `community` | 게시글 좋아요 구조·좋아요 수 조회 | 구현됨 |
| `ai` | AI 채팅방 생성, 메시지 저장, 이전 채팅 조회 | 구현됨 |
| `ai` | API 키가 있을 때 LLM 호출, 키가 없을 때 데모 응답 | 구현됨 |
| 공통 | JWT 인증, 본인 제품/진단/예약/AS 이력만 조회하도록 기본 분리 | 구현됨 |
| 공통 | Dockerfile, docker-compose 기본 골격 | 구현됨 |


## 아직 구현되지 않았고 + 추가 작업이 필요한 부분 

| 영역 | 미구현/보완 항목 | 이유 |
|---|---|---|
| CV 사진 진단 | 실제 사진 손상 분석 | 현재 사진은 업로드되어 `PENDING` 진단 이력만 생성됨 |
| CV 사진 진단 | `PENDING → DONE` 자동 전환 | 비전 AI 호출 또는 YOLO/ViT 모델 추론 작업 필요 |
| CV 사진 진단 | 손상 부위 박스 표시, heatmap 등 | 객체 탐지 모델 또는 이미지 분석 결과 좌표 필요 |
| AI 챗봇 | 실제 API 키 설정 | 현재는 키가 없어서 데모 답변이 나오는 상태 |
| AI 챗봇 | RAG: MCM 케어 가이드/FAQ 기반 답변 | 문서 임베딩·벡터 DB 검색 필요 |
| 케어 가이드 | 관리자용 가이드 등록·수정 API | 현재는 사용자 조회 전용 |
| 매장 | 지도 API, 거리순 검색, 지역/매장 검색 | 매장 기본 조회만 구현 |
| 방문 예약 | 시간대 중복 방지, 예약 가능 시간 조회 | 현재는 예약 생성만 가능 |
| 방문 예약 | QR 코드 이미지 생성 | 예약 번호만 생성 |
| AS | 담당자용 상태 변경 API, 예상 비용·완료일 | 사용자 접수/조회 중심 |
| 알림 | 진단 완료·예약·AS 상태 변경 시 자동 알림 생성 | 알림 데이터 구조만 존재 |
| 커뮤니티 | 댓글 수정 권한 제한, 게시글/댓글 신고 | 일부 권한 보완 필요 |
| 커뮤니티 | 다중 이미지, 검색, 정렬, 페이지네이션 | 기본 CRUD 중심 |
| 제품 | OCR 영수증 분석, 바코드/정품 자동 검증 | 이미지 업로드만 구현 |
| 마이페이지 | 내 제품·예약·AS·게시글을 한 API로 모은 대시보드 | 각 API를 따로 호출해야 함 |
| 배포 | PostgreSQL, S3 이미지 저장, HTTPS, CI/CD | Docker 기본 골격만 있음 |
| 테스트 | catalog 제품 등록 성공 | 이전 Postman 테스트는 401/URL 슬래시 오류로 성공 확인 전 |
| 테스트 | care·community·예약·AS 전체 API | 아직 실제 요청 테스트 필요 |
