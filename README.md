# AURA Backend

AURA 최종 와이어프레임과 확정된 팀 결정을 기준으로 한 Django REST Framework 백엔드입니다.

현재 백엔드는 일반 기능과 영수증·보증서 OCR, MCM 상품 추천 AI 챗봇, 제로샷 멀티모달 이미지 손상 진단을 지원합니다.

## 확정된 서비스 정책

- 로그인 ID는 이메일이며 회원가입과 로그인에서 이메일·비밀번호만 입력합니다.
- 온보딩 필수값은 닉네임·성별·나이대·활동 상황입니다. 관심 카테고리와 예산은 선택값입니다.
- 멤버십 포인트와 실제 결제는 없습니다.
- 멤버십 등급은 게시글 수와 댓글 수를 각각 모두 충족하면 Silver → Gold(50/50) → Platinum(100/100) → Diamond(200/200)로 올라갑니다.
- 커뮤니티 게시글에는 본인 클로젯 제품만 태그할 수 있으며 표시 정보는 제품명과 브랜드입니다.
- 제품 등록은 수동 입력이 가능하며 온라인·오프라인 구매 채널을 구분합니다. 영수증·보증서 OCR이 실패하거나 값이 누락되면 직접 입력할 필드를 반환합니다.
- 손상 진단 결과는 안전·주의·위험 3단계를 사용하며 사진 등록 후 자동으로 분석합니다.
- 공식 센터 및 방문 예약 기능은 AURA 내부 데모 흐름만 제공합니다.
- 브랜드 외부 AS 시스템 및 실제 매장 예약 시스템과 직접 연동하지 않습니다.
- AS 방문 예약 가능 시간은 오전 10시부터 오후 6시까지이며 마지막 예약 가능 시간은 오후 5시 30분입니다.
- AS 방문 예약은 30분 단위로 생성할 수 있습니다.
- 같은 매장과 같은 시간에는 하나의 활성 예약만 존재할 수 있습니다.

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
| POST | `/api/products/extract-document/` | Azure 영수증·보증서 OCR |
| GET | `/api/care-guides/` | 기본·구매 직후·사후 케어 가이드 |
| GET/POST/DELETE | `/api/care-bookmarks/` | 케어 가이드 북마크 |
| CRUD | `/api/diagnoses/` | 진단 요청·이력·수정·삭제 |
| GET | `/api/stores/` | 공식 케어 매장 목록·상세 |
| CRUD | `/api/visit-reservations/` | 내부 방문 예약 흐름 |
| GET | `/api/visit-reservations/availability/` | 매장과 날짜별 예약 가능 시간 조회 |
| POST | `/api/visit-reservations/{id}/cancel/` | AS 방문 예약 취소 |
| CRUD | `/api/service-requests/` | 내부 서비스 요청 흐름 |
| CRUD | `/api/posts/` | 커뮤니티 게시글·상품 태그 |
| CRUD | `/api/post-images/` | 게시글 다중 이미지 |
| CRUD | `/api/comments/` | 댓글 |
| GET/POST/DELETE | `/api/post-likes/` | 좋아요·취소 |
| POST | `/api/ai/chat/` | MCM 상품 상담·조건별 추천·카드 저장 대화 |
| GET/PATCH/DELETE | `/api/ai/chat-sessions/` | 내 상담 기록 |
| GET/POST/DELETE | `/api/ai/visit-cards/` | AI 방문 카드 목록·저장·상세·삭제 |
| POST | `/api/ai/care-recommendations/` | 사용자 제품 기반 AI 케어 추천 요청 |

세부 요청·응답은 [`API_SPEC.md`](API_SPEC.md)를 참고하세요.

## AI 상품 상담

- 제공받은 MCM 상품 94개의 상품명·카테고리·소재·사이즈·색상·가격·이미지·스타일·사용 상황을 검색 근거로 사용합니다.
- 사용자 문장과 온보딩의 예산·관심 카테고리·활동 상황을 반영해 최대 3개의 후보를 조회한 뒤 OpenAI Responses API에 전달합니다.
- 모델이 만든 상품 식별자를 신뢰하지 않고 서버가 조회한 상품만 `recommended_products`로 반환합니다.
- 상담 후 “카드로 저장해줘”라고 요청하면 직전 추천 상품을 AI 방문 카드로 저장하고, 사용자가 말한 니즈와 선택 상품이 맞는 이유를 2~4문장·300자 이내의 개인화된 문구로 요약합니다. 요약 생성에 실패하면 `상담 요약을 생성하지 못했습니다. 잠시 후 카드를 다시 저장해 주세요.`를 표시합니다.
- 실제 AI 답변을 사용하려면 `.env`의 `OPENAI_API_KEY`가 필요합니다.

## AI 손상 진단

- 사용자가 본인 클로젯 제품과 사진을 등록하면 OpenAI 멀티모달 비전 모델이 이미지를 제로샷으로 분석합니다.
- 진단 상태는 생성 시 `PENDING`이며 분석 성공 시 `DONE`, 실패 시 `FAILED`로 자동 변경됩니다.
- 결과는 안전·주의·위험 3단계와 손상 유형·설명·관리 제안으로 제공합니다.
- 사진 위 표시를 위해 가장 중요한 손상 위치를 최대 2개의 백분율 좌표로 반환합니다.
- 사진 또는 연결 상품을 수정하면 이전 결과를 초기화하고 다시 분석합니다.
- 결과는 참고용이며 촬영 각도와 조명에 따라 달라질 수 있으므로 공식 AS 점검 안내를 함께 제공합니다.
- 별도 학습 데이터로 훈련한 탐지 모델이 아니라 사전 학습 멀티모달 모델의 제로샷 분석입니다.

## AS 방문 예약

AI 케어 진단 결과 화면에서 공식 AS 센터 방문 예약을 생성할 수 있습니다.

방문 예약은 사용자 소유 제품, AI 진단 결과, 공식 케어 매장을 연결합니다. AI 진단 결과가 없는 경우에도 본인 제품을 직접 선택해 예약할 수 있습니다.

### 예약 입력 항목

| 필드 | 필수 여부 | 설명 |
|---|---|---|
| `product` | 필수 | 예약할 사용자 소유 제품 ID |
| `diagnosis` | 선택 | 예약과 연결할 AI 진단 결과 ID |
| `store` | 필수 | 방문할 공식 케어 매장 ID |
| `visit_at` | 필수 | 방문 예정 일시 |
| `purpose` | 필수 | 제품 증상 또는 방문 목적 |
| `contact_name` | 선택 | 예약자 이름 |
| `contact_phone` | 선택 | 예약자 연락처 |
| `request_note` | 선택 | 매장에 전달할 추가 요청사항 |

### 예약 검증 규칙

서버는 AS 방문 예약 생성 및 수정 시 다음 규칙을 검증합니다.

- 본인이 소유한 제품만 예약할 수 있습니다.
- AS를 지원하는 공식 케어 매장만 예약할 수 있습니다.
- AI 진단 결과를 연결할 경우 본인의 진단 결과만 사용할 수 있습니다.
- AI 진단 상태가 `DONE`인 완료된 진단만 예약에 연결할 수 있습니다.
- AI 진단 제품과 예약 제품이 일치해야 합니다.
- 현재 이후의 방문 일시만 예약할 수 있습니다.
- 예약은 정각 또는 30분 단위로만 생성할 수 있습니다.
- 예약 가능 시간은 오전 10시부터 오후 6시까지입니다.
- 마지막 예약 가능 시간은 오후 5시 30분입니다.
- 같은 매장과 같은 시간에는 하나의 활성 예약만 생성할 수 있습니다.
- 취소된 예약의 시간은 다시 예약할 수 있습니다.
- 예약 생성 시 고유한 8자리 `reservation_code`가 자동 발급됩니다.
- 사용자는 본인의 예약만 조회·수정·삭제·취소할 수 있습니다.

현재 운영시간은 모든 매장에 오전 10시부터 오후 6시까지 공통으로 적용됩니다. `Store.opening_hours`는 매장 운영시간 표시용 문자열이며 예약 시간 계산에는 사용하지 않습니다.

## 공식 케어 매장 조회

AS 예약에 사용할 공식 케어 매장 목록을 조회합니다.

```http
GET /api/stores/
Authorization: Bearer {access_token}
```

AS를 지원하는 `supports_as=true` 매장만 반환합니다.

매장명·주소·지역·매장 유형은 `q`로 검색할 수 있습니다. 현재 위치의
위도와 경도를 함께 전달하면 가까운 매장부터 정렬되며, `limit`으로 반환
개수를 제한할 수 있습니다.

```http
GET /api/stores/?q=서울&latitude=37.5172&longitude=127.0473&limit=2
Authorization: Bearer {access_token}
```

- `latitude`와 `longitude`는 반드시 함께 전달합니다.
- `limit`은 1부터 100까지 사용할 수 있습니다.
- 좌표가 없는 매장은 거리순 목록의 마지막에 표시됩니다.

응답 예시:

```json
{
  "count": 1,
  "search": "서울",
  "location_used": true,
  "stores": [
    {
      "id": 1,
      "name": "청담 공식 AS 센터",
      "address": "서울특별시 강남구 압구정로 123",
      "phone": "02-1234-5678",
      "latitude": "37.5250000",
      "longitude": "127.0400000",
      "opening_hours": "월-토 10:00-18:00",
      "supports_as": true,
      "distance_km": 1.8,
      "map_search_url": "https://map.naver.com/p/search/..."
    }
  ]
}
```

매장 API는 조회 전용입니다. MCM 매장 CSV는 `import_mcm_stores` 관리 명령으로
등록하며, 좌표 생성이 필요하면 `--geocode`와 Kakao REST API 키를 사용합니다.

## 예약 가능 시간 조회

선택한 매장과 날짜를 기준으로 예약 가능한 시간을 30분 단위로 조회합니다.

```http
GET /api/visit-reservations/availability/?store={store_id}&date={YYYY-MM-DD}
Authorization: Bearer {access_token}
```

요청 예시:

```http
GET /api/visit-reservations/availability/?store=1&date=2026-08-20
Authorization: Bearer {access_token}
```

응답 예시:

```json
{
  "store": {
    "id": 1,
    "name": "청담 공식 AS 센터"
  },
  "date": "2026-08-20",
  "slots": [
    {
      "visit_at": "2026-08-20T10:00:00+09:00",
      "time": "10:00",
      "available": true
    },
    {
      "visit_at": "2026-08-20T10:30:00+09:00",
      "time": "10:30",
      "available": false
    }
  ]
}
```

`available=false`인 시간은 해당 매장에 활성 예약이 존재하므로 예약할 수 없습니다.

다음 경우 HTTP `400 Bad Request`를 반환합니다.

- `store`가 누락된 경우
- `date`가 누락된 경우
- 날짜가 `YYYY-MM-DD` 형식이 아닌 경우
- 지난 날짜를 조회한 경우
- 존재하지 않는 매장을 조회한 경우
- AS를 지원하지 않는 매장을 조회한 경우

## AS 방문 예약 생성

```http
POST /api/visit-reservations/
Authorization: Bearer {access_token}
Content-Type: application/json
```

요청 예시:

```json
{
  "diagnosis": 12,
  "product": 4,
  "store": 2,
  "visit_at": "2026-08-20T14:30:00+09:00",
  "purpose": "가방 표면의 얼룩과 스크래치",
  "contact_name": "홍길동",
  "contact_phone": "010-1234-5678",
  "request_note": "AI 진단 결과를 바탕으로 제품 점검을 요청합니다."
}
```

AI 진단 결과를 연결하지 않을 경우 `diagnosis`를 생략하거나 `null`로 전송할 수 있습니다.

```json
{
  "product": 4,
  "store": 2,
  "visit_at": "2026-08-20T14:30:00+09:00",
  "purpose": "제품 상태 점검",
  "contact_name": "홍길동",
  "contact_phone": "010-1234-5678",
  "request_note": ""
}
```

예약 생성에 성공하면 HTTP `201 Created`를 반환합니다.

응답 예시:

```json
{
  "id": 7,
  "product_name": "비세토스 숄더백",
  "store_name": "청담 공식 AS 센터",
  "reservation_code": "A1B2C3D4",
  "status": "RESERVED",
  "visit_at": "2026-08-20T14:30:00+09:00",
  "purpose": "가방 표면의 얼룩과 스크래치",
  "contact_name": "홍길동",
  "contact_phone": "010-1234-5678",
  "request_note": "AI 진단 결과를 바탕으로 제품 점검을 요청합니다.",
  "diagnosis": 12,
  "product": 4,
  "store": 2,
  "user": 1,
  "created_at": "2026-08-16T15:30:00+09:00"
}
```

프론트엔드는 HTTP `201 Created` 응답을 받으면 `reservation_code`, 매장명, 방문일시를 이용해 예약 완료 팝업을 표시할 수 있습니다.

### 운영시간 외 예약 오류

오전 10시 이전 또는 오후 6시 이후로 예약을 요청하면 HTTP `400 Bad Request`를 반환합니다.

정확히 오후 6시인 예약도 생성할 수 없습니다.

```json
{
  "visit_at": [
    "예약 가능 시간은 오전 10시부터 오후 6시까지입니다."
  ]
}
```

### 예약 단위 오류

정각 또는 30분 단위가 아닌 시간을 요청하면 HTTP `400 Bad Request`를 반환합니다.

```json
{
  "visit_at": [
    "예약은 30분 단위로 선택해 주세요."
  ]
}
```

### 중복 예약 오류

같은 매장과 같은 시간에 활성 예약이 존재하면 HTTP `400 Bad Request`를 반환합니다.

```json
{
  "visit_at": [
    "이미 예약된 방문 시간입니다."
  ]
}
```

중복 예약은 serializer 검증과 데이터베이스 고유성 제약을 통해 이중으로 방지합니다.

## 예약 목록 조회

현재 로그인한 사용자의 예약 목록을 방문 예정일 역순으로 조회합니다.

```http
GET /api/visit-reservations/
Authorization: Bearer {access_token}
```

다른 사용자의 예약은 반환되지 않습니다.

## 예약 상세 조회

```http
GET /api/visit-reservations/{reservation_id}/
Authorization: Bearer {access_token}
```

본인의 예약만 조회할 수 있습니다. 다른 사용자의 예약 ID로 요청하면 HTTP `404 Not Found`를 반환합니다.

## 예약 수정

```http
PATCH /api/visit-reservations/{reservation_id}/
Authorization: Bearer {access_token}
Content-Type: application/json
```

요청 예시:

```json
{
  "visit_at": "2026-08-21T15:00:00+09:00",
  "request_note": "방문 전에 연락 부탁드립니다."
}
```

예약 수정 시에도 제품 소유권, 진단 소유권, 운영시간 및 중복 예약 검증이 동일하게 적용됩니다.

다음 필드는 API 요청으로 직접 변경할 수 없습니다.

- `user`
- `reservation_code`
- `status`
- `created_at`

## 예약 취소

예약 상태가 `RESERVED`인 본인의 미래 예약을 취소합니다.

```http
POST /api/visit-reservations/{reservation_id}/cancel/
Authorization: Bearer {access_token}
```

요청 본문은 필요하지 않습니다.

성공 응답 예시:

```json
{
  "id": 7,
  "product_name": "비세토스 숄더백",
  "store_name": "청담 공식 AS 센터",
  "reservation_code": "A1B2C3D4",
  "status": "CANCELLED",
  "visit_at": "2026-08-20T14:30:00+09:00",
  "diagnosis": 12,
  "product": 4,
  "store": 2
}
```

다음 경우 예약을 취소할 수 없습니다.

- 이미 취소된 예약
- 완료된 예약
- 방문 시간이 지난 예약
- 다른 사용자의 예약

## 예약 삭제

```http
DELETE /api/visit-reservations/{reservation_id}/
Authorization: Bearer {access_token}
```

본인의 예약만 삭제할 수 있습니다.

예약 이력을 유지해야 하는 운영 환경에서는 삭제 API보다 예약 취소 API 사용을 권장합니다.

## 예약 상태

| 값 | 설명 |
|---|---|
| `RESERVED` | 예약 완료 및 방문 대기 |
| `CANCELLED` | 사용자 또는 관리자가 예약 취소 |
| `COMPLETED` | 방문 및 AS 처리 완료 |

## 테스트용 공식 케어 매장 등록

`Store` API는 조회 전용이므로 테스트용 매장은 Django 관리자 페이지 또는 Django shell에서 등록합니다.

### 관리자 페이지에서 등록

관리자 계정을 생성합니다.

```bash
python manage.py createsuperuser
```

개발 서버를 실행합니다.

```bash
python manage.py runserver
```

다음 주소로 접속합니다.

```text
http://127.0.0.1:8000/admin/
```

`Stores` 메뉴에서 다음과 같이 테스트 매장을 생성합니다.

```text
Name: 청담 공식 AS 센터
Address: 서울특별시 강남구 압구정로 123
Phone: 02-1234-5678
Latitude: 37.525000
Longitude: 127.040000
Opening hours: 월-토 10:00-18:00
Supports as: 체크
```

관리자 페이지에 `Stores` 메뉴가 보이지 않는 경우 `apps/care/admin.py`에 `Store` 모델이 등록되어 있는지 확인해야 합니다.

### Django shell에서 등록

```bash
python manage.py shell
```

```python
from apps.care.models import Store

Store.objects.create(
    name="청담 공식 AS 센터",
    address="서울특별시 강남구 압구정로 123",
    phone="02-1234-5678",
    latitude=37.525000,
    longitude=127.040000,
    opening_hours="월-토 10:00-18:00",
    supports_as=True,
)
```
## 자동 알림

서버 규칙으로 다음 사건의 알림을 중복 없이 생성합니다.

- 진단 상태가 `DONE` 또는 `FAILED`로 변경됨
- 방문 예약이 생성됨
- 방문 예약 상태가 변경됨
- 게시글 수와 댓글 수가 모두 기준에 도달해 멤버십 등급이 상승함

알림 이동 경로는 다음 환경변수로 프론트엔드 라우트에 맞출 수 있습니다.

```env
FRONTEND_DIAGNOSIS_PATH_TEMPLATE=/care/diagnoses/{id}
FRONTEND_VISIT_PATH_TEMPLATE=/my/visit-reservations/{id}
FRONTEND_MEMBERSHIP_PATH=/my/membership
```

## 로컬 실행

가상환경을 생성하고 활성화합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
```

필요한 패키지와 환경설정을 준비합니다.

```bash
pip install -r requirements.txt
copy .env.example .env
```

데이터베이스 마이그레이션을 적용합니다.

```bash
python manage.py migrate
```

개발 서버를 실행합니다.

```bash
python manage.py runserver
```

Windows 환경에서 `python` 명령을 찾지 못하는 경우 `python` 대신 `py`를 사용할 수 있습니다.

```bash
py manage.py migrate
py manage.py runserver
```

## AS 예약 모델 변경 반영

`VisitReservation` 모델에 AI 진단 연결 필드와 중복 예약 방지 제약을 추가한 경우 마이그레이션을 생성하고 적용해야 합니다.

```bash
python manage.py makemigrations care
python manage.py migrate
```

마이그레이션 파일이 이미 저장소에 포함돼 있다면 다음 명령만 실행합니다.

```bash
python manage.py migrate
```

## 검증 및 테스트

프로젝트 설정을 검사합니다.

```bash
python manage.py check
```

적용되지 않은 모델 변경이 있는지 검사합니다.

```bash
python manage.py makemigrations --check
```

전체 테스트를 실행합니다.

```bash
python manage.py test
```

케어 앱 테스트만 실행하려면 다음 명령을 사용합니다.

```bash
python manage.py test apps.care
```

AS 방문 예약에서는 다음 항목을 확인해야 합니다.

- 정상적인 AS 예약 생성
- 예약번호 자동 발급
- 본인 제품 예약
- 다른 사용자의 제품 예약 차단
- 완료된 AI 진단 결과 연결
- 다른 사용자의 진단 결과 연결 차단
- 완료되지 않은 진단 결과 연결 차단
- 진단 제품과 예약 제품 불일치 차단
- AS 미지원 매장 예약 차단
- 지난 날짜 및 시간 예약 차단
- 30분 단위가 아닌 시간 예약 차단
- 오전 10시 이전 예약 차단
- 오후 6시 이후 예약 차단
- 같은 매장과 같은 시간의 중복 예약 차단
- 날짜별 예약 가능 시간 조회
- 이미 예약된 시간의 `available=false` 처리
- 정상 예약 취소
- 이미 취소된 예약의 재취소 차단
- 취소된 시간의 재예약
- 다른 사용자의 예약 조회 및 취소 차단

## 별도 작업 범위

- 실제 브랜드 AS 및 매장 시스템 연동
- 매장별 영업시간·휴무일·공휴일 관리
- 실제 멤버십 결제

이 기능들은 현재 데이터 및 API 연결 지점을 이용해 후속 브랜치에서 구현합니다.
