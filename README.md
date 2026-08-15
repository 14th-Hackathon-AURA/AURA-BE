# AURA Backend

AURA 최종 와이어프레임과 확정된 팀 결정을 기준으로 한 Django REST Framework 백엔드입니다.

현재 작업 범위는 **영수증 OCR 추출, AI 챗봇 고도화, 실제 사진 손상 판독을 제외한 일반 백엔드 기능**입니다. 세 기능의 업로드·저장·연결 지점은 유지하지만 실제 AI 추론이 완료되었다고 간주하지 않습니다.

## 확정된 서비스 정책

- 로그인 ID는 이메일이며 회원가입과 로그인에서 이메일·비밀번호만 입력합니다.
- 온보딩 필수값은 닉네임·성별·나이대·활동 상황입니다. 관심 카테고리와 예산은 선택값입니다.
- 멤버십 포인트와 실제 결제는 없습니다.
- 멤버십 등급은 게시글 수와 댓글 수를 각각 모두 충족하면 Silver → Gold(50/50) → Platinum(100/100) → Diamond(200/200)로 올라갑니다.
- 커뮤니티 게시글에는 본인 클로젯 제품만 태그할 수 있으며 표시 정보는 제품명과 브랜드입니다.
- 제품 등록은 수동 입력이 가능하며 온라인·오프라인 구매 채널을 구분합니다. OCR은 온라인 영수증/보증서 이미지 저장 이후 연결할 별도 작업입니다.
- 손상 진단 결과는 안전·주의·위험 3단계를 사용합니다. 실제 이미지 판독은 별도 작업입니다.
- 공식 센터/방문 기능은 AURA 내부 데모 흐름만 제공합니다. 브랜드 외부 AS 시스템과 직접 연동하지 않습니다.

## 주요 API

모든 `/api/` 요청은 별도 표기가 없으면 JWT 인증이 필요합니다.

| Method | Endpoint | 설명 |
|---|---|---|
| POST | `/api/auth/register/` | 이메일·비밀번호 회원가입 |
| POST | `/api/auth/token/` | JWT 로그인 |
| POST | `/api/auth/token/refresh/` | 토큰 갱신 |
| GET/PATCH | `/api/me/` | 프로필·온보딩·멤버십 등급 |
| GET/PATCH | `/api/notifications/` | 알림 목록·상세·읽음 처리 |
| CRUD | `/api/products/` | 내 클로젯 제품 |
| CRUD | `/api/product-images/` | 제품·영수증·보증서 이미지 |
| GET | `/api/care-guides/` | 기본·구매 직후·사후 케어 가이드 |
| GET/POST/DELETE | `/api/care-bookmarks/` | 케어 가이드 북마크 |
| CRUD | `/api/diagnoses/` | 진단 요청·이력·수정·삭제 |
| GET | `/api/stores/` | 공식 케어 매장 목록·상세 |
| CRUD | `/api/visit-reservations/` | 내부 방문 예약 흐름 |
| CRUD | `/api/service-requests/` | 내부 서비스 요청 흐름 |
| CRUD | `/api/posts/` | 커뮤니티 게시글·상품 태그 |
| CRUD | `/api/post-images/` | 게시글 다중 이미지 |
| CRUD | `/api/comments/` | 댓글 |
| GET/POST/DELETE | `/api/post-likes/` | 좋아요·취소 |

세부 요청·응답은 [`API_SPEC.md`](API_SPEC.md)를 참고하세요.

## 자동 알림

서버 규칙으로 다음 사건의 알림을 중복 없이 생성합니다.

- 진단 상태가 `DONE` 또는 `FAILED`로 변경됨
- 방문 예약이 생성되거나 상태가 변경됨
- 게시글 수와 댓글 수가 모두 기준에 도달하여 멤버십 등급이 상승함

알림 이동 경로는 다음 환경변수로 프론트 라우트에 맞출 수 있습니다.

```env
FRONTEND_DIAGNOSIS_PATH_TEMPLATE=/care/diagnoses/{id}
FRONTEND_VISIT_PATH_TEMPLATE=/my/visit-reservations/{id}
FRONTEND_MEMBERSHIP_PATH=/my/membership
```

## 로컬 실행

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

검증:

```bash
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

## 별도 작업 범위

- 온라인 영수증·보증서 OCR 추출
- AI 챗봇의 상품 추천·RAG·방문 준비 카드
- 실제 CV 사진 판독과 `PENDING → DONE/FAILED` 자동 처리
- 실제 브랜드 AS/매장 시스템 연동
- 실제 멤버십 결제

이 기능들은 현재 데이터/API 연결 지점을 이용해 후속 브랜치에서 구현합니다.
