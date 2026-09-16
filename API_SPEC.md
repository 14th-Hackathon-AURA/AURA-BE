# AURA Backend API Specification

모든 `/api/` 요청은 별도 표기가 없으면 JWT 인증이 필요합니다.

```http
Authorization: Bearer <access_token>
```

## 인증

- `POST /api/auth/register/` — `email`, `password`
- `POST /api/auth/token/` — `email`, `password`
- `POST /api/auth/token/refresh/` — `refresh`

로그인 ID는 이메일입니다. 닉네임은 온보딩 이후 표시 이름으로 사용하며 로그인 ID가 아닙니다.

## 프로필과 온보딩

- `GET /api/me/`
- `PATCH /api/me/`

필수 온보딩 값:

- `nickname`
- `gender`
- `age_range`
- `lifestyle`

선택값:

- `preferred_categories`
- `preferred_brands`
- `min_budget`, `max_budget`
- `phone`, `image`, `marketing_agreed`

`onboarding_completed=true`로 변경하려면 필수값이 모두 있어야 합니다. `membership_tier`는 읽기 전용이며 게시글·댓글 수로 계산합니다.

## 알림

- `GET /api/notifications/`
- `GET /api/notifications/{id}/`
- `PATCH /api/notifications/{id}/` — `{"is_read": true}`

필드: `type`, `title`, `body`, `action_url`, `is_read`, `created_at`

알림 종류는 `CARE`, `MEMBERSHIP`, `EVENT`, `GENERAL`입니다. 본인의 알림만 조회·수정할 수 있습니다.

자동 생성 사건:

- 진단 완료·실패
- 방문 예약 생성·상태 변경
- 멤버십 등급 상승

## 디지털 클로젯

- CRUD: `/api/products/`
- 이미지 CRUD: `/api/product-images/`

상품 필드:

- `name`, `brand`, `category`
- `purchased_at`, `purchase_place`
- `purchase_channel`: `ONLINE` 또는 `OFFLINE`
- `purchase_price`, `memo`
- `image`, `metadata`
- 읽기 전용: `passport_code`, `diagnosis_history`, `service_history`

이미지 `kind`:

- `PRODUCT`
- `RECEIPT`
- `WARRANTY`

수동 등록과 이미지 저장을 지원하며 다른 사용자의 제품 또는 제품 이미지에는 접근할 수 없습니다.

OCR 분석:

```http
POST /api/products/extract-document/
Content-Type: multipart/form-data
```

- `document`: JPG, JPEG, PNG 또는 PDF, 최대 4MB
- `document_type`: `receipt` 또는 `warranty`
- Azure 분석에 실패하거나 필드가 누락되면 `manual_input_required`로 직접 입력할 필드를 반환합니다.

## 케어 가이드

- `GET /api/care-guides/`
- `GET /api/care-guides/{id}/`
- 북마크: `GET/POST/DELETE /api/care-bookmarks/`

필터:

```http
GET /api/care-guides/?guide_type=POST_PURCHASE&material=가죽&category=bag&season=여름
```

`guide_type`:

- `BASIC` — 기본 관리
- `POST_PURCHASE` — 구매 직후 관리
- `AFTER_CARE` — 사후 케어

게시되지 않았거나 존재하지 않는 가이드는 북마크할 수 없습니다.

## AI 손상 진단

- `POST/GET /api/diagnoses/`
- `GET/PATCH/DELETE /api/diagnoses/{id}/`

생성은 `multipart/form-data`로 `product`, `image`를 전송합니다. 본인 상품의 진단만 생성하고 본인 기록만 조회·수정·삭제할 수 있습니다.

생성 직후 상태를 `PENDING`으로 저장한 뒤 OpenAI 멀티모달 비전 모델로 이미지를 분석합니다. 성공하면 `DONE`, 실패하면 `FAILED`로 자동 변경됩니다. 사진 또는 연결 상품을 수정하면 기존 결과를 초기화하고 다시 분석합니다.

필터:

```http
GET /api/diagnoses/?product=3&year=2026
```

결과 단계는 `SAFE`, `CAUTION`, `DANGER`이며 화면 표기는 안전·주의·위험입니다.

완료 응답의 주요 결과 필드:

- `condition_level`: `SAFE`, `CAUTION`, `DANGER`
- `damage_type`, `damage_description`
- `care_suggestion`
- `damage_location.points`: 이미지 위에 표시할 최대 2개의 `label`, `x_percent`, `y_percent`
- `result.damage_count`
- `result.analysis_method`: `ZERO_SHOT_MULTIMODAL`
- `result.is_reference_only`, `result.notice`

위치 좌표는 이미지 좌측 상단 `(0, 0)`부터 우측 하단 `(100, 100)`까지의 백분율입니다. 비전 모델의 제로샷 분석이므로 촬영 각도와 조명에 따라 결과가 달라질 수 있으며, 응답의 안내 문구와 함께 공식 AS 점검 경로를 제공해야 합니다.

## 공식 케어·방문 데모 흐름

- 매장 조회: `GET /api/stores/`, `GET /api/stores/{id}/`
- 방문 예약: CRUD `/api/visit-reservations/`
- 서비스 요청: CRUD `/api/service-requests/`

매장 목록은 다음 검색 조건을 지원합니다.

```http
GET /api/stores/?q=서울&latitude=37.5172&longitude=127.0473&limit=2
```

- `q`: 매장명·주소·시도·시군구·매장 유형·채널 검색
- `latitude`, `longitude`: 현재 위치이며 반드시 함께 전달
- `limit`: 1~100개의 결과 제한

매장 목록 응답은 배열이 아니라 다음 객체 형태입니다.

```json
{
  "count": 2,
  "search": "서울",
  "location_used": true,
  "stores": [
    {
      "id": 1,
      "name": "청담 공식 AS 센터",
      "distance_km": 1.8,
      "map_search_url": "https://map.naver.com/p/search/..."
    }
  ]
}
```

방문 예약은 필수 `store`, 필수 `product`, `visit_at`, `purpose`와 선택
`diagnosis`, `contact_name`, `contact_phone`, `request_note`를 저장합니다.
서비스 요청은 본인 상품과 본인 방문 예약만 연결할 수 있습니다.

이는 AURA 내부 데모 흐름이며 실제 브랜드 AS 시스템과 직접 연동하지 않습니다.

## 커뮤니티

### 게시글

CRUD: `/api/posts/`

응답에는 작성자 닉네임·멤버십 등급, 다중 이미지, 댓글, 좋아요 수, 내 좋아요 여부와 상품 태그가 포함됩니다.

상품 태그 입력은 `tagged_products`에 본인 상품 ID 목록을 전송합니다. 표시용 `tagged_product_cards`는 다음 형태입니다.

```json
[
  {
    "id": 3,
    "name": "모노그램 숄더백",
    "brand": "MCM"
  }
]
```

내부 관계 식별을 위한 `id` 외 표시 정보는 제품 이름과 브랜드만 제공합니다.

### 게시글 이미지

CRUD: `/api/post-images/`

`multipart/form-data`로 `post`, `image`, `order`를 전송합니다. 본인 게시글에만 이미지를 추가·수정·삭제할 수 있습니다.

### 댓글과 좋아요

- 댓글 CRUD: `/api/comments/`
- 좋아요 목록·생성·삭제: `/api/post-likes/`

게시글과 댓글은 작성자만 수정·삭제할 수 있고 한 사용자는 같은 게시글에 중복 좋아요할 수 없습니다.

## AI 상품 상담

### 대화 및 추천

```http
POST /api/ai/chat/
```

새 상담 요청:

```json
{
  "message": "200만원 이하 출근용 가방 추천해줘"
}
```

기존 상담 이어가기:

```json
{
  "session_id": 1,
  "message": "검은색 제품으로 다시 추천해줘"
}
```

응답의 `recommended_products`에는 최대 3개의 MCM 상품이 포함됩니다. 제공 필드는 `style_code`, `name`, `gender`, `category`, `material`, `size`, `color`, `price`, `price_value`, `style`, `usage`, `image_url`입니다.

서버가 받은 94개 MCM 상품 데이터에서 후보를 먼저 검색한 뒤 그 후보만 AI 답변 근거로 사용합니다. 목록에 없는 상품 정보나 모델이 임의 생성한 식별자는 카드 응답에 사용하지 않습니다.

### 상담 기록

- 목록·상세: `GET /api/ai/chat-sessions/`, `GET /api/ai/chat-sessions/{id}/`
- 제목 수정: `PATCH /api/ai/chat-sessions/{id}/`
- 삭제: `DELETE /api/ai/chat-sessions/{id}/`

본인의 상담 기록과 메시지만 조회할 수 있습니다.

### AI 방문 카드

직전 추천 중 하나를 대화로 저장:

```json
{
  "session_id": 1,
  "message": "이 제품 카드로 저장해줘",
  "product_code": "MWTGATA01CO001"
}
```

`product_code`를 생략하면 직전 추천의 첫 번째 상품을 저장합니다.

- 목록·상세: `GET /api/ai/visit-cards/`, `GET /api/ai/visit-cards/{id}/`
- 직접 저장: `POST /api/ai/visit-cards/` with `style_code`, 선택 `session_id`
- 삭제: `DELETE /api/ai/visit-cards/{id}/`

같은 사용자가 같은 상품을 다시 저장하면 중복 카드를 만들지 않고 기존 카드를 갱신합니다. 본인의 카드만 조회·삭제할 수 있습니다.

응답의 `consultation_summary`는 서버가 상담에서 사용자가 말한 색상·사이즈·착용 상황·예산 등의 니즈와 선택한 상품 정보를 OpenAI에 전달해 2~4문장·300자 이내의 개인화된 방문 카드 문구로 생성합니다. AI 추천 답변 원문, 여러 상품 목록, Markdown 및 이미지 URL은 저장하지 않습니다. 클라이언트가 보낸 `consultation_summary` 값은 저장에 사용하지 않습니다. 요약 생성에 실패해도 방문 카드는 정상적으로 저장되며 `consultation_summary`에는 `상담 요약을 생성하지 못했습니다. 잠시 후 카드를 다시 저장해 주세요.`가 저장됩니다.

## 현재 별도 작업

- 실제 CV 손상 판독
- 외부 브랜드 AS 연동
- 실제 멤버십 결제
